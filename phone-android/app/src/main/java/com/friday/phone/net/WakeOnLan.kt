package com.friday.phone.net

import com.friday.phone.domain.WakePlan
import com.friday.phone.domain.WakeResult
import com.friday.phone.domain.planWake
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress

/** Uyandırma paketini doğrudan IP'ye ve yerel ağ yayınına (255.255.255.255) gönderir. Eski köprüyle aynı davranış. */
object WakeOnLan {
    suspend fun send(mac: String, ip: String, port: String): WakeResult = withContext(Dispatchers.IO) {
        when (val plan = planWake(mac, ip, port)) {
            is WakePlan.Invalid -> plan.reason
            is WakePlan.Ready -> try {
                DatagramSocket().use { socket ->
                    socket.broadcast = true
                    val direct = InetAddress.getByName(plan.host)
                    socket.send(DatagramPacket(plan.packet, plan.packet.size, direct, plan.port))
                    val broadcast = InetAddress.getByName("255.255.255.255")
                    socket.send(DatagramPacket(plan.packet, plan.packet.size, broadcast, plan.port))
                }
                WakeResult.SENT
            } catch (_: Exception) {
                WakeResult.FAILED
            }
        }
    }
}
