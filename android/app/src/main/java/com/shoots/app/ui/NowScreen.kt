package com.shoots.app.ui

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.shoots.app.Amber
import com.shoots.app.Hairline
import com.shoots.app.Ink
import com.shoots.app.InkRaised
import com.shoots.app.InkSoft
import com.shoots.app.MutedWhite
import com.shoots.app.R
import com.shoots.app.WarmWhite
import com.shoots.app.data.LocalCaptureSessionEntity
import com.shoots.app.data.LocalCaptureState
import com.shoots.app.data.MobileSnapshotDto
import com.shoots.app.data.ShotDto
import com.shoots.app.data.ShotViewDto
import com.shoots.app.data.SourceStateEntity
import com.shoots.app.data.canStartReproduce
import com.shoots.app.phone.MediaAccess

@Composable
fun NowScreen(
    snapshot: MobileSnapshotDto?,
    source: SourceStateEntity?,
    localSession: LocalCaptureSessionEntity?,
    mediaAccess: MediaAccess,
    busy: Boolean,
    imageUrl: (ShotDto) -> String,
    onRequestMedia: () -> Unit,
    onEnableSource: () -> Unit,
    onOpenFreeCamera: () -> Unit,
    onChooseFreeShots: () -> Unit,
    onContinueSession: (String) -> Unit,
    onFinishSession: (String) -> Unit,
    onCancelSession: (String) -> Unit,
    onImportSessionAsFree: (String) -> Unit,
    onOpenShot: (String) -> Unit,
    onOpenExperiments: () -> Unit,
    onOpenSettings: () -> Unit,
) {
    val active = localSession?.takeIf { it.state in ACTIVE_SESSION_STATES }
    val latest = snapshot?.recentShots?.firstOrNull()
    val latestView = snapshot?.latestShot
    val focus = when {
        active != null -> "session"
        latestView?.analysis != null -> "insight"
        else -> "camera"
    }
    Column(
        Modifier
            .fillMaxSize()
            .background(Ink)
            .statusBarsPadding()
            .navigationBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp)
            .padding(top = 18.dp, bottom = 92.dp),
    ) {
        NowHeader(snapshot, onOpenSettings)
        Spacer(Modifier.height(26.dp))

        AnimatedContent(
            targetState = focus,
            transitionSpec = { fadeIn(tween(180)) togetherWith fadeOut(tween(120)) },
            label = "Now focus",
        ) { state ->
            when (state) {
                "session" -> CaptureSessionCard(
                    session = requireNotNull(active),
                    busy = busy,
                    onContinue = onContinueSession,
                    onFinish = onFinishSession,
                    onCancel = onCancelSession,
                    onImportAsFree = onImportSessionAsFree,
                )
                "insight" -> LatestInsightHero(
                    view = requireNotNull(latestView),
                    imageUrl = imageUrl,
                    access = mediaAccess,
                    source = source,
                    onOpenShot = onOpenShot,
                    onOpenCamera = onOpenFreeCamera,
                    onRequestMedia = onRequestMedia,
                    onEnableSource = onEnableSource,
                    onChoose = onChooseFreeShots,
                )
                else -> CameraHero(
                    source = source,
                    access = mediaAccess,
                    busy = busy,
                    onRequestMedia = onRequestMedia,
                    onEnableSource = onEnableSource,
                    onOpenCamera = onOpenFreeCamera,
                    onChoose = onChooseFreeShots,
                )
            }
        }

        snapshot?.openExperiment?.takeIf { it.canStartReproduce }?.let { experiment ->
            Spacer(Modifier.height(16.dp))
            InkCard(onClick = onOpenExperiments) {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(Modifier.weight(1f)) {
                        Text(
                            "OPEN EXPERIMENT",
                            color = Amber,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                        )
                        Spacer(Modifier.height(6.dp))
                        Text(
                            experiment.title,
                            color = WarmWhite,
                            fontSize = 17.sp,
                            lineHeight = 22.sp,
                            fontWeight = FontWeight.SemiBold,
                            maxLines = 2,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                    Row(
                        Modifier.padding(start = 14.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text("Open", color = Amber, fontSize = 13.sp)
                        Spacer(Modifier.size(3.dp))
                        ForwardChevron(Amber)
                    }
                }
            }
        }

        if (latestView?.analysis == null) {
            Spacer(Modifier.height(26.dp))
            SectionTitle("From your last Shot")
            Spacer(Modifier.height(10.dp))
            if (latest == null) {
                Text(
                    "Your newest Camera Shot will appear here while Shoots works in the background.",
                    color = MutedWhite,
                    fontSize = 14.sp,
                    lineHeight = 20.sp,
                )
            } else {
                LatestShotReceipt(latest, imageUrl(latest)) { onOpenShot(latest.id) }
            }
        }
    }
}

@Composable
private fun LatestInsightHero(
    view: ShotViewDto,
    imageUrl: (ShotDto) -> String,
    access: MediaAccess,
    source: SourceStateEntity?,
    onOpenShot: (String) -> Unit,
    onOpenCamera: () -> Unit,
    onRequestMedia: () -> Unit,
    onEnableSource: () -> Unit,
    onChoose: () -> Unit,
) {
    val shot = view.shot
    val analysis = requireNotNull(view.analysis)
    val strongest = analysis.techniques.filter(::isCorroborated).maxWithOrNull(
        compareBy<com.shoots.app.data.TechniqueEvidenceDto> { it.agreement }.thenBy { it.confidence }
    )
    val finding = analysis.findings.firstOrNull()
    Column(
        Modifier
            .fillMaxWidth()
            .background(InkRaised, RoundedCornerShape(24.dp))
            .border(1.dp, Hairline, RoundedCornerShape(24.dp))
            .clip(RoundedCornerShape(24.dp)),
    ) {
        Box(Modifier.fillMaxWidth().height(220.dp).clickable { onOpenShot(shot.id) }) {
            AsyncImage(
                model = imageUrl(shot),
                contentDescription = shot.filename,
                modifier = Modifier.fillMaxSize(),
                contentScale = ContentScale.Crop,
            )
            Text(
                "FROM YOUR LAST SHOT",
                color = WarmWhite,
                fontSize = 10.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.align(Alignment.TopStart).background(Ink.copy(alpha = 0.78f)).padding(horizontal = 9.dp, vertical = 7.dp),
            )
        }
        Column(Modifier.padding(19.dp)) {
            Text(
                when {
                    strongest != null -> "${lensCountLabel(strongest.agreement)} found ${humanLabel(strongest.techniqueId)}."
                    finding != null -> findingLabel(finding.findingId)
                    else -> "Shoots finished reading this Shot."
                },
                color = WarmWhite,
                fontSize = 21.sp,
                lineHeight = 26.sp,
                fontWeight = FontWeight.Bold,
            )
            val support = when {
                strongest != null -> plainCellReferences(strongest.note, shot.grid)
                finding != null -> plainCellReferences(finding.what, shot.grid)
                else -> compositionInstruction(analysis.composition, shot.grid)
            }
            if (support.isNotBlank()) {
                Spacer(Modifier.height(7.dp))
                Text(support, color = MutedWhite, fontSize = 13.sp, lineHeight = 19.sp, maxLines = 3, overflow = TextOverflow.Ellipsis)
            }
            Spacer(Modifier.height(17.dp))
            PrimaryAction("See the marked Shot") { onOpenShot(shot.id) }
            Spacer(Modifier.height(8.dp))
            when {
                access == MediaAccess.FULL && source?.enabled == true -> SecondaryAction("Make another Shot", onClick = onOpenCamera)
                access == MediaAccess.FULL -> SecondaryAction("Start future import", onClick = onEnableSource)
                access == MediaAccess.SELECTED -> SecondaryAction("Choose Camera Shots", onClick = onChoose)
                else -> SecondaryAction("Allow Camera media", onClick = onRequestMedia)
            }
        }
    }
}

@Composable
private fun NowHeader(snapshot: MobileSnapshotDto?, onOpenSettings: () -> Unit) {
    val name = snapshot?.user?.name.orEmpty().trim().substringBefore(' ').ifBlank { "there" }
    Row(
        Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column {
            Text("SHOOTS", color = Amber, fontSize = 11.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(4.dp))
            Text("Ready when you are, $name.", color = WarmWhite, fontSize = 23.sp, lineHeight = 28.sp, fontWeight = FontWeight.Bold)
        }
        Box(
            Modifier
                .size(42.dp)
                .clip(CircleShape)
                .background(InkSoft)
                .border(1.dp, Hairline, CircleShape)
                .semantics { contentDescription = "Open settings" }
                .clickable(role = Role.Button, onClick = onOpenSettings),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                painter = painterResource(R.drawable.ic_settings),
                contentDescription = null,
                tint = WarmWhite,
                modifier = Modifier.size(20.dp),
            )
        }
    }
}

@Composable
private fun CameraHero(
    source: SourceStateEntity?,
    access: MediaAccess,
    busy: Boolean,
    onRequestMedia: () -> Unit,
    onEnableSource: () -> Unit,
    onOpenCamera: () -> Unit,
    onChoose: () -> Unit,
) {
    Column(
        Modifier
            .fillMaxWidth()
            .background(InkRaised, RoundedCornerShape(24.dp))
            .border(1.dp, Amber.copy(alpha = 0.34f), RoundedCornerShape(24.dp))
            .padding(20.dp),
    ) {
        Text("MAKE A SHOT", color = Amber, fontSize = 10.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(9.dp))
        Text("Shoot first. Shoots remembers the rest.", color = WarmWhite, fontSize = 24.sp, lineHeight = 29.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(9.dp))
        Text(
            when {
                access == MediaAccess.FULL && source?.enabled == true -> "Future Camera Shots arrive automatically."
                access == MediaAccess.SELECTED -> "You choose which Camera Shots Shoots may read."
                else -> "Allow Camera media once so a new Shot can enter your record."
            },
            color = MutedWhite,
            fontSize = 14.sp,
            lineHeight = 20.sp,
        )
        Spacer(Modifier.height(20.dp))
        when {
            access == MediaAccess.FULL && source?.enabled == true -> {
                PrimaryAction("Open normal camera", enabled = !busy, onClick = onOpenCamera)
            }
            access == MediaAccess.FULL -> {
                PrimaryAction("Start future import", enabled = !busy, onClick = onEnableSource)
            }
            access == MediaAccess.SELECTED -> {
                PrimaryAction("Choose Camera Shots", enabled = !busy, onClick = onChoose)
                Spacer(Modifier.height(8.dp))
                SecondaryAction("Change media access", onClick = onRequestMedia)
            }
            else -> PrimaryAction("Allow Camera media", enabled = !busy, onClick = onRequestMedia)
        }
        if (access == MediaAccess.FULL && source?.enabled == true) {
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("Phone Source", color = MutedWhite, fontSize = 12.sp)
                Text("AUTOMATIC", color = Amber, fontSize = 10.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
private fun LatestShotReceipt(shot: ShotDto, url: String, onClick: () -> Unit) {
    InkCard(onClick = onClick) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            AsyncImage(
                model = url,
                contentDescription = shot.filename,
                modifier = Modifier.size(88.dp).clip(RoundedCornerShape(12.dp)).background(InkSoft),
                contentScale = ContentScale.Crop,
            )
            Column(Modifier.weight(1f).padding(start = 14.dp)) {
                StatusPill(shotReceiptStatus(shot), amber = shot.status in setOf("analysing", "ingested", "new"), red = shot.status == "failed")
                Spacer(Modifier.height(9.dp))
                Text(
                    when (shot.status) {
                        "analyzed" -> "See what Shoots noticed"
                        "failed" -> "See why this Shot was unreadable"
                        else -> "Shoots is reading this in the background"
                    },
                    color = WarmWhite,
                    fontSize = 15.sp,
                    lineHeight = 20.sp,
                    fontWeight = FontWeight.SemiBold,
                )
                Spacer(Modifier.height(4.dp))
                Text(displayTime(shot.displayTime), color = MutedWhite, fontSize = 11.sp)
            }
            Box(Modifier.padding(start = 8.dp)) { ForwardChevron() }
        }
    }
}

private fun shotReceiptStatus(shot: ShotDto): String = when (shot.status) {
    "analyzed" -> "read"
    "failed" -> "unreadable"
    "analysing" -> "reading"
    "ingested" -> "waiting"
    else -> "preparing"
}

private fun lensCountLabel(count: Int): String = if (count == 1) "One lens" else "$count lenses"

private val ACTIVE_SESSION_STATES = setOf(
    LocalCaptureState.RESERVED,
    LocalCaptureState.AWAITING_SELECTION,
    LocalCaptureState.MANIFEST_PENDING,
    LocalCaptureState.COMMITTED,
    LocalCaptureState.PROCESSING,
    LocalCaptureState.CONFLICT,
)
