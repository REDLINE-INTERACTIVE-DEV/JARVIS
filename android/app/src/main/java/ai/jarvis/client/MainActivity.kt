package ai.jarvis.client

import android.Manifest
import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import java.util.Locale
import kotlin.math.cos
import kotlin.math.sin

class MainActivity : ComponentActivity(), TextToSpeech.OnInitListener {
    private val viewModel: JarvisViewModel by viewModels()
    private var tts: TextToSpeech? = null
    private var recognizer: SpeechRecognizer? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        tts = TextToSpeech(this, this)
        setContent { JarvisApp(viewModel) }
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            tts?.language = Locale.UK
            tts?.setPitch(0.92f)
            tts?.setSpeechRate(0.88f)
            tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(utteranceId: String?) {
                    runOnUiThread { viewModel.setSpeaking(true) }
                }

                override fun onDone(utteranceId: String?) {
                    runOnUiThread { viewModel.setSpeaking(false) }
                }

                override fun onError(utteranceId: String?) {
                    runOnUiThread { viewModel.setSpeaking(false) }
                }
            })
        }
    }

    override fun onDestroy() {
        recognizer?.destroy()
        tts?.stop()
        tts?.shutdown()
        super.onDestroy()
    }

    @Composable
    private fun JarvisApp(vm: JarvisViewModel) {
        val state by vm.state.collectAsState()
        val context = LocalContext.current

        val permissionLauncher = rememberLauncherForActivityResult(
            ActivityResultContracts.RequestPermission()
        ) { granted ->
            if (granted) startListening(context)
            else vm.setListening(false)
        }

        LaunchedEffect(state.speakToken) {
            if (state.speakToken > 0) state.lastAssistantText?.let { speak(it) }
        }

        DisposableEffect(Unit) {
            onDispose {
                recognizer?.destroy()
                recognizer = null
            }
        }

        MaterialTheme {
            Column(
                Modifier.fillMaxSize().padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Text("JARVIS", style = MaterialTheme.typography.headlineMedium)
                JarvisCore(
                    listening = state.listening,
                    speaking = state.speaking,
                    thinking = state.busy && !state.listening && !state.speaking,
                )

                OutlinedTextField(
                    value = state.endpoint,
                    onValueChange = vm::setEndpoint,
                    label = { Text("API endpoint") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )

                LazyColumn(
                    Modifier.weight(1f).fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    items(state.messages) { message ->
                        Text(if (message.fromUser) "You: " + message.text else "JARVIS: " + message.text)
                    }
                }

                state.error?.let {
                    Text(it, color = MaterialTheme.colorScheme.error)
                }

                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    OutlinedTextField(
                        value = state.input,
                        onValueChange = vm::setInput,
                        label = { Text("Message") },
                        modifier = Modifier.weight(1f),
                        enabled = !state.busy,
                    )
                    Button(
                        onClick = {
                            if (SpeechRecognizer.isRecognitionAvailable(context)) {
                                permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                            } else {
                                vm.setListening(false)
                            }
                        },
                        enabled = !state.busy,
                    ) { Text(if (state.listening) "Listening..." else "Voice") }
                    Button(
                        onClick = vm::send,
                        enabled = !state.busy && state.input.isNotBlank(),
                    ) { Text(if (state.busy) "..." else "Send") }
                }
            }
        }
    }

    @Composable
    private fun JarvisCore(listening: Boolean, speaking: Boolean, thinking: Boolean) {
        val transition = rememberInfiniteTransition(label = "jarvis-core")
        val pulse by transition.animateFloat(
            initialValue = 0.8f,
            targetValue = 1.15f,
            animationSpec = infiniteRepeatable(
                tween(900),
                RepeatMode.Reverse,
            ),
            label = "pulse",
        )
        val active = listening || speaking || thinking

        Canvas(
            Modifier.fillMaxWidth().height(180.dp)
        ) {
            val center = Offset(size.width / 2f, size.height / 2f)
            val base = minOf(size.width, size.height) * 0.16f
            val radius = if (active) base * pulse else base
            val ring = Stroke(width = 4f, cap = StrokeCap.Round)

            drawCircle(
                color = MaterialTheme.colorScheme.primary,
                center = center,
                radius = radius,
                style = ring,
            )

            val bars = 72
            for (i in 0 until bars) {
                val angle = (i.toFloat() / bars) * (Math.PI * 2.0)
                val wave = if (active) {
                    0.65f + 0.35f * sin(i * 0.55f + pulse * 5f)
                } else {
                    0.25f + 0.08f * cos(i * 0.35f)
                }
                val inner = radius * (1.28f + wave * 0.12f)
                val outer = inner + if (active) 12f + 8f * wave else 5f
                val start = Offset(
                    center.x + cos(angle).toFloat() * inner,
                    center.y + sin(angle).toFloat() * inner,
                )
                val end = Offset(
                    center.x + cos(angle).toFloat() * outer,
                    center.y + sin(angle).toFloat() * outer,
                )
                drawLine(
                    color = MaterialTheme.colorScheme.primary,
                    start = start,
                    end = end,
                    strokeWidth = if (active) 4f else 2f,
                    cap = StrokeCap.Round,
                )
            }

            val path = Path()
            val waveWidth = radius * 1.8f
            val points = 80
            for (i in 0..points) {
                val x = center.x - waveWidth / 2f + waveWidth * i / points
                val y = center.y + sin(i * 0.55f + pulse * 6f) * if (active) 10f else 3f
                if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
            }
            drawPath(
                path = path,
                color = MaterialTheme.colorScheme.primary,
                style = Stroke(width = 3f, cap = StrokeCap.Round),
            )
        }
    }

    private fun startListening(context: android.content.Context) {
        recognizer?.destroy()
        viewModel.setListening(true)
        recognizer = SpeechRecognizer.createSpeechRecognizer(context).also { sr ->
            sr.setRecognitionListener(object : RecognitionListener {
                override fun onResults(results: Bundle?) {
                    viewModel.setListening(false)
                    results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                        ?.firstOrNull()
                        ?.let {
                            viewModel.setInput(it)
                            viewModel.send()
                        }
                    sr.destroy()
                }

                override fun onError(error: Int) {
                    viewModel.setListening(false)
                    sr.destroy()
                }

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

    private fun speak(text: String) {
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "jarvis")
    }
}
