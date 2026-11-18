package com.friday.phone.domain

/**
 * Bilgisayardaki FRIDAY'in gösterdiği 6 haneli doğrulama kodu.
 * jarvis/gate_client.py `pair_code` ve site/main.js `pairCode` ile birebir aynı hesap.
 */
fun pairCode(key: String): String {
    var total = 0L
    key.forEachIndexed { index, char -> total = (total * 131 + char.code + index) % 1_000_000L }
    return total.toString().padStart(6, '0')
}

fun codeMatches(key: String, entered: String): Boolean =
    key.isNotEmpty() && pairCode(key) == entered.trim()
