package ai.jarvis.client

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import android.os.Bundle
import android.content.pm.PackageManager
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import androidx.activity.ComponentActivity
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

    private val microphonePermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) WakeWordService.start(this)
    }

    private val wakeReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            when (intent?.action) {
                WakeWordService.ACTION_COMMAND -> viewModel.setListening(true)
                WakeWordService.ACTION_INITIATING -> viewModel.setInitiating()
                WakeWordService.ACTION_PERMISSION_REQUIRED -> {
                    if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                        microphonePermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                    }
                }
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
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            WakeWordService.start(this)
        } else {
            microphonePermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
        }
        setContent { JarvisApp(viewModel) }
    }

    private fun registerWakeReceiver() {
        val filter = IntentFilter().apply {
            addAction(WakeWordService.ACTION_COMMAND)
            addAction(WakeWordService.ACTION_INITIATING)
            addAction(WakeWordService.ACTION_RESPONSE)
            addAction(WakeWordService.ACTION_PERMISSION_REQUIRED)
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
        tts?.stop()
        tts?.shutdown()
        super.onDestroy()
    }

    @Composable
    private fun JarvisApp(vm: JarvisViewModel) {
        val state by vm.state.collectAsState()
        val context = LocalContext.current

        LaunchedEffect(state.speakToken) {
            if (state.speakToken > 0) state.lastAssistantText?.let { speak(it) }
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
                                if (!SpeechRecognizer.isRecognitionAvailable(context)) {
                                    vm.setListening(false)
                                    vm.setError("Speech recognition is not available on this device.")
                                } else if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
                                    WakeWordService.startInteractiveListening(context)
                                } else {
                                    microphonePermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
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
        val transition = rememberInfiniteTransition(label = "jarvis-visualizer")
        val phase by transition.animateFloat(
            initialValue = 0f,
            targetValue = (2f * Math.PI).toFloat(),
            animationSpec = infiniteRepeatable(tween(1800)),
            label = "visualizer-phase",
        )
        val haloAlpha by transition.animateFloat(
            initialValue = 0.12f,
            targetValue = 0.24f,
            animationSpec = infiniteRepeatable(tween(1400), RepeatMode.Reverse),
            label = "visualizer-halo",
        )
        val active = listening || speaking || initiating

        Box(
            Modifier
                .fillMaxWidth()
                .height(360.dp)
                .clickable(enabled = !initiating, onClick = onClick),
            contentAlignment = Alignment.Center,
        ) {
            Canvas(Modifier.fillMaxSize()) {
                val cx = size.width / 2f
                val cy = size.height / 2f
                val maxR = minOf(size.width * 0.37f, size.height * 0.39f)
                val rOuter = maxR * 0.91f
                val rMid = rOuter * 0.79f
                val rInner = rOuter * 0.61f
                val rCore = rOuter * 0.43f

                // Soft halo changes intensity, but the emblem and rings never move.
                drawCircle(
                    color = Color(0xFF12BFEA).copy(alpha = haloAlpha),
                    center = Offset(cx, cy),
                    radius = rOuter * 1.23f,
                )

                // Fixed outer frame.
                drawCircle(
                    color = Color(0xFF2D91AD).copy(alpha = if (active) 0.95f else 0.55f),
                    center = Offset(cx, cy),
                    radius = rOuter,
                    style = Stroke(width = 2.2f),
                )
                drawArc(
                    color = Color(0xFF65F3FF),
                    startAngle = 205f,
                    sweepAngle = 64f,
                    useCenter = false,
                    topLeft = Offset(cx - rOuter, cy - rOuter),
                    size = androidx.compose.ui.geometry.Size(rOuter * 2f, rOuter * 2f),
                    style = Stroke(width = 5f, cap = StrokeCap.Round),
                )
                drawArc(
                    color = Color(0xFF65F3FF),
                    startAngle = 28f,
                    sweepAngle = 54f,
                    useCenter = false,
                    topLeft = Offset(cx - rOuter, cy - rOuter),
                    size = androidx.compose.ui.geometry.Size(rOuter * 2f, rOuter * 2f),
                    style = Stroke(width = 5f, cap = StrokeCap.Round),
                )

                // Music-player style radial beats sit OUTSIDE the fixed emblem.
                // These are state-driven animations, not microphone amplitude readings.
                for (i in 0 until 64) {
                    val angle = Math.toRadians(i * (360.0 / 64.0) - 90.0)
                    val rhythm = kotlin.math.abs(sin(i * 0.63f + phase * 1.7f))
                    val length = when {
                        listening -> 7f + rhythm * 15f
                        speaking -> 9f + rhythm * 19f
                        initiating -> 5f + rhythm * 9f
                        else -> 3f + rhythm * 3f
                    }
                    val startR = rOuter * 1.045f
                    val endR = startR + length
                    val beatColor = when {
                        speaking -> Color(0xFF80F7FF)
                        listening -> Color(0xFF4DDCFF)
                        initiating -> Color(0xFF399AB7)
                        else -> Color(0xFF246477)
                    }
                    drawLine(
                        color = beatColor.copy(alpha = if (active) 0.98f else 0.55f),
                        start = Offset(
                            cx + cos(angle).toFloat() * startR,
                            cy + sin(angle).toFloat() * startR,
                        ),
                        end = Offset(
                            cx + cos(angle).toFloat() * endR,
                            cy + sin(angle).toFloat() * endR,
                        ),
                        strokeWidth = if (i % 4 == 0) 3.2f else 1.8f,
                        cap = StrokeCap.Round,
                    )
                }

                // Static precision rings; no scale, rotation, or translation animation.
                drawCircle(
                    color = Color(0xFF438BA5),
                    center = Offset(cx, cy),
                    radius = rMid,
                    style = Stroke(width = rOuter * 0.075f),
                )
                for (i in 0 until 48) {
                    val angle = Math.toRadians(i * 7.5)
                    val inner = rMid * 0.91f
                    val outer = rMid * 1.02f
                    drawLine(
                        color = Color(0xFF9BEFFF).copy(alpha = if (i % 4 == 0) 0.85f else 0.36f),
                        start = Offset(cx + cos(angle).toFloat() * inner, cy + sin(angle).toFloat() * inner),
                        end = Offset(cx + cos(angle).toFloat() * outer, cy + sin(angle).toFloat() * outer),
                        strokeWidth = if (i % 4 == 0) 2.1f else 1f,
                        cap = StrokeCap.Round,
                    )
                }
                drawCircle(
                    color = Color(0xFFB6FAFF),
                    center = Offset(cx, cy),
                    radius = rInner,
                    style = Stroke(width = 3.2f),
                )
                drawCircle(
                    color = Color(0xFF235C69),
                    center = Offset(cx, cy),
                    radius = rInner * 0.90f,
                    style = Stroke(width = 1.5f),
                )

                // Small fixed core emblem.
                drawCircle(
                    color = Color(0xFF0B222B),
                    center = Offset(cx, cy),
                    radius = rCore,
                )
                drawCircle(
                    color = Color(0xFF4DDCFF),
                    center = Offset(cx, cy),
                    radius = rCore,
                    style = Stroke(width = 2.5f),
                )
                drawCircle(
                    color = Color(0xFF1D7187),
                    center = Offset(cx, cy),
                    radius = rCore * 0.82f,
                    style = Stroke(width = 1.2f),
                )
                drawArc(
                    color = Color(0xFFF3D33A),
                    startAngle = 145f,
                    sweepAngle = 70f,
                    useCenter = false,
                    topLeft = Offset(cx - rCore * 0.91f, cy - rCore * 0.91f),
                    size = androidx.compose.ui.geometry.Size(rCore * 1.82f, rCore * 1.82f),
                    style = Stroke(width = 2.5f, cap = StrokeCap.Round),
                )
            }

            // Text is a normal fixed composable layered over the animated ring drawing.
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    "J.A.R.V.I.S.",
                    color = Color.White,
                    fontSize = 23.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 2.4.sp,
                )
                Spacer(Modifier.height(5.dp))
                Text(
                    when {
                        listening -> "LISTENING"
                        speaking -> "RESPONDING"
                        initiating -> "PROCESSING"
                        else -> "READY WHEN YOU ARE"
                    },
                    color = Color(0xFF80DFF0),
                    fontSize = 9.sp,
                    fontWeight = FontWeight.Medium,
                    letterSpacing = 1.5.sp,
                )
            }
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
