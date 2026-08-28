package com.shoots.app.identity

import android.app.Activity
import android.app.PendingIntent
import android.content.Intent
import com.google.android.gms.auth.api.identity.AuthorizationRequest
import com.google.android.gms.auth.api.identity.Identity
import com.google.android.gms.common.api.Scope
import com.shoots.app.BuildConfig
import kotlinx.coroutines.tasks.await

data class DriveAuthorizationStart(
    val serverCode: String = "",
    val resolution: PendingIntent? = null,
)

class DriveAuthorization(private val activity: Activity) {
    private val client = Identity.getAuthorizationClient(activity)

    @Suppress("DEPRECATION")
    suspend fun start(): DriveAuthorizationStart {
        check(BuildConfig.GOOGLE_SERVER_CLIENT_ID.isNotBlank()) {
            "This build has no Google server client ID"
        }
        val request = AuthorizationRequest.builder()
            .setRequestedScopes(
                listOf(
                    Scope(DRIVE_FILE_SCOPE),
                    Scope("openid"),
                    Scope("email"),
                )
            )
            // Disconnect deliberately deletes the server refresh token without
            // revoking the photographer's broader Google grant. The explicit
            // reconnect action must therefore replace the lost offline token.
            .requestOfflineAccess(BuildConfig.GOOGLE_SERVER_CLIENT_ID, true)
            .setPrompt(AuthorizationRequest.Prompt.CONSENT)
            .build()
        val result = client.authorize(request).await()
        return if (result.hasResolution()) {
            DriveAuthorizationStart(resolution = result.pendingIntent)
        } else {
            DriveAuthorizationStart(serverCode = result.serverAuthCode.orEmpty())
        }
    }

    fun finish(data: Intent?): String =
        client.getAuthorizationResultFromIntent(data).serverAuthCode.orEmpty()

    companion object {
        private const val DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
    }
}
