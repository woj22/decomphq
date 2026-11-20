package app.spindle

import android.content.ContentUris
import android.content.Context
import android.net.Uri
import android.provider.MediaStore
import org.json.JSONArray
import org.json.JSONObject

data class Song(
    val id: Long,
    val title: String,
    val artist: String,
    val album: String,
    val albumId: Long,
    val durationMs: Long,
    val track: Int,
    val dateAdded: Long,
) {
    val uri: Uri get() = ContentUris.withAppendedId(MediaStore.Audio.Media.EXTERNAL_CONTENT_URI, id)
}

data class Playlist(val id: String, val name: String, val songIds: List<Long>)

/** Reads every music file Android knows about on this phone (internal storage and SD card). */
object MusicScanner {
    fun scan(context: Context): List<Song> {
        val out = ArrayList<Song>()
        val projection = arrayOf(
            MediaStore.Audio.Media._ID,
            MediaStore.Audio.Media.TITLE,
            MediaStore.Audio.Media.ARTIST,
            MediaStore.Audio.Media.ALBUM,
            MediaStore.Audio.Media.ALBUM_ID,
            MediaStore.Audio.Media.DURATION,
            MediaStore.Audio.Media.TRACK,
            MediaStore.Audio.Media.DATE_ADDED,
        )
        // Skip ringtones, voice notes and very short clips.
        val selection = "${MediaStore.Audio.Media.IS_MUSIC} != 0 AND ${MediaStore.Audio.Media.DURATION} >= 20000"
        context.contentResolver.query(
            MediaStore.Audio.Media.EXTERNAL_CONTENT_URI, projection, selection, null,
            "${MediaStore.Audio.Media.TITLE} COLLATE NOCASE ASC",
        )?.use { c ->
            val iId = c.getColumnIndexOrThrow(MediaStore.Audio.Media._ID)
            val iTitle = c.getColumnIndexOrThrow(MediaStore.Audio.Media.TITLE)
            val iArtist = c.getColumnIndexOrThrow(MediaStore.Audio.Media.ARTIST)
            val iAlbum = c.getColumnIndexOrThrow(MediaStore.Audio.Media.ALBUM)
            val iAlbumId = c.getColumnIndexOrThrow(MediaStore.Audio.Media.ALBUM_ID)
            val iDur = c.getColumnIndexOrThrow(MediaStore.Audio.Media.DURATION)
            val iTrack = c.getColumnIndexOrThrow(MediaStore.Audio.Media.TRACK)
            val iAdded = c.getColumnIndexOrThrow(MediaStore.Audio.Media.DATE_ADDED)
            while (c.moveToNext()) {
                val artist = c.getString(iArtist).orEmpty()
                out += Song(
                    id = c.getLong(iId),
                    title = c.getString(iTitle).orEmpty().ifBlank { "Untitled" },
                    artist = if (artist.isBlank() || artist == "<unknown>") "Unknown artist" else artist,
                    album = c.getString(iAlbum).orEmpty().ifBlank { "Unknown album" },
                    albumId = c.getLong(iAlbumId),
                    durationMs = c.getLong(iDur),
                    track = c.getInt(iTrack) % 1000,
                    dateAdded = c.getLong(iAdded),
                )
            }
        }
        return out
    }
}

/** Likes and playlists, kept on the phone. */
class UserStore(context: Context) {
    private val prefs = context.getSharedPreferences("spindle", Context.MODE_PRIVATE)

    fun loadLikes(): Set<Long> =
        prefs.getString("likes", null)?.let { s -> JSONArray(s).let { a -> (0 until a.length()).map { a.getLong(it) }.toSet() } } ?: emptySet()

    fun saveLikes(ids: Set<Long>) = prefs.edit().putString("likes", JSONArray(ids.toList()).toString()).apply()

    fun loadPlaylists(): List<Playlist> {
        val s = prefs.getString("playlists", null) ?: return emptyList()
        val a = JSONArray(s)
        return (0 until a.length()).map { i ->
            val o = a.getJSONObject(i)
            val ids = o.getJSONArray("songs")
            Playlist(o.getString("id"), o.getString("name"), (0 until ids.length()).map { ids.getLong(it) })
        }
    }

    fun savePlaylists(list: List<Playlist>) {
        val a = JSONArray()
        list.forEach { p -> a.put(JSONObject().put("id", p.id).put("name", p.name).put("songs", JSONArray(p.songIds))) }
        prefs.edit().putString("playlists", a.toString()).apply()
    }
}
