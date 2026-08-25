package com.shoots.app

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val Ink = Color(0xFF0B0B0D)
val InkRaised = Color(0xFF151519)
val InkSoft = Color(0xFF1C1C22)
val WarmWhite = Color(0xFFF5F0E7)
val MutedWhite = Color(0xFFAAA59C)
val Amber = Color(0xFFF0B429)
val FindingRed = Color(0xFFE15B49)
val Hairline = Color(0xFF343239)

private val ShootsColours = darkColorScheme(
    primary = Amber,
    onPrimary = Ink,
    background = Ink,
    onBackground = WarmWhite,
    surface = InkRaised,
    onSurface = WarmWhite,
    error = FindingRed,
    onError = WarmWhite,
    outline = Hairline,
)

@Composable
fun ShootsTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = ShootsColours, content = content)
}
