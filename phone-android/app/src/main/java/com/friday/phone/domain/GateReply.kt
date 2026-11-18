package com.friday.phone.domain

enum class Delivery { DELIVERED, EMPTY, STALE_KEY, REJECTED, OFFLINE }

/** Kapının yanıtını yorumlar. Sıra site/main.js ile aynı: önce yönlendirme adresi, sonra sayfa metni. */
fun interpretGateReply(finalUrl: String, body: String): Delivery = when {
    finalUrl.contains("iletildi=1") -> Delivery.DELIVERED
    body.contains("Komut boş") -> Delivery.EMPTY
    body.contains("Anahtar olmadı") -> Delivery.STALE_KEY
    else -> Delivery.REJECTED
}
