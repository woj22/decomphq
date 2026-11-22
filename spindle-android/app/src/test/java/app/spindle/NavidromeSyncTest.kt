package app.spindle

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Test
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.nio.file.Files

/**
 * Runs the app's sync code against a real Navidrome server.
 * Set SPINDLE_TEST_SERVER, SPINDLE_TEST_USER and SPINDLE_TEST_PASSWORD to run it; it is skipped otherwise.
 * The server's library is expected to contain no playlists or favourites made by other tests.
 */
class NavidromeSyncTest {
    private val server = System.getenv("SPINDLE_TEST_SERVER")
    private lateinit var client: SubsonicClient
    private lateinit var dir: File
    private lateinit var pending: PendingOps
    private lateinit var pins: Pins

    @Before fun setUp() {
        assumeTrue("set SPINDLE_TEST_SERVER to run", server != null)
        client = SubsonicClient(Credentials.fromPassword(server!!, System.getenv("SPINDLE_TEST_USER"), System.getenv("SPINDLE_TEST_PASSWORD")))
        dir = Files.createTempDirectory("spindle").toFile()
        pending = PendingOps(File(dir, "pending.json"))
        pins = Pins(File(dir, "pins.json"))
    }

    private fun sync(c: Catalog, full: Boolean = false) = LibrarySync(client, pending, pins).run(c, full) {}

    @Test fun wrongPasswordIsReportedAsBadLogin() {
        val bad = SubsonicClient(Credentials.fromPassword(server!!, System.getenv("SPINDLE_TEST_USER"), "nope"))
        val e = runCatching { bad.ping() }.exceptionOrNull() as SubsonicException
        assertEquals(SubsonicException.Kind.BadLogin, e.kind)
    }

    @Test fun unreachableServerIsReportedAsUnreachable() {
        val off = SubsonicClient(Credentials.fromPassword("http://127.0.0.1:1", "a", "b"))
        val e = runCatching { off.ping() }.exceptionOrNull() as SubsonicException
        assertEquals(SubsonicException.Kind.Unreachable, e.kind)
    }

    @Test fun fullSyncThenCatalogueSurvivesSaveAndLoad() {
        val r = sync(Catalog(), full = true)
        val c = r.catalog
        assertTrue("songs", c.songs.isNotEmpty())
        assertTrue("albums", c.albums.isNotEmpty())
        assertTrue("artists", c.artists.isNotEmpty())
        assertEquals(c.albums.sumOf { it.songCount }, c.songs.size)
        c.songs.forEach { s -> assertTrue("album ${s.albumId} for ${s.title}", c.albums.any { it.id == s.albumId }) }

        val store = CatalogStore(File(dir, "catalog"))
        store.save(c)
        val back = store.load()
        assertEquals(c.songs.map { it.id }, back.songs.map { it.id })
        assertEquals(c.albums.map { it.signature }, back.albums.map { it.signature })
        assertEquals(c.playlists, back.playlists)
        assertEquals(c.lastScan, back.lastScan)
        println("Full sync: ${r.summary}; ${c.songs.size} songs, ${c.albums.size} albums, ${c.artists.size} artists")
    }

    @Test fun secondSyncWithNoChangesFetchesNothingNew() {
        val first = sync(Catalog(), full = true).catalog
        val second = sync(first)
        assertEquals("Library is up to date", second.summary)
        assertEquals(first.songs.map { it.id }.toSet(), second.catalog.songs.map { it.id }.toSet())
    }

    @Test fun incrementalSyncSeesOnlyTheChangedAlbum() {
        val base = sync(Catalog(), full = true).catalog
        // Make one album look out of date and drop its songs locally; an incremental sync must restore exactly that album.
        val victim = base.albums.first()
        val stale = base.copy(
            albums = base.albums.map { if (it.id == victim.id) it.copy(songCount = 0) else it },
            songs = base.songs.filterNot { it.albumId == victim.id },
        )
        val r = sync(stale)
        assertEquals(base.songs.map { it.id }.toSet(), r.catalog.songs.map { it.id }.toSet())
        assertTrue(r.summary, r.summary.contains("new song") && r.summary.contains("1 album updated"))
        println("Incremental: ${r.summary}")
    }

    @Test fun likesMadeOfflineReachTheServerLater() {
        val c = sync(Catalog(), full = true).catalog
        val song = c.songs.last()
        if (song.id in c.likes) client.unstar(song.id)

        // Offline: the change is queued, and a sync attempt against an unreachable server keeps it.
        pending.add(PendingOps.star(song.id))
        val offline = SubsonicClient(Credentials.fromPassword("http://127.0.0.1:1", "a", "b"))
        runCatching { LibrarySync(offline, pending, pins).flushPending(c) }
        assertFalse("kept while offline", pending.isEmpty())

        val r = sync(c)
        assertTrue("pending sent", pending.isEmpty())
        assertTrue("server has the like", song.id in client.starredSongIds())
        assertTrue("catalogue has the like", song.id in r.catalog.likes)

        // Like then unlike before syncing collapses to just the unlike.
        pending.add(PendingOps.star(song.id)); pending.add(PendingOps.unstar(song.id))
        assertEquals(1, pending.snapshot().size)
        sync(r.catalog)
        assertFalse(song.id in client.starredSongIds())
    }

    @Test fun playlistMadeOfflineIsCreatedOnceWithItsEdits() {
        val c = sync(Catalog(), full = true).catalog
        val songs = c.songs.take(3).map { it.id }
        val local = Playlist(Playlist.LOCAL_PREFIX + "test", "Offline mix", listOf(songs[0]))
        pending.add(PendingOps.playlistSave(local, isNew = true))
        pending.add(PendingOps.playlistSave(local.copy(songIds = songs), isNew = false)) // added songs before it synced
        pending.add(PendingOps.playlistRename(local.id, "Weekend mix"))
        pins.set(Pins.playlist(local.id), true)
        assertEquals(1, pending.snapshot().size)

        val r = sync(c.copy(playlists = c.playlists + local))
        assertTrue(pending.isEmpty())
        val onServer = client.playlists().filter { it.name == "Weekend mix" }
        assertEquals("created exactly once", 1, onServer.size)
        val id = onServer.single().id
        assertEquals(songs, client.playlistSongs(id).map { it.id })
        assertTrue("local copy uses the server id", r.catalog.playlists.any { it.id == id && it.songIds == songs })
        assertFalse(r.catalog.playlists.any { it.isLocalOnly })
        assertTrue("download choice follows the new id", pins.has(Pins.playlist(id)))
        assertEquals(songs.toSet(), pins.wantedSongs(r.catalog))

        // Removing every song, then deleting.
        pending.add(PendingOps.playlistSave(Playlist(id, "Weekend mix", emptyList()), isNew = false))
        sync(r.catalog)
        assertEquals(0, client.playlistSongs(id).size)
        pending.add(PendingOps.playlistDelete(id))
        val after = sync(r.catalog)
        assertFalse(client.playlists().any { it.id == id })
        assertFalse(after.catalog.playlists.any { it.id == id })
    }

    @Test fun playlistEditedOnServerIsPickedUpAndUnchangedOnesAreReused() {
        val c = sync(Catalog(), full = true).catalog
        val id = client.savePlaylist(null, "Server side", listOf(c.songs[0].id))
        val r1 = sync(c).catalog
        assertEquals(listOf(c.songs[0].id), r1.playlists.single { it.id == id }.songIds)
        Thread.sleep(1100)
        client.savePlaylist(id, null, listOf(c.songs[0].id, c.songs[1].id))
        val r2 = sync(r1).catalog
        assertEquals(listOf(c.songs[0].id, c.songs[1].id), r2.playlists.single { it.id == id }.songIds)
        client.deletePlaylist(id)
    }

    @Test fun playsRecordedOfflineKeepTheirTime() {
        val c = sync(Catalog(), full = true).catalog
        val song = c.songs.first()
        val before = c.songs.first { it.id == song.id }.playCount
        val when_ = System.currentTimeMillis() - 3_600_000
        pending.add(PendingOps.scrobble(song.id, when_))
        val r = sync(c).catalog
        val after = r.songs.first { it.id == song.id }
        assertEquals(before + 1, after.playCount)
        assertTrue("play time kept (within a minute)", kotlin.math.abs(after.played - when_) < 60_000)
    }

    @Test fun streamAndCoverAddressesServeMedia() {
        val c = sync(Catalog(), full = true).catalog
        val s = c.songs.first()
        fun head(u: String): Pair<Int, String?> = (URL(u).openConnection() as HttpURLConnection).run {
            setRequestProperty("Range", "bytes=0-1023"); val r = responseCode to contentType; disconnect(); r
        }
        val (code, type) = head(client.streamUrl(s.id))
        assertTrue("stream $code", code == 200 || code == 206)
        assertTrue("audio type $type", type!!.startsWith("audio/"))
        val (tc, tt) = head(client.streamUrl(s.id, 128, "mp3"))
        assertTrue("converted stream $tc", tc == 200 || tc == 206); assertEquals("audio/mpeg", tt)
        val cover = c.albums.first { it.id == s.albumId }.coverArt!!
        val (cc, ct) = head(client.coverUrl(cover, 300))
        assertEquals(200, cc); assertTrue(ct!!.startsWith("image/"))
    }
}
