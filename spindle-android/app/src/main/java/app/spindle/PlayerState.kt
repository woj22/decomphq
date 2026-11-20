package app.spindle

import android.content.ComponentName
import android.content.Context
import android.graphics.Bitmap
import android.net.Uri
import android.os.Build
import android.util.LruCache
import android.util.Size
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
import androidx.media3.session.MediaController
import androidx.media3.session.SessionToken
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.UUID

/** Everything the screens show: the library, likes, playlists, and what's playing. */
class AppState(private val context: Context, private val scope: CoroutineScope) {
    private val store = UserStore(context)

    var songs by mutableStateOf<List<Song>>(emptyList()); private set
    var byId by mutableStateOf<Map<Long, Song>>(emptyMap()); private set
    var scanned by mutableStateOf(false); private set
    var likes by mutableStateOf(store.loadLikes()); private set
    var playlists by mutableStateOf(store.loadPlaylists()); private set

    var current by mutableStateOf<Song?>(null); private set
    var isPlaying by mutableStateOf(false); private set
    var position by mutableLongStateOf(0L)
    var duration by mutableLongStateOf(0L); private set
    var shuffle by mutableStateOf(false); private set
    var repeat by mutableStateOf(Player.REPEAT_MODE_OFF); private set

    private var controller: MediaController? = null

    fun rescan() {
        scope.launch {
            val list = withContext(Dispatchers.IO) { runCatching { MusicScanner.scan(context) }.getOrDefault(emptyList()) }
            songs = list
            byId = list.associateBy { it.id }
            scanned = true
            syncFromPlayer()
        }
    }

    fun connect() {
        if (controller != null) return
        val token = SessionToken(context, ComponentName(context, PlaybackService::class.java))
        val future = MediaController.Builder(context, token).buildAsync()
        future.addListener({
            val c = runCatching { future.get() }.getOrNull() ?: return@addListener
            controller = c
            c.addListener(object : Player.Listener {
                override fun onEvents(player: Player, events: Player.Events) = syncFromPlayer()
            })
            syncFromPlayer()
        }, ContextCompat.getMainExecutor(context))
    }

    fun disconnect() {
        controller?.release()
        controller = null
    }

    fun syncFromPlayer() {
        val c = controller ?: return
        current = c.currentMediaItem?.mediaId?.toLongOrNull()?.let { byId[it] }
        isPlaying = c.isPlaying
        position = c.currentPosition.coerceAtLeast(0)
        duration = c.duration.takeIf { it > 0 } ?: (current?.durationMs ?: 0L)
        shuffle = c.shuffleModeEnabled
        repeat = c.repeatMode
    }

    fun tickPosition() { controller?.let { position = it.currentPosition.coerceAtLeast(0) } }

    // ---- playback ----
    fun play(list: List<Song>, index: Int, shuffled: Boolean = false) {
        val c = controller ?: return
        if (list.isEmpty()) return
        c.shuffleModeEnabled = shuffled
        c.setMediaItems(list.map { it.toMediaItem() }, if (shuffled) (list.indices).random() else index, 0L)
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
        c.addMediaItem(c.nextMediaItemIndex.takeIf { it != -1 } ?: c.mediaItemCount, song.toMediaItem())
    }

    // ---- likes and playlists ----
    fun toggleLike(song: Song) {
        likes = if (song.id in likes) likes - song.id else likes + song.id
        store.saveLikes(likes)
    }
    fun createPlaylist(name: String, first: Song? = null): Playlist {
        val p = Playlist(UUID.randomUUID().toString(), name.trim(), listOfNotNull(first?.id))
        playlists = playlists + p
        store.savePlaylists(playlists)
        return p
    }
    fun addToPlaylist(pid: String, song: Song) = editPlaylist(pid) { if (song.id in it.songIds) it else it.copy(songIds = it.songIds + song.id) }
    fun removeFromPlaylist(pid: String, song: Song) = editPlaylist(pid) { it.copy(songIds = it.songIds - song.id) }
    fun renamePlaylist(pid: String, name: String) = editPlaylist(pid) { it.copy(name = name.trim()) }
    fun deletePlaylist(pid: String) { playlists = playlists.filterNot { it.id == pid }; store.savePlaylists(playlists) }
    private fun editPlaylist(pid: String, f: (Playlist) -> Playlist) {
        playlists = playlists.map { if (it.id == pid) f(it) else it }
        store.savePlaylists(playlists)
    }
    fun songsOf(p: Playlist) = p.songIds.mapNotNull { byId[it] }
}

fun Song.toMediaItem(): MediaItem = MediaItem.Builder()
    .setMediaId(id.toString())
    .setUri(uri)
    .setMediaMetadata(
        MediaMetadata.Builder()
            .setTitle(title).setArtist(artist).setAlbumTitle(album)
            .setArtworkUri(Uri.parse("content://media/external/audio/albumart/$albumId"))
            .setIsPlayable(true).setIsBrowsable(false)
            .build(),
    )
    .build()

/** Album covers read from the music files, cached in memory. */
object ArtCache {
    private val cache = LruCache<Long, ImageBitmap>(300)
    private val missing = HashSet<Long>()
    fun peek(albumId: Long): ImageBitmap? = cache.get(albumId)
    fun isMissing(albumId: Long) = synchronized(missing) { albumId in missing }

    fun load(context: Context, song: Song, px: Int = 360): ImageBitmap? {
        cache.get(song.albumId)?.let { return it }
        if (isMissing(song.albumId)) return null
        val bmp: Bitmap? = runCatching {
            if (Build.VERSION.SDK_INT >= 29) context.contentResolver.loadThumbnail(song.uri, Size(px, px), null)
            else context.contentResolver.openInputStream(Uri.parse("content://media/external/audio/albumart/${song.albumId}"))
                ?.use { android.graphics.BitmapFactory.decodeStream(it) }
        }.getOrNull()
        return if (bmp != null) bmp.asImageBitmap().also { cache.put(song.albumId, it) }
        else { synchronized(missing) { missing += song.albumId }; null }
    }
}
