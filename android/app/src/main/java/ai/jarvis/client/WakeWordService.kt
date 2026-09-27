package ai.jarvis.client

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import java.net.HttpURLConnection
import java.net.Inet4Address
import java.net.NetworkInterface
import java.net.URL
import java.util.Locale
import java.util.concurrent.Callable
import java.util.concurrent.ExecutorCompletionService
import java.util.concurrent.Executors

class WakeWordService : Service() {
    private var recognizer: SpeechRecognizer? = null
    private var awaitingCommand = false
    private var listening = false
    private var wakeLock: android.os.PowerManager.WakeLock? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, notification())
        val powerManager = getSystemService(Context.POWER_SERVICE) as android.os.PowerManager
        wakeLock = powerManager.newWakeLock(android.os.PowerManager.PARTIAL_WAKE_LOCK, "JARVIS:WakeWord").apply {
            setReferenceCounted(false)
            acquire()
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopListening()
            stopSelf()
            return START_NOT_STICKY
        }
        startListening()
        return START_STICKY
    }

    private fun startListening() {
        if (listening || !SpeechRecognizer.isRecognitionAvailable(this)) return
        listening = true
        recognizer?.destroy()
        recognizer = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && SpeechRecognizer.isOnDeviceRecognitionAvailable(this)) {\n            SpeechRecognizer.createOnDeviceSpeechRecognizer(this)\n        } else {\n            SpeechRecognizer.createSpeechRecognizer(this)\n        }.also { sr ->
            sr.setRecognitionListener(object : RecognitionListener {
                override fun onResults(results: android.os.Bundle?) {
                    listening = false
                    val phrase = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull().orEmpty()
                    handlePhrase(phrase)
                }
                override fun onError(error: Int) { listening = false; scheduleRestart() }
                override fun onReadyForSpeech(params: android.os.Bundle?) {}
                override fun onBeginningOfSpeech() {}
                override fun onRmsChanged(rmsdB: Float) {}
                override fun onBufferReceived(buffer: ByteArray?) {}
                override fun onEndOfSpeech() {}
                override fun onPartialResults(partialResults: android.os.Bundle?) {}
                override fun onEvent(eventType: Int, params: android.os.Bundle?) {}
            })
            val recognizerIntent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault())
                putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false)
            }
            sr.startListening(recognizerIntent)
        }
    }

    private fun handlePhrase(raw: String) {
        val phrase = raw.trim().replace(Regex("\\s+"), " ")
        val wakeMatch = Regex("^\\s*(?:hey\\s+)?jarvis(?:\\b|[,.:;!?-])(.*)$", RegexOption.IGNORE_CASE).matchEntire(phrase)

        if (wakeMatch != null) {
            val afterWake = wakeMatch.groupValues.getOrNull(1).orEmpty().trimStart(',', '.', ':', ';', '-', ' ')
            broadcast(ACTION_COMMAND)
            if (afterWake.isNotBlank()) {
                awaitingCommand = false
                executeCommand(afterWake)
            } else {
                awaitingCommand = true
                scheduleRestart()
            }
            return
        }

        if (awaitingCommand && phrase.isNotBlank()) {
            awaitingCommand = false
            broadcast(ACTION_COMMAND)
            executeCommand(phrase)
        } else {
            scheduleRestart()
        }
    }

    private fun executeCommand(command: String) {
        broadcast(ACTION_INITIATING)
        Thread {
            val answer = try {
                postChat(command)
            } catch (e: Exception) {
                "I couldn't reach my JARVIS brain: " + (e.message ?: "connection error")
            }
            sendBroadcast(
                Intent(ACTION_RESPONSE).setPackage(packageName)
                    .putExtra(EXTRA_COMMAND, command)
                    .putExtra(EXTRA_RESPONSE, answer)
            )
            scheduleRestart()
        }.start()
    }

    private fun postChat(message: String): String {
        for (endpoint in candidateEndpoints()) {
            try {
                val connection = (URL(endpoint + "/chat").openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    connectTimeout = 10_000
                    readTimeout = 60_000
                    doOutput = true
                    setRequestProperty("Content-Type", "application/json")
                    setRequestProperty("Accept", "application/json")
                }
                try {
                    val body = org.json.JSONObject().put("message", message).toString()
                    connection.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
                    val status = connection.responseCode
                    val stream = if (status in 200..299) connection.inputStream else connection.errorStream
                    val response = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
                    if (status in 200..299) {
                        val answer = org.json.JSONObject(response).optString("response")
                        if (answer.isNotBlank()) return answer
                    }
                } finally {
                    connection.disconnect()
                }
            } catch (_: Exception) {}
        }
        throw IllegalStateException("no backend endpoint responded")
    }

    private fun candidateEndpoints(): List<String> {
        val prefs = getSharedPreferences("jarvis", MODE_PRIVATE)
        val configured = (prefs.getString("endpoint", BuildConfig.DEFAULT_API_BASE_URL) ?: BuildConfig.DEFAULT_API_BASE_URL).trimEnd('/')
        val candidates = linkedSetOf(configured)
        if (configured == BuildConfig.DEFAULT_API_BASE_URL) {
            candidates += "http://127.0.0.1:8000"
            discoverLanEndpoint()?.let { candidates += it }
        }
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
                    val ip = ((bytes[0].toInt() and 0xff) shl 24) or ((bytes[1].toInt() and 0xff) shl 16) or ((bytes[2].toInt() and 0xff) shl 8) or (bytes[3].toInt() and 0xff)
                    val mask = if (scanPrefix == 32) -1 else (-1 shl (32 - scanPrefix))
                    val network = ip and mask
                    val hostCount = 1 shl (32 - scanPrefix)
                    for (offset in 1 until hostCount - 1) {
                        val candidate = network + offset
                        hosts += (candidate shr 24 and 0xff).toString() + "." + (candidate shr 16 and 0xff).toString() + "." + (candidate shr 8 and 0xff).toString() + "." + (candidate and 0xff).toString()
                        if (hosts.size >= 254) break
                    }
                }
            }
        } catch (_: Exception) { return null }
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
                } catch (_: Exception) { null }
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

    private fun scheduleRestart() {
        android.os.Handler(mainLooper).postDelayed({ startListening() }, 300)
    }

    private fun broadcast(action: String) {
        sendBroadcast(Intent(action).setPackage(packageName))
    }

    private fun stopListening() {
        listening = false
        recognizer?.destroy()
        recognizer = null
        wakeLock?.let { if (it.isHeld) it.release() }
        wakeLock = null
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            getSystemService(NotificationManager::class.java).createNotificationChannel(
                NotificationChannel(CHANNEL_ID, "JARVIS wake word", NotificationManager.IMPORTANCE_LOW)
            )
        }
    }

    private fun notification(): Notification =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, CHANNEL_ID)
                .setContentTitle("JARVIS")
                .setContentText("Wake word listener is active")
                .setSmallIcon(android.R.drawable.ic_btn_speak_now)
                .setOngoing(true)
                .build()
        } else {
            Notification.Builder(this)
                .setContentTitle("JARVIS")
                .setContentText("Wake word listener is active")
                .setSmallIcon(android.R.drawable.ic_btn_speak_now)
                .setOngoing(true)
                .build()
        }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        stopListening()
        super.onDestroy()
    }

    companion object {
        const val ACTION_COMMAND = "ai.jarvis.client.ACTION_WAKE_COMMAND"
        const val ACTION_INITIATING = "ai.jarvis.client.ACTION_WAKE_INITIATING"
        const val ACTION_RESPONSE = "ai.jarvis.client.ACTION_WAKE_RESPONSE"
        const val ACTION_STOP = "ai.jarvis.client.ACTION_STOP_WAKE"
        const val EXTRA_COMMAND = "command"
        const val EXTRA_RESPONSE = "response"
        private const val CHANNEL_ID = "jarvis_wake"
        private const val NOTIFICATION_ID = 9011

        fun start(context: Context) {
            val intent = Intent(context, WakeWordService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) context.startForegroundService(intent)
            else context.startService(intent)
        }
    }
}
