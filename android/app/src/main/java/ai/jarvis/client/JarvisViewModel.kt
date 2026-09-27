package ai.jarvis.client

import android.app.Application
import android.content.Context
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.Inet4Address
import java.net.NetworkInterface
import java.net.URL
import java.util.concurrent.Callable
import java.util.concurrent.ExecutorCompletionService
import java.util.concurrent.Executors

data class ChatMessage(val text: String, val fromUser: Boolean)
data class JarvisUiState(
    val input: String = "",
    val endpoint: String = BuildConfig.DEFAULT_API_BASE_URL,
    val messages: List<ChatMessage> = emptyList(),
    val busy: Boolean = false,
    val error: String? = null,
    val speakToken: Long = 0,
    val lastAssistantText: String? = null,
    val listening: Boolean = false,
    val speaking: Boolean = false,
    val connected: Boolean = false,
    val connectionChecking: Boolean = false,
)

class JarvisViewModel(application: Application) : AndroidViewModel(application) {
    private val prefs = application.getSharedPreferences("jarvis", Context.MODE_PRIVATE)
    private val _state = MutableStateFlow(JarvisUiState(endpoint = sanitizeSavedEndpoint()))
    val state: StateFlow<JarvisUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch(Dispatchers.IO) {
            while (true) { checkConnection(); kotlinx.coroutines.delay(15_000) }
        }
    }

    private fun sanitizeSavedEndpoint(): String {
        val saved = prefs.getString("endpoint", null)?.trim()?.trimEnd('/')
        val staleLoopback = saved.isNullOrBlank() ||
            saved.equals("/127.0.0.1:8000", ignoreCase = true) ||
            saved.equals("127.0.0.1:8000", ignoreCase = true) ||
            saved.equals("http://127.0.0.1:8000", ignoreCase = true) ||
            saved.equals("http://localhost:8000", ignoreCase = true)
        if (staleLoopback) {
            prefs.edit().remove("endpoint").apply()
            return BuildConfig.DEFAULT_API_BASE_URL
        }
        return saved
    }

    fun setInput(value: String) { _state.value = _state.value.copy(input = value, error = null) }
    fun setEndpoint(value: String) { _state.value = _state.value.copy(endpoint = value.trimEnd('/'), error = null, connected = false) }
    fun setListening(active: Boolean) { _state.value = _state.value.copy(listening = active) }
    fun setInitiating() { _state.value = _state.value.copy(listening = false, busy = true, error = null) }
    fun setError(value: String?) { _state.value = _state.value.copy(error = value) }
    fun refreshConnection() { viewModelScope.launch(Dispatchers.IO) { checkConnection() } }
    fun setSpeaking(active: Boolean) { _state.value = _state.value.copy(speaking = active) }

    fun receiveExternalResponse(command: String, answer: String) {
        val cleanCommand = command.trim()
        val cleanAnswer = answer.trim().ifBlank { "I didn't receive a response from the backend." }
        val additions = buildList {
            if (cleanCommand.isNotBlank()) add(ChatMessage(cleanCommand, true))
            add(ChatMessage(cleanAnswer, false))
        }
        _state.value = _state.value.copy(
            input = "",
            messages = _state.value.messages + additions,
            busy = false,
            listening = false,
            speakToken = _state.value.speakToken + 1,
            lastAssistantText = cleanAnswer,
            error = null,
        )
    }

    fun send() {
        val message = _state.value.input.trim()
        if (message.isEmpty() || _state.value.busy) return
        val endpoint = _state.value.endpoint.trim().trimEnd('/')
        if (!endpoint.startsWith("http://") && !endpoint.startsWith("https://")) {
            _state.value = _state.value.copy(error = "API endpoint must start with http:// or https://")
            return
        }
        _state.value = _state.value.copy(input = "", messages = _state.value.messages + ChatMessage(message, true), busy = true, error = null, listening = false)
        viewModelScope.launch(Dispatchers.IO) {
            val result = try { postWithRetry(endpoint, message) } catch (error: Exception) { Result.failure(error) }
            result.fold(
                onSuccess = { (workingEndpoint, answer) ->
                    prefs.edit().putString("endpoint", workingEndpoint).apply()
                    _state.value = _state.value.copy(endpoint = workingEndpoint, messages = _state.value.messages + ChatMessage(answer, false), busy = false, speakToken = _state.value.speakToken + 1, lastAssistantText = answer, connected = true)
                },
                onFailure = { error ->
                    val detail = error.message ?: "unknown error"
                    _state.value = _state.value.copy(messages = _state.value.messages + ChatMessage("API error: " + detail, false), busy = false, error = detail, connected = false)
                },
            )
        }
    }

    private fun candidateEndpoints(endpoint: String): List<String> {
        val normalized = endpoint.trim().trimEnd('/')
        val loopback = normalized.equals("/127.0.0.1:8000", true) ||
            normalized.equals("127.0.0.1:8000", true) ||
            normalized.equals("http://127.0.0.1:8000", true) ||
            normalized.equals("http://localhost:8000", true)
        val candidates = linkedSetOf<String>()
        if (!loopback && normalized.isNotBlank()) candidates += normalized
        candidates += BuildConfig.DEFAULT_API_BASE_URL
        discoverLanEndpoint()?.let { candidates += it }
        // Emulator fallback; on a physical phone this will simply fail quickly.
        candidates += "http://127.0.0.1:8000"
        return candidates.toList()
    }

    private fun discoverLanEndpoint(): String? {
        val hosts = linkedSetOf<String>()
        try {
            val interfaces = NetworkInterface.getNetworkInterfaces()?.toList().orEmpty()
            for (networkInterface in interfaces) {
                if (!networkInterface.isUp || networkInterface.isLoopback) continue
                for (address in networkInterface.interfaceAddresses) {
                    val ipv4 = address.address as? Inet4Address ?: continue
                    if (!ipv4.isSiteLocalAddress) continue
                    val prefix = address.networkPrefixLength.toInt()
                    if (prefix !in 1..32) continue
                    val scanPrefix = maxOf(prefix, 24)
                    val bytes = ipv4.address
                    val ip = ((bytes[0].toInt() and 0xff) shl 24) or
                        ((bytes[1].toInt() and 0xff) shl 16) or
                        ((bytes[2].toInt() and 0xff) shl 8) or
                        (bytes[3].toInt() and 0xff)
                    val mask = if (scanPrefix == 32) -1 else (-1 shl (32 - scanPrefix))
                    val network = ip and mask
                    val hostCount = 1 shl (32 - scanPrefix)
                    for (offset in 1 until hostCount - 1) {
                        val candidate = network + offset
                        hosts += (candidate shr 24 and 0xff).toString() + "." +
                            (candidate shr 16 and 0xff).toString() + "." +
                            (candidate shr 8 and 0xff).toString() + "." +
                            (candidate and 0xff).toString()
                        if (hosts.size >= 254) break
                    }
                }
            }
        } catch (_: Exception) {
            return null
        }
        if (hosts.isEmpty()) return null

        val executor = Executors.newFixedThreadPool(32)
        val completion = ExecutorCompletionService<String?>(executor)
        val futures = hosts.map { host ->
            completion.submit(Callable {
                try {
                    val connection = (URL("http://" + host + ":8000/health").openConnection() as HttpURLConnection).apply {
                        requestMethod = "GET"
                        connectTimeout = 300
                        readTimeout = 500
                    }
                    try {
                        if (connection.responseCode in 200..299) "http://" + host + ":8000" else null
                    } finally {
                        connection.disconnect()
                    }
                } catch (_: Exception) {
                    null
                }
            })
        }
        return try {
            repeat(futures.size) {
                val found = completion.take().get()
                if (found != null) return found
            }
            null
        } catch (_: Exception) {
            null
        } finally {
            executor.shutdownNow()
        }
    }

    private fun postWithRetry(endpoint: String, message: String): Result<Pair<String, String>> {
        var last: Exception = IllegalStateException("Connection failed")
        for (candidate in candidateEndpoints(endpoint)) {
            repeat(3) { attempt ->
                try { return postChat(candidate, message).map { answer -> candidate to answer } }
                catch (error: Exception) { last = error; if (attempt < 2) Thread.sleep(500L * (attempt + 1)) }
            }
        }
        return Result.failure(last)
    }

    private fun checkConnection() {
        val endpoint = _state.value.endpoint.trim().trimEnd('/')
        if (!endpoint.startsWith("http://") && !endpoint.startsWith("https://")) { _state.value = _state.value.copy(connected = false, connectionChecking = false); return }
        _state.value = _state.value.copy(connectionChecking = true)
        for (candidate in candidateEndpoints(endpoint)) {
            try {
                val connection = (URL(candidate + "/health").openConnection() as HttpURLConnection).apply { requestMethod = "GET"; connectTimeout = 5_000; readTimeout = 5_000 }
                val status = try { connection.responseCode } finally { connection.disconnect() }
                if (status in 200..299) {
                    _state.value = _state.value.copy(endpoint = candidate, connected = true, connectionChecking = false)
                    return
                }
            } catch (_: Exception) { }
        }
        _state.value = _state.value.copy(connected = false, connectionChecking = false)
    }

    private fun postChat(endpoint: String, message: String): Result<String> {
        val connection = (URL(endpoint + "/chat").openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"; connectTimeout = 10_000; readTimeout = 60_000; doOutput = true
            setRequestProperty("Content-Type", "application/json"); setRequestProperty("Accept", "application/json")
        }
        return try {
            val body = JSONObject().put("message", message).toString()
            connection.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val response = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
            if (status !in 200..299) Result.failure(IllegalStateException("HTTP $status: $response"))
            else {
                val answer = JSONObject(response).optString("response")
                if (answer.isBlank()) Result.failure(IllegalStateException("Server returned no response")) else Result.success(answer)
            }
        } finally { connection.disconnect() }
    }
}
