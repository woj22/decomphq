@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class, androidx.compose.foundation.layout.ExperimentalLayoutApi::class)

package app.spindle

import android.text.format.DateUtils
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.DownloadForOffline
import androidx.compose.material.icons.filled.LibraryMusic
import androidx.compose.material.icons.outlined.CloudDone
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

// ---------------- sign-in ----------------

@Composable
fun SignInScreen(state: AppState) {
    val scope = rememberCoroutineScope()
    val saved = state.app.credentials
    var server by rememberSaveable { mutableStateOf(saved?.server ?: "") }
    var user by rememberSaveable { mutableStateOf(saved?.user ?: "") }
    var password by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }

    val connect = {
        if (!busy) {
            busy = true; error = null
            scope.launch { error = state.signIn(server, user, password); busy = false }
        }
    }

    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Spacer(Modifier.height(24.dp))
        Icon(Icons.Filled.LibraryMusic, null, tint = Amber, modifier = Modifier.size(48.dp))
        BigTitle(if (state.needsSignIn) "Sign in again" else "Connect your music", 30)
        Text("Spindle streams from your Navidrome server. Your library, artwork and playlists are saved on this phone so you can browse offline.", color = Muted)
        SpindleField(server, { server = it }, "Server address", "http://music-phone.your-tailnet.ts.net:4533", KeyboardType.Uri)
        SpindleField(user, { user = it }, "Username", "", KeyboardType.Text)
        SpindleField(password, { password = it }, "Password", "", KeyboardType.Password, password = true, onDone = { connect() })
        error?.let { Text(it, color = Rose, fontSize = 14.sp) }
        Button({ connect() }, enabled = !busy, colors = ButtonDefaults.buttonColors(containerColor = Amber, contentColor = AmberInk), modifier = Modifier.fillMaxWidth().height(50.dp)) {
            if (busy) CircularProgressIndicator(Modifier.size(20.dp), color = AmberInk, strokeWidth = 2.dp) else Text("Connect", fontWeight = FontWeight.Bold)
        }
        Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).background(Raise).padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("Using Tailscale", fontWeight = FontWeight.SemiBold)
            Text(
                "Install Tailscale on this phone and on the device running Navidrome, and sign in to the same account on both. " +
                    "Use the server's Tailscale name, shown in the Tailscale app, followed by :4533. Your password isn't stored; only a signed token is, encrypted.",
                color = Muted, fontSize = 13.sp,
            )
        }
    }
}

@Composable
private fun SpindleField(value: String, onChange: (String) -> Unit, label: String, hint: String, type: KeyboardType, password: Boolean = false, onDone: (() -> Unit)? = null) {
    OutlinedTextField(
        value, onChange, label = { Text(label) }, placeholder = { if (hint.isNotEmpty()) Text(hint, fontSize = 13.sp) },
        singleLine = true, modifier = Modifier.fillMaxWidth(),
        visualTransformation = if (password) PasswordVisualTransformation() else androidx.compose.ui.text.input.VisualTransformation.None,
        keyboardOptions = KeyboardOptions(keyboardType = type, imeAction = if (onDone != null) ImeAction.Go else ImeAction.Next, autoCorrectEnabled = false),
        keyboardActions = androidx.compose.foundation.text.KeyboardActions(onGo = { onDone?.invoke() }),
        shape = RoundedCornerShape(10.dp),
        colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = Amber, unfocusedBorderColor = Line, unfocusedContainerColor = Raise, focusedContainerColor = Raise, focusedLabelColor = Amber),
    )
}

// ---------------- settings ----------------

@Composable
fun SettingsScreen(state: AppState, back: () -> Unit) {
    val app = state.app
    val scope = rememberCoroutineScope()
    var streamBytes by remember { mutableLongStateOf(0L) }
    var downloadBytes by remember { mutableLongStateOf(0L) }
    var cacheMax by remember { mutableLongStateOf(app.cacheMaxBytes) }
    var wifiQ by remember { mutableIntStateOf(app.wifiQuality) }
    var mobileQ by remember { mutableIntStateOf(app.mobileQuality) }
    var dlQ by remember { mutableIntStateOf(app.downloadQuality) }
    var wifiOnly by remember { mutableStateOf(app.downloadWifiOnly) }
    var confirm by remember { mutableStateOf<String?>(null) }
    var tick by remember { mutableIntStateOf(0) }

    LaunchedEffect(tick, state.downloadState, state.cachedIds) {
        withContext(Dispatchers.IO) { streamBytes = app.streamCacheBytes(); downloadBytes = app.downloadBytes() }
    }
    LaunchedEffect(Unit) { while (true) { delay(3000); tick++ } }

    val downloaded = state.downloadState.values.count { it.state == androidx.media3.exoplayer.offline.Download.STATE_COMPLETED }

    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(bottom = 24.dp)) {
        IconButton(back, Modifier.padding(start = 4.dp, top = 4.dp)) { Icon(Icons.Filled.ArrowBack, "Back") }
        Column(Modifier.padding(horizontal = 16.dp)) { BigTitle("Settings", 34) }

        Section("Server") {
            Text(app.credentials?.server ?: "", fontWeight = FontWeight.SemiBold)
            Text("Signed in as ${app.credentials?.user ?: ""}", color = Muted, fontSize = 13.sp)
            Text(
                when { !state.networkUp -> "No internet connection"; !state.reachable -> "Can't reach the server right now"; else -> "Connected" },
                color = if (state.online) Amber else Rose, fontSize = 13.sp,
            )
            TextButton({ confirm = "signout" }, contentPadding = PaddingValues(0.dp)) { Text("Sign out", color = Muted) }
        }

        Section("Library") {
            val c = state.catalog
            Text("${c.songs.size} songs · ${c.albums.size} albums · ${c.artists.size} artists · ${c.playlists.size} playlists")
            Text(
                if (c.lastSync == 0L) "Not synced yet" else "Last synced " + DateUtils.getRelativeTimeSpanString(c.lastSync, System.currentTimeMillis(), DateUtils.MINUTE_IN_MILLIS),
                color = Muted, fontSize = 13.sp,
            )
            when {
                state.syncing -> Text(state.syncProgress, color = Amber, fontSize = 13.sp)
                state.syncError != null -> Text(state.syncError!!, color = Rose, fontSize = 13.sp)
                state.lastSyncSummary != null -> Text(state.lastSyncSummary!!, color = Muted, fontSize = 13.sp)
            }
            val waiting = remember(tick) { app.pending.snapshot().size }
            if (waiting > 0) Text("$waiting change${if (waiting == 1) "" else "s"} waiting to reach the server", color = Muted, fontSize = 13.sp)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(top = 6.dp)) {
                Button({ state.sync(manual = true) }, enabled = !state.syncing, colors = ButtonDefaults.buttonColors(containerColor = Amber, contentColor = AmberInk)) {
                    Text("Refresh library", fontWeight = FontWeight.Bold)
                }
                OutlinedButton({ confirm = "rebuild" }, enabled = !state.syncing) { Text("Rebuild", color = Fg) }
            }
            Hint("Refresh downloads only what changed on the server. Rebuild reads every song again; use it if something looks out of date.")
        }

        Section("Streaming quality") {
            Text("On Wi-Fi", fontSize = 13.sp, color = Muted)
            Choices(QUALITY_CHOICES, wifiQ, ::qualityLabel) { wifiQ = it; app.wifiQuality = it }
            Text("On mobile data", fontSize = 13.sp, color = Muted, modifier = Modifier.padding(top = 8.dp))
            Choices(QUALITY_CHOICES, mobileQ, ::qualityLabel) { mobileQ = it; app.mobileQuality = it }
            Hint("Original plays your files unchanged. Lower settings use less data; the server converts them, so you can only skip ahead to parts of the song that have already loaded. Applies from the next song you start.")
        }

        Section("Streaming cache") {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Outlined.CloudDone, null, tint = Muted, modifier = Modifier.size(18.dp))
                Text("${fmtBytes(streamBytes)} of ${fmtBytes(cacheMax)} used", modifier = Modifier.padding(start = 8.dp))
            }
            LinearProgressIndicator({ (streamBytes.toFloat() / cacheMax).coerceIn(0f, 1f) }, Modifier.fillMaxWidth().padding(vertical = 6.dp).height(4.dp), color = Muted, trackColor = Line)
            Hint("Songs you've played recently, kept so they start instantly and play offline. When the cache is full, the oldest songs are removed automatically. Downloads are stored separately and never affected.")
            Text("Cache size", fontSize = 13.sp, color = Muted, modifier = Modifier.padding(top = 8.dp))
            Choices(CACHE_CHOICES, cacheMax, ::fmtBytes) { cacheMax = it; app.cacheMaxBytes = it; scope.launch { delay(1000); tick++; state.refreshCached() } }
            TextButton({ confirm = "cache" }, contentPadding = PaddingValues(0.dp)) { Text("Clear cache", color = Muted) }
        }

        Section("Downloads") {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Filled.DownloadForOffline, null, tint = Amber, modifier = Modifier.size(18.dp))
                Text("$downloaded song${if (downloaded == 1) "" else "s"} · ${fmtBytes(downloadBytes)}", modifier = Modifier.padding(start = 8.dp))
            }
            Hint("Albums, playlists and songs you chose to download. They stay on this phone until you remove them, whatever the cache size.")
            Row(Modifier.fillMaxWidth().clickable { wifiOnly = !wifiOnly; app.downloadWifiOnly = wifiOnly }.padding(vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                Text("Download on Wi-Fi only", modifier = Modifier.weight(1f))
                Switch(wifiOnly, { wifiOnly = it; app.downloadWifiOnly = it },
                    colors = SwitchDefaults.colors(checkedTrackColor = Amber, checkedThumbColor = AmberInk, uncheckedTrackColor = Raise, uncheckedBorderColor = Line))
            }
            Text("Download quality", fontSize = 13.sp, color = Muted)
            Choices(QUALITY_CHOICES, dlQ, ::qualityLabel) { dlQ = it; app.downloadQuality = it }
            Hint("Applies to new downloads.")
            TextButton({ confirm = "downloads" }, enabled = downloaded > 0 || state.pinKeys.isNotEmpty(), contentPadding = PaddingValues(0.dp)) { Text("Remove all downloads", color = Rose) }
        }

        Section("What the icons mean") {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Filled.DownloadForOffline, null, tint = Amber, modifier = Modifier.size(16.dp))
                Text("Downloaded: kept until you remove it", fontSize = 13.sp, modifier = Modifier.padding(start = 8.dp))
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Outlined.CloudDone, null, tint = Muted, modifier = Modifier.size(16.dp))
                Text("Cached: played recently, may be cleared to make room", fontSize = 13.sp, modifier = Modifier.padding(start = 8.dp))
            }
            Text("Songs with no sign stream from your server and are greyed out while you're offline.", fontSize = 13.sp, color = Muted)
        }
    }

    confirm?.let { what ->
        val (title, body, action) = when (what) {
            "signout" -> Triple("Sign out?", "This removes your saved library, downloads and cache from this phone. Your music and playlists stay on the server.", "Sign out")
            "rebuild" -> Triple("Rebuild library?", "Spindle reads every song from the server again. Your downloads, likes and playlists are kept.", "Rebuild")
            "cache" -> Triple("Clear the streaming cache?", "Recently played songs will stream again next time. Downloads are not affected.", "Clear")
            else -> Triple("Remove all downloads?", "Every downloaded song is removed from this phone. They stay in your library and can still stream.", "Remove all")
        }
        AlertDialog(
            onDismissRequest = { confirm = null }, containerColor = Raise,
            title = { Text(title) }, text = { Text(body) },
            confirmButton = {
                TextButton({
                    confirm = null
                    when (what) {
                        "signout" -> { state.signOut(); back() }
                        "rebuild" -> state.sync(full = true, manual = true)
                        "cache" -> state.clearCache()
                        else -> state.removeAllDownloads()
                    }
                    scope.launch { delay(1000); tick++ }
                }) { Text(action, color = if (what == "rebuild") Amber else Rose) }
            },
            dismissButton = { TextButton({ confirm = null }) { Text("Cancel", color = Muted) } },
        )
    }
}

@Composable
private fun Section(title: String, content: @Composable ColumnScope.() -> Unit) {
    Column(Modifier.fillMaxWidth().padding(16.dp, 20.dp, 16.dp, 0.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(title.uppercase(), color = Muted, fontSize = 11.sp, letterSpacing = 1.4.sp, fontWeight = FontWeight.SemiBold, modifier = Modifier.padding(bottom = 6.dp))
        content()
        HorizontalDivider(color = Line, modifier = Modifier.padding(top = 14.dp))
    }
}

@Composable
private fun Hint(text: String) = Text(text, color = Muted, fontSize = 12.sp, lineHeight = 17.sp)

@Composable
private fun <T> Choices(options: List<T>, selected: T, label: (T) -> String, onPick: (T) -> Unit) {
    FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        options.forEach { o ->
            FilterChip(
                selected = o == selected, onClick = { onPick(o) },
                label = { Text(label(o), fontSize = 12.sp, maxLines = 1) },
                colors = FilterChipDefaults.filterChipColors(selectedContainerColor = Amber, selectedLabelColor = AmberInk, labelColor = Muted),
                border = FilterChipDefaults.filterChipBorder(true, o == selected, borderColor = Line),
            )
        }
    }
}

fun fmtBytes(b: Long): String = when {
    b >= 1L shl 30 -> "%.1f GB".format(b / (1L shl 30).toDouble()).replace(".0 ", " ")
    b >= 1L shl 20 -> "${b shr 20} MB"
    b > 0 -> "${b shr 10} KB"
    else -> "0 MB"
}
