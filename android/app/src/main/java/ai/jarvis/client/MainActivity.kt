package ai.jarvis.client

import android.Manifest
import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import java.util.Locale

class MainActivity : ComponentActivity(), TextToSpeech.OnInitListener {
    private val viewModel: JarvisViewModel by viewModels()
    private var tts: TextToSpeech? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        tts = TextToSpeech(this, this)
        setContent { JarvisApp(viewModel) }
    }

    override fun onInit(status: Int) { if (status == TextToSpeech.SUCCESS) tts?.language = Locale.getDefault() }
    override fun onDestroy() { tts?.stop(); tts?.shutdown(); super.onDestroy() }
    private fun speak(text: String) { tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "jarvis") }

    @Composable
    private fun JarvisApp(vm: JarvisViewModel) {
        val state by vm.state.collectAsState()
        val context = LocalContext.current
        var recognizer by remember { mutableStateOf<SpeechRecognizer?>(null) }
        val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) startListening(context)
        }
        DisposableEffect(Unit) { onDispose { recognizer?.destroy(); recognizer = null } }

        MaterialTheme {
            Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("JARVIS", style = MaterialTheme.typography.headlineMedium)
                OutlinedTextField(value = state.endpoint, onValueChange = vm::setEndpoint, label = { Text("API endpoint") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                LazyColumn(Modifier.weight(1f).fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    items(state.messages) { message ->
                        Text(if (message.fromUser) "You: " + message.text else "JARVIS: " + message.text)
                    }
                }
                state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(value = state.input, onValueChange = vm::setInput, label = { Text("Message") }, modifier = Modifier.weight(1f), enabled = !state.busy)
                    Button(onClick = {
                        if (SpeechRecognizer.isRecognitionAvailable(context)) permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                    }, enabled = !state.busy) { Text("Voice") }
                    Button(onClick = { vm.send() }, enabled = !state.busy && state.input.isNotBlank()) { Text(if (state.busy) "..." else "Send") }
                }
            }
        }
    }

    private fun startListening(context: android.content.Context) {
        recognizer?.destroy()
        recognizer = SpeechRecognizer.createSpeechRecognizer(context).also { sr ->
            sr.setRecognitionListener(object : RecognitionListener {
                override fun onResults(results: Bundle?) {
                    results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()?.let {
                        viewModel.setInput(it)
                        viewModel.send()
                    }
                    sr.destroy()
                }
                override fun onError(error: Int) { sr.destroy() }
                override fun onReadyForSpeech(params: Bundle?) {}
                override fun onBeginningOfSpeech() {}
                override fun onRmsChanged(rmsdB: Float) {}
                override fun onBufferReceived(buffer: ByteArray?) {}
                override fun onEndOfSpeech() {}
                override fun onPartialResults(partialResults: Bundle?) {}
                override fun onEvent(eventType: Int, params: Bundle?) {}
            })
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault())
                putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            }
            sr.startListening(intent)
        }
    }
}
