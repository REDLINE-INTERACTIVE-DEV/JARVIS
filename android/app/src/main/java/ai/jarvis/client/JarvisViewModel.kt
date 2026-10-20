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
import java.util.UUID
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
    private val deviceId = prefs.getString("device_id", null) ?: UUID.randomUUID().toString().also {
        prefs.edit().putString("device_id", it).apply()
    }
    private val _state = MutableStateFlow(JarvisUiState(endpoint = sanitizeSavedEndpoint()))
    val state: StateFlow<JarvisUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch(Dispatchers.IO) {
            while (true) { checkConnection(); kotlinx.coroutines.delay(15_000) }
        }
    }

    private fun sanitizeSavedEndpoint(): String {
        val saved = prefs.getString("endpoint", null)?.trim()?.trimEnd('/')
        val staleLoopback = saved != null && !RuntimeEndpointResolver.isUsable(saved)
        if (staleLoopback) prefs.edit().remove("endpoint").apply()
        return RuntimeEndpointResolver.resolve(prefs, BuildConfig.DEFAULT_API_BASE_URL) ?: ""
    }

    fun setInput(value: String) { _state.value = _state.value.copy(input = value, error = null) }
    fun setEndpoint(value: String) { _state.value = _state.value.copy(endpoint = value.trimEnd('/'), error = null, connected = false) }

    fun currentApiToken(): String = SecureTokenStore.readToken(getApplication())

    fun saveConnection(endpointValue: String, tokenValue: String): Boolean {
        val endpoint = endpointValue.trim().trimEnd('/')
        val token = tokenValue.trim()
        if (!RuntimeEndpointResolver.isUsable(endpoint)) {
            _state.value = _state.value.copy(error = "Enter a valid public HTTPS backend URL.", connected = false)
            return false
        }
        if (token.length < 32) {
            _state.value = _state.value.copy(error = "The private access token must be at least 32 characters.", connected = false)
            return false
        }
        if (!SecureTokenStore.saveToken(getApplication(), token)) {
            _state.value = _state.value.copy(error = "Android secure storage is unavailable. The token was not saved.", connected = false)
            return false
        }
        prefs.edit().putString("endpoint", endpoint).apply()
        _state.value = _state.value.copy(endpoint = endpoint, error = null, connected = false)
        refreshConnection()
        return true
    }
    fun setListening(active: Boolean) { _state.value = _state.value.copy(listening = active) }
    fun setInitiating() { _state.value = _state.value.copy(listening = false, busy = true, error = null) }
    fun setError(value: String?) { _state.value = _state.value.copy(error = value) }
    fun refreshConnection() { viewModelScope.launch(Dispatchers.IO) { checkConnection() } }
    fun setSpeaking(active: Boolean) { _state.value = _state.value.copy(speaking = active) }

    fun receiveExternalResponse(command: String, answer: String) {
        val cleanCommand = command.trim()
        val cleanAnswer = answer.trim().ifBlank { "I didn't receive a response from the backend." }
        val additions = buildList { if (cleanCommand.isNotBlank()) add(ChatMessage(cleanCommand, true)); add(ChatMessage(cleanAnswer, false)) }
        _state.value = _state.value.copy(input="",messages=_state.value.messages+additions,busy=false,listening=false,speakToken=_state.value.speakToken+1,lastAssistantText=cleanAnswer,error=null,connected=true)
    }

    fun send() {
        val message = _state.value.input.trim()
        if (message.isEmpty() || _state.value.busy) return
        val endpoint = _state.value.endpoint.trim().trimEnd('/')
        _state.value = _state.value.copy(input="",messages=_state.value.messages+ChatMessage(message,true),busy=true,error=null,listening=false)
        viewModelScope.launch(Dispatchers.IO) {
            val result = try { postWithRetry(endpoint,message) } catch (error:Exception) { Result.failure(error) }
            result.fold(
                onSuccess={ (workingEndpoint,answer) ->
                    prefs.edit().putString("endpoint",workingEndpoint).apply()
                    _state.value=_state.value.copy(endpoint=workingEndpoint,messages=_state.value.messages+ChatMessage(answer,false),busy=false,speakToken=_state.value.speakToken+1,lastAssistantText=answer,connected=true)
                },
                onFailure={ error ->
                    val detail=error.message?:"unknown error"
                    _state.value=_state.value.copy(messages=_state.value.messages+ChatMessage("API error: "+detail,false),busy=false,error=detail,connected=false)
                }
            )
        }
    }

    private fun candidateEndpoints(endpoint:String):List<String>{
        val normalized=endpoint.trim().trimEnd('/')
        return if (RuntimeEndpointResolver.isUsable(normalized)) listOf(normalized) else emptyList()
    }

    private fun postWithRetry(endpoint:String,message:String):Result<Pair<String,String>>{
        var last:Exception=IllegalStateException("Connection failed")
        for(candidate in candidateEndpoints(endpoint)){
            repeat(3){attempt->
                try{return postChat(candidate,message).map{answer->candidate to answer}}
                catch(error:Exception){last=error;if(attempt<2)Thread.sleep(500L*(attempt+1))}
            }
        }
        return Result.failure(last)
    }

    private fun checkConnection(){
        val endpoint=_state.value.endpoint.trim().trimEnd('/')
        val token = SecureTokenStore.readToken(getApplication())
        _state.value=_state.value.copy(connectionChecking=true)
        if (token.isBlank()) {
            _state.value = _state.value.copy(connected=false, connectionChecking=false)
            return
        }
        for(candidate in candidateEndpoints(endpoint)){
            try{
                val connection=(URL(candidate+"/auth/check").openConnection() as HttpURLConnection).apply{
                    requestMethod="GET";connectTimeout=5000;readTimeout=5000
                    setRequestProperty("Accept","application/json")
                    setRequestProperty("X-JARVIS-Token", token)
                }
                val status: Int
                val body: String
                try {
                    status = connection.responseCode
                    val stream = if (status in 200..299) connection.inputStream else connection.errorStream
                    body = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
                } finally { connection.disconnect() }
                val json = if (status in 200..299) JSONObject(body) else JSONObject()
                val authenticated = json.optBoolean("authenticated", false)
                val correctBrain = json.optString("brain") == "gemma-4-e4b-it-kaggle"
                if(status in 200..299 && authenticated && correctBrain){
                    _state.value=_state.value.copy(endpoint=candidate,connected=true,connectionChecking=false,error=null)
                    return
                }
                if (status == 401) {
                    _state.value = _state.value.copy(error="JARVIS rejected the access token. Recheck Connection settings.", connected=false, connectionChecking=false)
                    return
                }
            }catch(_:Exception){}
        }
        _state.value=_state.value.copy(connected=false,connectionChecking=false)
    }

    private fun postChat(endpoint:String,message:String):Result<String>{
        val connection=(URL(endpoint+"/chat").openConnection() as HttpURLConnection).apply{
            requestMethod="POST";connectTimeout=10000;readTimeout=60000;doOutput=true
            setRequestProperty("Content-Type","application/json");setRequestProperty("Accept","application/json");setRequestProperty("X-JARVIS-Device",deviceId)
            SecureTokenStore.readToken(getApplication()).takeIf { it.isNotBlank() }?.let { setRequestProperty("X-JARVIS-Token", it) }
        }
        return try{
            val body=JSONObject().put("message",message).toString()
            connection.outputStream.use{it.write(body.toByteArray(Charsets.UTF_8))}
            val status=connection.responseCode
            val stream=if(status in 200..299)connection.inputStream else connection.errorStream
            val response=stream?.bufferedReader()?.use{it.readText()}.orEmpty()
            if(status !in 200..299)Result.failure(IllegalStateException("HTTP $status: $response"))
            else{val answer=JSONObject(response).optString("response");if(answer.isBlank())Result.failure(IllegalStateException("Server returned no response"))else Result.success(answer)}
        }finally{connection.disconnect()}
    }
}
