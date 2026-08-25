package com.shoots.app

import android.content.Context
import org.json.JSONObject
import java.io.DataOutputStream
import java.net.HttpURLConnection
import java.net.URL

/**
 * Everything the camera says to the backend. Plain HttpURLConnection: the whole
 * surface is four calls, and a phone that has to be paired before it can do
 * anything does not need a networking framework to do it.
 *
 * The device token is the only credential here. It was handed over by a browser
 * that had already signed in (`api/pairing.py`) — the camera never runs an OAuth
 * flow, because that would mean shipping a client secret to a device.
 */
object Api {
    private const val PREFS = "shoots"
    private const val KEY_BASE = "base_url"
    private const val KEY_TOKEN = "token"
    private const val TIMEOUT_MS = 20_000

    fun baseUrl(context: Context): String =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_BASE, "") ?: ""

    fun token(context: Context): String =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_TOKEN, "") ?: ""

    fun isPaired(context: Context): Boolean = token(context).isNotEmpty()

    fun forget(context: Context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().clear().apply()
    }

    /** Exchange a code typed off the web page for this device's own token. */
    fun pair(context: Context, base: String, code: String): Result<Unit> = runCatching {
        val cleaned = base.trim().trimEnd('/')
        val body = JSONObject().put("code", code.trim().uppercase()).put("device", deviceName())
        val response = postJson("$cleaned/api/pair/claim", body, token = "")
        val token = response.getString("token")
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putString(KEY_BASE, cleaned)
            .putString(KEY_TOKEN, token)
            .apply()
    }

    /** The open challenge, pinned in the viewfinder. Null when there is none. */
    fun openQuest(context: Context): Experiment? = runCatching {
        val json = get(context, "/api/experiments/open") ?: return@runCatching null
        if (!json.has("id")) return@runCatching null
        Experiment(
            id = json.getString("id"),
            title = json.optString("title"),
            whyNow = json.optString("why_now"),
        )
    }.getOrNull()

    /**
     * Send the frame the shutter just took into the same ingest path the Drive
     * watcher feeds, with the pitch the phone was held at. The pipeline is
     * unchanged; the camera is a second door into it.
     */
    fun shoot(
        context: Context,
        jpeg: ByteArray,
        name: String,
        questId: String,
        pitchDeg: Float?,
    ): Result<String> = runCatching {
        val boundary = "----shoots${System.nanoTime()}"
        val url = URL(baseUrl(context) + "/drive/shoot")
        val connection = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            doOutput = true
            connectTimeout = TIMEOUT_MS
            readTimeout = 120_000
            setRequestProperty("Authorization", "Bearer ${token(context)}")
            setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
        }
        DataOutputStream(connection.outputStream).use { out ->
            fun field(key: String, value: String) {
                out.writeBytes("--$boundary\r\n")
                out.writeBytes("Content-Disposition: form-data; name=\"$key\"\r\n\r\n")
                out.write(value.toByteArray())
                out.writeBytes("\r\n")
            }
            if (questId.isNotEmpty()) field("experiment_id", questId)
            if (pitchDeg != null) field("pitch_deg", pitchDeg.toString())
            out.writeBytes("--$boundary\r\n")
            out.writeBytes(
                "Content-Disposition: form-data; name=\"file\"; filename=\"$name\"\r\n"
            )
            out.writeBytes("Content-Type: image/jpeg\r\n\r\n")
            out.write(jpeg)
            out.writeBytes("\r\n--$boundary--\r\n")
        }
        val json = read(connection)
        json.getString("shot_id")
    }

    /**
     * Has the panel finished with this shot, and what did it find? Null while
     * it is still being read — the phone polls, because the moment of
     * levelling up should land in the hand that took the picture.
     */
    fun pulse(context: Context, shotId: String): Pulse? = runCatching {
        val json = get(context, "/api/shots/$shotId") ?: return@runCatching null
        val shot = json.getJSONObject("shot")
        if (shot.optString("status") != "analyzed") return@runCatching null
        val analysis = json.optJSONObject("analysis") ?: return@runCatching null

        val techniques = analysis.optJSONArray("techniques")
        var praise = ""
        if (techniques != null) {
            for (i in 0 until techniques.length()) {
                val t = techniques.getJSONObject(i)
                // Praise first, and only what a second lens actually saw
                // (decision 33): one lens with a habit is one opinion.
                if (t.optInt("agreement") >= 2) {
                    praise = t.optString("technique_id").replace('_', ' ')
                    break
                }
            }
        }
        val findings = analysis.optJSONArray("findings")
        val finding = if (findings != null && findings.length() > 0) {
            findings.getJSONObject(0).optString("what")
        } else {
            ""
        }
        Pulse(praise = praise, finding = finding, keeper = !shot.optString("kept_at").isNullOrEmpty())
    }.getOrNull()

    /**
     * Mark or unmark a Shot as one the photographer values.
     *
     * PUT, not POST: the route is registered PUT-only and a POST answered 405,
     * so every tap on the camera's keeper button failed and reported success.
     * Returns whether the server actually took it - the caller has to be able
     * to put the button back, because a mark that only ever existed on screen
     * is a taste signal the Tendency Profile never sees, and an unmark that
     * never lands leaves a frame valued that the photographer let go.
     */
    fun setKeeper(context: Context, shotId: String, keeper: Boolean): Boolean = runCatching {
        sendJson(
            "PUT",
            baseUrl(context) + "/api/shots/$shotId/keeper",
            JSONObject().put("keeper", keeper),
            token(context),
        )
        true
    }.getOrDefault(false)

    // --- plumbing ---------------------------------------------------------

    private fun get(context: Context, path: String): JSONObject? {
        val connection = (URL(baseUrl(context) + path).openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = TIMEOUT_MS
            readTimeout = TIMEOUT_MS
            setRequestProperty("Authorization", "Bearer ${token(context)}")
        }
        if (connection.responseCode == 204) return null
        return read(connection)
    }

    private fun postJson(url: String, body: JSONObject, token: String): JSONObject =
        sendJson("POST", url, body, token)

    private fun sendJson(method: String, url: String, body: JSONObject, token: String): JSONObject {
        val connection = (URL(url).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            doOutput = true
            connectTimeout = TIMEOUT_MS
            readTimeout = TIMEOUT_MS
            setRequestProperty("Content-Type", "application/json")
            if (token.isNotEmpty()) setRequestProperty("Authorization", "Bearer $token")
        }
        connection.outputStream.use { it.write(body.toString().toByteArray()) }
        return read(connection)
    }

    private fun read(connection: HttpURLConnection): JSONObject {
        val code = connection.responseCode
        val text = if (code in 200..299) {
            connection.inputStream.bufferedReader().readText()
        } else {
            val detail = connection.errorStream?.bufferedReader()?.readText().orEmpty()
            throw IllegalStateException(if (detail.isBlank()) "HTTP $code" else detail)
        }
        return if (text.isBlank()) JSONObject() else JSONObject(text)
    }

    private fun deviceName(): String = "${android.os.Build.MANUFACTURER} ${android.os.Build.MODEL}"

    data class Experiment(val id: String, val title: String, val whyNow: String)

    data class Pulse(val praise: String, val finding: String, val keeper: Boolean)
}
