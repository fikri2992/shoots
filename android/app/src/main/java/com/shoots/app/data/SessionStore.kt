package com.shoots.app.data

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import java.util.UUID
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

class SessionStore(private val context: Context) {
    private val secure = context.getSharedPreferences("shoots_secure", Context.MODE_PRIVATE)
    private val legacy = context.getSharedPreferences("shoots", Context.MODE_PRIVATE)

    init {
        migrateLegacyToken()
    }

    fun token(): String {
        val ciphertext = secure.getString(CIPHERTEXT, "").orEmpty()
        val iv = secure.getString(IV, "").orEmpty()
        if (ciphertext.isBlank() || iv.isBlank()) return ""
        return runCatching {
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(
                Cipher.DECRYPT_MODE,
                key(),
                GCMParameterSpec(128, Base64.decode(iv, Base64.NO_WRAP)),
            )
            String(cipher.doFinal(Base64.decode(ciphertext, Base64.NO_WRAP)), Charsets.UTF_8)
        }.getOrDefault("")
    }

    fun putToken(token: String, expiresAt: String) {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val encrypted = cipher.doFinal(token.toByteArray(Charsets.UTF_8))
        secure.edit()
            .putString(CIPHERTEXT, Base64.encodeToString(encrypted, Base64.NO_WRAP))
            .putString(IV, Base64.encodeToString(cipher.iv, Base64.NO_WRAP))
            .putString(EXPIRES_AT, expiresAt)
            .apply()
    }

    fun isSignedIn(): Boolean = token().isNotBlank()

    fun deviceId(): String {
        val existing = legacy.getString(DEVICE_ID, "").orEmpty()
        if (existing.isNotBlank()) return existing
        return UUID.randomUUID().toString().also {
            legacy.edit().putString(DEVICE_ID, it).apply()
        }
    }

    fun clearIdentity() {
        secure.edit().clear().apply()
        legacy.edit().remove(DEVICE_ID).remove("token").remove("base_url").apply()
        val keyStore = KeyStore.getInstance(KEYSTORE).apply { load(null) }
        if (keyStore.containsAlias(KEY_ALIAS)) keyStore.deleteEntry(KEY_ALIAS)
    }

    private fun migrateLegacyToken() {
        if (secure.contains(CIPHERTEXT)) return
        val token = legacy.getString("token", "").orEmpty()
        if (token.isNotBlank()) {
            putToken(token, "")
            legacy.edit().remove("token").remove("base_url").apply()
        }
    }

    private fun key(): SecretKey {
        val keyStore = KeyStore.getInstance(KEYSTORE).apply { load(null) }
        (keyStore.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE)
        generator.init(
            KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .build()
        )
        return generator.generateKey()
    }

    private companion object {
        const val KEYSTORE = "AndroidKeyStore"
        const val KEY_ALIAS = "shoots.device.session"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val CIPHERTEXT = "token_ciphertext"
        const val IV = "token_iv"
        const val EXPIRES_AT = "expires_at"
        const val DEVICE_ID = "device_id"
    }
}
