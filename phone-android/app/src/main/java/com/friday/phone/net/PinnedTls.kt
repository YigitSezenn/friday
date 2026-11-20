package com.friday.phone.net

import com.friday.phone.domain.pinMatches
import java.security.MessageDigest
import java.security.SecureRandom
import java.security.cert.CertificateException
import java.security.cert.X509Certificate
import javax.net.ssl.SSLContext
import javax.net.ssl.SSLSocketFactory
import javax.net.ssl.X509TrustManager

/**
 * Bilgisayarın kendinden imzalı sertifikasını QR'daki SHA-256 parmak iziyle sabitler.
 * Parmak izi tutmazsa bağlantı kurulmaz; böylece ağdaki biri araya giremez.
 */
object PinnedTls {
    fun factory(pin: String): SSLSocketFactory {
        val trust = object : X509TrustManager {
            override fun checkClientTrusted(chain: Array<out X509Certificate>?, authType: String?) {
                throw CertificateException("İstemci sertifikası beklenmiyor")
            }

            override fun checkServerTrusted(chain: Array<out X509Certificate>?, authType: String?) {
                val leaf = chain?.firstOrNull() ?: throw CertificateException("Sertifika yok")
                val hash = MessageDigest.getInstance("SHA-256").digest(leaf.encoded)
                if (!pinMatches(hash, pin)) throw CertificateException("Sertifika parmak izi eşleşmedi")
            }

            override fun getAcceptedIssuers(): Array<X509Certificate> = emptyArray()
        }
        val context = SSLContext.getInstance("TLS")
        context.init(null, arrayOf(trust), SecureRandom())
        return context.socketFactory
    }
}
