package com.friday.phone.domain

import java.net.URI
import java.net.URLDecoder
import java.net.URLEncoder

const val LAN_PORT = 8766
const val LAN_TLS_PORT = 8767

/** Bilgisayardaki telefon köprüsüne (aynı Wi-Fi) giden adres ve erişim anahtarı. */
data class LanLink(val host: String, val port: Int, val token: String, val pin: String = "") {
    /** pin doluysa bağlantı şifreli (https) ve sunucu sertifikası bu SHA-256 parmak iziyle sabitlenir. */
    val secure: Boolean get() = pin.isNotEmpty()

    fun url(route: String): String =
        "${if (secure) "https" else "http"}://$host:$port$route?token=${URLEncoder.encode(token, Charsets.UTF_8.name())}"
}

/** Sertifika parmak izi: 64 hex karakter (küçük/büyük harf fark etmez). */
fun isValidPin(text: String): Boolean = text.length == 64 && text.all { it in '0'..'9' || it in 'a'..'f' || it in 'A'..'F' }

/** Sunucudan gelen sertifikanın (DER) SHA-256'sı beklenen parmak iziyle aynı mı? */
fun pinMatches(certHash: ByteArray, pin: String): Boolean {
    if (!isValidPin(pin) || certHash.size != 32) return false
    val hex = certHash.joinToString("") { "%02x".format(it.toInt() and 0xff) }
    return hex.equals(pin, ignoreCase = true)
}

/**
 * Yalnızca yerel ağ adresleri (10.x, 172.16–31.x, 192.168.x, 169.254.x).
 * Köprü düz HTTP konuşur; bu kontrol, internetteki bir adrese mikrofon sesi gitmesini engeller.
 */
fun isPrivateHost(host: String): Boolean {
    val parts = host.split('.')
    if (parts.size != 4) return false
    if (!parts.all { it.isNotEmpty() && it.length <= 3 && it.all(Char::isDigit) }) return false
    val n = parts.map { it.toInt() }
    if (n.any { it > 255 }) return false
    return n[0] == 10 ||
        (n[0] == 172 && n[1] in 16..31) ||
        (n[0] == 192 && n[1] == 168) ||
        (n[0] == 169 && n[1] == 254)
}

/** `http://<ip>:8766/join?token=…` (bilgisayardaki telefon QR'ı) bağlantısını çözer. Geçersizse null. */
fun lanLinkFrom(text: String): LanLink? {
    val uri = try {
        URI(text.trim())
    } catch (_: Exception) {
        return null
    }
    val secure = uri.scheme == "https"
    if (uri.scheme != "http" && !secure) return null
    val host = uri.host ?: return null
    if (!isPrivateHost(host)) return null
    if (uri.path != "/join" && uri.path != "/") return null
    val port = if (uri.port == -1) (if (secure) LAN_TLS_PORT else LAN_PORT) else uri.port
    if (port !in 1..65535) return null
    val query = uri.rawQuery.orEmpty().split('&')
    val raw = query.firstOrNull { it.startsWith("token=") }?.removePrefix("token=").orEmpty()
    val pin = query.firstOrNull { it.startsWith("fp=") }?.removePrefix("fp=").orEmpty().lowercase()
    // https yalnızca parmak iziyle kabul edilir; sabitlemesiz şifreli bağlantı güvence vermez.
    if (secure && !isValidPin(pin)) return null
    val token = try {
        URLDecoder.decode(raw, Charsets.UTF_8.name()).trim()
    } catch (_: Exception) {
        raw.trim()
    }
    if (token.isEmpty()) return null
    return LanLink(host, port, token, if (secure) pin else "")
}
