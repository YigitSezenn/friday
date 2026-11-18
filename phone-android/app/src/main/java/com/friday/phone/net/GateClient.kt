package com.friday.phone.net

import com.friday.phone.domain.Delivery
import com.friday.phone.domain.SITE
import com.friday.phone.domain.interpretGateReply
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

/** Komutu, sitenin /komut adresi üzerinden bilgisayardaki kapıya iletir (web sayfasındaki akışın aynısı). */
object GateClient {
    suspend fun send(key: String, text: String): Delivery = withContext(Dispatchers.IO) {
        try {
            val form = "key=${encode(key)}&text=${encode(text)}".toByteArray(Charsets.UTF_8)
            val connection = URL("$SITE/komut").openConnection() as HttpURLConnection
            connection.requestMethod = "POST"
            connection.connectTimeout = 10_000
            connection.readTimeout = 15_000
            connection.doOutput = true
            connection.instanceFollowRedirects = true
            connection.setRequestProperty("Content-Type", "application/x-www-form-urlencoded;charset=UTF-8")
            try {
                connection.outputStream.use { it.write(form) }
                val stream = if (connection.responseCode >= 400) connection.errorStream else connection.inputStream
                val page = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
                interpretGateReply(connection.url.toString(), page)
            } finally {
                connection.disconnect()
            }
        } catch (_: IOException) {
            Delivery.OFFLINE
        }
    }

    private fun encode(value: String): String = URLEncoder.encode(value, Charsets.UTF_8.name())
}
