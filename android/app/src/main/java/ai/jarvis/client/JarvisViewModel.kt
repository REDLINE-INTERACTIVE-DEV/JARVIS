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
import java.net.URL

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
    private val _state = MutableStateFlow(JarvisUiState(endpoint = prefs.getString("endpoint", BuildConfig.DEFAULT_API_BASE_URL) ?: BuildConfig.DEFAULT_API_BASE_URL))
    val state: StateFlow<JarvisUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch(Dispatchers.IO) {
            while (true) { checkConnection(); kotlinx.coroutines.delay(15_000) }
        }
    }

    fun setInput(value: String) { _state.value = _state.value.copy(input = value, error = null) }
    fun setEndpoint(value: String) { _state.value = _state.value.copy(endpoint = value.trimEnd('/'), error = null, connected = false) }
    fun setListening(active: Boolean) { _state.value = _state.value.copy(listening = active) }
    fun refreshConnection() { viewModelScope.launch(Dispatchers.IO) { checkConnection() } }
    fun setSpeaking(active: Boolean) { _state.value = _state.value.copy(speaking = active) }

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

    private fun candidateEndpoints(endpoint: String): List<String> =
        if (endpoint == BuildConfig.DEFAULT_API_BASE_URL) listOf(endpoint, "http://127.0.0.1:8000").distinct() else listOf(endpoint)

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
