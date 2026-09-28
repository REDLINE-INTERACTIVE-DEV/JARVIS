package ai.jarvis.client

import android.content.SharedPreferences
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

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

    fun resolve(prefs: SharedPreferences, compiledDefault: String): String? =
        savedEndpoint(prefs) ?: bootstrapEndpoint() ?: compiledDefault.trim().trimEnd('/').takeIf(::isUsable)

    fun isUsable(endpoint: String): Boolean {
        val value = endpoint.trim().trimEnd('/')
        if (!(value.startsWith("http://") || value.startsWith("https://"))) return false
        if (value.contains("127.0.0.1") || value.contains("localhost")) return false
        if (value == "http://10.0.2.2:8000") return false
        return true
    }
}
