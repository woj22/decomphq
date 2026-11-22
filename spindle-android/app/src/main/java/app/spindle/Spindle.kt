package app.spindle

import android.annotation.SuppressLint
import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import androidx.media3.common.C
import androidx.media3.common.util.UnstableApi
import androidx.media3.database.StandaloneDatabaseProvider
import androidx.media3.datasource.DataSource
import androidx.media3.datasource.DataSpec
import androidx.media3.datasource.DefaultHttpDataSource
import androidx.media3.datasource.TransferListener
import androidx.media3.datasource.cache.Cache
import androidx.media3.datasource.cache.CacheDataSource
import androidx.media3.datasource.cache.CacheEvictor
import androidx.media3.datasource.cache.CacheSpan
import androidx.media3.datasource.cache.ContentMetadata
import androidx.media3.datasource.cache.NoOpCacheEvictor
import androidx.media3.datasource.cache.SimpleCache
import androidx.media3.exoplayer.offline.Download
import androidx.media3.exoplayer.offline.DownloadManager
import androidx.media3.exoplayer.offline.DownloadNotificationHelper
import androidx.media3.exoplayer.offline.DownloadRequest
import androidx.media3.exoplayer.offline.DownloadService
import androidx.media3.exoplayer.scheduler.Requirements
import java.io.File
import java.security.KeyStore
import java.util.TreeSet
import java.util.concurrent.CopyOnWriteArrayList
import java.util.concurrent.Executors
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Streaming quality choices, in kbps. 0 means the original file, unchanged. */
val QUALITY_CHOICES = listOf(0, 320, 192, 128)
fun qualityLabel(kbps: Int) = if (kbps == 0) "Original" else "$kbps kbps"

/** Streaming-cache size choices, in bytes. */
val CACHE_CHOICES = listOf(512L shl 20, 1L shl 30, 2L shl 30, 5L shl 30, 10L shl 30)

/**
 * The app's long-lived pieces, shared by the screens, the player and the download service:
 * settings, sign-in, the local catalogue, the streaming cache and the downloads.
 */
@SuppressLint("UnsafeOptInUsageError")
@UnstableApi
class Spindle private constructor(val context: Context) {
    private val prefs = context.getSharedPreferences("spindle-settings", Context.MODE_PRIVATE)
    private val root = context.filesDir

    // ---------- settings ----------
    var cacheMaxBytes: Long
        get() = prefs.getLong("cacheMax", 2L shl 30)
        set(v) { prefs.edit().putLong("cacheMax", v).apply(); streamEvictor.maxBytes = v; Executors.newSingleThreadExecutor().execute { streamEvictor.trim(streamCache) } }
    var wifiQuality: Int
        get() = prefs.getInt("wifiQ", 0)
        set(v) = prefs.edit().putInt("wifiQ", v).apply()
    var mobileQuality: Int
        get() = prefs.getInt("mobileQ", 0)
        set(v) = prefs.edit().putInt("mobileQ", v).apply()
    var downloadQuality: Int
        get() = prefs.getInt("dlQ", 0)
        set(v) = prefs.edit().putInt("dlQ", v).apply()
    var downloadWifiOnly: Boolean
        get() = prefs.getBoolean("dlWifi", true)
        set(v) { prefs.edit().putBoolean("dlWifi", v).apply(); applyDownloadRequirements() }

    // ---------- sign-in ----------
    var credentials: Credentials? = loadCredentials(); private set
    var client: SubsonicClient? = credentials?.let { SubsonicClient(it) }; private set

    fun signIn(c: Credentials) {
        prefs.edit().putString("creds", Vault.encrypt(listOf(c.server, c.user, c.salt, c.token).joinToString("\n"))).apply()
        credentials = c; client = SubsonicClient(c)
    }

    /** Signs out and removes everything tied to the account: catalogue, pending changes, cache and downloads. */
    fun signOut() {
        prefs.edit().remove("creds").apply()
        credentials = null; client = null
        catalogStore.clear(); pending.clear(); pins.clear()
        DownloadService.sendRemoveAllDownloads(context, SpindleDownloadService::class.java, false)
        clearStreamCache()
    }

    private fun loadCredentials(): Credentials? = runCatching {
        val parts = Vault.decrypt(prefs.getString("creds", null) ?: return null).split("\n")
        Credentials(parts[0], parts[1], parts[2], parts[3])
    }.getOrNull()

    // ---------- catalogue ----------
    val catalogStore = CatalogStore(File(root, "catalog"))
    val pending = PendingOps(File(root, "pending.json"))
    val pins = Pins(File(root, "pins.json"))

    // ---------- network ----------
    @Volatile var networkUp = false; private set
    @Volatile var unmetered = true; private set
    val networkListeners = CopyOnWriteArrayList<(Boolean) -> Unit>()

    init {
        val cm = context.getSystemService(ConnectivityManager::class.java)
        cm.registerDefaultNetworkCallback(object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) { networkUp = true; networkListeners.forEach { it(true) } }
            override fun onLost(network: Network) { networkUp = false; networkListeners.forEach { it(false) } }
            override fun onCapabilitiesChanged(network: Network, caps: NetworkCapabilities) {
                unmetered = caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_NOT_METERED)
            }
        })
        networkUp = cm.activeNetwork != null
    }

    fun currentQuality() = if (unmetered) wifiQuality else mobileQuality

    // ---------- caches ----------
    private val db = StandaloneDatabaseProvider(context)

    /** Recently played songs. Oldest are removed automatically once the size limit is reached. */
    private val streamEvictor = AdjustableLruEvictor(cacheMaxBytes)
    val streamCache = SimpleCache(File(root, "stream-cache"), streamEvictor, db)

    /** Songs the person chose to keep. Never removed automatically. */
    val downloadCache = SimpleCache(File(root, "downloads"), NoOpCacheEvictor(), db)

    val http: DefaultHttpDataSource.Factory = DefaultHttpDataSource.Factory()
        .setUserAgent("Spindle/1.0").setAllowCrossProtocolRedirects(true)
        .setConnectTimeoutMs(10_000).setReadTimeoutMs(20_000)

    private val streamFactory = CacheDataSource.Factory().setCache(streamCache).setUpstreamDataSourceFactory(http)
    private val downloadReadFactory = CacheDataSource.Factory().setCache(downloadCache).setUpstreamDataSourceFactory(null).setCacheWriteDataSinkFactory(null)

    /** What the player reads from: a downloaded copy when there is one, otherwise the streaming cache backed by the server. */
    val playerDataSourceFactory = DataSource.Factory {
        RoutingDataSource(streamFactory.createDataSource(), downloadReadFactory.createDataSource()) { key ->
            val id = songIdFromKey(key)
            if (id != null && isDownloaded(id)) downloadKey(id) else null
        }
    }

    fun streamKey(id: String, quality: Int) = "s:$id:$quality"
    fun downloadKey(id: String) = "d:$id"
    private fun songIdFromKey(key: String?) = key?.takeIf { it.startsWith("s:") }?.split(":")?.getOrNull(1)

    /** Song id to the quality it is fully cached at, for every song played all the way through. */
    fun cachedQualities(): Map<String, Int> {
        val out = HashMap<String, Int>()
        for (key in streamCache.keys) {
            val id = songIdFromKey(key) ?: continue
            val len = ContentMetadata.getContentLength(streamCache.getContentMetadata(key))
            if (len > 0 && streamCache.isCached(key, 0, len)) {
                val q = key.substringAfterLast(':').toIntOrNull() ?: continue
                if (q == currentQuality() || id !in out) out[id] = q // prefer a copy at the quality in use
            }
        }
        return out
    }

    fun cachedSongIds(): Set<String> = cachedQualities().keys

    fun streamCacheBytes() = streamCache.cacheSpace
    fun downloadBytes() = downloadCache.cacheSpace

    fun clearStreamCache() {
        Executors.newSingleThreadExecutor().execute { streamCache.keys.toList().forEach { runCatching { streamCache.removeResource(it) } } }
    }

    // ---------- downloads ----------
    val downloadManager = DownloadManager(context, db, downloadCache, http, Executors.newFixedThreadPool(2)).apply {
        maxParallelDownloads = 2
    }
    val notificationHelper = DownloadNotificationHelper(context, DOWNLOAD_CHANNEL)

    /** Download state per song id, kept current by the download manager. */
    val downloads = java.util.concurrent.ConcurrentHashMap<String, Download>()
    val downloadListeners = CopyOnWriteArrayList<() -> Unit>()

    init {
        applyDownloadRequirements()
        downloadManager.addListener(object : DownloadManager.Listener {
            override fun onDownloadChanged(dm: DownloadManager, download: Download, finalException: Exception?) {
                downloads[download.request.id] = download; downloadListeners.forEach { it() }
            }
            override fun onDownloadRemoved(dm: DownloadManager, download: Download) {
                downloads.remove(download.request.id); downloadListeners.forEach { it() }
            }
            override fun onInitialized(dm: DownloadManager) { loadDownloads(); downloadListeners.forEach { it() } }
        })
        if (downloadManager.isInitialized) loadDownloads()
    }

    private fun loadDownloads() {
        downloadManager.downloadIndex.getDownloads().use { c -> while (c.moveToNext()) downloads[c.download.request.id] = c.download }
    }

    fun isDownloaded(id: String) = downloads[id]?.state == Download.STATE_COMPLETED

    private fun applyDownloadRequirements() {
        downloadManager.requirements = Requirements(if (downloadWifiOnly) Requirements.NETWORK_UNMETERED else Requirements.NETWORK)
    }

    /** Makes the downloads match the albums, playlists and songs the person chose to keep. */
    fun reconcileDownloads(cat: Catalog) {
        val c = client ?: return
        val wanted = pins.wantedSongs(cat)
        val byId = cat.songs.associateBy { it.id }
        for (id in wanted) {
            val d = downloads[id]
            if (d == null || d.state == Download.STATE_FAILED) {
                val s = byId[id] ?: continue
                val q = downloadQuality
                val req = DownloadRequest.Builder(id, android.net.Uri.parse(c.streamUrl(id, q, if (q > 0) "mp3" else null)))
                    .setCustomCacheKey(downloadKey(id))
                    .setData("${s.title} · ${s.artist}".toByteArray())
                    .build()
                DownloadService.sendAddDownload(context, SpindleDownloadService::class.java, req, false)
            }
        }
        for (id in downloads.keys.toList()) if (id !in wanted) {
            DownloadService.sendRemoveDownload(context, SpindleDownloadService::class.java, id, false)
        }
    }

    fun removeAllDownloads() {
        pins.clear()
        DownloadService.sendRemoveAllDownloads(context, SpindleDownloadService::class.java, false)
    }

    companion object {
        const val DOWNLOAD_CHANNEL = "downloads"
        @Volatile private var instance: Spindle? = null
        fun get(context: Context): Spindle = instance ?: synchronized(this) {
            instance ?: Spindle(context.applicationContext).also { instance = it }
        }
    }
}

/** Least-recently-used eviction whose size limit can change while the app runs. */
@UnstableApi
class AdjustableLruEvictor(@Volatile var maxBytes: Long) : CacheEvictor {
    private val spans = TreeSet<CacheSpan> { a, b ->
        val d = a.lastTouchTimestamp - b.lastTouchTimestamp
        if (d == 0L) a.compareTo(b) else if (d < 0) -1 else 1
    }
    private var size = 0L

    override fun requiresCacheSpanTouches() = true
    override fun onCacheInitialized() {}
    override fun onStartFile(cache: Cache, key: String, position: Long, length: Long) { if (length != C.LENGTH_UNSET.toLong()) evict(cache, length) }
    override fun onSpanAdded(cache: Cache, span: CacheSpan) { spans.add(span); size += span.length; evict(cache, 0) }
    override fun onSpanRemoved(cache: Cache, span: CacheSpan) { spans.remove(span); size -= span.length }
    override fun onSpanTouched(cache: Cache, oldSpan: CacheSpan, newSpan: CacheSpan) { onSpanRemoved(cache, oldSpan); onSpanAdded(cache, newSpan) }

    private fun evict(cache: Cache, required: Long) {
        while (size + required > maxBytes && spans.isNotEmpty()) cache.removeSpan(spans.first())
    }

    /** Applies a smaller limit right away. */
    fun trim(cache: SimpleCache) = synchronized(cache) { evict(cache, 0) }
}

/** Opens either the download cache or the streaming source for each request, decided when it opens. */
@UnstableApi
class RoutingDataSource(
    private val stream: DataSource,
    private val downloaded: DataSource,
    private val downloadedKeyFor: (String?) -> String?,
) : DataSource {
    private var active: DataSource? = null

    override fun addTransferListener(transferListener: TransferListener) {
        stream.addTransferListener(transferListener); downloaded.addTransferListener(transferListener)
    }

    override fun open(dataSpec: DataSpec): Long {
        val dk = downloadedKeyFor(dataSpec.key)
        return if (dk != null) {
            active = downloaded
            downloaded.open(dataSpec.buildUpon().setKey(dk).build())
        } else {
            active = stream
            stream.open(dataSpec)
        }
    }

    override fun read(buffer: ByteArray, offset: Int, length: Int) = active!!.read(buffer, offset, length)
    override fun getUri() = active?.uri
    override fun getResponseHeaders(): Map<String, List<String>> = active?.responseHeaders ?: emptyMap()
    override fun close() { active?.close(); active = null }
}

/** Encrypts the saved sign-in with a key that never leaves the phone's secure hardware. */
object Vault {
    private const val ALIAS = "spindle-signin"

    private fun key(): SecretKey {
        val ks = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (ks.getEntry(ALIAS, null) as? KeyStore.SecretKeyEntry)?.let { return it.secretKey }
        val gen = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        gen.init(KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
        return gen.generateKey()
    }

    fun encrypt(plain: String): String {
        val c = Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.ENCRYPT_MODE, key()) }
        return Base64.encodeToString(c.iv + c.doFinal(plain.toByteArray()), Base64.NO_WRAP)
    }

    fun decrypt(text: String): String {
        val all = Base64.decode(text, Base64.NO_WRAP)
        val c = Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, all, 0, 12)) }
        return String(c.doFinal(all, 12, all.size - 12))
    }
}
