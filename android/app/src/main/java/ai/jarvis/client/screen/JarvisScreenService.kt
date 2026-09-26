package ai.jarvis.client.screen

import ai.jarvis.client.BuildConfig
import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Bitmap
import android.graphics.Path
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.nio.charset.StandardCharsets
import java.util.concurrent.Executors
import kotlin.math.max

class JarvisScreenService : AccessibilityService() {
    private val executor = Executors.newSingleThreadExecutor()
    private val handler = Handler(Looper.getMainLooper())
    private val prefs by lazy { getSharedPreferences("jarvis", MODE_PRIVATE) }
    private val deviceId by lazy {
        prefs.getString("screen_device_id", null)
            ?: ("android-" + Build.MODEL.lowercase().replace(" ", "-")).also {
                prefs.edit().putString("screen_device_id", it).apply()
            }
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        register()
        poll()
        captureLoop()
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {}
    override fun onInterrupt() {}

    private fun baseUrl() =
        (prefs.getString("endpoint", BuildConfig.DEFAULT_API_BASE_URL)
            ?: BuildConfig.DEFAULT_API_BASE_URL).trimEnd('/')

    private fun register() {
        executor.execute {
            try {
                postJson("/screen/register", """{"device_id":"$deviceId","platform":"android"}""")
            } catch (_: Exception) {}
        }
    }

    private fun poll() {
        executor.execute {
            try {
                val raw = get("/screen/actions/$deviceId")
                Regex("""{"action_id":(d+),"action":"([^"]+)","arguments":({.*?})""")
                    .findAll(raw)
                    .forEach { executeAction(it.groupValues[2], it.groupValues[3]) }
            } catch (_: Exception) {}
        }
        handler.postDelayed({ poll() }, 350)
    }

    private fun captureLoop() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) {
            handler.postDelayed({ captureLoop() }, 1000)
            return
        }
        takeScreenshot(0, executor, object : TakeScreenshotCallback {
            override fun onSuccess(screenshot: ScreenshotResult) {
                try {
                    val bitmap = Bitmap.wrapHardwareBuffer(
                        screenshot.hardwareBuffer,
                        screenshot.colorSpace,
                    )
                    screenshot.hardwareBuffer.close()
                    if (bitmap != null) {
                        val copy = bitmap.copy(Bitmap.Config.ARGB_8888, false)
                        bitmap.recycle()
                        uploadFrame(copy)
                    }
                } catch (_: Exception) {}
            }

            override fun onFailure(errorCode: Int) {}
        })
        handler.postDelayed({ captureLoop() }, 1000)
    }

    private fun uploadFrame(bitmap: Bitmap) {
        executor.execute {
            try {
                val bytes = ByteArrayOutputStream().use {
                    bitmap.compress(Bitmap.CompressFormat.JPEG, 55, it)
                    it.toByteArray()
                }
                val connection = (
                    URL(
                        baseUrl() + "/screen/frame/" + deviceId +
                            "?width=" + bitmap.width + "&height=" + bitmap.height
                    ).openConnection() as HttpURLConnection
                )
                connection.requestMethod = "POST"
                connection.connectTimeout = 5000
                connection.readTimeout = 5000
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "image/jpeg")
                connection.outputStream.use { it.write(bytes) }
                connection.inputStream.close()
                connection.disconnect()
            } catch (_: Exception) {
            } finally {
                bitmap.recycle()
            }
        }
    }

    private fun executeAction(action: String, arguments: String) {
        when (action) {
            "tap", "click" -> {
                val x = jsonNumber(arguments, "x") ?: return
                val y = jsonNumber(arguments, "y") ?: return
                tap(x, y)
            }
            "swipe" -> {
                val x1 = jsonNumber(arguments, "x1") ?: return
                val y1 = jsonNumber(arguments, "y1") ?: return
                val x2 = jsonNumber(arguments, "x2") ?: return
                val y2 = jsonNumber(arguments, "y2") ?: return
                swipe(x1, y1, x2, y2)
            }
            "type" -> typeText(jsonString(arguments, "text") ?: return)
            "back" -> performGlobalAction(GLOBAL_ACTION_BACK)
            "home" -> performGlobalAction(GLOBAL_ACTION_HOME)
            "recents" -> performGlobalAction(GLOBAL_ACTION_RECENTS)
        }
    }

    private fun tap(x: Float, y: Float) {
        val path = Path().apply { moveTo(x, y) }
        val gesture = GestureDescription.Builder()
            .addStroke(GestureDescription.StrokeDescription(path, 0, 80))
            .build()
        dispatchGesture(gesture, null, null)
    }

    private fun swipe(x1: Float, y1: Float, x2: Float, y2: Float) {
        val path = Path().apply {
            moveTo(x1, y1)
            lineTo(x2, y2)
        }
        val gesture = GestureDescription.Builder()
            .addStroke(GestureDescription.StrokeDescription(path, 0, max(100L, 500L)))
            .build()
        dispatchGesture(gesture, null, null)
    }

    private fun jsonNumber(json: String, key: String): Float? =
        Regex("""["']?$key["']?s*:s*(-?d+(?:.d+)?)""")
            .find(json)?.groupValues?.get(1)?.toFloatOrNull()

    private fun jsonString(json: String, key: String): String? =
        Regex("""["']?$key["']?s*:s*"((?:\.|[^"])*)"""")
            .find(json)?.groupValues?.get(1)

    private fun typeText(text: String) {
        val node = rootInActiveWindow ?: return
        val args = Bundle()
        args.putCharSequence(
            AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,
            text,
        )
        node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
        node.recycle()
    }

    private fun postJson(path: String, body: String) {
        val connection = URL(baseUrl() + path).openConnection() as HttpURLConnection
        connection.requestMethod = "POST"
        connection.doOutput = true
        connection.setRequestProperty("Content-Type", "application/json")
        connection.outputStream.use { it.write(body.toByteArray(StandardCharsets.UTF_8)) }
        connection.inputStream.close()
        connection.disconnect()
    }

    private fun get(path: String): String {
        val connection = URL(baseUrl() + path).openConnection() as HttpURLConnection
        connection.connectTimeout = 5000
        connection.readTimeout = 5000
        return connection.inputStream.bufferedReader().use { it.readText() }
            .also { connection.disconnect() }
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        executor.shutdownNow()
        super.onDestroy()
    }
}
