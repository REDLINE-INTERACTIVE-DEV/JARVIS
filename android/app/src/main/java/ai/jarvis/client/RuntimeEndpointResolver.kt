package ai.jarvis.client

import android.content.SharedPreferences
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL
import java.util.Locale

object RuntimeEndpointResolver {
    const val BOOTSTRAP_URL = "https://raw.githubusercontent.com/REDLINE-INTERACTIVE-DEV/JARVIS/main/runtime-endpoint.json"

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
                if (connection.responseCode !in 200..299) null
                else JSONObject(connection.inputStream.bufferedReader().use { it.readText() })
                    .optString("endpoint").trim().trimEnd('/').takeIf(::isUsable)
            } finally { connection.disconnect() }
        } catch (_: Exception) { null }
    }

    fun resolve(prefs: SharedPreferences, compiledDefault: String): String? = savedEndpoint(prefs)

    /** Public HTTPS only: all non-health API requests carry a private token. */
    fun isUsable(endpoint: String): Boolean {
        val uri = try { URI(endpoint.trim().trimEnd('/')) } catch (_: Exception) { return false }
        if (!uri.scheme.equals("https", true) || uri.host.isNullOrBlank()) return false
        if (uri.rawUserInfo != null || uri.rawQuery != null || uri.rawFragment != null) return false
        val host = uri.host.lowercase(Locale.ROOT).removePrefix("[").removeSuffix("]")
        val private172 = host.startsWith("172.") &&
            host.substringAfter("172.").substringBefore(".").toIntOrNull() in 16..31
        if (host == "localhost" || host.endsWith(".localhost") || host == "::1" ||
            host == "10.0.2.2" || host == "0.0.0.0" || host.startsWith("127.") ||
            host.startsWith("10.") || host.startsWith("192.168.") ||
            host.startsWith("169.254.") || private172) return false
        return true
    }
}
