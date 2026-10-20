package ai.jarvis.client

import android.content.SharedPreferences
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL
import java.util.Locale

object RuntimeEndpointResolver {
    const val BOOTSTRAP_URL =
        "https://raw.githubusercontent.com/REDLINE-INTERACTIVE-DEV/JARVIS/main/runtime-endpoint.json"

    fun savedEndpoint(prefs: SharedPreferences): String? =
        prefs.getString("endpoint", null)?.trim()?.trimEnd('/')?.takeIf(::isUsable)

    fun bootstrapEndpoint(): String? {
        return try {
            val connection = (URL(BOOTSTRAP_URL).openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                connectTimeout = 2500
                readTimeout = 2500
                setRequestProperty("Accept", "application/json")
                setRequestProperty("Cache-Control", "no-cache")
            }
            try {
                if (connection.responseCode !in 200..299) return null
                val endpoint = JSONObject(connection.inputStream.bufferedReader().use { it.readText() })
                    .optString("endpoint").trim().trimEnd('/')
                endpoint.takeIf(::isUsable)
            } finally { connection.disconnect() }
        } catch (_: Exception) { null }
    }

    // JARVIS must use only the explicitly configured Kaggle brain endpoint.
    // No bootstrap, LAN scan, or compiled-default fallback is allowed.
    fun resolve(prefs: SharedPreferences, compiledDefault: String): String? =
        savedEndpoint(prefs)

    fun isUsable(endpoint: String): Boolean {
        val value = endpoint.trim().trimEnd('/')
        return try {
            val uri = URI(value)
            val host = uri.host?.lowercase(Locale.ROOT).orEmpty()
            uri.scheme.equals("https", ignoreCase = true) &&
                host.isNotBlank() &&
                uri.userInfo == null &&
                uri.fragment == null &&
                host != "localhost" &&
                !host.endsWith(".localhost") &&
                host != "127.0.0.1" &&
                host != "::1" &&
                host != "[::1]" &&
                host != "10.0.2.2"
        } catch (_: Exception) {
            false
        }
    }
}
