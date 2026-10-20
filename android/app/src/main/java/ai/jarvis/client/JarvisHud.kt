package ai.jarvis.client

import android.graphics.BitmapFactory
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.sin

private val HudCyan = Color(0xFF55E9FF)
private val HudIce = Color(0xFFB9FAFF)
private val HudBlue = Color(0xFF087BC8)
private val HudNight = Color(0xFF02091B)

/** Cinematic HUD. Place the untouched supplied core image at assets/jarvis_core.jpg. */
@Composable
fun JarvisHud(
    listening: Boolean,
    speaking: Boolean,
    initiating: Boolean,
    onClick: () -> Unit,
) {
    val context = LocalContext.current
    val core = remember {
        runCatching {
            context.assets.open("jarvis_core.jpg").use { BitmapFactory.decodeStream(it) }
                ?.asImageBitmap()
        }.getOrNull()
    }
    val transition = rememberInfiniteTransition(label = "jarvis-iron-hud")
    val phase by transition.animateFloat(0f, (Math.PI * 2).toFloat(),
        infiniteRepeatable(tween(2600)), label = "hud-phase")
    val scan by transition.animateFloat(0f, 360f,
        infiniteRepeatable(tween(if (listening) 1500 else 4200)), label = "hud-scan")
    val breathe by transition.animateFloat(0.72f, 1f,
        infiniteRepeatable(tween(if (speaking) 360 else 1250), RepeatMode.Reverse), label = "hud-breathe")
    val active = listening || speaking || initiating
    val status = when {
        listening -> "PERCEIVING · AUDIO INPUT"
        speaking -> "RESPONDING · VOICE OUTPUT"
        initiating -> "INITIATING · SYSTEM ACTIVE"
        else -> "J.A.R.V.I.S. · STANDBY"
    }

    Box(
        Modifier.fillMaxWidth().height(390.dp).clickable(enabled = !initiating, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Canvas(Modifier.fillMaxSize()) {
            val cx = size.width / 2f
            val cy = size.height / 2f
            val outer = minOf(size.width * 0.31f, size.height * 0.31f)
            val coreRadius = outer * 0.68f
            val stateGlow = when { speaking -> 1f; listening -> 0.92f; initiating -> 0.7f; else -> 0.42f }

            // Cinematic blue reactor glow and precision rings.
            drawCircle(Color(0xFF007EA8).copy(alpha = 0.10f * breathe), Offset(cx, cy), outer * 1.72f)
            drawCircle(HudBlue.copy(alpha = 0.24f), Offset(cx, cy), outer * 1.48f, style = Stroke(1.2f))
            drawCircle(HudCyan.copy(alpha = 0.32f * stateGlow), Offset(cx, cy), outer * 1.32f, style = Stroke(2f))
            drawCircle(HudIce.copy(alpha = 0.16f), Offset(cx, cy), outer * 1.19f, style = Stroke(1f))

            // Partial scanning arcs rotate independently around the untouched core artwork.
            drawArc(HudCyan.copy(alpha = 0.88f), scan, 64f, false,
                Offset(cx - outer * 1.32f, cy - outer * 1.32f), Size(outer * 2.64f, outer * 2.64f), style = Stroke(4f))
            drawArc(HudIce.copy(alpha = 0.72f), -scan * 0.63f, 30f, false,
                Offset(cx - outer * 1.48f, cy - outer * 1.48f), Size(outer * 2.96f, outer * 2.96f), style = Stroke(2.4f))
            drawArc(HudBlue.copy(alpha = 0.95f), scan * 0.4f + 150f, 82f, false,
                Offset(cx - outer * 1.18f, cy - outer * 1.18f), Size(outer * 2.36f, outer * 2.36f), style = Stroke(5f))

            // Independent radial beats: every bar has its own phase and envelope.
            val bars = 88
            for (i in 0 until bars) {
                val a = Math.toRadians(i * (360.0 / bars) - 90.0)
                val local = abs(sin(phase * (1.0 + (i % 7) * 0.075) + i * 1.731)).toFloat()
                val secondary = abs(sin(phase * 0.43f + i * 0.319f))
                val amplitude = when {
                    listening -> 0.18f + local * 0.78f + secondary * 0.20f
                    speaking -> 0.22f + local * 0.92f + secondary * 0.16f
                    initiating -> 0.12f + local * 0.42f
                    else -> 0.07f + local * 0.15f
                }
                val inner = outer * 1.52f
                val length = outer * amplitude
                val start = Offset(cx + cos(a).toFloat() * inner, cy + sin(a).toFloat() * inner)
                val end = Offset(cx + cos(a).toFloat() * (inner + length), cy + sin(a).toFloat() * (inner + length))
                val color = when {
                    speaking -> HudIce
                    listening -> HudCyan
                    initiating -> HudBlue
                    else -> Color(0xFF1B789D)
                }
                drawLine(color.copy(alpha = (0.50f + local * 0.48f) * stateGlow), start, end,
                    strokeWidth = if (i % 4 == 0) 4.1f else if (i % 2 == 0) 2.7f else 1.8f,
                    cap = androidx.compose.ui.graphics.StrokeCap.Round)
                if (i % 4 == 0) drawCircle(color.copy(alpha = 0.86f * stateGlow), end, 1.7f)
            }

            // Fine radial calibration ticks and orbit markers.
            for (i in 0 until 120) {
                val a = Math.toRadians(i * 3.0 - 90.0)
                val r1 = outer * if (i % 5 == 0) 1.28f else 1.30f
                val r2 = outer * if (i % 5 == 0) 1.38f else 1.33f
                drawLine(HudIce.copy(alpha = if (i % 5 == 0) 0.62f else 0.20f),
                    Offset(cx + cos(a).toFloat() * r1, cy + sin(a).toFloat() * r1),
                    Offset(cx + cos(a).toFloat() * r2, cy + sin(a).toFloat() * r2),
                    strokeWidth = if (i % 5 == 0) 1.6f else 0.8f)
            }

            // Keep the provided core artwork pixel-for-pixel unchanged. The animated rings
            // are separate Canvas layers; no scale/rotation is applied to the bitmap itself.
            if (core != null) {
                val maxW = outer * 1.58f
                val maxH = outer * 1.82f
                val ratio = core.width.toFloat() / core.height.toFloat()
                val dstH = minOf(maxH, maxW / ratio)
                val dstW = dstH * ratio
                drawImage(core, dstOffset = androidx.compose.ui.unit.IntOffset((cx - dstW / 2f).toInt(), (cy - dstH / 2f).toInt()),
                    dstSize = androidx.compose.ui.unit.IntSize(dstW.toInt(), dstH.toInt()))
            } else {
                // Safe visual fallback until the original asset is packaged with the app.
                drawCircle(HudNight, Offset(cx, cy), coreRadius)
                drawCircle(HudCyan.copy(alpha = stateGlow), Offset(cx, cy), coreRadius, style = Stroke(3.5f))
                drawCircle(HudIce.copy(alpha = 0.35f), Offset(cx, cy), coreRadius * 0.91f, style = Stroke(1.2f))
            }
        }
        if (core == null) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text("J.A.R.V.I.S", color = Color.White, fontSize = 22.sp, fontWeight = FontWeight.Bold, letterSpacing = 2.3.sp)
                Text("CORE ASSET REQUIRED", color = HudCyan, fontSize = 8.sp, letterSpacing = 1.4.sp)
            }
        }
        Text(status, modifier = Modifier.align(Alignment.BottomCenter).padding(bottom = 8.dp),
            color = HudCyan, fontSize = 10.sp, fontWeight = FontWeight.SemiBold, letterSpacing = 2.1.sp)
    }
}
