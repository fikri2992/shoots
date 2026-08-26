package com.shoots.app.identity

import android.app.Activity
import android.util.Base64
import androidx.credentials.ClearCredentialStateRequest
import androidx.credentials.CredentialManager
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.NoCredentialException
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.shoots.app.BuildConfig
import java.security.SecureRandom

data class IdentityProof(val idToken: String, val nonce: String)

class GoogleIdentity(private val activity: Activity) {
    private val credentials = CredentialManager.create(activity)

    suspend fun proof(): IdentityProof {
        check(BuildConfig.GOOGLE_SERVER_CLIENT_ID.isNotBlank()) {
            "This build has no Google server client ID"
        }
        val nonceBytes = ByteArray(24).also(SecureRandom()::nextBytes)
        val nonce = Base64.encodeToString(
            nonceBytes,
            Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING,
        )
        val option = GetGoogleIdOption.Builder()
            .setServerClientId(BuildConfig.GOOGLE_SERVER_CLIENT_ID)
            .setFilterByAuthorizedAccounts(false)
            .setAutoSelectEnabled(false)
            .setNonce(nonce)
            .build()
        val request = GetCredentialRequest.Builder().addCredentialOption(option).build()
        val credential = try {
            credentials.getCredential(activity, request).credential
        } catch (exception: NoCredentialException) {
            throw IllegalStateException("No Google account is available on this device", exception)
        }
        check(
            credential is CustomCredential &&
                credential.type == GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL
        ) { "Google returned an unsupported credential" }
        return IdentityProof(
            GoogleIdTokenCredential.createFrom(credential.data).idToken,
            nonce,
        )
    }

    suspend fun clear() {
        credentials.clearCredentialState(ClearCredentialStateRequest())
    }
}
