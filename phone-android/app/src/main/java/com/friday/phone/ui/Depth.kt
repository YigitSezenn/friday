package com.friday.phone.ui

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.composed
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity

private const val MAX_TILT = 11f

/**
 * Parmağın bastığı yere doğru eğilen 3B kart. Dokunmayı tüketmez; tıklama ve uzun basma çalışmaya devam eder.
 * Parmak kalkınca yay gibi yerine döner.
 */
fun Modifier.tilt3d(): Modifier = composed {
    var rotX by remember { mutableStateOf(0f) }
    var rotY by remember { mutableStateOf(0f) }
    val spec = spring<Float>(Spring.DampingRatioMediumBouncy, Spring.StiffnessLow)
    val animX by animateFloatAsState(rotX, spec, label = "tiltX")
    val animY by animateFloatAsState(rotY, spec, label = "tiltY")
    val density = LocalDensity.current.density
    this
        .pointerInput(Unit) {
            awaitEachGesture {
                val down = awaitFirstDown(requireUnconsumed = false, pass = PointerEventPass.Initial)
                fun aim(x: Float, y: Float) {
                    val w = size.width.coerceAtLeast(1)
                    val h = size.height.coerceAtLeast(1)
                    rotY = ((x / w) - 0.5f) * 2f * MAX_TILT
                    rotX = (0.5f - (y / h)) * 2f * MAX_TILT
                }
                aim(down.position.x, down.position.y)
                while (true) {
                    val event = awaitPointerEvent(PointerEventPass.Initial)
                    val change = event.changes.firstOrNull() ?: break
                    if (!change.pressed) break
                    aim(change.position.x, change.position.y)
                }
                rotX = 0f
                rotY = 0f
            }
        }
        .graphicsLayer {
            rotationX = animX
            rotationY = animY
            cameraDistance = 14f * density
        }
}

/** Düğme basılınca çöker ve hafifçe öne yatar; bırakınca yaylanır. Dokunmayı tüketmez. */
fun Modifier.pressDepth(): Modifier = composed {
    var pressed by remember { mutableStateOf(false) }
    val scale by animateFloatAsState(
        if (pressed) 0.93f else 1f,
        spring(Spring.DampingRatioMediumBouncy, Spring.StiffnessMedium),
        label = "pressScale",
    )
    val lean by animateFloatAsState(
        if (pressed) 8f else 0f,
        spring(Spring.DampingRatioMediumBouncy, Spring.StiffnessMedium),
        label = "pressLean",
    )
    val density = LocalDensity.current.density
    this
        .pointerInput(Unit) {
            awaitEachGesture {
                awaitFirstDown(requireUnconsumed = false, pass = PointerEventPass.Initial)
                pressed = true
                while (true) {
                    val event = awaitPointerEvent(PointerEventPass.Initial)
                    if (event.changes.none { it.pressed }) break
                }
                pressed = false
            }
        }
        .graphicsLayer {
            scaleX = scale
            scaleY = scale
            rotationX = lean
            cameraDistance = 12f * density
        }
}

/** Yüzen kart: yavaşça yukarı aşağı süzülür. [phase] kartların aynı anda oynamaması için kaydırma verir. */
fun Modifier.floating(phase: Int = 0, amplitude: Float = 3f): Modifier = composed {
    val transition = rememberInfiniteTransition(label = "float")
    val offset by transition.animateFloat(
        initialValue = -amplitude,
        targetValue = amplitude,
        animationSpec = infiniteRepeatable(tween(2600 + (phase % 4) * 450, easing = FastOutSlowInEasing), RepeatMode.Reverse),
        label = "floatY",
    )
    val density = LocalDensity.current.density
    this.graphicsLayer { translationY = offset * density }
}

/** Ekrana girerken aşağıdan süzülür, derinlikte öne gelir. */
fun Modifier.arrive(index: Int = 0): Modifier = composed {
    val progress = remember { Animatable(0f) }
    androidx.compose.runtime.LaunchedEffect(Unit) {
        kotlinx.coroutines.delay((index.coerceAtMost(8) * 70).toLong())
        progress.animateTo(1f, tween(520, easing = FastOutSlowInEasing))
    }
    val density = LocalDensity.current.density
    this.graphicsLayer {
        val p = progress.value
        alpha = p
        translationY = (1f - p) * 36f * density
        rotationX = (1f - p) * -18f
        cameraDistance = 14f * density
    }
}
