package app.spindle

import android.content.ComponentName
import android.content.Context
import android.graphics.BitmapFactory
import android.net.Uri
import android.util.LruCache
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.core.content.ContextCompat
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.common.Player
import androidx.media3.common.util.UnstableApi
import androidx.media3.exoplayer.offline.Download
import androidx.media3.session.MediaController
import androidx.media3.session.SessionToken
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import java.io.File
import java.util.UUID
import java.util.concurrent.Executors

/** Whether a song is on the phone, and how it got there. */
enum class Availability { Downloaded, Downloading, Cached, StreamOnly }

/** Everything the screens show: the catalogue, likes, playlists, downloads, and what's playing. */
@UnstableApi
class AppState(context: Context, private val scope: CoroutineScope) {
    val app = Spindle.get(context)
    private val ctx = context.applicationContext
    private val lock = Mutex()

    // ---- account and library ----
    var signedIn by mutableStateOf(app.client != null); private set
    var loaded by mutableStateOf(false); private set
    var catalog by mutableStateOf(Catalog()); private set
    var byId by mutableStateOf<Map<String, Song>>(emptyMap()); private set
    var albumsById by mutableStateOf<Map<String, Album>>(emptyMap()); private set
    val songs get() = catalog.songs
    val likes get() = catalog.likes
    val playlists get() = catalog.playlists

    // ---- sync and connection ----
    var syncing by mutableStateOf(false); private set
    var syncProgress by mutableStateOf(""); private set
    var lastSyncSummary by mutableStateOf<String?>(null); private set
    var syncError by mutableStateOf<String?>(null); private set
    var needsSignIn by mutableStateOf(false); private set
    var reachable by mutableStateOf(true); private set
    var networkUp by mutableStateOf(app.networkUp); private set
    val online get() = networkUp && reachable

    // ---- what's on the phone ----
    var downloadState by mutableStateOf<Map<String, Download>>(emptyMap()); private set
    var cachedIds by mutableStateOf<Set<String>>(emptySet()); private set
    var pinKeys by mutableStateOf(app.pins.all()); private set

    // ---- player ----
    var current by mutableStateOf<Song?>(null); private set
    var isPlaying by mutableStateOf(false); private set
    var position by mutableLongStateOf(0L)
    var duration by mutableLongStateOf(0L); private set
    var shuffle by mutableStateOf(false); private set
    var repeat by mutableStateOf(Player.REPEAT_MODE_OFF); private set
    private var controller: MediaController? = null
    private var lastItemId: String? = null

    private val onDownloads: () -> Unit = { scope.launch(Dispatchers.Main) { downloadState = HashMap(app.downloads) } }
    private val onNetwork: (Boolean) -> Unit = { up ->
        scope.launch(Dispatchers.Main) {
            val cameBack = up && !networkUp
            networkUp = up
            if (cameBack && signedIn) { reachable = true; sync() }
        }
    }

    init {
        app.downloadListeners += onDownloads
        app.networkListeners += onNetwork
        downloadState = HashMap(app.downloads)
        scope.launch {
            val c = withContext(Dispatchers.IO) { app.catalogStore.load() }
            applyCatalog(c)
            loaded = true
            refreshCached()
            if (signedIn && System.currentTimeMillis() - c.lastSync > 10 * 60_000) sync()
        }
    }

    fun dispose() {
        app.downloadListeners -= onDownloads
        app.networkListeners -= onNetwork
    }

    private fun applyCatalog(c: Catalog) {
        catalog = c
        byId = c.songs.associateBy { it.id }
        albumsById = c.albums.associateBy { it.id }
    }

    fun coverFor(s: Song?): String? = s?.let { albumsById[it.albumId]?.coverArt ?: it.coverArt }

    // ---------------- sign-in ----------------

    /** Checks the address and login, then saves them and runs the first sync. Returns an error to show, or null. */
    suspend fun signIn(server: String, user: String, password: String): String? {
        val normalized = Credentials.normalizeServer(server)
        ServerAddress.problem(normalized)?.let { return it }
        if (user.isBlank() || password.isEmpty()) return "Enter your Navidrome username and password."
        val creds = Credentials.fromPassword(normalized, user, password)
        val err = withContext(Dispatchers.IO) {
            try { SubsonicClient(creds).ping(); null } catch (e: SubsonicException) {
                when (e.kind) {
                    SubsonicException.Kind.Unreachable -> "Can't reach the server. Check that this phone is on the same Wi-Fi as the server phone (or connected to Tailscale, if you use it), and that Navidrome is running."
                    SubsonicException.Kind.BadLogin -> "Navidrome didn't accept that username and password."
                    SubsonicException.Kind.NotSubsonic -> "That address answered, but it isn't a Navidrome server. Check the port (usually 4533)."
                    SubsonicException.Kind.Server -> "The server refused the sign-in: ${e.message}"
                }
            }
        } ?: run {
            val changedAccount = app.credentials?.let { it.server != creds.server || it.user != creds.user } ?: true
            if (changedAccount) withContext(Dispatchers.IO) { app.catalogStore.clear(); app.pending.clear() }
            app.signIn(creds)
            if (changedAccount) applyCatalog(Catalog())
            signedIn = true; needsSignIn = false; reachable = true; syncError = null
            sync(full = changedAccount)
            null
        }
        return err
    }

    fun signOut() {
        controller?.run { stop(); clearMediaItems() }
        app.signOut()
        applyCatalog(Catalog()); pinKeys = emptySet(); cachedIds = emptySet()
        signedIn = false; lastSyncSummary = null; syncError = null
    }

    // ---------------- sync ----------------

    private var syncJob: Job? = null

    /** Brings the catalogue up to date. [full] re-reads every song instead of only changed albums. */
    fun sync(full: Boolean = false, manual: Boolean = false) {
        val client = app.client ?: return
        if (syncing) return
        syncing = true; syncError = null; syncProgress = "Connecting"
        syncJob = scope.launch {
            lock.withLock {
                try {
                    val result = withContext(Dispatchers.IO) {
                        LibrarySync(client, app.pending, app.pins).run(catalog, full) { msg -> scope.launch(Dispatchers.Main) { syncProgress = msg } }
                    }
                    withContext(Dispatchers.IO) { app.catalogStore.save(result.catalog) }
                    applyCatalog(result.catalog)
                    reachable = true
                    lastSyncSummary = result.summary
                    pinKeys = app.pins.all()
                    app.reconcileDownloads(result.catalog)
                    prefetchArtwork(client, result.catalog)
                } catch (e: SubsonicException) {
                    when (e.kind) {
                        SubsonicException.Kind.Unreachable -> { reachable = false; if (manual) syncError = "Can't reach your server. Showing your saved library." }
                        SubsonicException.Kind.BadLogin -> { needsSignIn = true; syncError = "Navidrome no longer accepts your saved sign-in. Sign in again." }
                        else -> syncError = "Sync failed: ${e.message}"
                    }
                } catch (e: Exception) {
                    syncError = "Sync failed: ${e.message ?: e.javaClass.simpleName}"
                } finally {
                    syncing = false; syncProgress = ""
                }
            }
        }
    }

    /** Sends likes, playlist edits and plays right away when the server is reachable; otherwise they wait for the next sync. */
    private fun pushChanges() {
        val client = app.client ?: return
        if (!networkUp) return
        scope.launch {
            lock.withLock {
                try {
                    val updated = withContext(Dispatchers.IO) { LibrarySync(client, app.pending, app.pins).flushPending(catalog) }
                    if (updated != catalog) { applyCatalog(updated); withContext(Dispatchers.IO) { app.catalogStore.savePlaylistsAndLikes(updated) }; pinKeys = app.pins.all() }
                    reachable = true
                } catch (e: SubsonicException) {
                    if (e.kind == SubsonicException.Kind.Unreachable) reachable = false
                }
            }
        }
    }

    private fun saveLocal(c: Catalog) {
        applyCatalog(c)
        scope.launch(Dispatchers.IO) { app.catalogStore.savePlaylistsAndLikes(c) }
    }

    // ---------------- downloads and cache ----------------

    fun availability(s: Song): Availability {
        val d = downloadState[s.id]
        return when {
            d?.state == Download.STATE_COMPLETED -> Availability.Downloaded
            d != null && d.state != Download.STATE_FAILED && d.state != Download.STATE_REMOVING -> Availability.Downloading
            s.id in cachedIds -> Availability.Cached
            else -> Availability.StreamOnly
        }
    }

    fun playable(s: Song) = online || availability(s).let { it == Availability.Downloaded || it == Availability.Cached }

    fun isPinned(key: String) = key in pinKeys

    /** Keeps an album, playlist, Liked songs or a single song on the phone, or stops keeping it. */
    fun setPinned(key: String, on: Boolean) {
        app.pins.set(key, on)
        pinKeys = app.pins.all()
        app.reconcileDownloads(catalog)
    }

    fun refreshCached() {
        scope.launch { cachedIds = withContext(Dispatchers.IO) { runCatching { app.cachedSongIds() }.getOrDefault(emptySet()) } }
    }

    fun removeAllDownloads() { app.removeAllDownloads(); pinKeys = emptySet() }
    fun clearCache() { app.clearStreamCache(); scope.launch { delay(800); refreshCached() } }

    // ---------------- player ----------------

    fun connect() {
        if (controller != null) return
        val token = SessionToken(ctx, ComponentName(ctx, PlaybackService::class.java))
        val future = MediaController.Builder(ctx, token).buildAsync()
        future.addListener({
            val c = runCatching { future.get() }.getOrNull() ?: return@addListener
            controller = c
            c.addListener(object : Player.Listener {
                override fun onEvents(player: Player, events: Player.Events) = syncFromPlayer()
            })
            syncFromPlayer()
        }, ContextCompat.getMainExecutor(ctx))
    }

    fun disconnect() { controller?.release(); controller = null }

    fun syncFromPlayer() {
        val c = controller ?: return
        val id = c.currentMediaItem?.mediaId
        current = id?.let { byId[it] }
        isPlaying = c.isPlaying
        position = c.currentPosition.coerceAtLeast(0)
        duration = c.duration.takeIf { it > 0 } ?: (current?.durationMs ?: 0L)
        shuffle = c.shuffleModeEnabled
        repeat = c.repeatMode
        if (id != lastItemId) { lastItemId = id; refreshCached() } // the previous song may now be fully cached
    }

    fun tickPosition() { controller?.let { position = it.currentPosition.coerceAtLeast(0) } }

    /** Plays [list] from [index]. Offline, songs that aren't on the phone are skipped. */
    fun play(list: List<Song>, index: Int, shuffled: Boolean = false) {
        val c = controller ?: return
        val start = list.getOrNull(index)
        val usable = if (online) list else list.filter { playable(it) }
        if (usable.isEmpty()) return
        val startIdx = if (shuffled) usable.indices.random() else usable.indexOf(start).coerceAtLeast(0)
        c.shuffleModeEnabled = shuffled
        c.setMediaItems(usable.map { toMediaItem(it) }, startIdx, 0L)
        c.prepare()
        c.play()
    }

    fun toggle() {
        val c = controller ?: return
        if (c.mediaItemCount == 0) { if (songs.isNotEmpty()) play(songs, 0, shuffled = true); return }
        if (c.isPlaying) c.pause() else { if (c.playbackState == Player.STATE_ENDED) c.seekTo(0, 0); c.play() }
    }
    fun next() { controller?.seekToNext() }
    fun prev() { controller?.seekToPrevious() }
    fun seekTo(ms: Long) { controller?.seekTo(ms); position = ms }
    fun toggleShuffle() { controller?.let { it.shuffleModeEnabled = !it.shuffleModeEnabled } }
    fun cycleRepeat() {
        controller?.let {
            it.repeatMode = when (it.repeatMode) {
                Player.REPEAT_MODE_OFF -> Player.REPEAT_MODE_ALL
                Player.REPEAT_MODE_ALL -> Player.REPEAT_MODE_ONE
                else -> Player.REPEAT_MODE_OFF
            }
        }
    }
    fun playNext(song: Song) {
        val c = controller ?: return
        if (c.mediaItemCount == 0) return play(listOf(song), 0)
        c.addMediaItem(c.nextMediaItemIndex.takeIf { it != -1 } ?: c.mediaItemCount, toMediaItem(song))
    }

    private fun toMediaItem(s: Song): MediaItem {
        val cover = coverFor(s)
        val art = cover?.let { ArtCache.diskFile(ctx, it, ArtCache.LARGE).takeIf { f -> f.exists() }?.let(Uri::fromFile)
            ?: app.client?.coverUrl(it, ArtCache.LARGE)?.let(Uri::parse) }
        return MediaItem.Builder()
            .setMediaId(s.id)
            .setMediaMetadata(
                MediaMetadata.Builder()
                    .setTitle(s.title).setArtist(s.artist).setAlbumTitle(s.album)
                    .setArtworkUri(art).setIsPlayable(true).setIsBrowsable(false)
                    .build(),
            )
            .build()
    }

    // ---------------- favourites and playlists ----------------

    fun toggleLike(song: Song) {
        val liked = song.id in likes
        saveLocal(catalog.copy(likes = if (liked) likes - song.id else likes + song.id))
        app.pending.add(if (liked) PendingOps.unstar(song.id) else PendingOps.star(song.id))
        if (isPinned(Pins.LIKED)) app.reconcileDownloads(catalog)
        pushChanges()
    }

    fun createPlaylist(name: String, first: Song? = null): Playlist {
        val p = Playlist(Playlist.LOCAL_PREFIX + UUID.randomUUID(), name.trim(), listOfNotNull(first?.id))
        saveLocal(catalog.copy(playlists = playlists + p))
        app.pending.add(PendingOps.playlistSave(p, isNew = true))
        pushChanges()
        return p
    }

    fun addToPlaylist(pid: String, song: Song) = editSongs(pid) { if (song.id in it) it else it + song.id }
    fun removeFromPlaylist(pid: String, song: Song) = editSongs(pid) { it - song.id }

    private fun editSongs(pid: String, f: (List<String>) -> List<String>) {
        val p = playlists.find { it.id == pid } ?: return
        val updated = p.copy(songIds = f(p.songIds))
        saveLocal(catalog.copy(playlists = playlists.map { if (it.id == pid) updated else it }))
        app.pending.add(PendingOps.playlistSave(updated, isNew = p.isLocalOnly))
        if (isPinned(Pins.playlist(pid))) app.reconcileDownloads(catalog)
        pushChanges()
    }

    fun renamePlaylist(pid: String, name: String) {
        saveLocal(catalog.copy(playlists = playlists.map { if (it.id == pid) it.copy(name = name.trim()) else it }))
        app.pending.add(PendingOps.playlistRename(pid, name.trim()))
        pushChanges()
    }

    fun deletePlaylist(pid: String) {
        saveLocal(catalog.copy(playlists = playlists.filterNot { it.id == pid }))
        app.pending.add(PendingOps.playlistDelete(pid))
        if (isPinned(Pins.playlist(pid))) setPinned(Pins.playlist(pid), false)
        pushChanges()
    }

    fun songsOf(p: Playlist) = p.songIds.mapNotNull { byId[it] }

    // ---------------- artwork ----------------

    private fun prefetchArtwork(client: SubsonicClient, c: Catalog) {
        scope.launch(Dispatchers.IO) {
            val ids = (c.albums.mapNotNull { it.coverArt } + c.artists.mapNotNull { it.coverArt }).distinct()
            val pool = Executors.newFixedThreadPool(4)
            ids.filterNot { ArtCache.diskFile(ctx, it, ArtCache.SMALL).exists() }
                .forEach { id -> pool.execute { ArtCache.fetch(ctx, client, id, ArtCache.SMALL) } }
            pool.shutdown()
        }
    }
}

/** Cover art: kept in memory while the app runs, and on disk so it shows offline. */
object ArtCache {
    const val SMALL = 300
    const val LARGE = 800
    private val mem = LruCache<String, ImageBitmap>(250)

    fun peek(id: String, size: Int): ImageBitmap? = mem.get("$id@$size") ?: if (size == SMALL) null else mem.get("$id@$SMALL")

    fun diskFile(context: Context, id: String, size: Int) =
        File(File(context.filesDir, "art").apply { mkdirs() }, "${id.replace(Regex("[^A-Za-z0-9_-]"), "_")}_$size.jpg")

    /** Network fetch to disk. Returns true when the file is there afterwards. */
    fun fetch(context: Context, client: SubsonicClient, id: String, size: Int): Boolean {
        val f = diskFile(context, id, size)
        if (f.exists()) return true
        return runCatching {
            val conn = java.net.URL(client.coverUrl(id, size)).openConnection() as java.net.HttpURLConnection
            conn.connectTimeout = 8000; conn.readTimeout = 15000
            try {
                if (conn.responseCode != 200 || conn.contentType?.startsWith("image/") != true) return false
                val tmp = File(f.path + ".tmp")
                conn.inputStream.use { input -> tmp.outputStream().use { input.copyTo(it) } }
                tmp.renameTo(f)
            } finally { conn.disconnect() }
        }.getOrDefault(false)
    }

    /** Memory, then disk, then the server (when [client] is given). */
    fun load(context: Context, client: SubsonicClient?, id: String, size: Int): ImageBitmap? {
        mem.get("$id@$size")?.let { return it }
        var f = diskFile(context, id, size)
        if (!f.exists() && client != null) fetch(context, client, id, size)
        if (!f.exists() && size != SMALL) f = diskFile(context, id, SMALL) // offline: fall back to the small copy
        if (!f.exists()) return null
        val bmp = runCatching { BitmapFactory.decodeFile(f.path)?.asImageBitmap() }.getOrNull() ?: return null
        mem.put("$id@$size", bmp)
        return bmp
    }
}
