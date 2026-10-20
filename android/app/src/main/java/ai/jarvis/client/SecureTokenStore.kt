package ai.jarvis.client

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.nio.ByteBuffer
import java.nio.charset.StandardCharsets
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Stores the JARVIS API token encrypted with an AES key held by Android Keystore.
 * Legacy plaintext tokens are migrated on first read and removed after encryption succeeds.
 */
object SecureTokenStore {
    private const val PREFS_NAME = "jarvis"
    private const val LEGACY_TOKEN_KEY = "api_token"
    private const val ENCRYPTED_TOKEN_KEY = "api_token_encrypted"
    private const val KEY_ALIAS = "jarvis_api_token_aes_gcm"
    private const val TRANSFORMATION = "AES/GCM/NoPadding"
    private const val IV_LENGTH_BYTES = 12

    fun readToken(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val encrypted = prefs.getString(ENCRYPTED_TOKEN_KEY, null)
        if (!encrypted.isNullOrBlank()) return decrypt(encrypted).orEmpty()

        val legacy = prefs.getString(LEGACY_TOKEN_KEY, "").orEmpty()
        if (legacy.isBlank()) return ""
        return if (saveToken(context, legacy)) legacy else ""
    }

    fun saveToken(context: Context, token: String): Boolean {
        if (token.isBlank()) return false
        return try {
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(Cipher.ENCRYPT_MODE, getOrCreateKey())
            val iv = cipher.iv
            val ciphertext = cipher.doFinal(token.toByteArray(StandardCharsets.UTF_8))
            val packed = ByteBuffer.allocate(iv.size + ciphertext.size).put(iv).put(ciphertext).array()
            val encoded = Base64.encodeToString(packed, Base64.NO_WRAP)
            context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE).edit()
                .putString(ENCRYPTED_TOKEN_KEY, encoded)
                .remove(LEGACY_TOKEN_KEY)
                .commit()
        } catch (_: Exception) {
            false
        }
    }

    private fun decrypt(encoded: String): String? = try {
        val packed = Base64.decode(encoded, Base64.NO_WRAP)
        if (packed.size <= IV_LENGTH_BYTES) null else {
            val iv = packed.copyOfRange(0, IV_LENGTH_BYTES)
            val ciphertext = packed.copyOfRange(IV_LENGTH_BYTES, packed.size)
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(Cipher.DECRYPT_MODE, getOrCreateKey(), GCMParameterSpec(128, iv))
            String(cipher.doFinal(ciphertext), StandardCharsets.UTF_8)
        }
    } catch (_: Exception) {
        null
    }

    private fun getOrCreateKey(): SecretKey {
        val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        val existing = keyStore.getKey(KEY_ALIAS, null) as? SecretKey
        if (existing != null) return existing

        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(
            KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true)
                .build(),
        )
        return generator.generateKey()
    }
}
