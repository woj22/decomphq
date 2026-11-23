package app.mapwright

import android.annotation.SuppressLint
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.util.Base64
import android.webkit.JavascriptInterface
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.widget.FrameLayout
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.enableEdgeToEdge
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.webkit.WebViewAssetLoader
import androidx.webkit.WebViewClientCompat
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.OutputStream
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap

/** Hosts the map editor (assets/index.html) full screen, fully offline. */
class MainActivity : ComponentActivity() {
    private lateinit var web: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val desk = Color.parseColor("#171C19")
        enableEdgeToEdge(SystemBarStyle.dark(desk), SystemBarStyle.dark(desk))

        val root = FrameLayout(this).apply { setBackgroundColor(desk) }
        web = WebView(this).apply { setBackgroundColor(desk) }
        root.addView(web)
        setContentView(root)
        // Keep the editor clear of the status bar, navigation bar, camera cutout and keyboard.
        ViewCompat.setOnApplyWindowInsetsListener(root) { v, insets ->
            val b = insets.getInsets(WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.displayCutout() or WindowInsetsCompat.Type.ime())
            v.setPadding(b.left, b.top, b.right, b.bottom)
            WindowInsetsCompat.CONSUMED
        }

        // Serve the bundled page from a private https address, so it behaves like a normal web page.
        val assets = WebViewAssetLoader.Builder().addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(this)).build()
        web.webViewClient = object : WebViewClientCompat() {
            override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? =
                assets.shouldInterceptRequest(request.url)

            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                if (request.url.host == "appassets.androidplatform.net") return false
                runCatching { startActivity(Intent(Intent.ACTION_VIEW, request.url)) } // anything else opens in the browser
                return true
            }
        }
        web.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            setSupportZoom(false) // the map handles its own pinch zoom
            builtInZoomControls = false
            allowFileAccess = false
            allowContentAccess = false
        }
        web.addJavascriptInterface(MapStore(this), "MapwrightAndroid")
        web.loadUrl("https://appassets.androidplatform.net/assets/index.html")
    }

    override fun onPause() {
        // Save any edit made in the last second before the app goes to the background.
        web.evaluateJavascript("window.__flush && window.__flush()", null)
        super.onPause()
    }

    override fun onDestroy() {
        web.destroy()
        super.onDestroy()
    }
}

/**
 * Storage the page uses through `window.MapwrightAndroid`: each map is a JSON file in the app's private
 * storage, and exported images go to Pictures/Mapwright where the gallery and file apps can see them.
 */
class MapStore(private val context: Context) {
    private val dir = File(context.filesDir, "maps").apply { mkdirs() }
    private val prefs = context.getSharedPreferences("mapwright", Context.MODE_PRIVATE)
    private val exports = ConcurrentHashMap<String, Pair<Uri, OutputStream>>()
    private val validId = Regex("^[a-z0-9]{1,40}$")

    private fun fileFor(id: String): File? = if (validId.matches(id)) File(dir, "$id.json") else null

    @JavascriptInterface
    fun listMaps(): String {
        val out = JSONArray()
        dir.listFiles { f -> f.name.endsWith(".json") }
            ?.mapNotNull { f -> runCatching { val o = JSONObject(f.readText()); Triple(f.nameWithoutExtension, o.optString("name", "Untitled map"), o.optLong("updatedAt")) }.getOrNull() }
            ?.sortedByDescending { it.third }
            ?.forEach { (id, name, updated) -> out.put(JSONObject().put("id", id).put("name", name).put("updatedAt", updated)) }
        return out.toString()
    }

    @JavascriptInterface
    fun loadMap(id: String): String = fileFor(id)?.takeIf { it.exists() }?.readText() ?: ""

    @JavascriptInterface
    fun saveMap(id: String, json: String): String {
        val f = fileFor(id) ?: return "error"
        return try {
            val tmp = File(dir, "$id.json.tmp")
            tmp.writeText(json)
            if (!tmp.renameTo(f)) { f.delete(); if (!tmp.renameTo(f)) return "error" }
            "ok"
        } catch (e: Exception) {
            if (context.filesDir.usableSpace < 1_000_000) "full" else "error"
        }
    }

    @JavascriptInterface
    fun deleteMap(id: String): String { fileFor(id)?.delete(); return "ok" }

    @JavascriptInterface
    fun lastMap(): String = prefs.getString("last", "") ?: ""

    @JavascriptInterface
    fun setLastMap(id: String) { prefs.edit().putString("last", id).apply() }

    /** Starts a PNG export. The image arrives as base64 in pieces through [appendPng], then [finishPng]. */
    @JavascriptInterface
    fun beginPng(filename: String): String {
        val name = filename.replace(Regex("[^A-Za-z0-9._-]"), "").ifBlank { "map.png" }
        val values = ContentValues().apply {
            put(MediaStore.Images.Media.DISPLAY_NAME, name)
            put(MediaStore.Images.Media.MIME_TYPE, "image/png")
            put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/Mapwright")
            put(MediaStore.Images.Media.IS_PENDING, 1)
        }
        return try {
            val uri = context.contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values) ?: return "Couldn't create the image file"
            val stream = context.contentResolver.openOutputStream(uri) ?: return "Couldn't create the image file"
            val job = UUID.randomUUID().toString()
            exports[job] = uri to stream
            job
        } catch (e: Exception) {
            "Couldn't create the image file: ${e.message}"
        }
    }

    @JavascriptInterface
    fun appendPng(job: String, base64Chunk: String): String {
        val (_, stream) = exports[job] ?: return "error"
        return try { stream.write(Base64.decode(base64Chunk, Base64.DEFAULT)); "ok" } catch (e: Exception) { cancel(job); "error" }
    }

    @JavascriptInterface
    fun finishPng(job: String): String {
        val (uri, stream) = exports.remove(job) ?: return "Export failed"
        return try {
            stream.close()
            context.contentResolver.update(uri, ContentValues().apply { put(MediaStore.Images.Media.IS_PENDING, 0) }, null, null)
            val name = context.contentResolver.query(uri, arrayOf(MediaStore.Images.Media.DISPLAY_NAME), null, null, null)
                ?.use { c -> if (c.moveToFirst()) c.getString(0) else null } ?: "the image"
            "Saved to Pictures/Mapwright as $name"
        } catch (e: Exception) {
            runCatching { context.contentResolver.delete(uri, null, null) }
            "Export failed: ${e.message}"
        }
    }

    private fun cancel(job: String) {
        exports.remove(job)?.let { (uri, stream) -> runCatching { stream.close() }; runCatching { context.contentResolver.delete(uri, null, null) } }
    }
}
