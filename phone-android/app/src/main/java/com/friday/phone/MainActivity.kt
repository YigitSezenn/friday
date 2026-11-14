package com.friday.phone

import android.Manifest
import android.annotation.SuppressLint
import android.content.Intent
import android.content.pm.PackageManager
import android.content.ActivityNotFoundException
import android.os.Bundle
import android.speech.RecognizerIntent
import android.webkit.JavascriptInterface
import android.webkit.PermissionRequest
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions
import org.json.JSONObject
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.URLDecoder

class MainActivity : ComponentActivity() {
    private lateinit var page: WebView
    private lateinit var speech: SpeechBridge
    private var pendingKey: String = ""
    private val scan = registerForActivityResult(ScanContract()) { result ->
        val text = result.contents?.trim().orEmpty()
        if (text.isEmpty() || !::page.isInitialized) return@registerForActivityResult
        if (!text.startsWith(SITE)) return@registerForActivityResult
        val key = keyFrom(text)
        if (key.isEmpty()) return@registerForActivityResult
        storeKey(key)
        deliverKey(key)
    }
    private val cameraPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) openScanner()
    }
    private val micPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted && ::speech.isInitialized) speech.start()
        else runJs("window.__fridayVoiceError&&window.__fridayVoiceError()")
    }
    private val hear = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        val said = result.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)?.firstOrNull().orEmpty()
        runJs("window.__fridayHeard&&window.__fridayHeard(${JSONObject.quote(said)})")
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val view = WebView(this)
        page = view
        speech = SpeechBridge(this)
        view.settings.javaScriptEnabled = true
        view.settings.mediaPlaybackRequiresUserGesture = false
        view.settings.domStorageEnabled = true
        val agent = view.settings.userAgentString.orEmpty()
        view.settings.userAgentString = "$agent FRIDAYAndroid"
        view.addJavascriptInterface(WakeBridge(), "FridayWake")
        view.addJavascriptInterface(KeyBridge(this), "FridayKey")
        view.addJavascriptInterface(speech, "FridaySpeech")
        view.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView?, url: String?) {
                val key = pendingKey.ifEmpty { storedKey() }
                if (key.isNotEmpty()) deliverKey(key)
            }
        }
        view.webChromeClient = object : WebChromeClient() {
            override fun onPermissionRequest(request: PermissionRequest) {
                request.grant(request.resources)
            }
        }
        setContentView(view)
        val incoming = intent?.dataString
        val start = if (incoming.isNullOrBlank()) "$SITE/#yaz" else incoming
        val carried = if (incoming.isNullOrBlank()) "" else keyFrom(incoming)
        if (carried.isNotEmpty()) {
            storeKey(carried)
            pendingKey = carried
        }
        view.loadUrl(start.substringBefore('#'))
    }

    fun requestCamera() {
        cameraPermission.launch(Manifest.permission.CAMERA)
    }

    fun requestMic() {
        micPermission.launch(Manifest.permission.RECORD_AUDIO)
    }

    fun openSpeech(intent: Intent) {
        hear.launch(intent)
    }

    fun openScanner() {
        val options = ScanOptions()
        options.setDesiredBarcodeFormats(ScanOptions.QR_CODE)
        options.setPrompt("Kapı anahtarını okut")
        options.setBeepEnabled(false)
        scan.launch(options)
    }

    fun storedKey(): String {
        return getSharedPreferences(PREFS, MODE_PRIVATE).getString(GATE, "") ?: ""
    }

    fun storeKey(value: String) {
        val text = value.trim()
        if (text.isEmpty()) return
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(GATE, text).apply()
    }

    fun deliverKey(key: String) {
        val text = key.trim()
        if (text.isEmpty() || !::page.isInitialized) return
        pendingKey = text
        val quoted = JSONObject.quote(text)
        runJs("window.__fridayApplyKey&&window.__fridayApplyKey($quoted)")
    }

    fun runJs(script: String) {
        if (!::page.isInitialized) return
        page.post { page.evaluateJavascript(script, null) }
    }

    companion object {
        private const val PREFS = "friday"
        private const val GATE = "gate"
        private const val SITE = "https://site-seven-bay-75.vercel.app"
    }
}

private fun keyFrom(url: String): String {
    val hash = url.substringAfter('#', "")
    val raw = hash.substringAfter("k=", "").substringBefore('&').trim()
    if (raw.isEmpty()) return ""
    return try {
        URLDecoder.decode(raw, Charsets.UTF_8.name()).trim()
    } catch (_: Exception) {
        raw
    }
}

private class KeyBridge(private val activity: MainActivity) {
    @JavascriptInterface
    fun current(): String = activity.storedKey()

    @JavascriptInterface
    fun store(value: String?) {
        activity.storeKey(value.orEmpty())
    }

    @JavascriptInterface
    fun scan() {
        activity.runOnUiThread {
            if (ContextCompat.checkSelfPermission(activity, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
                activity.openScanner()
            } else {
                activity.requestCamera()
            }
        }
    }
}

private class SpeechBridge(private val activity: MainActivity) {
    @JavascriptInterface
    fun listen() {
        activity.runOnUiThread {
            if (ContextCompat.checkSelfPermission(activity, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
                start()
            } else {
                activity.requestMic()
            }
        }
    }

    fun start() {
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "tr-TR")
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "tr-TR")
        intent.putExtra(RecognizerIntent.EXTRA_PROMPT, "Dinliyorum")
        intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3)
        try {
            activity.openSpeech(intent)
        } catch (_: ActivityNotFoundException) {
            activity.runJs("window.__fridayHeard&&window.__fridayHeard('')")
        }
    }
}

private class WakeBridge {
    @JavascriptInterface
    fun wake(mac: String?, ip: String?, port: String?): String {
        val packet = magicPacket(mac ?: "") ?: return "mac"
        val host = ip?.trim().orEmpty()
        if (!HOST.matches(host)) return "ip"
        val chosen = port?.trim()?.toIntOrNull() ?: 9
        if (chosen !in 1..65535) return "port"
        return try {
            DatagramSocket().use { socket ->
                socket.broadcast = true
                val direct = InetAddress.getByName(host)
                socket.send(DatagramPacket(packet, packet.size, direct, chosen))
                val broadcast = InetAddress.getByName("255.255.255.255")
                socket.send(DatagramPacket(packet, packet.size, broadcast, chosen))
            }
            "ok"
        } catch (_: Exception) {
            "no"
        }
    }

    private fun magicPacket(mac: String): ByteArray? {
        val hex = mac.lowercase().replace(Regex("[:\\-\\s.]"), "")
        if (hex.length != 12 || hex.any { it !in '0'..'9' && it !in 'a'..'f' }) return null
        val address = ByteArray(6) { index -> hex.substring(index * 2, index * 2 + 2).toInt(16).toByte() }
        val packet = ByteArray(102)
        for (index in 0 until 6) packet[index] = 0xFF.toByte()
        for (copy in 0 until 16) System.arraycopy(address, 0, packet, 6 + copy * 6, 6)
        return packet
    }

    companion object {
        private val HOST = Regex("""^(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}$""")
    }
}
