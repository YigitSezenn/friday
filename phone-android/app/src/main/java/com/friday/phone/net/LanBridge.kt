package com.friday.phone.net

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.AudioTrack
import android.media.MediaRecorder
import com.friday.phone.domain.LAN_CHUNK_BYTES
import com.friday.phone.domain.LAN_SAMPLE_RATE
import com.friday.phone.domain.LanLink
import com.friday.phone.domain.playablePcm
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

/**
 * Telefon mikrofonunu (/mic) bilgisayara, bilgisayarın sesini (/speaker) telefona taşır.
 * Yalnızca aynı Wi-Fi'deki özel adrese bağlanır; bağlantı koparsa durur ve nedenini bildirir.
 */
class LanBridge(private val link: LanLink, private val scope: CoroutineScope) {
    private var job: Job? = null

    val running: Boolean get() = job?.isActive == true

    /** RECORD_AUDIO izni çağıran tarafta alınmış olmalı. */
    @SuppressLint("MissingPermission")
    fun start(onError: (String) -> Unit) {
        if (running) return
        job = scope.launch(Dispatchers.IO) {
            try {
                coroutineScope {
                    launch { micLoop() }
                    launch { speakerLoop() }
                }
            } catch (e: IOException) {
                onError("Yerel köprüye ulaşılamadı. Aynı Wi-Fi'de misin?")
            } catch (e: SecurityException) {
                onError("Mikrofon izni gerekli.")
            } catch (e: IllegalStateException) {
                onError("Mikrofon açılamadı.")
            }
        }
    }

    fun stop() {
        job?.cancel()
        job = null
    }

    @SuppressLint("MissingPermission")
    private suspend fun micLoop() {
        val minBuf = AudioRecord.getMinBufferSize(
            LAN_SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT,
        )
        val record = AudioRecord(
            MediaRecorder.AudioSource.VOICE_RECOGNITION,
            LAN_SAMPLE_RATE,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
            maxOf(minBuf, LAN_CHUNK_BYTES * 4),
        )
        check(record.state == AudioRecord.STATE_INITIALIZED) { "mic" }
        val buffer = ByteArray(LAN_CHUNK_BYTES)
        try {
            record.startRecording()
            while (currentCoroutineContext().isActive) {
                val read = record.read(buffer, 0, buffer.size)
                if (read > 0) post(link.url("/mic"), buffer.copyOf(read))
            }
        } finally {
            runCatching { record.stop() }
            record.release()
        }
    }

    private suspend fun speakerLoop() {
        val minOut = AudioTrack.getMinBufferSize(
            LAN_SAMPLE_RATE, AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_16BIT,
        )
        val track = AudioTrack(
            AudioManager.STREAM_VOICE_CALL,
            LAN_SAMPLE_RATE,
            AudioFormat.CHANNEL_OUT_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
            maxOf(minOut, LAN_CHUNK_BYTES * 4),
            AudioTrack.MODE_STREAM,
        )
        try {
            track.play()
            while (currentCoroutineContext().isActive) {
                delay(250)
                val pcm = playablePcm(fetch(link.url("/speaker")))
                if (pcm.isNotEmpty()) track.write(pcm, 0, pcm.size)
            }
        } finally {
            runCatching { track.stop() }
            track.release()
        }
    }

    private fun post(url: String, body: ByteArray) {
        val connection = open(url)
        try {
            connection.requestMethod = "POST"
            connection.doOutput = true
            connection.setRequestProperty("Content-Type", "application/octet-stream")
            connection.outputStream.use { it.write(body) }
            connection.responseCode
        } finally {
            connection.disconnect()
        }
    }

    private fun fetch(url: String): ByteArray? {
        val connection = open(url)
        return try {
            if (connection.responseCode != HttpURLConnection.HTTP_OK) null
            else connection.inputStream.use { it.readBytes() }
        } finally {
            connection.disconnect()
        }
    }

    private fun open(url: String): HttpURLConnection =
        (URL(url).openConnection() as HttpURLConnection).apply {
            connectTimeout = 3_000
            readTimeout = 3_000
        }
}
