package com.shoots.app.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateContentSize
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.layout.width
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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.shoots.app.Amber
import com.shoots.app.FindingRed
import com.shoots.app.Ink
import com.shoots.app.InkRaised
import com.shoots.app.MutedWhite
import com.shoots.app.WarmWhite
import com.shoots.app.data.ExperimentDto
import com.shoots.app.data.LocalCaptureSessionEntity
import com.shoots.app.data.LocalCaptureState
import com.shoots.app.data.MobileSnapshotDto
import com.shoots.app.data.ShotDto
import com.shoots.app.data.canStartReproduce
import com.shoots.app.data.canStartExplore

@Composable
fun ExperimentsScreen(
    snapshot: MobileSnapshotDto?,
    localSession: LocalCaptureSessionEntity?,
    busy: Boolean,
    imageUrl: (ShotDto) -> String,
    onRequestExperiment: (Boolean) -> Unit,
    onRequestExplore: (Boolean) -> Unit,
    onStartExperiment: (String, String) -> Unit,
    onCompleteExplore: (String) -> Unit,
    onContinueSession: (String) -> Unit,
    onFinishSession: (String) -> Unit,
    onCancelSession: (String) -> Unit,
    onImportSessionAsFree: (String) -> Unit,
    onShot: (String) -> Unit,
) {
    val open = snapshot?.openExperiment
    val active = localSession?.takeIf { it.state in EXPERIMENT_SESSION_STATES }
    var replaceConfirm by remember { mutableStateOf(false) }
    Column(
        Modifier
            .fillMaxSize()
            .background(Ink)
            .statusBarsPadding()
            .navigationBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp)
            .padding(top = 22.dp, bottom = 96.dp),
    ) {
        ScreenTitle(
            "Experiments",
            "Try one decision on purpose.",
            "Explore optional Variations, or Reproduce something you value.",
        )
        Spacer(Modifier.height(24.dp))

        when {
            active != null -> CaptureSessionCard(
                session = active,
                busy = busy,
                onContinue = onContinueSession,
                onFinish = onFinishSession,
                onCancel = onCancelSession,
                onImportAsFree = onImportSessionAsFree,
            )
            open?.canStartReproduce == true -> ActiveExperimentCard(
                experiment = open,
                keeper = snapshot.recentShots.firstOrNull { it.id == open.referenceShotId },
                imageUrl = imageUrl,
                busy = busy,
                onStart = { onStartExperiment(open.id, "") },
                onKeeper = { open.referenceShotId.takeIf(String::isNotBlank)?.let(onShot) },
                onAnother = { replaceConfirm = true },
            )
            open?.canStartExplore == true -> ActiveExploreCard(
                experiment = open,
                busy = busy,
                onStart = { variationId -> onStartExperiment(open.id, variationId) },
                onComplete = { onCompleteExplore(open.id) },
                onAnother = { onRequestExplore(true) },
            )
            open != null -> OlderExperimentCard(
                experiment = open,
                busy = busy,
                onReplace = { replaceConfirm = true },
            )
            else -> NoExperimentCard(
                busy = busy,
                onExplore = { onRequestExplore(false) },
                onReproduce = { onRequestExperiment(false) },
            )
        }

        Spacer(Modifier.height(30.dp))
        SectionTitle("Earlier Experiments")
        Spacer(Modifier.height(10.dp))
        val history = snapshot?.experiments.orEmpty().filter { it.id != open?.id }
        if (history.isEmpty()) {
            Text(
                "Completed and left Experiments will remain here as records, not streaks.",
                color = MutedWhite,
                fontSize = 14.sp,
                lineHeight = 20.sp,
            )
        } else {
            history.take(12).forEach { experiment ->
                val targetShot = experiment.resultShotIds.lastOrNull()
                    ?.ifBlank { null }
                    ?: experiment.referenceShotId.takeIf(String::isNotBlank)
                ExperimentHistoryRow(
                    experiment = experiment,
                    onClick = targetShot?.let { shotId -> { onShot(shotId) } },
                )
                Spacer(Modifier.height(8.dp))
            }
        }
    }

    if (replaceConfirm) {
        AlertDialog(
            onDismissRequest = { replaceConfirm = false },
            title = { Text("Ask Scout for a current Experiment?", color = WarmWhite) },
            text = {
                Text(
                    "Scout will look at your current Keepers. This older Experiment stays as-is if no supported direction is available. It becomes left only after a replacement is ready.",
                    color = MutedWhite,
                    lineHeight = 20.sp,
                )
            },
            confirmButton = {
                TextButton(onClick = { replaceConfirm = false; onRequestExperiment(true) }) {
                    Text("Ask Scout", color = Amber)
                }
            },
            dismissButton = {
                TextButton(onClick = { replaceConfirm = false }) { Text("Cancel", color = WarmWhite) }
            },
            containerColor = InkRaised,
        )
    }
}

@Composable
private fun ActiveExploreCard(
    experiment: ExperimentDto,
    busy: Boolean,
    onStart: (String) -> Unit,
    onComplete: () -> Unit,
    onAnother: () -> Unit,
) {
    InkCard {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            StatusPill("Explore", amber = true)
            Text("NO VERDICT", color = MutedWhite, fontSize = 10.sp, fontWeight = FontWeight.Bold)
        }
        Spacer(Modifier.height(13.dp))
        Text(
            experiment.title,
            color = WarmWhite,
            fontSize = 24.sp,
            lineHeight = 29.sp,
            fontWeight = FontWeight.Bold,
        )
        if (experiment.whyNow.isNotBlank()) {
            Spacer(Modifier.height(8.dp))
            Text(experiment.whyNow, color = MutedWhite, fontSize = 13.sp, lineHeight = 19.sp)
        }
        Spacer(Modifier.height(18.dp))
        Text("CHOOSE ONE VARIATION", color = Amber, fontSize = 10.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(8.dp))
        experiment.variations.forEach { variation ->
            InkCard(onClick = { if (!busy) onStart(variation.id) }) {
                Text(
                    variation.title,
                    color = WarmWhite,
                    fontSize = 15.sp,
                    fontWeight = FontWeight.SemiBold,
                )
                Spacer(Modifier.height(4.dp))
                Text(variation.instruction, color = MutedWhite, fontSize = 12.sp, lineHeight = 17.sp)
                Spacer(Modifier.height(7.dp))
                Text("TRY WITH NORMAL CAMERA", color = Amber, fontSize = 10.sp, fontWeight = FontWeight.Bold)
            }
            Spacer(Modifier.height(8.dp))
        }
        if (experiment.resultShotIds.isNotEmpty()) {
            Spacer(Modifier.height(6.dp))
            Text(
                "${experiment.resultShotIds.size} explicit result Shots · " +
                    "${experiment.variationObservations.map { it.variationId }.distinct().size} Variations observed",
                color = MutedWhite,
                fontSize = 12.sp,
            )
            Spacer(Modifier.height(12.dp))
            SecondaryAction("Finish Explore", enabled = !busy, onClick = onComplete)
        }
        TextButton(onClick = onAnother, modifier = Modifier.align(Alignment.End)) {
            Text("Another Explore direction", color = MutedWhite, fontSize = 12.sp)
        }
    }
}

@Composable
private fun ActiveExperimentCard(
    experiment: ExperimentDto,
    keeper: ShotDto?,
    imageUrl: (ShotDto) -> String,
    busy: Boolean,
    onStart: () -> Unit,
    onKeeper: () -> Unit,
    onAnother: () -> Unit,
) {
    var details by remember(experiment.id) { mutableStateOf(false) }
    InkCard {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            StatusPill("Reproduce", amber = true)
            Text("OPTIONAL", color = MutedWhite, fontSize = 10.sp, fontWeight = FontWeight.Bold)
        }
        Spacer(Modifier.height(13.dp))
        Text(experiment.title, color = WarmWhite, fontSize = 24.sp, lineHeight = 29.sp, fontWeight = FontWeight.Bold)
        if (keeper != null) {
            Spacer(Modifier.height(16.dp))
            AsyncImage(
                model = imageUrl(keeper),
                contentDescription = "Keeper reference",
                modifier = Modifier.fillMaxWidth().aspectRatio(4f / 3f).clickable(onClick = onKeeper),
                contentScale = ContentScale.Crop,
            )
            Spacer(Modifier.height(7.dp))
            Text("YOUR KEEPER · REFERENCE", color = Amber, fontSize = 10.sp, fontWeight = FontWeight.Bold, modifier = Modifier.clickable(onClick = onKeeper))
        }
        Spacer(Modifier.height(16.dp))
        PrimaryAction("Try with normal camera", enabled = !busy, onClick = onStart)
        Spacer(Modifier.height(10.dp))
        Row(
            Modifier
                .fillMaxWidth()
                .clickable(role = Role.Button) { details = !details }
                .semantics(mergeDescendants = true) {
                    stateDescription = if (details) "Expanded" else "Collapsed"
                }
                .padding(vertical = 7.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(if (details) "Hide why and Criteria" else "Why this · what Shoots checks", color = WarmWhite, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
            DisclosureChevron(details)
        }
        AnimatedVisibility(details) {
            Column(Modifier.fillMaxWidth().animateContentSize(animationSpec = tween(180))) {
                if (experiment.whyNow.isNotBlank()) {
                    Spacer(Modifier.height(8.dp))
                    LabelValue("Why now", experiment.whyNow)
                }
                if (experiment.brief.isNotBlank()) {
                    Spacer(Modifier.height(14.dp))
                    LabelValue("How to try it", experiment.brief)
                }
                if (experiment.criteria.text.isNotEmpty()) {
                    Spacer(Modifier.height(14.dp))
                    Text("CRITERIA", color = MutedWhite, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(5.dp))
                    experiment.criteria.text.forEach { criterion ->
                        Text("• $criterion", color = WarmWhite, fontSize = 13.sp, lineHeight = 19.sp)
                    }
                }
            }
        }
        TextButton(
            onClick = onAnother,
            modifier = Modifier.align(Alignment.End),
        ) {
            Text("Another direction", color = MutedWhite, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
        }
    }
}

@Composable
private fun OlderExperimentCard(
    experiment: ExperimentDto,
    busy: Boolean,
    onReplace: () -> Unit,
) {
    InkCard {
        StatusPill("Older Experiment")
        Spacer(Modifier.height(12.dp))
        Text(experiment.title, color = WarmWhite, fontSize = 21.sp, lineHeight = 26.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(8.dp))
        Text(
            "An older Shoots version made this without a usable Keeper reference. It stays in your record, but Shoots cannot safely attach new Shots to it.",
            color = MutedWhite,
            fontSize = 14.sp,
            lineHeight = 20.sp,
        )
        Spacer(Modifier.height(17.dp))
        PrimaryAction("Find a current Experiment", enabled = !busy, onClick = onReplace)
    }
}

@Composable
private fun NoExperimentCard(
    busy: Boolean,
    onExplore: () -> Unit,
    onReproduce: () -> Unit,
) {
    InkCard {
        StatusPill("Quiet")
        Spacer(Modifier.height(12.dp))
        Text("Want something deliberate to try?", color = WarmWhite, fontSize = 21.sp, lineHeight = 26.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(7.dp))
        Text(
            "Scout can open optional Variations from a Tendency, or test a decision supported by one of your Keepers.",
            color = MutedWhite,
            fontSize = 14.sp,
            lineHeight = 20.sp,
        )
        Spacer(Modifier.height(18.dp))
        PrimaryAction("Explore a Tendency", enabled = !busy, onClick = onExplore)
        Spacer(Modifier.height(8.dp))
        SecondaryAction("Reproduce a Keeper", enabled = !busy, onClick = onReproduce)
    }
}

@Composable
fun CaptureSessionCard(
    session: LocalCaptureSessionEntity,
    busy: Boolean,
    onContinue: (String) -> Unit,
    onFinish: (String) -> Unit,
    onCancel: (String) -> Unit,
    onImportAsFree: (String) -> Unit,
) {
    InkCard {
        StatusPill(
            session.state,
            amber = session.state != LocalCaptureState.CONFLICT,
            red = session.state == LocalCaptureState.CONFLICT,
        )
        Spacer(Modifier.height(12.dp))
        Text(
            when (session.state) {
                LocalCaptureState.RESERVED -> "Your Experiment Camera visit is open."
                LocalCaptureState.AWAITING_SELECTION -> "Choose the exact Shots that belong to this Experiment."
                LocalCaptureState.MANIFEST_PENDING -> "Freezing this batch before upload."
                LocalCaptureState.COMMITTED -> "The batch is frozen and ready to upload."
                LocalCaptureState.PROCESSING -> "Shoots is reading every member."
                LocalCaptureState.CONFLICT -> "This local batch does not match the frozen manifest."
                else -> "Capture Session in progress."
            },
            color = WarmWhite,
            fontSize = 21.sp,
            lineHeight = 27.sp,
            fontWeight = FontWeight.Bold,
        )
        if (session.error.isNotBlank()) {
            Spacer(Modifier.height(7.dp))
            Text(session.error, color = FindingRed, fontSize = 13.sp, lineHeight = 18.sp)
        }
        if (session.state == LocalCaptureState.RESERVED) {
            Spacer(Modifier.height(17.dp))
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
private fun ExperimentHistoryRow(experiment: ExperimentDto, onClick: (() -> Unit)?) {
    InkCard(onClick = onClick) {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    experiment.title,
                    color = WarmWhite,
                    fontSize = 15.sp,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    when {
                        experiment.type == "explore" && experiment.variationObservations.isNotEmpty() ->
                            "${experiment.variationObservations.map { it.variationId }.distinct().size} Variations observed · no Verdict"
                        experiment.change != null -> experiment.change.outcome.ifBlank { experiment.change.state }
                        experiment.resultShotIds.isNotEmpty() -> "${experiment.resultShotIds.size} explicit result Shots"
                        experiment.status == "skipped" -> "Left without result Shots"
                        experiment.status == "completed" -> "Completed before explicit result tracking"
                        else -> "No explicit result Shots yet"
                    },
                    color = MutedWhite,
                    fontSize = 12.sp,
                    lineHeight = 17.sp,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                StatusPill(
                    if (experiment.status == "skipped") "left" else experiment.status,
                    amber = experiment.status == "open",
                )
                if (onClick != null) {
                    Spacer(Modifier.width(4.dp))
                    ForwardChevron()
                }
            }
        }
    }
}

private val EXPERIMENT_SESSION_STATES = setOf(
    LocalCaptureState.RESERVED,
    LocalCaptureState.AWAITING_SELECTION,
    LocalCaptureState.MANIFEST_PENDING,
    LocalCaptureState.COMMITTED,
    LocalCaptureState.PROCESSING,
    LocalCaptureState.CONFLICT,
)
