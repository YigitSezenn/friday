package com.friday.phone

import android.Manifest
import android.annotation.SuppressLint
import android.content.pm.PackageManager
import android.os.Bundle
import android.webkit.JavascriptInterface
import android.webkit.PermissionRequest
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress

class MainActivity : ComponentActivity() {
    private lateinit var page: WebView
    private val scan = registerForActivityResult(ScanContract()) { result ->
        val text = result.contents?.trim().orEmpty()
        if (text.isEmpty() || !::page.isInitialized) return@registerForActivityResult
        if (text.startsWith("https://site-seven-bay-75.vercel.app/")) {
            page.loadUrl(text)
            return@registerForActivityResult
        }
    }
    private val cameraPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) openScanner()
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.RECORD_AUDIO), 1)
        }
        val view = WebView(this)
        page = view
        view.settings.javaScriptEnabled = true
        view.settings.mediaPlaybackRequiresUserGesture = false
        view.settings.domStorageEnabled = true
        val agent = view.settings.userAgentString.orEmpty()
        view.settings.userAgentString = "$agent FRIDAYAndroid"
        view.addJavascriptInterface(WakeBridge(), "FridayWake")
        view.addJavascriptInterface(KeyBridge(this), "FridayKey")
        view.webViewClient = WebViewClient()
        view.webChromeClient = object : WebChromeClient() {
            override fun onPermissionRequest(request: PermissionRequest) {
                request.grant(request.resources)
            }
        }
        setContentView(view)
        val incoming = intent?.dataString
        val start = if (incoming.isNullOrBlank()) "https://site-seven-bay-75.vercel.app/#yaz" else incoming
        view.loadUrl(start)
    }

    fun requestCamera() {
        cameraPermission.launch(Manifest.permission.CAMERA)
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

    companion object {
        private const val PREFS = "friday"
        private const val GATE = "gate"
    }
}

private class KeyBridge(private val activity: MainActivity) {
    @JavascriptInterface
    fun current(): String = activity.storedKey()

    @JavascriptInterface
    fun store(value: String?) {
        val text = value?.trim().orEmpty()
        if (text.isEmpty()) return
        activity.getSharedPreferences("friday", android.content.Context.MODE_PRIVATE)
            .edit()
            .putString("gate", text)
            .apply()
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
