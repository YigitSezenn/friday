package com.friday.phone.data

import android.content.Context
import com.friday.phone.domain.DEFAULT_WAKE_PORT
import com.friday.phone.domain.HistoryItem
import com.friday.phone.domain.LAN_PORT
import com.friday.phone.domain.LanLink
import org.json.JSONArray
import org.json.JSONObject

data class WakeConfig(val mac: String = "", val ip: String = "", val port: String = DEFAULT_WAKE_PORT.toString())

/** Telefonda kalıcı tutulanlar. Dosya adı ve "gate" anahtarı eski sürümle aynı: güncellemede eşleşme kaybolmaz. */
class FridayStore(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    var gateKey: String
        get() = prefs.getString(GATE, "").orEmpty()
        set(value) = prefs.edit().putString(GATE, value.trim()).apply()

    fun clearGateKey() = prefs.edit().remove(GATE).apply()

    var wake: WakeConfig
        get() = WakeConfig(
            mac = prefs.getString(WAKE_MAC, "").orEmpty(),
            ip = prefs.getString(WAKE_IP, "").orEmpty(),
            port = prefs.getString(WAKE_PORT, DEFAULT_WAKE_PORT.toString()).orEmpty().ifEmpty { DEFAULT_WAKE_PORT.toString() },
        )
        set(value) = prefs.edit()
            .putString(WAKE_MAC, value.mac)
            .putString(WAKE_IP, value.ip)
            .putString(WAKE_PORT, value.port)
            .apply()

    /** Aynı Wi-Fi'deki bilgisayar köprüsü (telefon mikrofonu/hoparlörü). Token bu cihazda düz metin saklanır; yedekleme kapalı. */
    var lan: LanLink?
        get() {
            val host = prefs.getString(LAN_HOST, "").orEmpty()
            val token = prefs.getString(LAN_TOKEN, "").orEmpty()
            if (host.isEmpty() || token.isEmpty()) return null
            return LanLink(host, prefs.getInt(LAN_PORT_KEY, LAN_PORT), token)
        }
        set(value) {
            val editor = prefs.edit()
            if (value == null) {
                editor.remove(LAN_HOST).remove(LAN_PORT_KEY).remove(LAN_TOKEN)
            } else {
                editor.putString(LAN_HOST, value.host).putInt(LAN_PORT_KEY, value.port).putString(LAN_TOKEN, value.token)
            }
            editor.apply()
        }

    fun history(): List<HistoryItem> {
        val raw = prefs.getString(HISTORY, null) ?: return emptyList()
        return try {
            val array = JSONArray(raw)
            (0 until array.length()).map { index ->
                val item = array.getJSONObject(index)
                HistoryItem(item.getString("text"), item.getLong("time"), item.getBoolean("ok"))
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    fun saveHistory(items: List<HistoryItem>) {
        val array = JSONArray()
        items.forEach { array.put(JSONObject().put("text", it.text).put("time", it.time).put("ok", it.delivered)) }
        prefs.edit().putString(HISTORY, array.toString()).apply()
    }

    private companion object {
        const val PREFS = "friday"
        const val GATE = "gate"
        const val WAKE_MAC = "wake_mac"
        const val WAKE_IP = "wake_ip"
        const val WAKE_PORT = "wake_port"
        const val HISTORY = "history"
        const val LAN_HOST = "lan_host"
        const val LAN_PORT_KEY = "lan_port"
        const val LAN_TOKEN = "lan_token"
    }
}
