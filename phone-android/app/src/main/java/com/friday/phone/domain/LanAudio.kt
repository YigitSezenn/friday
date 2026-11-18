package com.friday.phone.domain

/** Köprünün ses biçimi: 16 kHz, tek kanal, 16 bit. Bilgisayardaki /mic ve /speaker aynısını bekler. */
const val LAN_SAMPLE_RATE = 16_000

/** 100 ms'lik mikrofon parçası (16 bit ⇒ örnek başına 2 bayt). */
const val LAN_CHUNK_BYTES = LAN_SAMPLE_RATE / 10 * 2

/** /speaker yanıtından çalınabilir kısmı ayırır: tek bayt ya da boş yanıt çalınmaz, tek sayıdaki son bayt atılır. */
fun playablePcm(bytes: ByteArray?): ByteArray {
    if (bytes == null || bytes.size < 2) return ByteArray(0)
    return if (bytes.size % 2 == 0) bytes else bytes.copyOf(bytes.size - 1)
}
