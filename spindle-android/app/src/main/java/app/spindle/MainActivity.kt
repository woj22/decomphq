@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)

package app.spindle

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
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
import androidx.compose.foundation.lazy.LazyListScope
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
import androidx.compose.material.icons.outlined.FavoriteBorder
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
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
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext

// The same dim listening-room palette as the web version.
private val Ink = Color(0xFF12101A)
private val Deep = Color(0xFF1A1724)
private val Raise = Color(0xFF252131)
private val Line = Color(0xFF332E43)
private val Fg = Color(0xFFECE8F4)
private val Muted = Color(0xFF9B94AD)
private val Amber = Color(0xFFFFB547)
private val AmberInk = Color(0xFF2A1A00)
private val Rose = Color(0xFFFF6F7D)

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
    data class AlbumD(val albumId: Long) : Detail
    data class ArtistD(val name: String) : Detail
    data class PlaylistD(val id: String) : Detail
}

private val audioPermission =
    if (Build.VERSION.SDK_INT >= 33) Manifest.permission.READ_MEDIA_AUDIO else Manifest.permission.READ_EXTERNAL_STORAGE

@Composable
fun SpindleApp() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val state = remember { AppState(context.applicationContext, scope) }
    var granted by remember { mutableStateOf(ContextCompat.checkSelfPermission(context, audioPermission) == PackageManager.PERMISSION_GRANTED) }
    var asked by remember { mutableStateOf(false) }
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { res ->
        asked = true
        granted = res[audioPermission] == true
    }

    // Connect to the player while the app is open; rescan the music each time it comes back to the front.
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    DisposableEffect(lifecycle, granted) {
        val obs = LifecycleEventObserver { _, e ->
            when (e) {
                Lifecycle.Event.ON_START -> state.connect()
                Lifecycle.Event.ON_RESUME -> {
                    granted = ContextCompat.checkSelfPermission(context, audioPermission) == PackageManager.PERMISSION_GRANTED
                    if (granted) state.rescan()
                }
                Lifecycle.Event.ON_STOP -> state.disconnect()
                else -> {}
            }
        }
        lifecycle.addObserver(obs)
        onDispose { lifecycle.removeObserver(obs) }
    }
    LaunchedEffect(Unit) {
        if (!granted) {
            val perms = buildList { add(audioPermission); if (Build.VERSION.SDK_INT >= 33) add(Manifest.permission.POST_NOTIFICATIONS) }
            launcher.launch(perms.toTypedArray())
        }
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
        artist = { stack += Detail.ArtistD(it) },
        playlist = { stack += Detail.PlaylistD(it) },
        more = { song, pid -> menuFor = song to pid },
    )

    Box(Modifier.fillMaxSize().background(Ink)) {
        Scaffold(
            containerColor = Ink,
            bottomBar = {
                Column(Modifier.background(Deep)) {
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
            Box(Modifier.padding(pad).statusBarsPadding()) {
                when {
                    !granted -> PermissionScreen(asked) { launcher.launch(arrayOf(audioPermission)) }
                    !state.scanned -> Centered { CircularProgressIndicator(color = Amber) }
                    state.songs.isEmpty() -> EmptyLibrary { state.rescan() }
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
            goArtist = { menuFor = null; nowOpen = false; stack += Detail.ArtistD(song.artist) },
        )
    }
    addToPl?.let { song -> AddToPlaylistDialog(state, song) { addToPl = null } }
}

private class Nav(
    val album: (Long) -> Unit,
    val artist: (String) -> Unit,
    val playlist: (String) -> Unit,
    val more: (Song, String?) -> Unit,
)

// ---------------- screens ----------------

private enum class Sort(val label: String) { Title("Title"), Artist("Artist"), Recent("Recently added") }

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
                    Sort.Artist -> l.sortedWith(compareBy({ it.artist.lowercase() }, { it.album.lowercase() }, { it.track }))
                    Sort.Recent -> l.sortedByDescending { it.dateAdded }
                }
            }
    }
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 16.dp)) {
        item {
            Header("Songs", "${state.songs.size} songs · ${totalTime(state.songs)}")
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

private data class AlbumInfo(val id: Long, val name: String, val artist: String, val songs: List<Song>)

@Composable
private fun AlbumsScreen(state: AppState, nav: Nav) {
    val albums = remember(state.songs) {
        state.songs.groupBy { it.albumId }.map { (id, s) ->
            val artists = s.map { it.artist }.distinct()
            AlbumInfo(id, s.first().album, if (artists.size == 1) artists[0] else "Various artists", s)
        }.sortedBy { it.name.lowercase() }
    }
    LazyVerticalGrid(GridCells.Adaptive(150.dp), Modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp, 0.dp, 16.dp, 16.dp),
        horizontalArrangement = Arrangement.spacedBy(14.dp), verticalArrangement = Arrangement.spacedBy(18.dp)) {
        item(span = { GridItemSpan(maxLineSpan) }) { Header("Albums", "${albums.size} albums", pad = false) }
        items(albums, key = { it.id }) { a ->
            Column(Modifier.clip(RoundedCornerShape(8.dp)).clickable { nav.album(a.id) }) {
                Art(a.songs.first(), Modifier.fillMaxWidth().aspectRatio(1f), 8.dp, big = true)
                Text(a.name, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.padding(top = 8.dp))
                Text(a.artist, color = Muted, fontSize = 13.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
        }
    }
}

@Composable
private fun ArtistsScreen(state: AppState, nav: Nav) {
    val artists = remember(state.songs) { state.songs.groupBy { it.artist }.toList().sortedBy { it.first.lowercase() } }
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 16.dp)) {
        item { Header("Artists", "${artists.size} artists") }
        items(artists, key = { it.first }) { (name, songs) ->
            Row(Modifier.fillMaxWidth().clickable { nav.artist(name) }.padding(16.dp, 8.dp), verticalAlignment = Alignment.CenterVertically) {
                Art(songs.first(), Modifier.size(52.dp), 26.dp)
                Column(Modifier.padding(start = 14.dp).weight(1f)) {
                    Text(name, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    val albums = songs.map { it.albumId }.distinct().size
                    Text("${songs.size} songs · $albums album${if (albums == 1) "" else "s"}", color = Muted, fontSize = 13.sp)
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
        empty = "Tap the heart on any song to save it here.")
}

@Composable
private fun PlaylistsScreen(state: AppState, nav: Nav) {
    var creating by remember { mutableStateOf(false) }
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 16.dp)) {
        item {
            Header("Playlists", "${state.playlists.size} playlists")
            Row(Modifier.fillMaxWidth().clickable { creating = true }.padding(16.dp, 8.dp), verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(52.dp).clip(RoundedCornerShape(6.dp)).background(Raise), contentAlignment = Alignment.Center) { Icon(Icons.Filled.Add, null, tint = Amber) }
                Text("New playlist", fontWeight = FontWeight.SemiBold, modifier = Modifier.padding(start = 14.dp))
            }
        }
        items(state.playlists, key = { it.id }) { p ->
            val songs = state.songsOf(p)
            Row(Modifier.fillMaxWidth().clickable { nav.playlist(p.id) }.padding(16.dp, 8.dp), verticalAlignment = Alignment.CenterVertically) {
                Art(songs.firstOrNull(), Modifier.size(52.dp), 6.dp, fallbackKey = p.name)
                Column(Modifier.padding(start = 14.dp).weight(1f)) {
                    Text(p.name, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text("${songs.size} songs", color = Muted, fontSize = 13.sp)
                }
            }
        }
    }
    if (creating) NameDialog("New playlist", "", "Create", { creating = false }) { state.createPlaylist(it); creating = false }
}

@Composable
private fun DetailScreen(state: AppState, d: Detail, nav: Nav, back: () -> Unit) {
    when (d) {
        is Detail.AlbumD -> {
            val list = remember(state.songs, d) { state.songs.filter { it.albumId == d.albumId }.sortedWith(compareBy({ it.track }, { it.title.lowercase() })) }
            if (list.isEmpty()) return back()
            val artists = list.map { it.artist }.distinct()
            TrackListScreen(state, list.first().album, (if (artists.size == 1) artists[0] else "Various artists") + " · ${list.size} songs · ${totalTime(list)}",
                list, nav, null, back = back, art = list.first(), numbered = true)
        }
        is Detail.ArtistD -> {
            val list = remember(state.songs, d) { state.songs.filter { it.artist == d.name }.sortedWith(compareBy({ it.album.lowercase() }, { it.track })) }
            if (list.isEmpty()) return back()
            TrackListScreen(state, d.name, "${list.size} songs · ${totalTime(list)}", list, nav, null, back = back, art = list.first())
        }
        is Detail.PlaylistD -> {
            val p = state.playlists.find { it.id == d.id } ?: return back()
            val list = state.songsOf(p)
            var renaming by remember { mutableStateOf(false) }
            var confirmDelete by remember { mutableStateOf(false) }
            TrackListScreen(state, p.name, "${list.size} songs" + if (list.isNotEmpty()) " · ${totalTime(list)}" else "", list, nav, p.id, back = back,
                art = list.firstOrNull(), fallbackKey = p.name, empty = "Add songs with the ⋮ button next to any song.",
                extra = {
                    TextButton({ renaming = true }) { Text("Rename", color = Muted) }
                    TextButton({ confirmDelete = true }) { Text("Delete", color = Muted) }
                })
            if (renaming) NameDialog("Rename playlist", p.name, "Save", { renaming = false }) { state.renamePlaylist(p.id, it); renaming = false }
            if (confirmDelete) AlertDialog(
                onDismissRequest = { confirmDelete = false }, containerColor = Raise,
                title = { Text("Delete \"${p.name}\"?") }, text = { Text("The songs stay in your library.") },
                confirmButton = { TextButton({ confirmDelete = false; state.deletePlaylist(p.id) }) { Text("Delete", color = Rose) } },
                dismissButton = { TextButton({ confirmDelete = false }) { Text("Cancel", color = Muted) } },
            )
        }
    }
}

@Composable
private fun TrackListScreen(
    state: AppState, title: String, sub: String, list: List<Song>, nav: Nav, playlistId: String?,
    back: (() -> Unit)? = null, art: Song? = null, fallbackKey: String? = null, numbered: Boolean = false,
    empty: String = "", extra: @Composable RowScope.() -> Unit = {},
) {
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 16.dp)) {
        item {
            if (back != null) IconButton(back, Modifier.padding(start = 4.dp, top = 4.dp)) { Icon(Icons.Filled.ArrowBack, "Back") }
            if (back != null) {
                Row(Modifier.padding(16.dp, 8.dp), verticalAlignment = Alignment.Bottom) {
                    Art(art, Modifier.size(128.dp), 10.dp, big = true, fallbackKey = fallbackKey ?: title)
                    Column(Modifier.padding(start = 16.dp)) { BigTitle(title, 28); Text(sub, color = Muted, fontSize = 13.sp) }
                }
            } else Header(title, sub)
            Row(Modifier.padding(16.dp, 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                if (list.isNotEmpty()) PlayButtons(list, state)
                Spacer(Modifier.weight(1f)); extra()
            }
            if (list.isEmpty() && empty.isNotEmpty()) Text(empty, color = Muted, modifier = Modifier.padding(16.dp))
        }
        itemsIndexed(list, key = { i, s -> "${s.id}-$i" }) { i, s ->
            SongRow(state, s, number = if (numbered) (if (s.track > 0) s.track else i + 1) else null,
                onClick = { state.play(list, i) }, onMore = { nav.more(s, playlistId) })
        }
    }
}

// ---------------- pieces ----------------

@Composable
private fun Header(title: String, sub: String, pad: Boolean = true) {
    Column(if (pad) Modifier.padding(16.dp, 20.dp, 16.dp, 12.dp) else Modifier.padding(top = 20.dp, bottom = 4.dp)) {
        BigTitle(title, 34)
        Text(sub, color = Muted, fontSize = 13.sp)
    }
}

@Composable
private fun BigTitle(text: String, size: Int) =
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

@Composable
private fun SongRow(state: AppState, s: Song, number: Int? = null, onClick: () -> Unit, onMore: () -> Unit) {
    val playing = state.current?.id == s.id
    Row(Modifier.fillMaxWidth().clickable(onClick = onClick).padding(start = 16.dp, top = 6.dp, bottom = 6.dp, end = 4.dp), verticalAlignment = Alignment.CenterVertically) {
        if (number != null) Text("$number", color = if (playing) Amber else Muted, fontSize = 13.sp, modifier = Modifier.width(30.dp))
        else Art(s, Modifier.size(48.dp), 6.dp)
        Column(Modifier.padding(start = if (number != null) 0.dp else 12.dp).weight(1f)) {
            Text(s.title, color = if (playing) Amber else Fg, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text(s.artist, color = Muted, fontSize = 13.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
        if (s.id in state.likes) Icon(Icons.Filled.Favorite, "Liked", tint = Rose, modifier = Modifier.size(16.dp))
        Text(fmt(s.durationMs), color = Muted, fontSize = 12.sp, modifier = Modifier.padding(start = 10.dp))
        IconButton(onMore) { Icon(Icons.Filled.MoreVert, "More", tint = Muted) }
    }
}

@Composable
private fun SongMenu(state: AppState, song: Song, playlistId: String?, dismiss: () -> Unit, addToPlaylist: () -> Unit, goAlbum: () -> Unit, goArtist: () -> Unit) {
    ModalBottomSheet(onDismissRequest = dismiss, containerColor = Deep) {
        Row(Modifier.padding(20.dp, 0.dp, 20.dp, 12.dp), verticalAlignment = Alignment.CenterVertically) {
            Art(song, Modifier.size(52.dp), 6.dp)
            Column(Modifier.padding(start = 12.dp)) {
                Text(song.title, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(song.artist, color = Muted, fontSize = 13.sp, maxLines = 1)
            }
        }
        HorizontalDivider(color = Line)
        val liked = song.id in state.likes
        MenuItem(if (liked) Icons.Filled.Favorite else Icons.Outlined.FavoriteBorder, if (liked) "Remove from Liked" else "Like") { state.toggleLike(song); dismiss() }
        MenuItem(Icons.Filled.PlaylistPlay, "Play next") { state.playNext(song); dismiss() }
        MenuItem(Icons.Filled.PlaylistAdd, "Add to playlist", addToPlaylist)
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
            Art(s, Modifier.size(44.dp), 6.dp)
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
        Art(s, Modifier.fillMaxWidth().aspectRatio(1f), 12.dp, big = true, px = 900)
        Spacer(Modifier.weight(0.4f))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(s.title, fontSize = 24.sp, fontWeight = FontWeight.ExtraBold, maxLines = 2, overflow = TextOverflow.Ellipsis, lineHeight = 28.sp)
                Text(s.artist, color = Muted, fontSize = 16.sp, maxLines = 1, overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.clickable { onClose(); nav.artist(s.artist) })
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
                Icon(if (state.repeat == androidx.media3.common.Player.REPEAT_MODE_ONE) Icons.Filled.RepeatOne else Icons.Filled.Repeat, "Repeat",
                    tint = if (state.repeat == androidx.media3.common.Player.REPEAT_MODE_OFF) Muted else Amber)
            }
        }
        Spacer(Modifier.weight(0.3f))
    }
}

@Composable
private fun Art(song: Song?, modifier: Modifier, corner: Dp, big: Boolean = false, fallbackKey: String? = null, px: Int = 360) {
    val context = LocalContext.current
    val key = song?.albumId
    var bmp by remember(key) { mutableStateOf<ImageBitmap?>(key?.let { ArtCache.peek(it) }) }
    LaunchedEffect(key) {
        if (song != null && bmp == null && !ArtCache.isMissing(song.albumId)) bmp = withContext(Dispatchers.IO) { ArtCache.load(context, song, px) }
    }
    Box(modifier.clip(RoundedCornerShape(corner))) {
        val b = bmp
        if (b != null) Image(b, null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
        else {
            val name = fallbackKey ?: song?.album ?: "Spindle"
            Box(Modifier.fillMaxSize().background(Brush.linearGradient(listOf(hueColor(name, 0.55f, 0.38f), hueColor(name, 0.6f, 0.22f, shift = 50f)))))
            if (big) Text(name.split(" ").first().take(8), color = Color.White.copy(alpha = 0.5f), fontWeight = FontWeight.ExtraBold, fontSize = 26.sp,
                modifier = Modifier.align(Alignment.BottomStart).padding(10.dp), maxLines = 1)
            else Icon(Icons.Filled.MusicNote, null, tint = Color.White.copy(alpha = 0.45f), modifier = Modifier.align(Alignment.Center).fillMaxSize(0.45f))
        }
    }
}

@Composable
private fun PermissionScreen(asked: Boolean, request: () -> Unit) {
    val context = LocalContext.current
    Centered {
        Icon(Icons.Filled.LibraryMusic, null, tint = Amber, modifier = Modifier.size(56.dp))
        Text("Let Spindle find your music", fontSize = 22.sp, fontWeight = FontWeight.ExtraBold, modifier = Modifier.padding(top = 16.dp))
        Text("Spindle plays the songs stored on this phone. It needs permission to see your music files. Nothing leaves your phone.",
            color = Muted, modifier = Modifier.padding(top = 8.dp, bottom = 20.dp))
        Button(request, colors = ButtonDefaults.buttonColors(containerColor = Amber, contentColor = AmberInk)) { Text("Allow access", fontWeight = FontWeight.Bold) }
        if (asked) TextButton({
            context.startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.fromParts("package", context.packageName, null)))
        }) { Text("Open app settings", color = Muted) }
    }
}

@Composable
private fun EmptyLibrary(rescan: () -> Unit) {
    Centered {
        Icon(Icons.Filled.Album, null, tint = Amber, modifier = Modifier.size(56.dp))
        Text("No music on this phone yet", fontSize = 22.sp, fontWeight = FontWeight.ExtraBold, modifier = Modifier.padding(top = 16.dp))
        Text("Copy MP3, M4A, FLAC or other audio files into the Music folder on your phone, for example over a USB cable or from a download. Spindle finds them automatically.",
            color = Muted, modifier = Modifier.padding(top = 8.dp, bottom = 20.dp))
        Button(rescan, colors = ButtonDefaults.buttonColors(containerColor = Amber, contentColor = AmberInk)) { Text("Look again", fontWeight = FontWeight.Bold) }
    }
}

@Composable
private fun Centered(content: @Composable ColumnScope.() -> Unit) =
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
