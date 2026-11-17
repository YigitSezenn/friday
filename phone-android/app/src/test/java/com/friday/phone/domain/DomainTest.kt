package com.friday.phone.domain

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class DomainTest {
    @Test
    fun pairCodeMatchesDesktopAndSite() {
        // Değerler jarvis/gate_client.py pair_code çıktısından alındı.
        assertEquals("677687", pairCode("abc"))
        assertEquals("317524", pairCode("Zk3-_x9Q"))
        assertEquals("306960", pairCode("a".repeat(32)))
        assertEquals("000000", pairCode(""))
    }

    @Test
    fun codeMatchTrimsAndRejectsEmptyKey() {
        assertTrue(codeMatches("abc", " 677687 "))
        assertFalse(codeMatches("abc", "677688"))
        assertFalse(codeMatches("", "000000"))
    }

    @Test
    fun keyIsReadFromPairingLink() {
        assertEquals("abc", gateKeyFrom("$SITE/#k=abc"))
        assertEquals("a/b c", gateKeyFrom("$SITE/#k=a%2Fb%20c&x=1"))
        assertEquals("", gateKeyFrom("$SITE/"))
        assertEquals("", gateKeyFrom("$SITE/#k="))
        assertTrue(isPairingLink("$SITE/#k=abc"))
        assertFalse(isPairingLink("https://baska.site/#k=abc"))
    }

    @Test
    fun magicPacketLayout() {
        val packet = buildMagicPacket("AA:bb-CC.dd ee ff")
        assertNotNull(packet)
        assertEquals(102, packet!!.size)
        for (i in 0 until 6) assertEquals(0xFF.toByte(), packet[i])
        val mac = byteArrayOf(0xAA.toByte(), 0xBB.toByte(), 0xCC.toByte(), 0xDD.toByte(), 0xEE.toByte(), 0xFF.toByte())
        for (copy in 0 until 16) assertArrayEquals(mac, packet.copyOfRange(6 + copy * 6, 12 + copy * 6))
    }

    @Test
    fun badMacIsRejected() {
        assertNull(buildMagicPacket(""))
        assertNull(buildMagicPacket("AA:BB:CC:DD:EE"))
        assertNull(buildMagicPacket("GG:BB:CC:DD:EE:FF"))
    }

    @Test
    fun wakePlanChecksInTheOldOrder() {
        assertEquals(WakeResult.BAD_MAC, (planWake("x", "bad", "bad") as WakePlan.Invalid).reason)
        assertEquals(WakeResult.BAD_IP, (planWake("AA:BB:CC:DD:EE:FF", "300.1.1.1", "9") as WakePlan.Invalid).reason)
        assertEquals(WakeResult.BAD_IP, (planWake("AA:BB:CC:DD:EE:FF", "", "9") as WakePlan.Invalid).reason)
        assertEquals(WakeResult.BAD_PORT, (planWake("AA:BB:CC:DD:EE:FF", "192.168.1.20", "0") as WakePlan.Invalid).reason)
        assertEquals(WakeResult.BAD_PORT, (planWake("AA:BB:CC:DD:EE:FF", "192.168.1.20", "70000") as WakePlan.Invalid).reason)
    }

    @Test
    fun wakePortDefaultsToNineLikeBefore() {
        for (raw in listOf(null, "", "  ", "abc", "9")) {
            val plan = planWake("AA:BB:CC:DD:EE:FF", " 192.168.1.20 ", raw) as WakePlan.Ready
            assertEquals(9, plan.port)
            assertEquals("192.168.1.20", plan.host)
        }
        assertEquals(7, (planWake("AA:BB:CC:DD:EE:FF", "10.0.0.2", "7") as WakePlan.Ready).port)
    }

    @Test
    fun gateReplyIsReadInSiteOrder() {
        assertEquals(Delivery.DELIVERED, interpretGateReply("$SITE/?iletildi=1", "Komut boş"))
        assertEquals(Delivery.EMPTY, interpretGateReply("$SITE/komut", "... Komut boş ..."))
        assertEquals(Delivery.STALE_KEY, interpretGateReply("$SITE/komut", "Anahtar olmadı"))
        assertEquals(Delivery.REJECTED, interpretGateReply("$SITE/komut", "baska"))
    }

    @Test
    fun historyKeepsNewestFirstWithoutDuplicatesAndCapped() {
        val first = HistoryItem("a", 1, true)
        val again = HistoryItem("a", 2, false)
        val list = listOf(first).withNewest(HistoryItem("b", 2, true)).withNewest(again)
        assertEquals(listOf("a", "b"), list.map { it.text })
        assertEquals(2L, list.first().time)
        var big = emptyList<HistoryItem>()
        for (i in 0 until 50) big = big.withNewest(HistoryItem("k$i", i.toLong(), true))
        assertEquals(HISTORY_LIMIT, big.size)
        assertEquals("k49", big.first().text)
    }
}
