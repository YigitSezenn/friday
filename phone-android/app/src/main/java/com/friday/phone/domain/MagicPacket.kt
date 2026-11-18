package com.friday.phone.domain

enum class WakeResult { SENT, BAD_MAC, BAD_IP, BAD_PORT, FAILED }

sealed interface WakePlan {
    class Ready(val packet: ByteArray, val host: String, val port: Int) : WakePlan
    class Invalid(val reason: WakeResult) : WakePlan
}

const val DEFAULT_WAKE_PORT = 9

private val HOST = Regex("""^(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}$""")
private val MAC_SEPARATORS = Regex("[:\\-\\s.]")

/** 6 × 0xFF ardından MAC adresinin 16 kez tekrarı (102 bayt). MAC geçersizse null. */
fun buildMagicPacket(mac: String): ByteArray? {
    val hex = mac.lowercase().replace(MAC_SEPARATORS, "")
    if (hex.length != 12 || hex.any { it !in '0'..'9' && it !in 'a'..'f' }) return null
    val address = ByteArray(6) { index -> hex.substring(index * 2, index * 2 + 2).toInt(16).toByte() }
    val packet = ByteArray(102)
    for (index in 0 until 6) packet[index] = 0xFF.toByte()
    for (copy in 0 until 16) System.arraycopy(address, 0, packet, 6 + copy * 6, 6)
    return packet
}

/** Denetim sırası eski köprüyle aynı: MAC, IP, port. Port boş ya da sayı değilse 9. */
fun planWake(mac: String?, ip: String?, port: String?): WakePlan {
    val packet = buildMagicPacket(mac.orEmpty()) ?: return WakePlan.Invalid(WakeResult.BAD_MAC)
    val host = ip?.trim().orEmpty()
    if (!HOST.matches(host)) return WakePlan.Invalid(WakeResult.BAD_IP)
    val chosen = port?.trim()?.toIntOrNull() ?: DEFAULT_WAKE_PORT
    if (chosen !in 1..65535) return WakePlan.Invalid(WakeResult.BAD_PORT)
    return WakePlan.Ready(packet, host, chosen)
}
