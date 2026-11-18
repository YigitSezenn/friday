package com.friday.phone.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

// Masaüstü HUD'un altın/siyah paleti.
private val Gold = Color(0xFFE6C98A)
private val Cream = Color(0xFFF3E6C8)
private val Dim = Color(0xFFB7A98A)

private val Colors = darkColorScheme(
    primary = Gold,
    onPrimary = Color(0xFF1A140C),
    primaryContainer = Color(0xFF3A2F1A),
    onPrimaryContainer = Gold,
    secondary = Dim,
    onSecondary = Color(0xFF1A140C),
    background = Color(0xFF070605),
    onBackground = Cream,
    surface = Color(0xFF100E0A),
    onSurface = Cream,
    surfaceVariant = Color(0xFF1A1610),
    onSurfaceVariant = Dim,
    outline = Color(0x59E6C98A),
    error = Color(0xFFE7A0AE),
)

private val Type = Typography(
    titleLarge = TextStyle(fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Medium, fontSize = 20.sp, letterSpacing = 5.sp),
    titleMedium = TextStyle(fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Medium, fontSize = 15.sp, letterSpacing = 2.sp),
    labelLarge = TextStyle(fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Medium, fontSize = 13.sp, letterSpacing = 2.sp),
    labelMedium = TextStyle(fontFamily = FontFamily.Monospace, fontSize = 11.sp, letterSpacing = 2.sp),
)

@Composable
fun FridayTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = Colors, typography = Type, content = content)
}
