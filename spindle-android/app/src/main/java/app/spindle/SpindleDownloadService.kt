package app.spindle

import android.app.Notification
import androidx.media3.common.util.UnstableApi
import androidx.media3.exoplayer.offline.Download
import androidx.media3.exoplayer.offline.DownloadManager
import androidx.media3.exoplayer.offline.DownloadService
import androidx.media3.exoplayer.scheduler.PlatformScheduler
import androidx.media3.exoplayer.scheduler.Scheduler

/** Downloads songs for offline listening in the background, showing progress in a notification. */
@UnstableApi
class SpindleDownloadService : DownloadService(
    NOTIFICATION_ID, DEFAULT_FOREGROUND_NOTIFICATION_UPDATE_INTERVAL,
    Spindle.DOWNLOAD_CHANNEL, R.string.downloads_channel, R.string.downloads_channel_description,
) {
    override fun getDownloadManager(): DownloadManager = Spindle.get(this).downloadManager

    override fun getScheduler(): Scheduler = PlatformScheduler(this, JOB_ID)

    override fun getForegroundNotification(downloads: MutableList<Download>, notMetRequirements: Int): Notification {
        val active = downloads.count { it.state == Download.STATE_DOWNLOADING || it.state == Download.STATE_QUEUED }
        val message = if (notMetRequirements != 0) "Waiting for Wi-Fi" else "Downloading $active song${if (active == 1) "" else "s"}"
        return Spindle.get(this).notificationHelper.buildProgressNotification(
            this, R.drawable.ic_stat_spindle, null, message, downloads, notMetRequirements,
        )
    }

    private companion object {
        const val NOTIFICATION_ID = 2
        const val JOB_ID = 1
    }
}
