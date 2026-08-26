package com.shoots.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.shoots.app.Ink
import com.shoots.app.MutedWhite
import com.shoots.app.WarmWhite

@Composable
fun SignInScreen(busy: Boolean, error: String, onSignIn: () -> Unit, onDismiss: () -> Unit) {
    Column(
        Modifier
            .fillMaxSize()
            .background(Ink)
            .statusBarsPadding()
            .navigationBarsPadding()
            .padding(horizontal = 24.dp, vertical = 32.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        ScreenTitle(
            "Shoots",
            "Learn to see like yourself.",
            "Shoots learns from every Shot, offers one personal Experiment, and tracks what changes.",
        )
        Spacer(Modifier.height(34.dp))
        Text("WHAT IT DOES", color = MutedWhite, fontSize = 10.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(9.dp))
        Text(
            "Your phone stays your camera. Shoots quietly reads future Camera Shots, remembers the decisions you repeat, and compares Experiments with your own Keepers.",
            color = WarmWhite,
            fontSize = 15.sp,
            lineHeight = 22.sp,
        )
        Spacer(Modifier.height(24.dp))
        MessageBanner(error, true, onDismiss)
        if (error.isNotBlank()) Spacer(Modifier.height(14.dp))
        PrimaryAction(if (busy) "Signing in…" else "Continue with Google", enabled = !busy, onClick = onSignIn)
        Spacer(Modifier.height(12.dp))
        Text(
            "Drive is not connected by signing in. You can grant it separately later.",
            color = MutedWhite,
            fontSize = 12.sp,
            lineHeight = 17.sp,
        )
    }
}
