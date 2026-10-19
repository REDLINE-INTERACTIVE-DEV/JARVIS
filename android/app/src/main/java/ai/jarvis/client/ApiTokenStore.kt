package ai.jarvis.client

import android.content.Context
import android.util.Base64
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** AES-GCM token storage using a key held by Android Keystore. Migrates legacy plaintext tokens. */
internal class ApiTokenStore(context: Context) {
    private val prefs = context.getSharedPreferences("jarvis", Context.MODE_PRIVATE)
    @Synchronized fun read(): String {
        val encrypted = prefs.getString(ENCRYPTED_KEY, null)
        if (!encrypted.isNullOrBlank()) return try { decrypt(encrypted) } catch (_: Exception) {
            prefs.edit().remove(ENCRYPTED_KEY).apply(); ""
        }
        val legacy = prefs.getString(LEGACY_KEY, "").orEmpty()
        if (legacy.isNotBlank()) return try {
            write(legacy); prefs.edit().remove(LEGACY_KEY).apply(); legacy
        } catch (_: Exception) { "" }
        return ""
    }
    @Synchronized fun write(token: String) {
        if (token.isBlank()) { prefs.edit().remove(ENCRYPTED_KEY).remove(LEGACY_KEY).apply(); return }
        prefs.edit().putString(ENCRYPTED_KEY, encrypt(token)).remove(LEGACY_KEY).apply()
    }
    private fun encrypt(value: String): String {
        val cipher = Cipher.getInstance(TRANSFORMATION); cipher.init(Cipher.ENCRYPT_MODE, key())
        return Base64.encodeToString(cipher.iv + cipher.doFinal(value.toByteArray(Charsets.UTF_8)), Base64.NO_WRAP)
    }
    private fun decrypt(value: String): String {
        val bytes = Base64.decode(value, Base64.NO_WRAP)
        require(bytes.size > IV_BYTES)
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(TAG_BITS, bytes.copyOfRange(0, IV_BYTES)))
        return String(cipher.doFinal(bytes.copyOfRange(IV_BYTES, bytes.size)), Charsets.UTF_8)
    }
    private fun key(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(KeyGenParameterSpec.Builder(KEY_ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setRandomizedEncryptionRequired(true).build())
        return generator.generateKey()
    }
    private companion object {
        const val ENCRYPTED_KEY = "api_token_enc"
        const val LEGACY_KEY = "api_token"
        const val KEY_ALIAS = "jarvis.api.token.v1"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val IV_BYTES = 12
        const val TAG_BITS = 128
    }
}
