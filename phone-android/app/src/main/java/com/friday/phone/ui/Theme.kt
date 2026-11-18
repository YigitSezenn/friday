package com.friday.phone.ui

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

// Masaüstü HUD'un varsayılan V3 teal paleti (jarvis/config.py UI_COLORS["teal"]).
val Teal = Color(0xFF00D4C4)
val TealInk = Color(0xFFC8F5F0)
val TealDim = Color(0xFF3A8A82)
val Alert = Color(0xFFFF4D4D)

private val Colors = darkColorScheme(
    primary = Teal,
    onPrimary = Color(0xFF001A18),
    primaryContainer = Color(0xFF00332F),
    onPrimaryContainer = Teal,
    secondary = TealDim,
    onSecondary = Color(0xFF001A18),
    tertiary = Alert,
    background = Color(0xFF030808),
    onBackground = TealInk,
    surface = Color(0xFF071312),
    onSurface = TealInk,
    surfaceVariant = Color(0xFF0C1E1C),
    onSurfaceVariant = Color(0xFF7FB8B1),
    outline = Color(0x4000D4C4),
    outlineVariant = Color(0x2200D4C4),
    error = Alert,
)

private val Type = Typography(
    headlineMedium = TextStyle(fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold, fontSize = 26.sp, letterSpacing = 9.sp),
    titleLarge = TextStyle(fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Medium, fontSize = 20.sp, letterSpacing = 5.sp),
    titleMedium = TextStyle(fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Medium, fontSize = 15.sp, letterSpacing = 2.sp),
    bodyLarge = TextStyle(fontSize = 16.sp, lineHeight = 22.sp),
    labelLarge = TextStyle(fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Medium, fontSize = 13.sp, letterSpacing = 2.sp),
    labelMedium = TextStyle(fontFamily = FontFamily.Monospace, fontSize = 11.sp, letterSpacing = 2.sp),
)

private val Shape = Shapes(
    small = RoundedCornerShape(12.dp),
    medium = RoundedCornerShape(18.dp),
    large = RoundedCornerShape(26.dp),
)

@Composable
fun FridayTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = Colors, typography = Type, shapes = Shape, content = content)
}
