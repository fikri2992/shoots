package com.shoots.app.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateContentSize
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.shoots.app.Amber
import com.shoots.app.FindingRed
import com.shoots.app.Hairline
import com.shoots.app.Ink
import com.shoots.app.InkRaised
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
    onBack: () -> Unit,
    onRequestMedia: () -> Unit,
    onEnableSource: () -> Unit,
    onDisableSource: () -> Unit,
    onRequestNotifications: () -> Unit,
    onConnectDrive: () -> Unit,
    onDisconnectDrive: () -> Unit,
    onOpenDrive: (String) -> Unit,
    onForgetSignal: (String) -> Unit,
    onReauthenticate: () -> Unit,
    onRevoke: () -> Unit,
    onDelete: () -> Unit,
) {
    var expanded by remember { mutableStateOf<String?>(null) }
    var confirmRevoke by remember { mutableStateOf(false) }
    var confirmDelete by remember { mutableStateOf(false) }
    val rememberedSignals = snapshot?.photographerSignals.orEmpty()
        .filterNot { it.kind == "source_role" }
    Column(
        Modifier
            .fillMaxSize()
            .background(Ink)
            .statusBarsPadding()
            .navigationBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp)
            .padding(top = 14.dp, bottom = 34.dp),
    ) {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            BackAction("Now", onBack)
            Text("SETTINGS", color = Amber, fontSize = 11.sp, fontWeight = FontWeight.Bold)
        }
        Spacer(Modifier.height(18.dp))
        if (snapshot?.user?.recordMode == "sample") {
            Text("Sample Record", color = WarmWhite, fontSize = 26.sp, lineHeight = 31.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(7.dp))
            Text(
                "This fixture is read-only. Account, Phone Source, Drive, notification, memory, and deletion controls are unavailable.",
                color = MutedWhite,
                fontSize = 14.sp,
                lineHeight = 20.sp,
            )
            return@Column
        }
        Text("Account and access", color = WarmWhite, fontSize = 26.sp, lineHeight = 31.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(7.dp))
        Text(
            snapshot?.user?.email.orEmpty(),
            color = MutedWhite,
            fontSize = 13.sp,
            maxLines = 1,
        )
        source?.lastSuccessfulSyncAt?.takeIf(String::isNotBlank)?.let {
            Spacer(Modifier.height(3.dp))
            Text("Last synced ${displayTime(it)}", color = MutedWhite, fontSize = 11.sp)
        }
        Spacer(Modifier.height(24.dp))

        Column(
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(18.dp))
                .background(InkRaised)
                .border(1.dp, Hairline, RoundedCornerShape(18.dp))
                .animateContentSize(animationSpec = tween(180)),
        ) {
            SettingsDisclosure(
                title = "Phone Source",
                summary = when {
                    mediaAccess == MediaAccess.FULL && source?.enabled == true -> "Automatic · future Camera Shots"
                    mediaAccess == MediaAccess.SELECTED -> "Selected Shots only"
                    else -> "Off"
                },
                expanded = expanded == "source",
                onToggle = { expanded = expanded.toggle("source") },
            ) {
                Text(
                    "Full access observes only future still Shots in the Camera album. Selected access imports only what you pick.",
                    color = MutedWhite,
                    fontSize = 13.sp,
                    lineHeight = 19.sp,
                )
                Spacer(Modifier.height(13.dp))
                when {
                    mediaAccess != MediaAccess.FULL -> SecondaryAction("Change media access", onClick = onRequestMedia)
                    source?.enabled == true -> SecondaryAction("Stop automatic future import", onClick = onDisableSource)
                    else -> PrimaryAction("Start automatic future import", enabled = !busy, onClick = onEnableSource)
                }
            }
            HorizontalDivider(color = Hairline)

            SettingsDisclosure(
                title = "What Shoots remembers",
                summary = when (val count = rememberedSignals.size) {
                    0 -> "Nothing explicitly stored"
                    1 -> "1 Photographer statement"
                    else -> "$count Photographer statements"
                },
                expanded = expanded == "memory",
                onToggle = { expanded = expanded.toggle("memory") },
            ) {
                Text(
                    "Only your direct statements and actions belong here. You can remove any one without deleting your Shots.",
                    color = MutedWhite,
                    fontSize = 13.sp,
                    lineHeight = 19.sp,
                )
                rememberedSignals.forEach { signal ->
                    Spacer(Modifier.height(12.dp))
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Column(Modifier.weight(1f)) {
                            Text(signal.value, color = WarmWhite, fontSize = 13.sp)
                            Text(
                                "${signal.kind.replace('_', ' ')} · ${signal.scope.replace('_', ' ')}",
                                color = MutedWhite,
                                fontSize = 10.sp,
                            )
                        }
                        TextButton(onClick = { onForgetSignal(signal.id) }) {
                            Text("Forget", color = Amber)
                        }
                    }
                }
            }
            HorizontalDivider(color = Hairline)

            SettingsDisclosure(
                title = "Session summaries",
                summary = if (notificationsGranted) "Allowed" else "Off",
                expanded = expanded == "notifications",
                onToggle = { expanded = expanded.toggle("notifications") },
            ) {
                Text(
                    "Shoots sends one summary after it finishes the whole Experiment group. It will not interrupt you for every Shot.",
                    color = MutedWhite,
                    fontSize = 13.sp,
                    lineHeight = 19.sp,
                )
                if (!notificationsGranted) {
                    Spacer(Modifier.height(13.dp))
                    PrimaryAction("Allow session summaries", enabled = !busy, onClick = onRequestNotifications)
                }
            }
            HorizontalDivider(color = Hairline)

            SettingsDisclosure(
                title = "Google Drive",
                summary = if (snapshot?.driveConnected == true) "Connected" else "Not connected · optional",
                expanded = expanded == "drive",
                onToggle = { expanded = expanded.toggle("drive") },
            ) {
                Text(
                    "Drive is separate from sign-in. Disconnecting removes Shoots access while your files remain yours.",
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
            HorizontalDivider(color = Hairline)

            SettingsDisclosure(
                title = "Account and data",
                summary = snapshot?.user?.name.orEmpty().ifBlank { "Google account" },
                expanded = expanded == "account",
                onToggle = { expanded = expanded.toggle("account") },
            ) {
                SecondaryAction("Refresh Google sign-in", onClick = onReauthenticate)
                Spacer(Modifier.height(8.dp))
                SecondaryAction("Revoke this device") { confirmRevoke = true }
                Spacer(Modifier.height(8.dp))
                SecondaryAction("Delete account and Shoots data", danger = true) { confirmDelete = true }
            }
        }
    }

    if (confirmRevoke) {
        ConfirmSettingsDialog(
            title = "Revoke this device?",
            body = "This device token, local cache, queued imports, and notification target will be removed.",
            action = "Revoke",
            onDismiss = { confirmRevoke = false },
            onConfirm = { confirmRevoke = false; onRevoke() },
        )
    }
    if (confirmDelete) {
        ConfirmSettingsDialog(
            title = "Delete your Shoots account?",
            body = "Google will confirm your identity again. Shoots records and stored blobs are deleted. User-owned Drive files remain.",
            action = "Delete account",
            onDismiss = { confirmDelete = false },
            onConfirm = { confirmDelete = false; onDelete() },
        )
    }
}

@Composable
private fun SettingsDisclosure(
    title: String,
    summary: String,
    expanded: Boolean,
    onToggle: () -> Unit,
    content: @Composable ColumnScope.() -> Unit,
) {
    Column(Modifier.fillMaxWidth().animateContentSize(animationSpec = tween(180))) {
        Row(
            Modifier
                .fillMaxWidth()
                .clickable(role = Role.Button, onClick = onToggle)
                .semantics(mergeDescendants = true) {
                    stateDescription = if (expanded) "Expanded" else "Collapsed"
                }
                .padding(horizontal = 16.dp, vertical = 14.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text(title, color = WarmWhite, fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.height(3.dp))
                Text(summary, color = MutedWhite, fontSize = 12.sp, lineHeight = 17.sp)
            }
            DisclosureChevron(expanded)
        }
        AnimatedVisibility(expanded) {
            Column(
                Modifier.fillMaxWidth().padding(start = 16.dp, end = 16.dp, bottom = 16.dp),
                content = content,
            )
        }
    }
}

@Composable
private fun ConfirmSettingsDialog(
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
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel", color = WarmWhite) } },
        containerColor = InkRaised,
    )
}

private fun String?.toggle(key: String): String? = if (this == key) null else key
