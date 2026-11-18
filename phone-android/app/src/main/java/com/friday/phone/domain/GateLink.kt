package com.friday.phone.domain

import java.net.URLDecoder

const val SITE = "https://site-seven-bay-75.vercel.app"

/** QR'dan ya da bağlantıdan gelen metin FRIDAY eşleştirme bağlantısı mı? */
fun isPairingLink(text: String): Boolean = text.startsWith(SITE)

/** `https://…/#k=<anahtar>` bağlantısından kapı anahtarını çıkarır. Bulamazsa boş döner. */
fun gateKeyFrom(url: String): String {
    val hash = url.substringAfter('#', "")
    val raw = hash.substringAfter("k=", "").substringBefore('&').trim()
    if (raw.isEmpty()) return ""
    return try {
        URLDecoder.decode(raw, Charsets.UTF_8.name()).trim()
    } catch (_: Exception) {
        raw
    }
}
