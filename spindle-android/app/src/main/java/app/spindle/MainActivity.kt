@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)

package app.spindle

import android.Manifest
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.QueueMusic
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.CloudDone
import androidx.compose.material.icons.outlined.CloudOff
import androidx.compose.material.icons.outlined.FavoriteBorder
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.media3.common.Player
import androidx.media3.exoplayer.offline.Download
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext

// The same dim listening-room palette as the web version.
internal val Ink = Color(0xFF12101A)
internal val Deep = Color(0xFF1A1724)
internal val Raise = Color(0xFF252131)
internal val Line = Color(0xFF332E43)
internal val Fg = Color(0xFFECE8F4)
internal val Muted = Color(0xFF9B94AD)
internal val Amber = Color(0xFFFFB547)
internal val AmberInk = Color(0xFF2A1A00)
internal val Rose = Color(0xFFFF6F7D)

private val SpindleColors = darkColorScheme(
    primary = Amber, onPrimary = AmberInk, background = Ink, onBackground = Fg,
    surface = Deep, onSurface = Fg, surfaceVariant = Raise, onSurfaceVariant = Muted,
    surfaceContainer = Deep, surfaceContainerHigh = Raise, surfaceContainerHighest = Raise,
    outline = Line, outlineVariant = Line, secondaryContainer = Raise, onSecondaryContainer = Amber,
    error = Rose,
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent { MaterialTheme(colorScheme = SpindleColors) { SpindleApp() } }
    }
}

private enum class Tab(val label: String, val icon: ImageVector) {
    Songs("Songs", Icons.Filled.MusicNote),
    Albums("Albums", Icons.Filled.Album),
    Artists("Artists", Icons.Filled.Person),
    Liked("Liked", Icons.Filled.Favorite),
    Playlists("Playlists", Icons.AutoMirrored.Filled.QueueMusic),
}

private sealed interface Detail {
    data class AlbumD(val albumId: String) : Detail
    data class ArtistD(val id: String?, val name: String) : Detail
    data class PlaylistD(val id: String) : Detail
    data object SettingsD : Detail
}

@Composable
fun SpindleApp() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val state = remember { AppState(context.applicationContext, scope) }
    DisposableEffect(Unit) { onDispose { state.dispose() } }
    val notifyLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) {}

    // Connect to the player while the app is open; check for library changes when it comes back to the front.
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    DisposableEffect(lifecycle) {
        val obs = LifecycleEventObserver { _, e ->
            when (e) {
                Lifecycle.Event.ON_START -> state.connect()
                Lifecycle.Event.ON_RESUME -> {
                    state.refreshCached()
                    if (state.signedIn && System.currentTimeMillis() - state.catalog.lastSync > 15 * 60_000) state.sync()
                }
                Lifecycle.Event.ON_STOP -> state.disconnect()
                else -> {}
            }
        }
        lifecycle.addObserver(obs)
        onDispose { lifecycle.removeObserver(obs) }
    }
    // Playback and download notifications need permission on Android 13 and later.
    LaunchedEffect(state.signedIn) {
        if (state.signedIn && Build.VERSION.SDK_INT >= 33) notifyLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
    }
    LaunchedEffect(state.isPlaying) {
        while (state.isPlaying) { state.tickPosition(); delay(500) }
    }

    var tab by rememberSaveable { mutableStateOf(Tab.Songs) }
    val stack = remember { mutableStateListOf<Detail>() }
    var nowOpen by rememberSaveable { mutableStateOf(false) }
    var menuFor by remember { mutableStateOf<Pair<Song, String?>?>(null) }
    var addToPl by remember { mutableStateOf<Song?>(null) }

    BackHandler(enabled = nowOpen || stack.isNotEmpty()) {
        if (nowOpen) nowOpen = false else stack.removeAt(stack.lastIndex)
    }

    val nav = Nav(
        album = { stack += Detail.AlbumD(it) },
        artist = { id, name -> stack += Detail.ArtistD(id, name) },
        playlist = { stack += Detail.PlaylistD(it) },
        more = { song, pid -> menuFor = song to pid },
        settings = { stack += Detail.SettingsD },
    )
    val showLibrary = state.loaded && state.signedIn && !state.needsSignIn

    Box(Modifier.fillMaxSize().background(Ink)) {
        Scaffold(
            containerColor = Ink,
            bottomBar = {
                if (showLibrary) Column(Modifier.background(Deep)) {
                    state.current?.let { MiniPlayer(state, it) { nowOpen = true } }
                    NavigationBar(containerColor = Deep, tonalElevation = 0.dp) {
                        Tab.entries.forEach { t ->
                            NavigationBarItem(
                                selected = tab == t && stack.isEmpty(),
                                onClick = { tab = t; stack.clear() },
                                icon = { Icon(t.icon, null) },
                                label = { Text(t.label, fontSize = 11.sp) },
                                colors = NavigationBarItemDefaults.colors(
                                    selectedIconColor = Amber, selectedTextColor = Amber, indicatorColor = Raise,
                                    unselectedIconColor = Muted, unselectedTextColor = Muted,
                                ),
                            )
                        }
                    }
                }
            },
        ) { pad ->
            Column(Modifier.padding(pad).statusBarsPadding()) {
                if (showLibrary) StatusBanner(state)
                Box(Modifier.weight(1f)) {
                    when {
                        !state.loaded -> Centered { CircularProgressIndicator(color = Amber) }
                        !state.signedIn || state.needsSignIn -> SignInScreen(state)
                        stack.lastOrNull() == Detail.SettingsD -> SettingsScreen(state) { stack.removeAt(stack.lastIndex) }
                        state.songs.isEmpty() && state.syncing -> FirstSync(state)
                        state.songs.isEmpty() -> EmptyLibrary(state, nav)
                        stack.isNotEmpty() -> DetailScreen(state, stack.last(), nav) { stack.removeAt(stack.lastIndex) }
                        else -> when (tab) {
                            Tab.Songs -> SongsScreen(state, nav)
                            Tab.Albums -> AlbumsScreen(state, nav)
                            Tab.Artists -> ArtistsScreen(state, nav)
                            Tab.Liked -> LikedScreen(state, nav)
                            Tab.Playlists -> PlaylistsScreen(state, nav)
                        }
                    }
                }
            }
        }

        AnimatedVisibility(
            visible = nowOpen && state.current != null,
            enter = slideInVertically { it }, exit = slideOutVertically { it },
        ) {
            state.current?.let { NowPlaying(state, it, close = { nowOpen = false }, nav = nav, onClose = { nowOpen = false }) }
        }
    }

    menuFor?.let { (song, pid) ->
        SongMenu(
            state, song, pid,
            dismiss = { menuFor = null },
            addToPlaylist = { menuFor = null; addToPl = song },
            goAlbum = { menuFor = null; nowOpen = false; stack += Detail.AlbumD(song.albumId) },
            goArtist = { menuFor = null; nowOpen = false; stack += Detail.ArtistD(song.artistId, song.artist) },
        )
    }
    addToPl?.let { song -> AddToPlaylistDialog(state, song) { addToPl = null } }
}

private class Nav(
    val album: (String) -> Unit,
    val artist: (String?, String) -> Unit,
    val playlist: (String) -> Unit,
    val more: (Song, String?) -> Unit,
    val settings: () -> Unit,
)

/** Offline notice, sync errors, and a thin line while syncing. */
@Composable
private fun StatusBanner(state: AppState) {
    val err = state.syncError
    when {
        !state.online -> Row(Modifier.fillMaxWidth().background(Raise).padding(16.dp, 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Outlined.CloudOff, null, tint = Amber, modifier = Modifier.size(18.dp))
            Text(
                if (!state.networkUp) "Offline. Downloaded and cached songs still play." else "Server not reachable (away from home?). Downloaded and cached songs still play.",
                fontSize = 13.sp, modifier = Modifier.padding(start = 10.dp).weight(1f),
            )
            if (state.networkUp) TextButton({ state.sync(manual = true) }) { Text("Retry", color = Amber) }
        }
        err != null -> Row(Modifier.fillMaxWidth().background(Raise).padding(16.dp, 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(err, fontSize = 13.sp, color = Rose, modifier = Modifier.weight(1f))
        }
    }
    if (state.syncing) LinearProgressIndicator(Modifier.fillMaxWidth().height(2.dp), color = Amber, trackColor = Ink)
}

// ---------------- screens ----------------

private enum class Sort(val label: String) { Title("Title"), Artist("Artist"), Recent("Recently added"), Played("Most played") }

@Composable
private fun SongsScreen(state: AppState, nav: Nav) {
    var query by rememberSaveable { mutableStateOf("") }
    var sort by rememberSaveable { mutableStateOf(Sort.Title) }
    val list = remember(state.songs, query, sort) {
        val q = query.trim().lowercase()
        state.songs
            .filter { q.isEmpty() || it.title.lowercase().contains(q) || it.artist.lowercase().contains(q) || it.album.lowercase().contains(q) }
            .let { l ->
                when (sort) {
                    Sort.Title -> l
                    Sort.Artist -> l.sortedWith(compareBy({ it.artist.lowercase() }, { it.album.lowercase() }, { it.disc }, { it.track }))
                    Sort.Recent -> l.sortedByDescending { it.created }
                    Sort.Played -> l.sortedWith(compareByDescending<Song> { it.playCount }.thenByDescending { it.played })
                }
            }
    }
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 16.dp)) {
        item {
            Header("Songs", "${state.songs.size} songs · ${totalTime(state.songs)}", nav.settings)
            OutlinedTextField(
                value = query, onValueChange = { query = it },
                placeholder = { Text("Search title, artist or album") },
                leadingIcon = { Icon(Icons.Filled.Search, null) },
                trailingIcon = { if (query.isNotEmpty()) IconButton({ query = "" }) { Icon(Icons.Filled.Close, "Clear") } },
                singleLine = true,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                shape = RoundedCornerShape(10.dp),
                colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = Amber, unfocusedBorderColor = Line, unfocusedContainerColor = Raise, focusedContainerColor = Raise),
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
            )
            Row(Modifier.padding(16.dp, 12.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                PlayButtons(list, state)
                Spacer(Modifier.weight(1f))
                SortChip(sort) { sort = it }
            }
        }
        if (list.isEmpty()) item { Text("Nothing matches \"$query\".", color = Muted, modifier = Modifier.padding(16.dp)) }
        itemsIndexed(list, key = { _, s -> s.id }) { i, s -> SongRow(state, s, onClick = { state.play(list, i) }, onMore = { nav.more(s, null) }) }
    }
}

@Composable
private fun SortChip(sort: Sort, onPick: (Sort) -> Unit) {
    var open by remember { mutableStateOf(false) }
    Box {
        AssistChip(onClick = { open = true }, label = { Text(sort.label) }, leadingIcon = { Icon(Icons.Filled.Sort, null, Modifier.size(18.dp)) },
            colors = AssistChipDefaults.assistChipColors(labelColor = Muted, leadingIconContentColor = Muted), border = AssistChipDefaults.assistChipBorder(true, borderColor = Line))
        DropdownMenu(open, { open = false }, containerColor = Raise) {
            Sort.entries.forEach { s -> DropdownMenuItem(text = { Text(s.label, color = if (s == sort) Amber else Fg) }, onClick = { onPick(s); open = false }) }
        }
    }
}

@Composable
private fun AlbumsScreen(state: AppState, nav: Nav) {
    val albums = remember(state.catalog.albums) { state.catalog.albums.sortedBy { it.name.lowercase() } }
    LazyVerticalGrid(GridCells.Adaptive(150.dp), Modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp, 0.dp, 16.dp, 16.dp),
        horizontalArrangement = Arrangement.spacedBy(14.dp), verticalArrangement = Arrangement.spacedBy(18.dp)) {
        item(span = { GridItemSpan(maxLineSpan) }) { Header("Albums", "${albums.size} albums", nav.settings, pad = false) }
        items(albums, key = { it.id }) { a ->
            Column(Modifier.clip(RoundedCornerShape(8.dp)).clickable { nav.album(a.id) }) {
                Box {
                    Art(a.coverArt, Modifier.fillMaxWidth().aspectRatio(1f), 8.dp, big = true, fallbackKey = a.name)
                    if (state.isPinned(Pins.album(a.id))) Icon(Icons.Filled.DownloadForOffline, "Downloaded", tint = Amber,
                        modifier = Modifier.align(Alignment.BottomEnd).padding(6.dp).size(22.dp).background(Ink.copy(alpha = 0.6f), CircleShape))
                }
                Text(a.name, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.padding(top = 8.dp))
                Text(a.artist, color = Muted, fontSize = 13.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
        }
    }
}

/** Songs credited to an artist, either on the track or as the album artist. */
private fun songsByArtist(state: AppState, id: String?, name: String): List<Song> =
    state.songs.filter { s -> if (id != null) s.artistId == id || state.albumsById[s.albumId]?.artistId == id else s.artist == name }

@Composable
private fun ArtistsScreen(state: AppState, nav: Nav) {
    val artists = remember(state.catalog) {
        val songCount = HashMap<String, Int>()
        state.songs.forEach { s ->
            val ids = setOfNotNull(s.artistId, state.albumsById[s.albumId]?.artistId)
            ids.forEach { songCount[it] = (songCount[it] ?: 0) + 1 }
        }
        state.catalog.artists.sortedBy { it.name.lowercase() }.map { it to (songCount[it.id] ?: 0) }
    }
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 16.dp)) {
        item { Header("Artists", "${artists.size} artists", nav.settings) }
        items(artists, key = { it.first.id }) { (artist, songs) ->
            Row(Modifier.fillMaxWidth().clickable { nav.artist(artist.id, artist.name) }.padding(16.dp, 8.dp), verticalAlignment = Alignment.CenterVertically) {
                Art(artist.coverArt, Modifier.size(52.dp), 26.dp, fallbackKey = artist.name)
                Column(Modifier.padding(start = 14.dp).weight(1f)) {
                    Text(artist.name, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text("$songs songs · ${artist.albumCount} album${if (artist.albumCount == 1) "" else "s"}", color = Muted, fontSize = 13.sp)
                }
                Icon(Icons.Filled.ChevronRight, null, tint = Muted)
            }
        }
    }
}

@Composable
private fun LikedScreen(state: AppState, nav: Nav) {
    val list = remember(state.songs, state.likes) { state.songs.filter { it.id in state.likes } }
    TrackListScreen(state, "Liked songs", "${list.size} songs" + if (list.isNotEmpty()) " · ${totalTime(list)}" else "", list, nav, null,
        empty = "Tap the heart on any song to save it here. Likes sync with your Navidrome favourites.", pinKey = Pins.LIKED, settings = nav.settings)
}

@Composable
private fun PlaylistsScreen(state: AppState, nav: Nav) {
    var creating by remember { mutableStateOf(false) }
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 16.dp)) {
        item {
            Header("Playlists", "${state.playlists.size} playlists", nav.settings)
            Row(Modifier.fillMaxWidth().clickable { creating = true }.padding(16.dp, 8.dp), verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(52.dp).clip(RoundedCornerShape(6.dp)).background(Raise), contentAlignment = Alignment.Center) { Icon(Icons.Filled.Add, null, tint = Amber) }
                Text("New playlist", fontWeight = FontWeight.SemiBold, modifier = Modifier.padding(start = 14.dp))
            }
        }
        items(state.playlists, key = { it.id }) { p ->
            val songs = state.songsOf(p)
            Row(Modifier.fillMaxWidth().clickable { nav.playlist(p.id) }.padding(16.dp, 8.dp), verticalAlignment = Alignment.CenterVertically) {
                Art(state.coverFor(songs.firstOrNull()), Modifier.size(52.dp), 6.dp, fallbackKey = p.name)
                Column(Modifier.padding(start = 14.dp).weight(1f)) {
                    Text(p.name, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text("${songs.size} songs", color = Muted, fontSize = 13.sp)
                }
                if (state.isPinned(Pins.playlist(p.id))) Icon(Icons.Filled.DownloadForOffline, "Downloaded", tint = Amber, modifier = Modifier.size(18.dp))
            }
        }
    }
    if (creating) NameDialog("New playlist", "", "Create", { creating = false }) { state.createPlaylist(it); creating = false }
}

@Composable
private fun DetailScreen(state: AppState, d: Detail, nav: Nav, back: () -> Unit) {
    when (d) {
        is Detail.AlbumD -> {
            val list = remember(state.songs, d) { state.songs.filter { it.albumId == d.albumId }.sortedWith(compareBy({ it.disc }, { it.track }, { it.title.lowercase() })) }
            val album = state.albumsById[d.albumId]
            if (list.isEmpty() || album == null) return back()
            TrackListScreen(state, album.name, album.artist + (if (album.year > 0) " · ${album.year}" else "") + " · ${list.size} songs · ${totalTime(list)}",
                list, nav, null, back = back, cover = album.coverArt, numbered = true, pinKey = Pins.album(album.id))
        }
        is Detail.ArtistD -> {
            val list = remember(state.songs, d) {
                songsByArtist(state, d.id, d.name).sortedWith(compareBy({ state.albumsById[it.albumId]?.year ?: 0 }, { it.album.lowercase() }, { it.disc }, { it.track }))
            }
            if (list.isEmpty()) return back()
            val cover = state.catalog.artists.find { it.id == d.id }?.coverArt ?: state.coverFor(list.first())
            TrackListScreen(state, d.name, "${list.size} songs · ${totalTime(list)}", list, nav, null, back = back, cover = cover)
        }
        is Detail.PlaylistD -> {
            val p = state.playlists.find { it.id == d.id } ?: return back()
            val list = state.songsOf(p)
            var renaming by remember { mutableStateOf(false) }
            var confirmDelete by remember { mutableStateOf(false) }
            TrackListScreen(state, p.name, "${list.size} songs" + if (list.isNotEmpty()) " · ${totalTime(list)}" else "", list, nav, p.id, back = back,
                cover = state.coverFor(list.firstOrNull()), fallbackKey = p.name, empty = "Add songs with the ⋮ button next to any song.",
                pinKey = Pins.playlist(p.id),
                extra = {
                    TextButton({ renaming = true }) { Text("Rename", color = Muted) }
                    TextButton({ confirmDelete = true }) { Text("Delete", color = Muted) }
                })
            if (renaming) NameDialog("Rename playlist", p.name, "Save", { renaming = false }) { state.renamePlaylist(p.id, it); renaming = false }
            if (confirmDelete) AlertDialog(
                onDismissRequest = { confirmDelete = false }, containerColor = Raise,
                title = { Text("Delete \"${p.name}\"?") }, text = { Text("It's deleted on your server too. The songs stay in your library.") },
                confirmButton = { TextButton({ confirmDelete = false; state.deletePlaylist(p.id) }) { Text("Delete", color = Rose) } },
                dismissButton = { TextButton({ confirmDelete = false }) { Text("Cancel", color = Muted) } },
            )
        }
        Detail.SettingsD -> SettingsScreen(state, back)
    }
}

@Composable
private fun TrackListScreen(
    state: AppState, title: String, sub: String, list: List<Song>, nav: Nav, playlistId: String?,
    back: (() -> Unit)? = null, cover: String? = null, fallbackKey: String? = null, numbered: Boolean = false,
    empty: String = "", pinKey: String? = null, settings: (() -> Unit)? = null, extra: @Composable RowScope.() -> Unit = {},
) {
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 16.dp)) {
        item {
            if (back != null) IconButton(back, Modifier.padding(start = 4.dp, top = 4.dp)) { Icon(Icons.Filled.ArrowBack, "Back") }
            if (back != null) {
                Row(Modifier.padding(16.dp, 8.dp), verticalAlignment = Alignment.Bottom) {
                    Art(cover, Modifier.size(128.dp), 10.dp, big = true, fallbackKey = fallbackKey ?: title, size = ArtCache.LARGE)
                    Column(Modifier.padding(start = 16.dp)) { BigTitle(title, 28); Text(sub, color = Muted, fontSize = 13.sp) }
                }
            } else Header(title, sub, settings)
            Row(Modifier.padding(16.dp, 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                if (list.isNotEmpty()) PlayButtons(list, state)
                Spacer(Modifier.weight(1f)); extra()
            }
            if (pinKey != null && list.isNotEmpty()) DownloadToggle(state, pinKey, list)
            if (list.isEmpty() && empty.isNotEmpty()) Text(empty, color = Muted, modifier = Modifier.padding(16.dp))
        }
        itemsIndexed(list, key = { i, s -> "${s.id}-$i" }) { i, s ->
            SongRow(state, s, number = if (numbered) (if (s.track > 0) s.track else i + 1) else null,
                onClick = { state.play(list, i) }, onMore = { nav.more(s, playlistId) })
        }
    }
}

/** Keep a whole album, playlist or Liked songs on the phone, with progress while it downloads. */
@Composable
private fun DownloadToggle(state: AppState, key: String, list: List<Song>) {
    val pinned = state.isPinned(key)
    var confirmRemove by remember { mutableStateOf(false) }
    val done = list.count { state.availability(it) == Availability.Downloaded }
    val waitingForWifi = pinned && done < list.size && state.app.downloadWifiOnly && !state.app.unmetered
    Row(
        Modifier.fillMaxWidth().clickable { if (pinned) confirmRemove = true else state.setPinned(key, true) }.padding(16.dp, 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(if (pinned && done == list.size) Icons.Filled.DownloadForOffline else Icons.Filled.Download, null, tint = if (pinned) Amber else Muted)
        Column(Modifier.padding(start = 12.dp).weight(1f)) {
            Text(
                when {
                    !pinned -> "Download"
                    done == list.size -> "Downloaded"
                    waitingForWifi -> "Waiting for Wi-Fi · $done of ${list.size}"
                    else -> "Downloading · $done of ${list.size}"
                },
                fontWeight = FontWeight.SemiBold, color = if (pinned) Amber else Fg,
            )
            Text(if (pinned) "Kept on this phone until you remove it" else "Keep these songs on this phone for offline listening", color = Muted, fontSize = 12.sp)
        }
        Switch(pinned, { on -> if (on) state.setPinned(key, true) else confirmRemove = true },
            colors = SwitchDefaults.colors(checkedTrackColor = Amber, checkedThumbColor = AmberInk, uncheckedTrackColor = Raise, uncheckedBorderColor = Line))
    }
    if (pinned && done < list.size) LinearProgressIndicator({ done.toFloat() / list.size }, Modifier.fillMaxWidth().padding(horizontal = 16.dp).height(3.dp), color = Amber, trackColor = Line)
    if (confirmRemove) AlertDialog(
        onDismissRequest = { confirmRemove = false }, containerColor = Raise,
        title = { Text("Remove download?") },
        text = { Text("These songs stay in your library and can still stream. Songs also kept by another album or playlist stay downloaded.") },
        confirmButton = { TextButton({ confirmRemove = false; state.setPinned(key, false) }) { Text("Remove", color = Rose) } },
        dismissButton = { TextButton({ confirmRemove = false }) { Text("Cancel", color = Muted) } },
    )
}

// ---------------- pieces ----------------

@Composable
internal fun Header(title: String, sub: String, onSettings: (() -> Unit)? = null, pad: Boolean = true) {
    Row(if (pad) Modifier.padding(16.dp, 20.dp, 4.dp, 12.dp) else Modifier.padding(top = 20.dp, bottom = 4.dp), verticalAlignment = Alignment.Top) {
        Column(Modifier.weight(1f)) {
            BigTitle(title, 34)
            Text(sub, color = Muted, fontSize = 13.sp)
        }
        if (onSettings != null) IconButton(onSettings) { Icon(Icons.Filled.Settings, "Settings", tint = Muted) }
    }
}

@Composable
internal fun BigTitle(text: String, size: Int) =
    Text(text, fontSize = size.sp, fontWeight = FontWeight.ExtraBold, letterSpacing = (-0.5).sp, lineHeight = (size + 4).sp, maxLines = 2, overflow = TextOverflow.Ellipsis)

@Composable
private fun PlayButtons(list: List<Song>, state: AppState) {
    Button({ state.play(list, 0) }, colors = ButtonDefaults.buttonColors(containerColor = Amber, contentColor = AmberInk), enabled = list.isNotEmpty()) {
        Icon(Icons.Filled.PlayArrow, null); Spacer(Modifier.width(4.dp)); Text("Play", fontWeight = FontWeight.Bold)
    }
    OutlinedButton({ state.play(list, 0, shuffled = true) }, border = ButtonDefaults.outlinedButtonBorder(true).copy(brush = Brush.linearGradient(listOf(Line, Line))), enabled = list.isNotEmpty()) {
        Icon(Icons.Filled.Shuffle, null, tint = Fg, modifier = Modifier.size(18.dp)); Spacer(Modifier.width(6.dp)); Text("Shuffle", color = Fg)
    }
}

/** Downloaded (kept until removed) and cached (recently played, may be cleared) look different at a glance. */
@Composable
private fun AvailabilityIcon(a: Availability) {
    when (a) {
        Availability.Downloaded -> Icon(Icons.Filled.DownloadForOffline, "Downloaded", tint = Amber, modifier = Modifier.size(16.dp))
        Availability.Downloading -> CircularProgressIndicator(Modifier.size(13.dp), color = Amber, strokeWidth = 2.dp)
        Availability.Cached -> Icon(Icons.Outlined.CloudDone, "Cached", tint = Muted, modifier = Modifier.size(16.dp))
        Availability.StreamOnly -> {}
    }
}

@Composable
private fun SongRow(state: AppState, s: Song, number: Int? = null, onClick: () -> Unit, onMore: () -> Unit) {
    val playing = state.current?.id == s.id
    val playable = state.playable(s)
    Row(
        Modifier.fillMaxWidth().clickable(enabled = playable, onClick = onClick).alpha(if (playable) 1f else 0.4f)
            .padding(start = 16.dp, top = 6.dp, bottom = 6.dp, end = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (number != null) Text("$number", color = if (playing) Amber else Muted, fontSize = 13.sp, modifier = Modifier.width(30.dp))
        else Art(state.coverFor(s), Modifier.size(48.dp), 6.dp, fallbackKey = s.album)
        Column(Modifier.padding(start = if (number != null) 0.dp else 12.dp).weight(1f)) {
            Text(s.title, color = if (playing) Amber else Fg, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text(s.artist, color = Muted, fontSize = 13.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
            if (s.id in state.likes) Icon(Icons.Filled.Favorite, "Liked", tint = Rose, modifier = Modifier.size(16.dp))
            AvailabilityIcon(state.availability(s))
        }
        Text(fmt(s.durationMs), color = Muted, fontSize = 12.sp, modifier = Modifier.padding(start = 10.dp))
        IconButton(onMore) { Icon(Icons.Filled.MoreVert, "More", tint = Muted) }
    }
}

@Composable
private fun SongMenu(state: AppState, song: Song, playlistId: String?, dismiss: () -> Unit, addToPlaylist: () -> Unit, goAlbum: () -> Unit, goArtist: () -> Unit) {
    ModalBottomSheet(onDismissRequest = dismiss, containerColor = Deep) {
        Row(Modifier.padding(20.dp, 0.dp, 20.dp, 12.dp), verticalAlignment = Alignment.CenterVertically) {
            Art(state.coverFor(song), Modifier.size(52.dp), 6.dp, fallbackKey = song.album)
            Column(Modifier.padding(start = 12.dp)) {
                Text(song.title, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(song.artist, color = Muted, fontSize = 13.sp, maxLines = 1)
                val a = state.availability(song)
                Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(top = 4.dp)) {
                    AvailabilityIcon(a)
                    Text(
                        when (a) {
                            Availability.Downloaded -> "Downloaded · kept until you remove it"
                            Availability.Downloading -> "Downloading"
                            Availability.Cached -> "Cached · may be cleared to make room"
                            Availability.StreamOnly -> "Streams from your server"
                        },
                        color = if (a == Availability.Downloaded) Amber else Muted, fontSize = 12.sp,
                        modifier = Modifier.padding(start = if (a == Availability.StreamOnly) 0.dp else 6.dp),
                    )
                }
            }
        }
        HorizontalDivider(color = Line)
        val liked = song.id in state.likes
        MenuItem(if (liked) Icons.Filled.Favorite else Icons.Outlined.FavoriteBorder, if (liked) "Remove from Liked" else "Like") { state.toggleLike(song); dismiss() }
        MenuItem(Icons.Filled.PlaylistPlay, "Play next") { state.playNext(song); dismiss() }
        MenuItem(Icons.Filled.PlaylistAdd, "Add to playlist", addToPlaylist)
        val songPin = Pins.song(song.id)
        if (state.isPinned(songPin)) MenuItem(Icons.Filled.RemoveCircleOutline, "Remove download") { state.setPinned(songPin, false); dismiss() }
        else if (state.availability(song) != Availability.Downloaded) MenuItem(Icons.Filled.Download, "Download") { state.setPinned(songPin, true); dismiss() }
        if (playlistId != null) MenuItem(Icons.Filled.RemoveCircleOutline, "Remove from this playlist") { state.removeFromPlaylist(playlistId, song); dismiss() }
        MenuItem(Icons.Filled.Album, "Go to album", goAlbum)
        MenuItem(Icons.Filled.Person, "Go to artist", goArtist)
        Spacer(Modifier.navigationBarsPadding().height(12.dp))
    }
}

@Composable
private fun MenuItem(icon: ImageVector, label: String, onClick: () -> Unit) {
    Row(Modifier.fillMaxWidth().clickable(onClick = onClick).padding(20.dp, 14.dp), verticalAlignment = Alignment.CenterVertically) {
        Icon(icon, null, tint = Muted); Text(label, modifier = Modifier.padding(start = 16.dp))
    }
}

@Composable
private fun AddToPlaylistDialog(state: AppState, song: Song, dismiss: () -> Unit) {
    var newName by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = dismiss, containerColor = Raise,
        title = { Text("Add to playlist") },
        text = {
            Column {
                state.playlists.forEach { p ->
                    val has = song.id in p.songIds
                    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(6.dp)).clickable(enabled = !has) { state.addToPlaylist(p.id, song); dismiss() }.padding(8.dp, 12.dp)) {
                        Text(p.name, Modifier.weight(1f), color = if (has) Muted else Fg)
                        if (has) Text("Added", color = Muted, fontSize = 12.sp)
                    }
                }
                OutlinedTextField(newName, { newName = it }, placeholder = { Text("New playlist name") }, singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = Amber, unfocusedBorderColor = Line), modifier = Modifier.fillMaxWidth().padding(top = 8.dp))
            }
        },
        confirmButton = { TextButton({ state.createPlaylist(newName, song); dismiss() }, enabled = newName.isNotBlank()) { Text("Create", color = if (newName.isNotBlank()) Amber else Muted) } },
        dismissButton = { TextButton(dismiss) { Text("Cancel", color = Muted) } },
    )
}

@Composable
private fun NameDialog(title: String, initial: String, action: String, dismiss: () -> Unit, done: (String) -> Unit) {
    var name by remember { mutableStateOf(initial) }
    AlertDialog(
        onDismissRequest = dismiss, containerColor = Raise, title = { Text(title) },
        text = { OutlinedTextField(name, { name = it }, singleLine = true, placeholder = { Text("Playlist name") },
            colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = Amber, unfocusedBorderColor = Line)) },
        confirmButton = { TextButton({ done(name) }, enabled = name.isNotBlank()) { Text(action, color = if (name.isNotBlank()) Amber else Muted) } },
        dismissButton = { TextButton(dismiss) { Text("Cancel", color = Muted) } },
    )
}

@Composable
private fun MiniPlayer(state: AppState, s: Song, open: () -> Unit) {
    Column(Modifier.fillMaxWidth().clickable(onClick = open)) {
        val p = if (state.duration > 0) (state.position.toFloat() / state.duration).coerceIn(0f, 1f) else 0f
        Box(Modifier.fillMaxWidth().height(2.dp).background(Line)) { Box(Modifier.fillMaxWidth(p).fillMaxHeight().background(Amber)) }
        Row(Modifier.padding(12.dp, 8.dp, 4.dp, 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Art(state.coverFor(s), Modifier.size(44.dp), 6.dp, fallbackKey = s.album)
            Column(Modifier.padding(start = 12.dp).weight(1f)) {
                Text(s.title, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(s.artist, color = Muted, fontSize = 13.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            IconButton({ state.toggle() }) { Icon(if (state.isPlaying) Icons.Filled.Pause else Icons.Filled.PlayArrow, if (state.isPlaying) "Pause" else "Play", Modifier.size(30.dp)) }
            IconButton({ state.next() }) { Icon(Icons.Filled.SkipNext, "Next") }
        }
    }
}

@Composable
private fun NowPlaying(state: AppState, s: Song, close: () -> Unit, nav: Nav, onClose: () -> Unit) {
    var dragging by remember { mutableStateOf<Float?>(null) }
    Column(
        Modifier.fillMaxSize().background(Brush.verticalGradient(listOf(hueColor(s.album, 0.32f, 0.22f), Ink, Ink)))
            .clickable(enabled = false) {}.statusBarsPadding().navigationBarsPadding().padding(horizontal = 24.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(vertical = 8.dp)) {
            IconButton(close, Modifier.offset(x = (-12).dp)) { Icon(Icons.Filled.KeyboardArrowDown, "Close", Modifier.size(30.dp)) }
            Text("Now playing", color = Muted, fontSize = 12.sp, letterSpacing = 1.5.sp, modifier = Modifier.weight(1f))
            IconButton({ nav.more(s, null) }, Modifier.offset(x = 12.dp)) { Icon(Icons.Filled.MoreVert, "More") }
        }
        Spacer(Modifier.weight(0.4f))
        Art(state.coverFor(s), Modifier.fillMaxWidth().aspectRatio(1f), 12.dp, big = true, fallbackKey = s.album, size = ArtCache.LARGE)
        Spacer(Modifier.weight(0.4f))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(s.title, fontSize = 24.sp, fontWeight = FontWeight.ExtraBold, maxLines = 2, overflow = TextOverflow.Ellipsis, lineHeight = 28.sp)
                Text(s.artist, color = Muted, fontSize = 16.sp, maxLines = 1, overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.clickable { onClose(); nav.artist(s.artistId, s.artist) })
            }
            val liked = s.id in state.likes
            IconButton({ state.toggleLike(s) }) { Icon(if (liked) Icons.Filled.Favorite else Icons.Outlined.FavoriteBorder, "Like", tint = if (liked) Rose else Fg, modifier = Modifier.size(28.dp)) }
        }
        val dur = state.duration.coerceAtLeast(1)
        Slider(
            value = dragging ?: (state.position.toFloat() / dur).coerceIn(0f, 1f),
            onValueChange = { dragging = it },
            onValueChangeFinished = { dragging?.let { state.seekTo((it * dur).toLong()) }; dragging = null },
            colors = SliderDefaults.colors(thumbColor = Fg, activeTrackColor = Amber, inactiveTrackColor = Line),
            modifier = Modifier.padding(top = 12.dp),
        )
        Row {
            Text(fmt(dragging?.let { (it * dur).toLong() } ?: state.position), color = Muted, fontSize = 12.sp)
            Spacer(Modifier.weight(1f))
            Text(fmt(state.duration), color = Muted, fontSize = 12.sp)
        }
        Row(Modifier.fillMaxWidth().padding(vertical = 16.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            IconButton({ state.toggleShuffle() }) { Icon(Icons.Filled.Shuffle, "Shuffle", tint = if (state.shuffle) Amber else Muted) }
            IconButton({ state.prev() }, Modifier.size(56.dp)) { Icon(Icons.Filled.SkipPrevious, "Previous", Modifier.size(38.dp)) }
            Box(Modifier.size(72.dp).clip(CircleShape).background(Amber).clickable { state.toggle() }, contentAlignment = Alignment.Center) {
                Icon(if (state.isPlaying) Icons.Filled.Pause else Icons.Filled.PlayArrow, if (state.isPlaying) "Pause" else "Play", tint = AmberInk, modifier = Modifier.size(40.dp))
            }
            IconButton({ state.next() }, Modifier.size(56.dp)) { Icon(Icons.Filled.SkipNext, "Next", Modifier.size(38.dp)) }
            IconButton({ state.cycleRepeat() }) {
                Icon(if (state.repeat == Player.REPEAT_MODE_ONE) Icons.Filled.RepeatOne else Icons.Filled.Repeat, "Repeat",
                    tint = if (state.repeat == Player.REPEAT_MODE_OFF) Muted else Amber)
            }
        }
        Spacer(Modifier.weight(0.3f))
    }
}

/** Cover art from the server, kept on the phone; a generated cover when there is none. */
@Composable
internal fun Art(coverId: String?, modifier: Modifier, corner: Dp, big: Boolean = false, fallbackKey: String? = null, size: Int = ArtCache.SMALL) {
    val context = LocalContext.current
    var bmp by remember(coverId, size) { mutableStateOf<ImageBitmap?>(coverId?.let { ArtCache.peek(it, size) }) }
    LaunchedEffect(coverId, size) {
        if (coverId != null && bmp == null) bmp = withContext(Dispatchers.IO) { ArtCache.load(context, Spindle.get(context).client, coverId, size) }
    }
    Box(modifier.clip(RoundedCornerShape(corner))) {
        val b = bmp
        if (b != null) Image(b, null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
        else {
            val name = fallbackKey ?: "Spindle"
            Box(Modifier.fillMaxSize().background(Brush.linearGradient(listOf(hueColor(name, 0.55f, 0.38f), hueColor(name, 0.6f, 0.22f, shift = 50f)))))
            if (big) Text(name.split(" ").first().take(8), color = Color.White.copy(alpha = 0.5f), fontWeight = FontWeight.ExtraBold, fontSize = 26.sp,
                modifier = Modifier.align(Alignment.BottomStart).padding(10.dp), maxLines = 1)
            else Icon(Icons.Filled.MusicNote, null, tint = Color.White.copy(alpha = 0.45f), modifier = Modifier.align(Alignment.Center).fillMaxSize(0.45f))
        }
    }
}

@Composable
private fun FirstSync(state: AppState) {
    Centered {
        CircularProgressIndicator(color = Amber)
        Text("Loading your library", fontSize = 22.sp, fontWeight = FontWeight.ExtraBold, modifier = Modifier.padding(top = 20.dp))
        Text(state.syncProgress.ifBlank { "Connecting" }, color = Muted, modifier = Modifier.padding(top = 8.dp))
        Text("This takes longest the first time. After that, only changes are downloaded.", color = Muted, fontSize = 13.sp, modifier = Modifier.padding(top = 16.dp))
    }
}

@Composable
private fun EmptyLibrary(state: AppState, nav: Nav) {
    Centered {
        Icon(Icons.Filled.Album, null, tint = Amber, modifier = Modifier.size(56.dp))
        Text(if (state.online) "Your server has no music yet" else "Your library hasn't loaded yet", fontSize = 22.sp, fontWeight = FontWeight.ExtraBold, modifier = Modifier.padding(top = 16.dp))
        Text(
            if (state.online) "Add music to Navidrome's music folder on your server device and let it finish scanning. Then refresh here."
            else "Spindle needs to reach your server once to load your library. Connect to the same Wi-Fi as your server phone and check that Navidrome is running.",
            color = Muted, modifier = Modifier.padding(top = 8.dp, bottom = 20.dp),
        )
        Button({ state.sync(manual = true) }, colors = ButtonDefaults.buttonColors(containerColor = Amber, contentColor = AmberInk)) { Text("Refresh library", fontWeight = FontWeight.Bold) }
        TextButton(nav.settings) { Text("Settings", color = Muted) }
    }
}

@Composable
internal fun Centered(content: @Composable ColumnScope.() -> Unit) =
    Column(Modifier.fillMaxSize().padding(32.dp), verticalArrangement = Arrangement.Center, horizontalAlignment = Alignment.CenterHorizontally, content = content)

private fun hueColor(key: String, s: Float, l: Float, shift: Float = 0f): Color {
    var h = 0L
    for (c in key) h = (h * 31 + c.code) and 0xffffffffL
    return Color.hsl(((h % 360) + shift) % 360, s, l)
}

private fun fmt(ms: Long): String { val s = (ms / 1000).coerceAtLeast(0); return "${s / 60}:${(s % 60).toString().padStart(2, '0')}" }

private fun totalTime(list: List<Song>): String {
    val m = list.sumOf { it.durationMs } / 60000
    return if (m >= 60) "${m / 60} hr ${m % 60} min" else "$m min"
}
