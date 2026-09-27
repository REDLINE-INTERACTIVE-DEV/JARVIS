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
import androidx.compose.foundation.background
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
                onBackground = Color(0xFFE6FBFF),
                surface = Color(0xFF04151A),
                onSurface = Color(0xFFE6FBFF),
            )
        ) {
            Box(
                Modifier
                    .fillMaxSize()
                    .background(JarvisBackground)
            ) {
                Column(
                    Modifier
                        .fillMaxSize()
                        .padding(horizontal = 12.dp, vertical = 8.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Spacer(Modifier.height(8.dp))

                    JarvisHud(
                        listening = state.listening,
                        speaking = state.speaking,
                        initiating = state.busy && !state.listening && !state.speaking,
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
                        Text(
                            status,
                            color = JarvisBlue,
                            fontSize = 13.sp,
                            fontWeight = FontWeight.SemiBold,
                            letterSpacing = 2.8.sp,
                        )
                    } else {
                        Spacer(Modifier.height(19.dp))
                    }

                    Spacer(Modifier.height(8.dp))

                    Row(
                        Modifier.fillMaxWidth().padding(horizontal = 10.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        OutlinedTextField(
                            value = state.input,
                            onValueChange = vm::setInput,
                            placeholder = {
                                Text(
                                    "Talk to JARVIS...",
                                    color = Color(0xFF8BAAB0),
                                )
                            },
                            singleLine = true,
                            modifier = Modifier.weight(1f),
                            enabled = !state.busy,
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = JarvisBlue,
                                unfocusedBorderColor = Color(0xFF24606C),
                                cursorColor = JarvisBlue,
                                focusedTextColor = Color.White,
                                unfocusedTextColor = Color.White,
                            ),
                        )

                        Button(
                            onClick = vm::send,
                            enabled = !state.busy && state.input.isNotBlank(),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = Color(0xFF425055),
                                disabledContainerColor = Color(0xFF2C3437),
                                contentColor = Color.White,
                            ),
                            contentPadding = PaddingValues(horizontal = 22.dp, vertical = 15.dp),
                        ) {
                            Text("Send", fontSize = 16.sp, fontWeight = FontWeight.Bold)
                        }
                    }

                    state.error?.let {
                        Spacer(Modifier.height(6.dp))
                        Text(
                            "JARVIS CONNECTION UNAVAILABLE",
                            color = Color(0xFFFFB4A8),
                            fontSize = 10.sp,
                            letterSpacing = 1.2.sp,
                        )
                    }

                    if (state.messages.isNotEmpty()) {
                        Spacer(Modifier.height(8.dp))
                        val last = state.messages.last()
                        Text(
                            last.text,
                            modifier = Modifier.fillMaxWidth().padding(horizontal = 14.dp),
                            color = if (last.fromUser) Color(0xFF82AAB3) else Color(0xFFD8F8FF),
                            fontSize = 12.sp,
                        )
                    }
                }
            }
        }
    }

    @Composable
    private fun JarvisHud(
        listening: Boolean,
        speaking: Boolean,
        initiating: Boolean,
        onClick: () -> Unit,
    ) {
        val transition = rememberInfiniteTransition(label = "jarvis-hud")
        val pulse by transition.animateFloat(
            initialValue = 0.97f,
            targetValue = 1.03f,
            animationSpec = infiniteRepeatable(
                tween(900),
                RepeatMode.Reverse,
            ),
            label = "hud-pulse",
        )
        val sweep by transition.animateFloat(
            initialValue = 0f,
            targetValue = 360f,
            animationSpec = infiniteRepeatable(tween(3200)),
            label = "hud-sweep",
        )
        val active = listening || speaking || initiating

        Box(
            Modifier
                .fillMaxWidth()
                .height(390.dp)
                .clickable(enabled = !initiating, onClick = onClick),
            contentAlignment = Alignment.Center,
        ) {
            Canvas(Modifier.fillMaxSize()) {
                val cx = size.width / 2f
                val cy = size.height / 2f
                val maxR = minOf(size.width * 0.48f, size.height * 0.47f)
                val scale = if (active) pulse else 1f
                val rOuter = maxR * scale
                val rBlue = rOuter * 0.79f
                val rInner = rOuter * 0.60f
                val rCore = rOuter * 0.45f

                // Outer HUD ring.
                drawCircle(
                    color = Color(0xFF65F3FF),
                    center = Offset(cx, cy),
                    radius = rOuter,
                    style = Stroke(width = 3.2f),
                )

                // Outer segmented ticks, matching the reference HUD silhouette.
                for (i in 0 until 72) {
                    val angle = Math.toRadians(i * 5.0)
                    val long = i % 6 == 0
                    val inner = rOuter * (if (long) 0.88f else 0.925f)
                    val outer = rOuter * 0.975f
                    drawLine(
                        color = if (active && i % 9 == 0) Color.White else Color(0xFF74EFFF),
                        start = Offset(
                            cx + cos(angle).toFloat() * inner,
                            cy + sin(angle).toFloat() * inner,
                        ),
                        end = Offset(
                            cx + cos(angle).toFloat() * outer,
                            cy + sin(angle).toFloat() * outer,
                        ),
                        strokeWidth = if (long) 2.5f else 1.3f,
                        cap = StrokeCap.Round,
                    )
                }

                // Outer HUD brackets / broken arcs.
                drawArc(
                    color = Color(0xFF73F4FF),
                    startAngle = 198f,
                    sweepAngle = 112f,
                    useCenter = false,
                    topLeft = Offset(cx - rOuter, cy - rOuter),
                    size = androidx.compose.ui.geometry.Size(rOuter * 2f, rOuter * 2f),
                    style = Stroke(width = 8f, cap = StrokeCap.Round),
                )
                drawArc(
                    color = Color(0xFF73F4FF),
                    startAngle = 8f,
                    sweepAngle = 105f,
                    useCenter = false,
                    topLeft = Offset(cx - rOuter, cy - rOuter),
                    size = androidx.compose.ui.geometry.Size(rOuter * 2f, rOuter * 2f),
                    style = Stroke(width = 7f, cap = StrokeCap.Round),
                )

                // Blue segmented middle band.
                drawCircle(
                    color = Color(0xFF4CA8D1),
                    center = Offset(cx, cy),
                    radius = rBlue,
                    style = Stroke(width = rOuter * 0.105f),
                )
                for (i in 0 until 36) {
                    val angle = Math.toRadians(i * 10.0 + 5.0)
                    val inner = rBlue * 0.88f
                    val outer = rBlue * 1.02f
                    drawLine(
                        color = Color(0xFF93EFFF),
                        start = Offset(cx + cos(angle).toFloat() * inner, cy + sin(angle).toFloat() * inner),
                        end = Offset(cx + cos(angle).toFloat() * outer, cy + sin(angle).toFloat() * outer),
                        strokeWidth = 1.5f,
                    )
                }

                // Inner bright ring.
                drawCircle(
                    color = Color(0xFFB6FAFF),
                    center = Offset(cx, cy),
                    radius = rInner,
                    style = Stroke(width = 4.5f),
                )
                drawCircle(
                    color = Color(0xFF235C69),
                    center = Offset(cx, cy),
                    radius = rInner * 0.91f,
                    style = Stroke(width = 1.5f),
                )

                // Yellow telemetry arc from the reference.
                drawArc(
                    color = Color(0xFFF3D33A),
                    startAngle = 146f,
                    sweepAngle = 112f,
                    useCenter = false,
                    topLeft = Offset(cx - rInner * 1.05f, cy - rInner * 1.05f),
                    size = androidx.compose.ui.geometry.Size(rInner * 2.1f, rInner * 2.1f),
                    style = Stroke(width = 4f, cap = StrokeCap.Round),
                )

                // Animated listening/speaking waveform inside the core.
                val path = Path()
                val waveWidth = rCore * 1.65f
                for (i in 0..96) {
                    val x = cx - waveWidth / 2f + waveWidth * i / 96f
                    val amplitude = when {
                        listening -> 12f + 8f * sin(i * 0.8f + sweep / 18f)
                        speaking -> 15f + 10f * sin(i * 0.55f + sweep / 14f)
                        initiating -> 7f
                        else -> 2.5f
                    }
                    val y = cy + sin(i * 0.55f + sweep / 20f) * amplitude
                    if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
                }
                drawPath(
                    path,
                    color = Color(0xFF58E9FF),
                    style = Stroke(width = if (active) 3f else 1.8f, cap = StrokeCap.Round),
                )

                // Core rings.
                drawCircle(
                    color = Color(0xFF4DDCFF),
                    center = Offset(cx, cy),
                    radius = rCore,
                    style = Stroke(width = 2.5f),
                )
                drawCircle(
                    color = Color(0xFF183E47),
                    center = Offset(cx, cy),
                    radius = rCore * 0.83f,
                    style = Stroke(width = 1.2f),
                )
            }

            Text(
                "J.A.R.V.I.S.",
                color = Color.White,
                fontSize = 25.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 2.6.sp,
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
