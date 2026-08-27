package com.shoots.app.ui

import java.io.IOException
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import retrofit2.HttpException

private val errorJson = Json { ignoreUnknownKeys = true }

internal fun isAuthenticationFailure(exception: Throwable): Boolean =
    exception is HttpException && exception.code() == 401

internal fun friendlyMessage(exception: Throwable): String {
    if (isAuthenticationFailure(exception)) return "Sign in again to continue."
    if (exception is IOException) {
        return "Shoots cannot connect right now. Your cached work stays available."
    }
    val raw = when (exception) {
        is HttpException -> exception.response()?.errorBody()?.string()
            ?.takeIf(String::isNotBlank)
            ?: exception.message()
        else -> exception.message
    }.orEmpty()
    return parseDetail(raw)
        ?.take(300)
        ?: raw.take(300).takeIf(String::isNotBlank)
        ?: "Shoots could not finish that yet."
}

private fun parseDetail(raw: String): String? = runCatching {
    errorJson.parseToJsonElement(raw).jsonObject["detail"]?.jsonPrimitive?.contentOrNull
}.getOrNull()?.takeIf(String::isNotBlank)
