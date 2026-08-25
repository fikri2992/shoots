package com.shoots.app

import android.content.Context
import org.json.JSONObject
import java.io.DataOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID

/**
 * Everything the Phone Source says to the backend. Plain HttpURLConnection: the
 * surface is deliberately small, and a phone that has to be paired before it can do
 * anything does not need a networking framework to do it.
 *
 * The device token is the only credential here. It was handed over by a browser
 * that had already signed in (`api/pairing.py`) — the phone never runs an OAuth
 * flow, because that would mean shipping a client secret to a device.
 */
object Api {
    private const val PREFS = "shoots"
    private const val KEY_BASE = "base_url"
    private const val KEY_TOKEN = "token"
    private const val KEY_DEVICE_ID = "device_id"
    private const val TIMEOUT_MS = 20_000

    fun baseUrl(context: Context): String =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_BASE, "") ?: ""

    fun token(context: Context): String =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_TOKEN, "") ?: ""

    fun isPaired(context: Context): Boolean = token(context).isNotEmpty()

    fun deviceId(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val existing = prefs.getString(KEY_DEVICE_ID, "").orEmpty()
        if (existing.isNotEmpty()) return existing
        return UUID.randomUUID().toString().also {
            prefs.edit().putString(KEY_DEVICE_ID, it).apply()
        }
    }

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

    /** Distinguishes "no open Experiment" from a network failure. */
    fun fetchOpenExperiment(context: Context): Result<Experiment?> = runCatching {
        val json = get(context, "/api/experiments/open") ?: return@runCatching null
        if (!json.has("id")) return@runCatching null
        Experiment(
            id = json.getString("id"),
            title = json.optString("title"),
            whyNow = json.optString("why_now"),
            type = json.optString("type"),
        )
    }

    /** Upload one original found in Android's Camera media. */
    fun importShot(
        context: Context,
        bytes: ByteArray,
        name: String,
        mimeType: String,
        sourceId: String,
        experimentId: String = "",
    ): Result<ImportResult> = runCatching {
        val fields = linkedMapOf("source_id" to "${deviceId(context)}:$sourceId")
        if (experimentId.isNotBlank()) fields["experiment_id"] = experimentId
        val json = postImage(
            context,
            "/api/ingress/shots",
            bytes,
            name,
            fields,
            mimeType,
        )
        ImportResult(
            shotId = json.getString("shot_id"),
            created = json.optBoolean("created"),
        )
    }

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

    private fun postImage(
        context: Context,
        path: String,
        jpeg: ByteArray,
        name: String,
        fields: Map<String, String>,
        mimeType: String = "image/jpeg",
    ): JSONObject {
        val boundary = "----shoots${System.nanoTime()}"
        val safeName = name.replace(Regex("[\\r\\n\"]"), "_").take(180).ifBlank { "shot.jpg" }
        val safeMime = mimeType
            .takeIf { it.startsWith("image/") && !it.contains(Regex("[\\r\\n]")) }
            ?: "image/jpeg"
        val connection = (
            URL(baseUrl(context) + path).openConnection() as HttpURLConnection
        ).apply {
            requestMethod = "POST"
            doOutput = true
            connectTimeout = TIMEOUT_MS
            readTimeout = 120_000
            setRequestProperty("Authorization", "Bearer ${token(context)}")
            setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
        }
        return try {
            DataOutputStream(connection.outputStream).use { out ->
                fields.forEach { (key, value) ->
                    out.writeBytes("--$boundary\r\n")
                    out.writeBytes("Content-Disposition: form-data; name=\"$key\"\r\n\r\n")
                    out.write(value.toByteArray(Charsets.UTF_8))
                    out.writeBytes("\r\n")
                }
                out.writeBytes("--$boundary\r\n")
                out.writeBytes(
                    "Content-Disposition: form-data; name=\"file\"; filename=\"$safeName\"\r\n"
                )
                out.writeBytes("Content-Type: $safeMime\r\n\r\n")
                out.write(jpeg)
                out.writeBytes("\r\n--$boundary--\r\n")
            }
            read(connection)
        } finally {
            connection.disconnect()
        }
    }

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

    data class Experiment(val id: String, val title: String, val whyNow: String, val type: String)

    data class ImportResult(val shotId: String, val created: Boolean)
}
