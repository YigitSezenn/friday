package com.friday.phone.domain

import java.net.URI
import java.net.URLDecoder
import java.net.URLEncoder

const val LAN_PORT = 8766

/** Bilgisayardaki telefon köprüsüne (aynı Wi-Fi) giden adres ve erişim anahtarı. */
data class LanLink(val host: String, val port: Int, val token: String) {
    fun url(route: String): String =
        "http://$host:$port$route?token=${URLEncoder.encode(token, Charsets.UTF_8.name())}"
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
    if (uri.scheme != "http") return null
    val host = uri.host ?: return null
    if (!isPrivateHost(host)) return null
    if (uri.path != "/join" && uri.path != "/") return null
    val port = if (uri.port == -1) LAN_PORT else uri.port
    if (port !in 1..65535) return null
    val raw = uri.rawQuery.orEmpty().split('&').firstOrNull { it.startsWith("token=") }
        ?.removePrefix("token=").orEmpty()
    val token = try {
        URLDecoder.decode(raw, Charsets.UTF_8.name()).trim()
    } catch (_: Exception) {
        raw.trim()
    }
    if (token.isEmpty()) return null
    return LanLink(host, port, token)
}
