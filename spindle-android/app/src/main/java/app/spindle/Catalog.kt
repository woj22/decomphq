package app.spindle

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.UUID

data class Playlist(val id: String, val name: String, val songIds: List<String>, val changed: String = "", val owner: String = "") {
    val isLocalOnly get() = id.startsWith(LOCAL_PREFIX)
    companion object { const val LOCAL_PREFIX = "local-" }
}

/** The library as last synced from the server. Kept on the phone so browsing works offline. */
data class Catalog(
    val songs: List<Song> = emptyList(),
    val albums: List<Album> = emptyList(),
    val artists: List<Artist> = emptyList(),
    val playlists: List<Playlist> = emptyList(),
    val likes: Set<String> = emptySet(),
    val lastSync: Long = 0L,
    val lastScan: String = "",
)

/** Reads and writes the catalogue as JSON files in the app's private storage. */
class CatalogStore(private val dir: File) {
    init { dir.mkdirs() }

    @Synchronized
    fun load(): Catalog = runCatching {
        val meta = read("meta")?.let { JSONObject(it) } ?: return Catalog()
        Catalog(
            songs = read("songs")?.let { JSONArray(it).objects().map(::songFrom) } ?: emptyList(),
            albums = read("albums")?.let { JSONArray(it).objects().map(::albumFrom) } ?: emptyList(),
            artists = read("artists")?.let { JSONArray(it).objects().map(::artistFrom) } ?: emptyList(),
            playlists = read("playlists")?.let { JSONArray(it).objects().map(::playlistFrom) } ?: emptyList(),
            likes = meta.optJSONArray("likes").strings().toSet(),
            lastSync = meta.optLong("lastSync"),
            lastScan = meta.optString("lastScan"),
        )
    }.getOrDefault(Catalog())

    @Synchronized
    fun save(c: Catalog) {
        write("songs", JSONArray().apply { c.songs.forEach { put(songTo(it)) } }.toString())
        write("albums", JSONArray().apply { c.albums.forEach { put(albumTo(it)) } }.toString())
        write("artists", JSONArray().apply { c.artists.forEach { put(JSONObject().put("id", it.id).put("name", it.name).put("albumCount", it.albumCount).put("coverArt", it.coverArt)) } }.toString())
        savePlaylistsAndLikes(c)
    }

    /** Cheaper save for changes that only touch playlists and likes. */
    @Synchronized
    fun savePlaylistsAndLikes(c: Catalog) {
        write("playlists", JSONArray().apply { c.playlists.forEach { p -> put(JSONObject().put("id", p.id).put("name", p.name).put("changed", p.changed).put("owner", p.owner).put("songs", JSONArray(p.songIds))) } }.toString())
        write("meta", JSONObject().put("lastSync", c.lastSync).put("lastScan", c.lastScan).put("likes", JSONArray(c.likes.toList())).toString())
    }

    @Synchronized
    fun clear() { dir.listFiles()?.forEach { it.delete() } }

    private fun read(name: String) = File(dir, "$name.json").takeIf { it.exists() }?.readText()
    private fun write(name: String, text: String) {
        val tmp = File(dir, "$name.json.tmp")
        tmp.writeText(text)
        tmp.renameTo(File(dir, "$name.json"))
    }

    private fun songTo(s: Song) = JSONObject().put("id", s.id).put("title", s.title).put("artist", s.artist).put("artistId", s.artistId)
        .put("album", s.album).put("albumId", s.albumId).put("coverArt", s.coverArt).put("durationMs", s.durationMs).put("track", s.track)
        .put("disc", s.disc).put("year", s.year).put("genre", s.genre).put("suffix", s.suffix).put("bitRate", s.bitRate).put("size", s.size)
        .put("created", s.created).put("playCount", s.playCount).put("played", s.played)

    private fun songFrom(o: JSONObject) = Song(
        o.getString("id"), o.optString("title"), o.optString("artist"), o.optString("artistId").ifBlank { null }, o.optString("album"),
        o.optString("albumId"), o.optString("coverArt").ifBlank { null }, o.optLong("durationMs"), o.optInt("track"), o.optInt("disc"),
        o.optInt("year"), o.optString("genre").ifBlank { null }, o.optString("suffix"), o.optInt("bitRate"), o.optLong("size"),
        o.optLong("created"), o.optInt("playCount"), o.optLong("played"), false,
    )

    private fun albumTo(a: Album) = JSONObject().put("id", a.id).put("name", a.name).put("artist", a.artist).put("artistId", a.artistId)
        .put("coverArt", a.coverArt).put("songCount", a.songCount).put("durationMs", a.durationMs).put("year", a.year)
        .put("created", a.created).put("playCount", a.playCount).put("played", a.played)

    private fun albumFrom(o: JSONObject) = Album(
        o.getString("id"), o.optString("name"), o.optString("artist"), o.optString("artistId").ifBlank { null }, o.optString("coverArt").ifBlank { null },
        o.optInt("songCount"), o.optLong("durationMs"), o.optInt("year"), o.optLong("created"), o.optInt("playCount"), o.optLong("played"),
    )

    private fun artistFrom(o: JSONObject) = Artist(o.getString("id"), o.optString("name"), o.optInt("albumCount"), o.optString("coverArt").ifBlank { null })
    private fun playlistFrom(o: JSONObject) = Playlist(o.getString("id"), o.optString("name"), o.optJSONArray("songs").strings(), o.optString("changed"), o.optString("owner"))
}

internal fun JSONArray?.strings(): List<String> = if (this == null) emptyList() else (0 until length()).map { getString(it) }

/**
 * Changes made in the app (likes, playlist edits, plays) waiting to reach the server.
 * They are sent straight away when the server is reachable, and kept here when it isn't.
 */
class PendingOps(private val file: File) {
    private val ops = ArrayList<JSONObject>()

    init { runCatching { ops += JSONArray(file.readText()).objects() } }

    @Synchronized fun isEmpty() = ops.isEmpty()
    @Synchronized fun snapshot(): List<JSONObject> = ops.map { JSONObject(it.toString()) }
    @Synchronized fun touchesPlaylist(id: String) = ops.any { it.optString("id") == id && it.optString("op").startsWith("pl") }

    @Synchronized
    fun add(op: JSONObject) {
        val kind = op.getString("op"); val id = op.optString("id")
        when (kind) {
            "star", "unstar" -> ops.removeAll { (it.optString("op") == "star" || it.optString("op") == "unstar") && it.optString("id") == id }
            "plSave" -> {
                val prev = ops.firstOrNull { it.optString("op") == "plSave" && it.optString("id") == id }
                if (prev != null && prev.optBoolean("isNew")) op.put("isNew", true)
                ops.removeAll { (it.optString("op") == "plSave" || it.optString("op") == "plRename") && it.optString("id") == id }
            }
            "plRename" -> {
                val save = ops.firstOrNull { it.optString("op") == "plSave" && it.optString("id") == id }
                if (save != null) { save.put("name", op.getString("name")); persist(); return }
                ops.removeAll { it.optString("op") == "plRename" && it.optString("id") == id }
            }
            "plDelete" -> {
                val neverCreated = ops.any { it.optString("op") == "plSave" && it.optString("id") == id && it.optBoolean("isNew") }
                ops.removeAll { it.optString("op").startsWith("pl") && it.optString("id") == id }
                if (neverCreated) { persist(); return }
            }
        }
        ops += op
        persist()
    }

    @Synchronized
    fun remove(op: JSONObject) { ops.removeAll { it.toString() == op.toString() }; persist() }

    /** A playlist created offline got its real id from the server; point the remaining changes at it. */
    @Synchronized
    fun remapPlaylist(from: String, to: String) { ops.forEach { if (it.optString("id") == from) it.put("id", to).remove("isNew") }; persist() }

    @Synchronized fun clear() { ops.clear(); persist() }

    private fun persist() { runCatching { file.writeText(JSONArray(ops).toString()) } }

    companion object {
        fun star(id: String) = JSONObject().put("op", "star").put("id", id)
        fun unstar(id: String) = JSONObject().put("op", "unstar").put("id", id)
        fun playlistSave(p: Playlist, isNew: Boolean) = JSONObject().put("op", "plSave").put("id", p.id).put("name", p.name).put("songs", JSONArray(p.songIds)).put("isNew", isNew)
        fun playlistRename(id: String, name: String) = JSONObject().put("op", "plRename").put("id", id).put("name", name)
        fun playlistDelete(id: String) = JSONObject().put("op", "plDelete").put("id", id)
        fun scrobble(id: String, time: Long) = JSONObject().put("op", "scrobble").put("id", id).put("time", time).put("key", UUID.randomUUID().toString())
    }
}

/** What the person chose to keep on the phone: whole albums, playlists, Liked songs, or single songs. */
class Pins(private val file: File) {
    private val set = LinkedHashSet<String>()
    init { runCatching { set += JSONArray(file.readText()).strings() } }

    @Synchronized fun all(): Set<String> = set.toSet()
    @Synchronized fun has(key: String) = key in set
    @Synchronized fun set(key: String, on: Boolean) { if (on) set += key else set -= key; persist() }
    @Synchronized fun rename(from: String, to: String) { if (set.remove(from)) { set += to; persist() } }
    @Synchronized fun clear() { set.clear(); persist() }
    private fun persist() { runCatching { file.writeText(JSONArray(set.toList()).toString()) } }

    companion object {
        fun album(id: String) = "album:$id"
        fun playlist(id: String) = "playlist:$id"
        fun song(id: String) = "song:$id"
        const val LIKED = "liked"
    }

    /** Every song id that should be downloaded, given the current catalogue. */
    fun wantedSongs(c: Catalog): Set<String> {
        val out = HashSet<String>()
        val keys = all()
        val songsByAlbum = c.songs.groupBy { it.albumId }
        for (k in keys) when {
            k == LIKED -> out += c.likes
            k.startsWith("album:") -> songsByAlbum[k.removePrefix("album:")]?.forEach { out += it.id }
            k.startsWith("playlist:") -> c.playlists.find { it.id == k.removePrefix("playlist:") }?.let { out += it.songIds }
            k.startsWith("song:") -> out += k.removePrefix("song:")
        }
        val known = c.songs.mapTo(HashSet()) { it.id }
        return out.filterTo(HashSet()) { it in known }
    }
}

/** Brings the local catalogue up to date with the server, downloading only what changed. */
class LibrarySync(private val client: SubsonicClient, private val pending: PendingOps, private val pins: Pins) {

    class Result(val catalog: Catalog, val summary: String)

    fun run(old: Catalog, full: Boolean, progress: (String) -> Unit): Result {
        var cat = old
        // 1. Send changes made in the app first, so the server's answer below already includes them.
        progress("Sending your changes")
        cat = flushPending(cat)

        // 2. Albums: a handful of requests even for thousands of songs. Compare each album's signature with the last sync.
        progress("Checking for changes")
        val scan = client.scanStatus().optString("lastScan")
        val albums = pageAll { o, n -> client.albumsPage(o, n) }
        val oldAlbums = old.albums.associateBy { it.id }
        val changed = albums.filter { oldAlbums[it.id]?.signature != it.signature }
        val removed = oldAlbums.keys - albums.mapTo(HashSet()) { it.id }

        val songs: List<Song>
        var added = 0; var updated = 0
        if (full || old.songs.isEmpty() || changed.size > maxOf(25, albums.size / 4)) {
            // First sync, a big change, or a requested rebuild: page through every song.
            val all = ArrayList<Song>()
            var offset = 0
            while (true) {
                val page = client.songsPage(offset, PAGE)
                all += page; offset += page.size
                progress("Loading songs: ${all.size}")
                if (page.size < PAGE) break
            }
            val oldIds = old.songs.mapTo(HashSet()) { it.id }
            added = all.count { it.id !in oldIds }
            updated = changed.count { it.id in oldAlbums }
            songs = all
        } else {
            // Incremental: fetch only the albums that changed.
            val byAlbum = old.songs.groupBy { it.albumId }.toMutableMap()
            removed.forEach { byAlbum.remove(it) }
            changed.forEachIndexed { i, a ->
                progress("Updating albums: ${i + 1} of ${changed.size}")
                val fresh = client.album(a.id).second
                val before = byAlbum[a.id]?.map { it.id }?.toSet() ?: emptySet()
                added += fresh.count { it.id !in before }
                byAlbum[a.id] = fresh
            }
            updated = changed.count { it.id in oldAlbums }
            songs = byAlbum.values.flatten()
        }

        // 3. Artists, favourites and playlists are small: refresh them every time.
        progress("Updating artists and favourites")
        val artists = client.artists()
        val likes = client.starredSongIds()
        progress("Updating playlists")
        val oldPl = old.playlists.associateBy { it.id }
        val playlists = client.playlists().map { info ->
            val prev = oldPl[info.id]
            val ids = if (prev != null && prev.changed == info.changed && prev.songIds.size == info.songCount) prev.songIds
            else client.playlistSongs(info.id).map { it.id }
            Playlist(info.id, info.name, ids, info.changed, info.owner)
        } + cat.playlists.filter { it.isLocalOnly } // created offline and not sent yet

        val songIds = songs.mapTo(HashSet()) { it.id }
        cat = Catalog(
            songs = songs.sortedBy { it.title.lowercase() },
            albums = albums,
            artists = artists,
            playlists = playlists,
            likes = likes.filterTo(HashSet()) { it in songIds },
            lastSync = System.currentTimeMillis(),
            lastScan = scan,
        )
        if (old.songs.isEmpty()) return Result(cat, "Loaded ${songs.size} songs from ${albums.size} albums")
        val parts = buildList {
            if (added > 0) add("$added new song${if (added == 1) "" else "s"}")
            if (updated > 0) add("$updated album${if (updated == 1) "" else "s"} updated")
            if (removed.isNotEmpty()) add("${removed.size} album${if (removed.size == 1) "" else "s"} removed")
        }
        return Result(cat, if (parts.isEmpty()) "Library is up to date" else parts.joinToString(", "))
    }

    /** Sends queued changes. Stops at the first connection failure and keeps the rest for later. */
    fun flushPending(start: Catalog): Catalog {
        var cat = start
        for (op in pending.snapshot()) {
            val id = op.optString("id")
            try {
                when (op.getString("op")) {
                    "star" -> client.star(id)
                    "unstar" -> client.unstar(id)
                    "scrobble" -> client.scrobble(id, submission = true, timeMs = op.optLong("time"))
                    "plRename" -> client.renamePlaylist(id, op.getString("name"))
                    "plDelete" -> client.deletePlaylist(id)
                    "plSave" -> {
                        val songs = op.optJSONArray("songs").strings()
                        val name = op.optString("name")
                        if (op.optBoolean("isNew") || id.startsWith(Playlist.LOCAL_PREFIX)) {
                            val newId = client.savePlaylist(null, name, songs)
                            pending.remove(op) // before remapping, so this create is never sent twice
                            pending.remapPlaylist(id, newId)
                            pins.rename(Pins.playlist(id), Pins.playlist(newId))
                            cat = cat.copy(playlists = cat.playlists.map { if (it.id == id) it.copy(id = newId) else it })
                        } else client.savePlaylist(id, name, songs)
                    }
                }
                pending.remove(op)
            } catch (e: SubsonicException) {
                if (e.kind == SubsonicException.Kind.Unreachable || e.kind == SubsonicException.Kind.BadLogin) throw e
                pending.remove(op) // the server rejected it (for example the song was deleted); drop it
            }
        }
        return cat
    }

    private fun <T> pageAll(fetch: (Int, Int) -> List<T>): List<T> {
        val out = ArrayList<T>()
        while (true) {
            val page = fetch(out.size, PAGE)
            out += page
            if (page.size < PAGE) return out
        }
    }

    companion object { const val PAGE = 500 }
}
