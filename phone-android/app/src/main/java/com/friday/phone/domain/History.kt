package com.friday.phone.domain

const val HISTORY_LIMIT = 30

/** Gönderilen komut. [pinned] kayıtlar en üstte durur ve sınır yüzünden silinmez. */
data class HistoryItem(val text: String, val time: Long, val delivered: Boolean, val pinned: Boolean = false)

/** Sabitlenenler önce (kendi sıralarıyla), sonra diğerleri yeniden eskiye. */
fun List<HistoryItem>.ordered(): List<HistoryItem> = filter { it.pinned } + filterNot { it.pinned }

/** Sınır yalnızca sabitlenmemiş kayıtlara uygulanır; sabitlenenler hiç düşmez. */
private fun List<HistoryItem>.capped(limit: Int): List<HistoryItem> =
    filter { it.pinned } + filterNot { it.pinned }.take(limit)

/** Yeni komutu başa ekler, aynı metnin eski kaydını düşürür (sabitlemesi korunur), en çok [limit] kayıt tutar. */
fun List<HistoryItem>.withNewest(item: HistoryItem, limit: Int = HISTORY_LIMIT): List<HistoryItem> {
    val old = firstOrNull { it.text == item.text }
    val fresh = item.copy(pinned = item.pinned || (old?.pinned ?: false))
    return (listOf(fresh) + filterNot { it.text == item.text }).ordered().capped(limit)
}

/** Kaydı siler. */
fun List<HistoryItem>.without(text: String): List<HistoryItem> = filterNot { it.text == text }

/** Kaydın metnini değiştirir; yeni metin boşsa değişmez, başka bir kayıtla aynıysa ikisi birleşir. */
fun List<HistoryItem>.edited(old: String, new: String): List<HistoryItem> {
    val text = new.trim()
    if (text.isEmpty() || text == old) return this
    val target = firstOrNull { it.text == old } ?: return this
    val merged = target.copy(text = text, pinned = target.pinned || any { it.text == text && it.pinned })
    return map { if (it.text == old) merged else it }.filterNot { it.text == text && it !== merged }.ordered()
}

/** Sabitlemeyi açar/kapatır. */
fun List<HistoryItem>.togglePinned(text: String): List<HistoryItem> =
    map { if (it.text == text) it.copy(pinned = !it.pinned) else it }.ordered()

/** Sabitlenmemiş kayıtları temizler. */
fun List<HistoryItem>.clearedUnpinned(): List<HistoryItem> = filter { it.pinned }
