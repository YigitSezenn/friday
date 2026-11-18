package com.friday.phone.domain

const val HISTORY_LIMIT = 30

data class HistoryItem(val text: String, val time: Long, val delivered: Boolean)

/** Yeni komutu başa ekler, aynı metnin eski kaydını düşürür, en çok [limit] kayıt tutar. */
fun List<HistoryItem>.withNewest(item: HistoryItem, limit: Int = HISTORY_LIMIT): List<HistoryItem> =
    (listOf(item) + this.filterNot { it.text == item.text }).take(limit)
