package com.friday.phone.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.friday.phone.data.FridayStore
import com.friday.phone.data.WakeConfig
import com.friday.phone.domain.Delivery
import com.friday.phone.domain.HistoryItem
import com.friday.phone.domain.WakeResult
import com.friday.phone.domain.codeMatches
import com.friday.phone.domain.gateKeyFrom
import com.friday.phone.domain.isPairingLink
import com.friday.phone.domain.pairCode
import com.friday.phone.domain.withNewest
import com.friday.phone.net.GateClient
import com.friday.phone.net.WakeOnLan
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class UiState(
    val paired: Boolean,
    val pairingCode: String = "",
    val pendingKey: String = "",
    val pairError: String? = null,
    val sending: Boolean = false,
    val history: List<HistoryItem> = emptyList(),
    val wake: WakeConfig = WakeConfig(),
    val waking: Boolean = false,
    val message: String? = null,
)

class FridayViewModel(app: Application) : AndroidViewModel(app) {
    private val store = FridayStore(app)
    private val _state = MutableStateFlow(initialState())
    val state: StateFlow<UiState> = _state.asStateFlow()

    private fun initialState(): UiState {
        val key = store.gateKey
        return UiState(
            paired = key.isNotEmpty(),
            pairingCode = if (key.isNotEmpty()) pairCode(key) else "",
            history = store.history(),
            wake = store.wake,
        )
    }

    // ---- Eşleştirme ----

    /** QR'dan ya da açılış bağlantısından gelen metin. Anahtarı hemen kaydetmez: önce ekrandaki kod doğrulanır. */
    fun onLink(text: String) {
        val link = text.trim()
        if (!isPairingLink(link)) return say("Bu bir FRIDAY QR kodu değil.")
        val key = gateKeyFrom(link)
        if (key.isEmpty()) return say("QR kodunda anahtar yok. FRIDAY ekranındaki kodu yeniden okut.")
        _state.update { it.copy(pendingKey = key, pairError = null) }
    }

    fun confirmCode(entered: String) {
        val key = _state.value.pendingKey
        if (!codeMatches(key, entered)) {
            _state.update { it.copy(pairError = "Kod tutmadı. Bilgisayardaki 6 haneli kodu gir.") }
            return
        }
        store.gateKey = key
        _state.update { it.copy(paired = true, pairingCode = pairCode(key), pendingKey = "", pairError = null, message = "Eşleşti.") }
    }

    fun cancelPairing() = _state.update { it.copy(pendingKey = "", pairError = null) }

    fun forgetPairing() {
        store.clearGateKey()
        _state.update { it.copy(paired = false, pairingCode = "", pendingKey = "", message = "Eşleşme silindi.") }
    }

    // ---- Komut ----

    fun send(text: String) {
        val command = text.trim()
        val key = store.gateKey
        if (command.isEmpty()) return
        if (key.isEmpty()) return say("Önce QR okutup eşleş.")
        if (_state.value.sending) return
        _state.update { it.copy(sending = true) }
        viewModelScope.launch {
            val outcome = GateClient.send(key, command)
            val history = _state.value.history.withNewest(HistoryItem(command, System.currentTimeMillis(), outcome == Delivery.DELIVERED))
            store.saveHistory(history)
            _state.update { it.copy(sending = false, history = history, message = describe(outcome)) }
        }
    }

    fun onHeard(said: String) {
        if (said.isBlank()) say("Ses alınamadı.") else send(said)
    }

    private fun describe(outcome: Delivery): String = when (outcome) {
        Delivery.DELIVERED -> "Komut bilgisayara iletildi."
        Delivery.EMPTY -> "Komut boş."
        Delivery.STALE_KEY -> "QR eski. FRIDAY ekranındaki QR kodu yeniden okut."
        Delivery.REJECTED -> "Komut iletilemedi."
        Delivery.OFFLINE -> "Bağlantı kurulamadı."
    }

    // ---- Uyandırma ----

    fun wake(config: WakeConfig) {
        if (_state.value.waking) return
        _state.update { it.copy(waking = true) }
        viewModelScope.launch {
            val result = WakeOnLan.send(config.mac, config.ip, config.port)
            if (result == WakeResult.SENT) store.wake = config
            _state.update {
                it.copy(waking = false, wake = if (result == WakeResult.SENT) config else it.wake, message = describe(result))
            }
        }
    }

    private fun describe(result: WakeResult): String = when (result) {
        WakeResult.SENT -> "Uyandırma paketi gönderildi."
        WakeResult.BAD_MAC -> "MAC adresi olmadı."
        WakeResult.BAD_IP -> "IP adresi olmadı."
        WakeResult.BAD_PORT -> "Port olmadı."
        WakeResult.FAILED -> "Paket gönderilemedi."
    }

    // ---- Ortak ----

    fun say(message: String) = _state.update { it.copy(message = message) }

    fun consumeMessage() = _state.update { it.copy(message = null) }
}
