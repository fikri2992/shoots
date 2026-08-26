package com.shoots.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.shoots.app.Amber
import com.shoots.app.Ink
import com.shoots.app.MutedWhite
import com.shoots.app.WarmWhite
import com.shoots.app.data.LocalCaptureSessionEntity
import com.shoots.app.data.LocalCaptureState
import com.shoots.app.data.MobileSnapshotDto
import com.shoots.app.data.SourceStateEntity
import com.shoots.app.phone.MediaAccess

@Composable
fun NowScreen(
    snapshot: MobileSnapshotDto?,
    source: SourceStateEntity?,
    localSession: LocalCaptureSessionEntity?,
    mediaAccess: MediaAccess,
    busy: Boolean,
    imageUrl: (com.shoots.app.data.ShotDto) -> String,
    onRequestMedia: () -> Unit,
    onEnableSource: () -> Unit,
    onOpenFreeCamera: () -> Unit,
    onChooseFreeShots: () -> Unit,
    onStartExperiment: (String) -> Unit,
    onContinueSession: (String) -> Unit,
    onFinishSession: (String) -> Unit,
    onCancelSession: (String) -> Unit,
    onImportSessionAsFree: (String) -> Unit,
    onSync: () -> Unit,
) {
    Column(
        Modifier
            .fillMaxSize()
            .background(Ink)
            .statusBarsPadding()
            .navigationBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 24.dp),
    ) {
        ScreenTitle("Now", greeting(snapshot), "One Experiment when it is supported. Silence when it is not.")
        Spacer(Modifier.height(24.dp))

        val experiment = snapshot?.openExperiment
        val active = localSession?.takeIf {
            it.state in setOf(
                LocalCaptureState.RESERVED,
                LocalCaptureState.AWAITING_SELECTION,
                LocalCaptureState.MANIFEST_PENDING,
                LocalCaptureState.COMMITTED,
                LocalCaptureState.PROCESSING,
                LocalCaptureState.CONFLICT,
            )
        }
        if (active != null) {
            ActiveSessionCard(
                active,
                busy,
                onContinueSession,
                onFinishSession,
                onCancelSession,
                onImportSessionAsFree,
            )
            Spacer(Modifier.height(18.dp))
        } else if (experiment?.type == "reproduce") {
            val keeper = snapshot.recentShots.firstOrNull { it.id == experiment.referenceShotId }
            InkCard {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    StatusPill("Reproduce", amber = true)
                    Text("OPTIONAL", color = MutedWhite, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                }
                Spacer(Modifier.height(13.dp))
                Text(experiment.title, color = WarmWhite, fontSize = 22.sp, lineHeight = 27.sp, fontWeight = FontWeight.Bold)
                if (experiment.whyNow.isNotBlank()) {
                    Spacer(Modifier.height(8.dp))
                    Text(experiment.whyNow, color = MutedWhite, fontSize = 14.sp, lineHeight = 20.sp)
                }
                if (keeper != null) {
                    Spacer(Modifier.height(15.dp))
                    AsyncImage(
                        model = imageUrl(keeper),
                        contentDescription = "Keeper reference",
                        modifier = Modifier.fillMaxWidth().aspectRatio(4f / 3f),
                        contentScale = ContentScale.Crop,
                    )
                    Spacer(Modifier.height(8.dp))
                    Text("YOUR KEEPER IS THE REFERENCE", color = Amber, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                }
                if (experiment.criteria.text.isNotEmpty()) {
                    Spacer(Modifier.height(16.dp))
                    Text("WHAT SHOOTS WILL CHECK", color = MutedWhite, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(6.dp))
                    experiment.criteria.text.forEach { criterion ->
                        Text("• $criterion", color = WarmWhite, fontSize = 14.sp, lineHeight = 20.sp)
                    }
                }
                Spacer(Modifier.height(18.dp))
                PrimaryAction("Try with normal camera", enabled = !busy) {
                    onStartExperiment(experiment.id)
                }
            }
            Spacer(Modifier.height(18.dp))
        } else {
            InkCard {
                StatusPill("Quiet")
                Spacer(Modifier.height(12.dp))
                Text("No supported Experiment right now.", color = WarmWhite, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.height(6.dp))
                Text("Keep shooting. Shoots will offer one when your own Evidence gives it a reason.", color = MutedWhite, fontSize = 14.sp, lineHeight = 20.sp)
            }
            Spacer(Modifier.height(18.dp))
        }

        SectionTitle("Phone Source")
        Spacer(Modifier.height(10.dp))
        PhoneSourceCard(
            source,
            mediaAccess,
            busy,
            onRequestMedia,
            onEnableSource,
            onOpenFreeCamera,
            onChooseFreeShots,
        )
        Spacer(Modifier.height(18.dp))

        snapshot?.latestRun?.let { run ->
            SectionTitle("Latest Run", displayTime(run.updatedAt))
            Spacer(Modifier.height(10.dp))
            InkCard {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    StatusPill(run.status, amber = run.status in listOf("running", "retrying"), red = run.status == "terminal")
                    Text(run.shotId.takeLast(8), color = MutedWhite, fontSize = 11.sp)
                }
                val current = run.steps.entries.lastOrNull { it.value.state != "pending" }
                if (current != null) {
                    Spacer(Modifier.height(10.dp))
                    Text(current.key.replaceFirstChar(Char::uppercase), color = WarmWhite, fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
                    if (current.value.outcome.isNotBlank()) {
                        Spacer(Modifier.height(4.dp))
                        Text(current.value.outcome, color = MutedWhite, fontSize = 13.sp, lineHeight = 18.sp)
                    }
                }
            }
            Spacer(Modifier.height(18.dp))
        }

        SecondaryAction("Sync now", onClick = onSync)
        source?.lastSuccessfulSyncAt?.takeIf(String::isNotBlank)?.let {
            Spacer(Modifier.height(7.dp))
            Text("Last synced ${displayTime(it)}", color = MutedWhite, fontSize = 11.sp)
        }
        Spacer(Modifier.height(74.dp))
    }
}

@Composable
private fun ActiveSessionCard(
    session: LocalCaptureSessionEntity,
    busy: Boolean,
    onContinue: (String) -> Unit,
    onFinish: (String) -> Unit,
    onCancel: (String) -> Unit,
    onImportAsFree: (String) -> Unit,
) {
    InkCard {
        StatusPill(session.state, amber = session.state != LocalCaptureState.CONFLICT, red = session.state == LocalCaptureState.CONFLICT)
        Spacer(Modifier.height(12.dp))
        Text(
            when (session.state) {
                LocalCaptureState.RESERVED -> "Your Capture Session is still open."
                LocalCaptureState.AWAITING_SELECTION -> "Choose the exact Shots that belong to this Experiment."
                LocalCaptureState.MANIFEST_PENDING -> "Freezing the batch before upload."
                LocalCaptureState.COMMITTED -> "The batch is frozen and ready to upload."
                LocalCaptureState.PROCESSING -> "Shoots is reading every member."
                LocalCaptureState.CONFLICT -> "This local batch does not match the committed manifest."
                else -> "Capture Session in progress."
            },
            color = WarmWhite,
            fontSize = 18.sp,
            lineHeight = 24.sp,
            fontWeight = FontWeight.SemiBold,
        )
        if (session.error.isNotBlank()) {
            Spacer(Modifier.height(7.dp))
            Text(session.error, color = com.shoots.app.FindingRed, fontSize = 13.sp, lineHeight = 18.sp)
        }
        if (session.state == LocalCaptureState.RESERVED) {
            Spacer(Modifier.height(16.dp))
            PrimaryAction("Continue with normal camera", enabled = !busy) { onContinue(session.id) }
            Spacer(Modifier.height(8.dp))
            SecondaryAction("Finish this Camera visit") { onFinish(session.id) }
            Spacer(Modifier.height(8.dp))
            SecondaryAction("Cancel empty session") { onCancel(session.id) }
        } else if (session.state == LocalCaptureState.CONFLICT) {
            Spacer(Modifier.height(14.dp))
            SecondaryAction("Import these as free Shots") { onImportAsFree(session.id) }
        }
    }
}

@Composable
private fun PhoneSourceCard(
    source: SourceStateEntity?,
    access: MediaAccess,
    busy: Boolean,
    onRequestMedia: () -> Unit,
    onEnable: () -> Unit,
    onOpenCamera: () -> Unit,
    onChoose: () -> Unit,
) {
    InkCard {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("Normal camera stays in control", color = WarmWhite, fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
            StatusPill(
                when {
                    access == MediaAccess.FULL && source?.enabled == true -> "automatic"
                    access == MediaAccess.SELECTED -> "selected"
                    else -> "off"
                },
                amber = access == MediaAccess.FULL && source?.enabled == true,
            )
        }
        Spacer(Modifier.height(8.dp))
        Text(
            when (access) {
                MediaAccess.FULL -> "Only future still Shots in DCIM/Camera are observed. Your archive is not imported."
                MediaAccess.SELECTED -> "Android only lets Shoots read items you choose. Automatic future import is off."
                MediaAccess.NONE -> "Allow Camera media to observe future Shots, or keep access selected-only."
            },
            color = MutedWhite,
            fontSize = 13.sp,
            lineHeight = 19.sp,
        )
        Spacer(Modifier.height(15.dp))
        when {
            access == MediaAccess.NONE -> PrimaryAction("Choose media access", enabled = !busy, onClick = onRequestMedia)
            access == MediaAccess.FULL && source?.enabled != true -> PrimaryAction("Observe future Camera Shots", enabled = !busy, onClick = onEnable)
            else -> {
                PrimaryAction("Open normal camera", enabled = !busy, onClick = onOpenCamera)
                if (access == MediaAccess.SELECTED) {
                    Spacer(Modifier.height(8.dp))
                    SecondaryAction("Choose existing Shots", onClick = onChoose)
                }
            }
        }
        if (!source?.lastError.isNullOrBlank()) {
            Spacer(Modifier.height(9.dp))
            Text(source?.lastError.orEmpty(), color = com.shoots.app.FindingRed, fontSize = 12.sp)
        }
    }
}

private fun greeting(snapshot: MobileSnapshotDto?): String {
    val name = snapshot?.user?.name?.trim()?.split(" ")?.firstOrNull().orEmpty()
    return if (name.isBlank()) "What are you seeing?" else "What are you seeing, $name?"
}
