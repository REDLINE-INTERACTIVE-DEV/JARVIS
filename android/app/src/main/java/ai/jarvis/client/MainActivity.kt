package ai.jarvis.client

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
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
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.util.Locale
import kotlin.math.cos
import kotlin.math.sin

class MainActivity : ComponentActivity(), TextToSpeech.OnInitListener {
    private val viewModel: JarvisViewModel by viewModels()
    private var tts: TextToSpeech? = null
    private var recognizer: SpeechRecognizer? = null

    private val wakeReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            when (intent?.action) {
                WakeWordService.ACTION_COMMAND -> viewModel.setListening(true)
                WakeWordService.ACTION_INITIATING -> viewModel.setInitiating()
                WakeWordService.ACTION_RESPONSE -> {
                    viewModel.receiveExternalResponse(
                        intent.getStringExtra(WakeWordService.EXTRA_COMMAND).orEmpty(),
                        intent.getStringExtra(WakeWordService.EXTRA_RESPONSE).orEmpty(),
                    )
                }
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        tts = TextToSpeech(this, this)
        registerWakeReceiver()
        WakeWordService.start(this)
        setContent { JarvisApp(viewModel) }
    }

    private fun registerWakeReceiver() {
        val filter = IntentFilter().apply {
            addAction(WakeWordService.ACTION_COMMAND)
            addAction(WakeWordService.ACTION_INITIATING)
            addAction(WakeWordService.ACTION_RESPONSE)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(wakeReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            @Suppress("DEPRECATION")
            registerReceiver(wakeReceiver, filter)
        }
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            tts?.language = Locale.UK
            tts?.setPitch(0.92f)
            tts?.setSpeechRate(0.88f)
            tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(utteranceId: String?) { runOnUiThread { viewModel.setSpeaking(true) } }
                override fun onDone(utteranceId: String?) { runOnUiThread { viewModel.setSpeaking(false) } }
                override fun onError(utteranceId: String?) { runOnUiThread { viewModel.setSpeaking(false) } }
            })
        }
    }

    override fun onDestroy() {
        try { unregisterReceiver(wakeReceiver) } catch (_: Exception) {}
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
            if (granted) startListening(context) else vm.setListening(false)
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

        MaterialTheme(
            colorScheme = darkColorScheme(
                primary = JarvisBlue,
                onPrimary = Color.Black,
                background = JarvisBackground,
                onBackground = Color(0xFFD9F8FF),
                surface = Color(0xFF06171D),
                onSurface = Color(0xFFD9F8FF),
            )
        ) {
            Column(
                Modifier.fillMaxSize().padding(horizontal = 16.dp, vertical = 12.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Spacer(Modifier.height(8.dp))

                JarvisCore(
                    listening = state.listening,
                    speaking = state.speaking,
                    thinking = state.busy && !state.listening && !state.speaking,
                    onClick = {
                        if (!state.busy) {
                            if (SpeechRecognizer.isRecognitionAvailable(context)) {
                                permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                            } else {
                                vm.setListening(false)
                                vm.setError("Speech recognition is not available on this device.")
                            }
                        }
                    },
                )

                val status = when {
                    state.listening -> "PERCEIVING"
                    state.busy -> "INITIATING"
                    state.speaking -> "SPEAKING"
                    else -> null
                }

                if (status != null) {
                    Text(status, color = JarvisBlue, fontSize = 13.sp, fontWeight = FontWeight.SemiBold, letterSpacing = 2.sp)
                } else {
                    Spacer(Modifier.height(17.dp))
                }

                Spacer(Modifier.height(12.dp))

                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    OutlinedTextField(
                        value = state.input,
                        onValueChange = vm::setInput,
                        placeholder = { Text("Talk to JARVIS...") },
                        singleLine = true,
                        modifier = Modifier.weight(1f),
                        enabled = !state.busy,
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = JarvisBlue,
                            unfocusedBorderColor = Color(0xFF28515C),
                            cursorColor = JarvisBlue,
                        ),
                    )
                    Button(
                        onClick = vm::send,
                        enabled = !state.busy && state.input.isNotBlank(),
                        colors = ButtonDefaults.buttonColors(containerColor = JarvisBlue, contentColor = Color.Black),
                    ) { Text("Send") }
                }

                Spacer(Modifier.height(8.dp))
                Text("Say JARVIS anytime to wake him", color = Color(0xFF6F9CA6), fontSize = 11.sp)

                state.error?.let {
                    Spacer(Modifier.height(6.dp))
                    Text(it, color = MaterialTheme.colorScheme.error, fontSize = 12.sp)
                }

                Spacer(Modifier.height(8.dp))

                LazyColumn(
                    Modifier.weight(1f).fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(7.dp),
                    reverseLayout = true,
                ) {
                    items(state.messages.asReversed()) { message ->
                        Text(
                            if (message.fromUser) "YOU  " + message.text else "JARVIS  " + message.text,
                            color = if (message.fromUser) Color(0xFF87B9C4) else Color(0xFFD9F8FF),
                            fontSize = 13.sp,
                        )
                    }
                }
            }
        }
    }

    @Composable
    private fun JarvisCore(
        listening: Boolean,
        speaking: Boolean,
        thinking: Boolean,
        onClick: () -> Unit,
    ) {
        val transition = rememberInfiniteTransition(label = "jarvis-core")
        val pulse by transition.animateFloat(
            initialValue = 0.9f,
            targetValue = 1.08f,
            animationSpec = infiniteRepeatable(tween(750), RepeatMode.Reverse),
            label = "pulse",
        )
        val active = listening || speaking || thinking

        Box(
            Modifier.fillMaxWidth().height(148.dp).clickable(enabled = !thinking, onClick = onClick),
            contentAlignment = Alignment.Center,
        ) {
            Canvas(Modifier.fillMaxSize()) {
                val center = Offset(size.width / 2f, size.height / 2f)
                val base = minOf(size.width, size.height) * 0.18f
                val radius = if (active) base * pulse else base

                drawCircle(
                    color = JarvisBlue,
                    center = center,
                    radius = radius,
                    style = Stroke(width = 3.5f, cap = StrokeCap.Round),
                )

                val bars = 72
                for (i in 0 until bars) {
                    val angle = (i.toFloat() / bars) * (Math.PI * 2.0)
                    val wave = if (active) 0.6f + 0.4f * sin(i * 0.55f + pulse * 5f)
                    else 0.2f + 0.06f * cos(i * 0.35f)
                    val inner = radius * (1.25f + wave * 0.10f)
                    val outer = inner + if (active) 9f + 7f * wave else 4f
                    drawLine(
                        color = JarvisBlue,
                        start = Offset(center.x + cos(angle).toFloat() * inner, center.y + sin(angle).toFloat() * inner),
                        end = Offset(center.x + cos(angle).toFloat() * outer, center.y + sin(angle).toFloat() * outer),
                        strokeWidth = if (active) 3f else 1.5f,
                        cap = StrokeCap.Round,
                    )
                }

                val path = Path()
                val waveWidth = radius * 1.7f
                for (i in 0..80) {
                    val x = center.x - waveWidth / 2f + waveWidth * i / 80
                    val y = center.y + sin(i * 0.55f + pulse * 6f) * if (active) 8f else 2f
                    if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
                }
                drawPath(path = path, color = JarvisBlue, style = Stroke(width = 2.5f, cap = StrokeCap.Round))
            }

            Text(
                "J.A.R.V.I.S.",
                color = Color(0xFFE7FCFF),
                fontSize = 22.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 2.sp,
            )
        }
    }

    private fun startListening(context: Context) {
        recognizer?.destroy()
        viewModel.setListening(true)
        recognizer = SpeechRecognizer.createSpeechRecognizer(context).also { sr ->
            sr.setRecognitionListener(object : RecognitionListener {
                override fun onResults(results: Bundle?) {
                    viewModel.setListening(false)
                    results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()?.let {
                        viewModel.setInput(it)
                        viewModel.send()
                    }
                    sr.destroy()
                }
                override fun onError(error: Int) { viewModel.setListening(false); sr.destroy() }
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

    companion object {
        private val JarvisBlue = Color(0xFF4DDCFF)
        private val JarvisBackground = Color(0xFF020B0F)
    }
}
