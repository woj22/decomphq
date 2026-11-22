package app.spindle

import android.app.PendingIntent
import android.content.Intent
import android.os.Handler
import android.os.Looper
import androidx.media3.common.AudioAttributes
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.common.util.UnstableApi
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.source.DefaultMediaSourceFactory
import androidx.media3.session.MediaSession
import androidx.media3.session.MediaSessionService
import com.google.common.util.concurrent.Futures
import com.google.common.util.concurrent.ListenableFuture
import java.util.concurrent.Executors

/**
 * Plays music in the background, with lock-screen, notification and headphone controls.
 * Songs come from a download when there is one, otherwise they stream from the server through the cache.
 */
@UnstableApi
class PlaybackService : MediaSessionService() {
    private var session: MediaSession? = null
    private lateinit var app: Spindle
    private val io = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())

    // Listening history: report "now playing", then count a play once half the song (or 4 minutes) has been heard.
    private var playingId: String? = null
    private var heardMs = 0L
    private var counted = false
    private val ticker = object : Runnable {
        override fun run() {
            val p = session?.player ?: return
            if (p.isPlaying) {
                heardMs += 1000
                val dur = p.duration.takeIf { it > 0 } ?: Long.MAX_VALUE
                val id = playingId
                if (!counted && id != null && heardMs >= minOf(dur / 2, 240_000L)) { counted = true; recordPlay(id) }
            }
            main.postDelayed(this, 1000)
        }
    }

    override fun onCreate() {
        super.onCreate()
        app = Spindle.get(this)
        val player = ExoPlayer.Builder(this)
            .setMediaSourceFactory(DefaultMediaSourceFactory(app.playerDataSourceFactory))
            .setAudioAttributes(
                AudioAttributes.Builder().setUsage(C.USAGE_MEDIA).setContentType(C.AUDIO_CONTENT_TYPE_MUSIC).build(),
                /* handleAudioFocus = */ true,
            )
            .setHandleAudioBecomingNoisy(true) // pause when headphones are unplugged
            .setWakeMode(C.WAKE_MODE_NETWORK)
            .build()
        player.addListener(object : Player.Listener {
            override fun onMediaItemTransition(mediaItem: MediaItem?, reason: Int) {
                playingId = mediaItem?.mediaId; heardMs = 0; counted = false
                val id = playingId ?: return
                val c = app.client ?: return
                io.execute { runCatching { c.scrobble(id, submission = false) } } // "now playing"; never queued
            }
        })
        val open = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        session = MediaSession.Builder(this, player)
            .setSessionActivity(open)
            .setCallback(object : MediaSession.Callback {
                // Items arrive from the screens with only an id; give each its streaming address and cache key here,
                // so the address always carries the current sign-in and quality.
                override fun onAddMediaItems(
                    mediaSession: MediaSession,
                    controller: MediaSession.ControllerInfo,
                    mediaItems: MutableList<MediaItem>,
                ): ListenableFuture<MutableList<MediaItem>> {
                    val client = app.client ?: return Futures.immediateFuture(mutableListOf())
                    val wanted = app.currentQuality()
                    val cached = app.cachedQualities() // a complete cached copy plays even offline, whatever its quality
                    return Futures.immediateFuture(mediaItems.map { item ->
                        val q = cached[item.mediaId] ?: wanted
                        item.buildUpon()
                            .setUri(client.streamUrl(item.mediaId, q))
                            .setCustomCacheKey(app.streamKey(item.mediaId, q))
                            .build()
                    }.toMutableList())
                }
            })
            .build()
        main.post(ticker)
    }

    private fun recordPlay(id: String) {
        val time = System.currentTimeMillis()
        io.execute {
            val c = app.client
            val sent = c != null && runCatching { c.scrobble(id, submission = true, timeMs = time) }.isSuccess
            if (!sent) app.pending.add(PendingOps.scrobble(id, time)) // sent with the next sync
        }
    }

    override fun onGetSession(controllerInfo: MediaSession.ControllerInfo): MediaSession? = session

    override fun onTaskRemoved(rootIntent: Intent?) {
        val p = session?.player
        if (p == null || !p.playWhenReady || p.mediaItemCount == 0) stopSelf()
    }

    override fun onDestroy() {
        main.removeCallbacks(ticker)
        session?.run { player.release(); release() }
        session = null
        super.onDestroy()
    }
}
