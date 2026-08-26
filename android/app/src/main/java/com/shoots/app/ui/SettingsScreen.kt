package com.shoots.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.shoots.app.FindingRed
import com.shoots.app.Ink
import com.shoots.app.MutedWhite
import com.shoots.app.WarmWhite
import com.shoots.app.data.MobileSnapshotDto
import com.shoots.app.data.SourceStateEntity
import com.shoots.app.phone.MediaAccess

@Composable
fun SettingsScreen(
    snapshot: MobileSnapshotDto?,
    source: SourceStateEntity?,
    mediaAccess: MediaAccess,
    notificationsGranted: Boolean,
    busy: Boolean,
    onRequestMedia: () -> Unit,
    onDisableSource: () -> Unit,
    onRequestNotifications: () -> Unit,
    onConnectDrive: () -> Unit,
    onDisconnectDrive: () -> Unit,
    onOpenDrive: (String) -> Unit,
    onReauthenticate: () -> Unit,
    onRevoke: () -> Unit,
    onDelete: () -> Unit,
) {
    var confirmRevoke by remember { mutableStateOf(false) }
    var confirmDelete by remember { mutableStateOf(false) }
    Column(
        Modifier.fillMaxSize().background(Ink).statusBarsPadding().verticalScroll(rememberScrollState()).padding(horizontal = 20.dp, vertical = 22.dp),
    ) {
        ScreenTitle("Settings", "Your account and sources.", "Permissions describe what Shoots can observe. You can remove each one.")
        Spacer(Modifier.height(24.dp))

        SectionTitle("Account")
        Spacer(Modifier.height(10.dp))
        InkCard {
            Text(snapshot?.user?.name.orEmpty().ifBlank { "Google account" }, color = WarmWhite, fontSize = 17.sp, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(4.dp))
            Text(snapshot?.user?.email.orEmpty(), color = MutedWhite, fontSize = 13.sp)
            source?.lastSuccessfulSyncAt?.takeIf(String::isNotBlank)?.let {
                Spacer(Modifier.height(10.dp))
                Text("Last synced ${displayTime(it)}", color = MutedWhite, fontSize = 11.sp)
            }
        }

        Spacer(Modifier.height(22.dp))
        SectionTitle("Camera media")
        Spacer(Modifier.height(10.dp))
        InkCard {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = androidx.compose.foundation.layout.Arrangement.SpaceBetween) {
                Text("Phone Source", color = WarmWhite, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
                StatusPill(
                    when {
                        mediaAccess == MediaAccess.FULL && source?.enabled == true -> "future only"
                        mediaAccess == MediaAccess.SELECTED -> "selected only"
                        else -> "off"
                    }
                )
            }
            Spacer(Modifier.height(7.dp))
            Text(
                "Full access observes future still Shots in the Camera album. Selected access only imports what you pick.",
                color = MutedWhite,
                fontSize = 13.sp,
                lineHeight = 19.sp,
            )
            Spacer(Modifier.height(13.dp))
            if (mediaAccess != MediaAccess.FULL) {
                SecondaryAction("Change media access", onClick = onRequestMedia)
            } else if (source?.enabled == true) {
                SecondaryAction("Stop automatic future import", onClick = onDisableSource)
            }
        }

        Spacer(Modifier.height(22.dp))
        SectionTitle("Session summaries")
        Spacer(Modifier.height(10.dp))
        InkCard {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = androidx.compose.foundation.layout.Arrangement.SpaceBetween) {
                Text("Notifications", color = WarmWhite, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
                StatusPill(if (notificationsGranted) "allowed" else "off")
            }
            Spacer(Modifier.height(7.dp))
            Text(
                "Shoots sends one summary after every member of a Capture Session settles. It does not send a verdict for each Shot.",
                color = MutedWhite,
                fontSize = 13.sp,
                lineHeight = 19.sp,
            )
            if (!notificationsGranted) {
                Spacer(Modifier.height(13.dp))
                SecondaryAction("Allow session summaries", onClick = onRequestNotifications)
            }
        }

        Spacer(Modifier.height(22.dp))
        SectionTitle("Google Drive", "OPTIONAL")
        Spacer(Modifier.height(10.dp))
        InkCard {
            Text(
                if (snapshot?.driveConnected == true) "Drive is connected." else "Drive is not connected.",
                color = WarmWhite,
                fontSize = 15.sp,
                fontWeight = FontWeight.SemiBold,
            )
            Spacer(Modifier.height(7.dp))
            Text(
                "Drive consent is separate from sign-in. Disconnecting removes Shoots access; your files remain in Drive.",
                color = MutedWhite,
                fontSize = 13.sp,
                lineHeight = 19.sp,
            )
            Spacer(Modifier.height(13.dp))
            if (snapshot?.driveConnected == true) {
                if (snapshot.driveFolderUrl.isNotBlank()) {
                    SecondaryAction("Open Shoots folder") { onOpenDrive(snapshot.driveFolderUrl) }
                    Spacer(Modifier.height(8.dp))
                }
                SecondaryAction("Disconnect Drive", onClick = onDisconnectDrive)
            } else {
                PrimaryAction("Connect Drive", enabled = !busy, onClick = onConnectDrive)
            }
        }

        Spacer(Modifier.height(26.dp))
        SectionTitle("Account controls")
        Spacer(Modifier.height(10.dp))
        SecondaryAction("Refresh Google sign-in", onClick = onReauthenticate)
        Spacer(Modifier.height(8.dp))
        SecondaryAction("Revoke this device") { confirmRevoke = true }
        Spacer(Modifier.height(8.dp))
        SecondaryAction("Delete account and Shoots data", danger = true) { confirmDelete = true }
        Spacer(Modifier.height(94.dp))
    }

    if (confirmRevoke) {
        ConfirmDialog(
            title = "Revoke this device?",
            body = "This device token, local cache, queued imports, and notification target will be removed.",
            action = "Revoke",
            onDismiss = { confirmRevoke = false },
            onConfirm = { confirmRevoke = false; onRevoke() },
        )
    }
    if (confirmDelete) {
        ConfirmDialog(
            title = "Delete your Shoots account?",
            body = "Google will confirm your identity again. Shoots records and stored blobs are deleted. User-owned Drive files remain.",
            action = "Delete account",
            onDismiss = { confirmDelete = false },
            onConfirm = { confirmDelete = false; onDelete() },
        )
    }
}

@Composable
private fun ConfirmDialog(
    title: String,
    body: String,
    action: String,
    onDismiss: () -> Unit,
    onConfirm: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title, color = WarmWhite) },
        text = { Text(body, color = MutedWhite, lineHeight = 20.sp) },
        confirmButton = { TextButton(onClick = onConfirm) { Text(action, color = FindingRed) } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Keep account", color = WarmWhite) } },
        containerColor = com.shoots.app.InkRaised,
    )
}
