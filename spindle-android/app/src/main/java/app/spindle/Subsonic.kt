package app.spindle

import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.security.MessageDigest
import java.security.SecureRandom
import java.time.Instant

/** Login details for a Navidrome (Subsonic API) server. Only a salted token is kept, never the password. */
data class Credentials(val server: String, val user: String, val salt: String, val token: String) {
    companion object {
        fun fromPassword(server: String, user: String, password: String): Credentials {
            val salt = ByteArray(8).also { SecureRandom().nextBytes(it) }.joinToString("") { "%02x".format(it) }
            return Credentials(normalizeServer(server), user.trim(), salt, md5(password + salt))
        }

        fun normalizeServer(raw: String): String {
            var s = raw.trim().trimEnd('/')
            if (!s.startsWith("http://") && !s.startsWith("https://")) s = "http://$s"
            return s.removeSuffix("/rest")
        }

        private fun md5(s: String) = MessageDigest.getInstance("MD5").digest(s.toByteArray()).joinToString("") { "%02x".format(it) }
    }
}

/**
 * Which server addresses Spindle accepts. Plain http is allowed only where the network itself is private:
 * home-network addresses (192.168.x.x, 10.x.x.x, 172.16-31.x.x) and Tailscale names (*.ts.net), which Tailscale
 * encrypts. Anything reachable from the open internet must use https.
 */
object ServerAddress {
    fun isPrivateHost(host: String): Boolean {
        val h = host.lowercase().trim('[', ']')
        if (h.endsWith(".ts.net")) return true
        val parts = h.split('.').map { it.toIntOrNull() ?: return false }
        if (parts.size != 4 || parts.any { it !in 0..255 }) return false
        return parts[0] == 10 ||
            (parts[0] == 172 && parts[1] in 16..31) ||
            (parts[0] == 192 && parts[1] == 168) ||
            (parts[0] == 100 && parts[1] in 64..127) // Tailscale's own addresses
    }

    /** Returns a message explaining what's wrong with [normalized], or null if it can be used. */
    fun problem(normalized: String): String? {
        val host = runCatching { java.net.URI(normalized).host }.getOrNull()
        if (host.isNullOrBlank()) return "Enter the server address, for example http://192.168.1.20:4533"
        if (normalized.startsWith("http://") && !isPrivateHost(host))
            return "For your security, plain http only works with home-network addresses (like 192.168.1.20) or Tailscale names. Use one of those, or an https address."
        return null
    }
}

/** Why a request failed, in terms the sign-in and status screens can explain. */
class SubsonicException(val kind: Kind, message: String, val code: Int = 0) : IOException(message) {
    enum class Kind { Unreachable, BadLogin, NotSubsonic, Server }
}

class SubsonicClient(val creds: Credentials) {
    private val auth = "u=${enc(creds.user)}&t=${creds.token}&s=${creds.salt}&v=1.16.1&c=Spindle"

    // ---- addresses the player and image loader fetch directly ----
    fun streamUrl(id: String, maxBitRate: Int = 0, format: String? = null): String =
        "${creds.server}/rest/stream.view?$auth&id=${enc(id)}" +
            (if (maxBitRate > 0) "&maxBitRate=$maxBitRate&format=${format ?: "mp3"}" else "&format=raw")

    fun coverUrl(coverId: String, size: Int): String = "${creds.server}/rest/getCoverArt.view?$auth&id=${enc(coverId)}&size=$size"

    // ---- API calls ----
    fun ping(): JSONObject = call("ping")

    fun scanStatus(): JSONObject = call("getScanStatus").optJSONObject("scanStatus") ?: JSONObject()

    /** Every song in the library, a page at a time (an empty search returns everything on Navidrome). */
    fun songsPage(offset: Int, count: Int): List<Song> =
        call("search3", "query" to "", "songCount" to "$count", "songOffset" to "$offset", "artistCount" to "0", "albumCount" to "0")
            .optJSONObject("searchResult3")?.optJSONArray("song").objects().map(::parseSong)

    fun albumsPage(offset: Int, count: Int): List<Album> =
        call("getAlbumList2", "type" to "alphabeticalByName", "size" to "$count", "offset" to "$offset")
            .optJSONObject("albumList2")?.optJSONArray("album").objects().map(::parseAlbum)

    fun album(id: String): Pair<Album, List<Song>> {
        val a = call("getAlbum", "id" to id).getJSONObject("album")
        return parseAlbum(a) to a.optJSONArray("song").objects().map(::parseSong)
    }

    fun artists(): List<Artist> =
        call("getArtists").optJSONObject("artists")?.optJSONArray("index").objects()
            .flatMap { it.optJSONArray("artist").objects() }
            .map { Artist(it.getString("id"), it.optString("name"), it.optInt("albumCount"), it.optString("coverArt").ifBlank { null }) }

    fun starredSongIds(): Set<String> =
        call("getStarred2").optJSONObject("starred2")?.optJSONArray("song").objects().map { it.getString("id") }.toSet()

    fun playlists(): List<RemotePlaylistInfo> =
        call("getPlaylists").optJSONObject("playlists")?.optJSONArray("playlist").objects().map {
            RemotePlaylistInfo(it.getString("id"), it.optString("name"), it.optString("changed"), it.optString("owner"), it.optInt("songCount"))
        }

    fun playlistSongs(id: String): List<Song> =
        call("getPlaylist", "id" to id).getJSONObject("playlist").optJSONArray("entry").objects().map(::parseSong)

    /** Creates a playlist, or with [id] replaces an existing playlist's songs. Returns the playlist id. */
    fun savePlaylist(id: String?, name: String?, songIds: List<String>): String {
        val params = ArrayList<Pair<String, String>>()
        if (id != null) params += "playlistId" to id
        if (name != null) params += "name" to name
        if (songIds.isEmpty() && id != null) {
            // createPlaylist cannot empty a playlist; remove every entry instead.
            val count = playlistSongs(id).size
            if (count > 0) call("updatePlaylist", *(listOf("playlistId" to id) + (0 until count).map { "songIndexToRemove" to "$it" }).toTypedArray())
            if (name != null) call("updatePlaylist", "playlistId" to id, "name" to name)
            return id
        }
        songIds.forEach { params += "songId" to it }
        val res = call("createPlaylist", *params.toTypedArray())
        return res.optJSONObject("playlist")?.optString("id")?.ifBlank { null } ?: id
            ?: throw SubsonicException(SubsonicException.Kind.Server, "The server didn't return the new playlist")
    }

    fun renamePlaylist(id: String, name: String) { call("updatePlaylist", "playlistId" to id, "name" to name) }
    fun deletePlaylist(id: String) { call("deletePlaylist", "id" to id) }
    fun star(id: String) { call("star", "id" to id) }
    fun unstar(id: String) { call("unstar", "id" to id) }

    /** Reports a play. [timeMs] lets plays recorded offline keep the time they happened. */
    fun scrobble(id: String, submission: Boolean, timeMs: Long? = null) {
        val p = mutableListOf("id" to id, "submission" to submission.toString())
        if (timeMs != null) p += "time" to "$timeMs"
        call("scrobble", *p.toTypedArray())
    }

    // ---- plumbing ----
    private fun call(method: String, vararg params: Pair<String, String>): JSONObject {
        val body = buildString {
            append(auth).append("&f=json")
            params.forEach { (k, v) -> append('&').append(enc(k)).append('=').append(enc(v)) }
        }
        val conn = try {
            (URL("${creds.server}/rest/$method.view").openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = 8000
                readTimeout = 30000
                doOutput = true
                setRequestProperty("Content-Type", "application/x-www-form-urlencoded")
                outputStream.use { it.write(body.toByteArray()) }
            }
        } catch (e: IOException) {
            throw SubsonicException(SubsonicException.Kind.Unreachable, e.message ?: "Can't reach the server")
        }
        val text = try {
            val status = conn.responseCode
            if (status == 401) throw SubsonicException(SubsonicException.Kind.BadLogin, "Wrong username or password")
            if (status >= 400) throw SubsonicException(SubsonicException.Kind.NotSubsonic, "The server answered with error $status")
            conn.inputStream.bufferedReader().use { it.readText() }
        } catch (e: SubsonicException) {
            throw e
        } catch (e: IOException) {
            throw SubsonicException(SubsonicException.Kind.Unreachable, e.message ?: "Lost the connection to the server")
        } finally {
            conn.disconnect()
        }
        val root = runCatching { JSONObject(text).getJSONObject("subsonic-response") }.getOrElse {
            throw SubsonicException(SubsonicException.Kind.NotSubsonic, "That address isn't a Navidrome server")
        }
        if (root.optString("status") != "ok") {
            val err = root.optJSONObject("error")
            val code = err?.optInt("code") ?: 0
            val kind = if (code == 40 || code == 41 || code == 44) SubsonicException.Kind.BadLogin else SubsonicException.Kind.Server
            throw SubsonicException(kind, err?.optString("message")?.ifBlank { null } ?: "The server refused the request", code)
        }
        return root
    }

    companion object {
        fun enc(s: String): String = URLEncoder.encode(s, "UTF-8")

        fun parseTime(s: String?): Long =
            if (s.isNullOrBlank()) 0L else runCatching { Instant.parse(s).toEpochMilli() }.getOrDefault(0L)

        fun parseSong(o: JSONObject) = Song(
            id = o.getString("id"),
            title = o.optString("title").ifBlank { "Untitled" },
            artist = o.optString("artist").ifBlank { "Unknown artist" },
            artistId = o.optString("artistId").ifBlank { null },
            album = o.optString("album").ifBlank { "Unknown album" },
            albumId = o.optString("albumId").ifBlank { o.optString("parent") },
            coverArt = o.optString("coverArt").ifBlank { null },
            durationMs = o.optLong("duration") * 1000,
            track = o.optInt("track"),
            disc = o.optInt("discNumber"),
            year = o.optInt("year"),
            genre = o.optString("genre").ifBlank { null },
            suffix = o.optString("suffix"),
            bitRate = o.optInt("bitRate"),
            size = o.optLong("size"),
            created = parseTime(o.optString("created")),
            playCount = o.optInt("playCount"),
            played = parseTime(o.optString("played")),
            starred = o.has("starred"),
        )

        fun parseAlbum(o: JSONObject) = Album(
            id = o.getString("id"),
            name = o.optString("name").ifBlank { o.optString("album") }.ifBlank { "Unknown album" },
            artist = o.optString("artist").ifBlank { "Unknown artist" },
            artistId = o.optString("artistId").ifBlank { null },
            coverArt = o.optString("coverArt").ifBlank { null },
            songCount = o.optInt("songCount"),
            durationMs = o.optLong("duration") * 1000,
            year = o.optInt("year"),
            created = parseTime(o.optString("created")),
            playCount = o.optInt("playCount"),
            played = parseTime(o.optString("played")),
        )
    }
}

data class Song(
    val id: String, val title: String, val artist: String, val artistId: String?, val album: String, val albumId: String,
    val coverArt: String?, val durationMs: Long, val track: Int, val disc: Int, val year: Int, val genre: String?,
    val suffix: String, val bitRate: Int, val size: Long, val created: Long, val playCount: Int, val played: Long, val starred: Boolean,
)

data class Album(
    val id: String, val name: String, val artist: String, val artistId: String?, val coverArt: String?,
    val songCount: Int, val durationMs: Long, val year: Int, val created: Long, val playCount: Int, val played: Long,
) {
    /** Changes whenever the album's tracks, artwork or listening history change on the server. */
    val signature: String get() = "$name|$artist|$coverArt|$songCount|$durationMs|$year|$playCount|$played"
}

data class Artist(val id: String, val name: String, val albumCount: Int, val coverArt: String?)
data class RemotePlaylistInfo(val id: String, val name: String, val changed: String, val owner: String, val songCount: Int)

internal fun JSONArray?.objects(): List<JSONObject> = if (this == null) emptyList() else (0 until length()).map { getJSONObject(it) }
