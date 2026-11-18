package com.friday.phone.ui

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.graphics.drawscope.withTransform
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin

/**
 * Masaüstündeki 3D çekirdeğin telefon hali: eğik dönen halkalar, yörünge boncukları, nefes alan çekirdek.
 * [busy] iken (komut gönderilirken) hızlanır ve parlar.
 */
@Composable
fun Reactor(modifier: Modifier = Modifier, busy: Boolean = false, color: Color = Teal, accent: Color = Alert) {
    val infinite = rememberInfiniteTransition(label = "reactor")
    val turn by infinite.animateFloat(
        initialValue = 0f, targetValue = 360f,
        animationSpec = infiniteRepeatable(tween(14000, easing = LinearEasing)), label = "turn",
    )
    val breath by infinite.animateFloat(
        initialValue = 0.85f, targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(1800), RepeatMode.Reverse), label = "breath",
    )
    val energy by animateFloatAsState(if (busy) 1f else 0f, tween(500), label = "energy")
    val speed = 1f + energy * 2.2f

    Canvas(modifier) {
        val r = min(size.width, size.height) / 2f
        val c = center
        // Arka parıltı
        drawCircle(
            Brush.radialGradient(
                listOf(color.copy(alpha = 0.28f + 0.2f * energy), color.copy(alpha = 0.06f), Color.Transparent),
                center = c, radius = r,
            ),
            radius = r, center = c,
        )
        // Eğik halkalar (3D hissi: dikeyde basık elips + dönen düzlem)
        val rings = listOf(
            Triple(0.92f, 0.34f, 1f),
            Triple(0.74f, 0.55f, -1.4f),
            Triple(0.56f, 0.8f, 1.9f),
        )
        rings.forEachIndexed { i, (scale, squash, dir) ->
            val angle = turn * dir * speed + i * 40f
            withTransform({
                rotate(angle, c)
            }) {
                val w = r * 2 * scale
                val h = w * squash
                drawOval(
                    color = color.copy(alpha = 0.55f - i * 0.1f + energy * 0.2f),
                    topLeft = Offset(c.x - w / 2, c.y - h / 2),
                    size = Size(w, h),
                    style = Stroke(width = r * 0.018f * (1.4f - i * 0.25f)),
                )
                // Boncuk
                val t = Math.toRadians((turn * 2.3f * dir * speed + i * 120f).toDouble())
                val bx = c.x + (w / 2) * cos(t).toFloat()
                val by = c.y + (h / 2) * sin(t).toFloat()
                val bead = if (i == 1) accent else color
                drawCircle(Brush.radialGradient(listOf(Color.White, bead, Color.Transparent), Offset(bx, by), r * 0.07f), r * 0.07f, Offset(bx, by))
            }
        }
        // İşaret çizgileri
        rotate(-turn * 0.5f * speed, c) {
            for (k in 0 until 60) {
                val a = Math.toRadians(k * 6.0)
                val long = k % 5 == 0
                val inner = r * (if (long) 0.95f else 0.97f)
                drawLine(
                    color.copy(alpha = if (long) 0.5f else 0.2f),
                    Offset(c.x + inner * cos(a).toFloat(), c.y + inner * sin(a).toFloat()),
                    Offset(c.x + r * cos(a).toFloat(), c.y + r * sin(a).toFloat()),
                    strokeWidth = r * 0.01f,
                )
            }
        }
        // Çekirdek
        val core = r * 0.24f * breath * (1f + 0.15f * energy)
        drawCircle(Brush.radialGradient(listOf(Color.White, color, color.copy(alpha = 0f)), c, core * 1.8f), core * 1.8f, c)
        drawCircle(Color.White.copy(alpha = 0.92f), core * 0.38f, c)
    }
}
