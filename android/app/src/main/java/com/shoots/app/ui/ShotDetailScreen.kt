package com.shoots.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
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
import com.shoots.app.FindingRed
import com.shoots.app.Ink
import com.shoots.app.InkRaised
import com.shoots.app.MutedWhite
import com.shoots.app.WarmWhite
import com.shoots.app.data.CompositionDto
import com.shoots.app.data.GridSpecDto
import com.shoots.app.data.ShotDto
import com.shoots.app.data.ShotViewDto

@Composable
fun ShotDetailScreen(
    view: ShotViewDto?,
    imageUrl: (ShotDto, Boolean) -> String,
    onBack: () -> Unit,
    onKeeper: (Boolean) -> Unit,
    onRetry: () -> Unit,
    onOpenDrive: (String) -> Unit,
) {
    val shot = view?.shot
    Column(
        Modifier
            .fillMaxSize()
            .background(Ink)
            .statusBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(bottom = 40.dp),
    ) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("‹ Shots", color = WarmWhite, fontSize = 15.sp, modifier = Modifier.clickableNoRipple(onBack))
            view?.let {
                val state = detailStatus(it)
                StatusPill(state, red = state == "unreadable" || state == "interrupted")
            }
        }
        if (shot == null) {
            Column(Modifier.padding(20.dp)) { Text("Loading Shot...", color = MutedWhite) }
            return@Column
        }

        val analysis = view.analysis
        ShotImage(
            shot = shot,
            composition = analysis?.composition,
            source = imageUrl(shot, true),
        )

        Column(Modifier.padding(horizontal = 20.dp, vertical = 20.dp)) {
            Text(
                shot.filename,
                color = WarmWhite,
                fontSize = 21.sp,
                lineHeight = 26.sp,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.height(5.dp))
            Text(displayTime(shot.displayTime), color = MutedWhite, fontSize = 12.sp)
            Spacer(Modifier.height(15.dp))
            PrimaryAction(if (shot.keptAt == null) "Mark as Keeper" else "Keeper · remove mark") {
                onKeeper(shot.keptAt == null)
            }
            Spacer(Modifier.height(22.dp))

            if (analysis == null) {
                AnalysisState(view, onRetry)
            } else {
                val instruction = compositionInstruction(analysis.composition, shot.grid)
                if (instruction.isNotBlank()) {
                    SectionTitle("One thing to try", "COMPANION")
                    Spacer(Modifier.height(10.dp))
                    InkCard {
                        Text(instruction, color = WarmWhite, fontSize = 14.sp, lineHeight = 21.sp)
                    }
                    Spacer(Modifier.height(22.dp))
                }

                SectionTitle("What worked")
                Spacer(Modifier.height(10.dp))
                if (analysis.techniques.isEmpty()) {
                    Text(
                        "The panel did not corroborate a Technique in this Shot.",
                        color = MutedWhite,
                        fontSize = 14.sp,
                        lineHeight = 20.sp,
                    )
                } else {
                    analysis.techniques.sortedByDescending { it.agreement }.forEach { evidence ->
                        InkCard {
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text(
                                    evidence.techniqueId.replace('_', ' '),
                                    color = WarmWhite,
                                    fontSize = 15.sp,
                                    fontWeight = FontWeight.SemiBold,
                                )
                                Text(
                                    lensCount(evidence.agreement),
                                    color = MutedWhite,
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                )
                            }
                            if (evidence.note.isNotBlank()) {
                                Spacer(Modifier.height(6.dp))
                                Text(
                                    plainCellReferences(evidence.note, shot.grid),
                                    color = MutedWhite,
                                    fontSize = 13.sp,
                                    lineHeight = 18.sp,
                                )
                            }
                        }
                        Spacer(Modifier.height(8.dp))
                    }
                }

                Spacer(Modifier.height(14.dp))
                SectionTitle("Measured Findings")
                Spacer(Modifier.height(10.dp))
                if (analysis.findings.isEmpty()) {
                    Text("No deterministic Finding was raised.", color = MutedWhite, fontSize = 14.sp)
                } else {
                    analysis.findings.forEach { finding ->
                        InkCard {
                            Text(
                                plainCellReferences(finding.what, shot.grid),
                                color = FindingRed,
                                fontSize = 15.sp,
                                lineHeight = 20.sp,
                                fontWeight = FontWeight.SemiBold,
                            )
                            Spacer(Modifier.height(5.dp))
                            Text(
                                plainCellReferences(finding.why, shot.grid),
                                color = MutedWhite,
                                fontSize = 12.sp,
                                lineHeight = 17.sp,
                            )
                        }
                        Spacer(Modifier.height(8.dp))
                    }
                }

                if (analysis.critique.isNotBlank() || analysis.abstained.isNotBlank()) {
                    Spacer(Modifier.height(14.dp))
                    SectionTitle("Panel read", "MODEL OPINION")
                    Spacer(Modifier.height(10.dp))
                    InkCard {
                        Text(
                            plainCellReferences(
                                analysis.abstained.ifBlank { analysis.critique },
                                shot.grid,
                            ),
                            color = WarmWhite,
                            fontSize = 14.sp,
                            lineHeight = 21.sp,
                        )
                        Spacer(Modifier.height(8.dp))
                        Text(
                            "${analysis.model} · ${analysis.promptVersion.take(10)}",
                            color = MutedWhite,
                            fontSize = 10.sp,
                        )
                    }
                }
            }

            view.run?.let { run ->
                Spacer(Modifier.height(22.dp))
                SectionTitle("Run receipt", run.status.uppercase())
                Spacer(Modifier.height(10.dp))
                InkCard {
                    run.steps.forEach { (stage, step) ->
                        Row(
                            Modifier.fillMaxWidth().padding(vertical = 5.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                        ) {
                            Text(stage.replaceFirstChar(Char::uppercase), color = WarmWhite, fontSize = 13.sp)
                            Text(
                                step.state,
                                color = if (step.state == "terminal") FindingRed else MutedWhite,
                                fontSize = 11.sp,
                            )
                        }
                    }
                }
            }

            if (shot.experimentId.isNotBlank()) {
                Spacer(Modifier.height(20.dp))
                LabelValue(
                    "Experiment",
                    if (shot.captureSessionId.isNotBlank()) {
                        "Captured in an explicit Experiment session"
                    } else {
                        "Associated with an Experiment"
                    },
                )
            }
            if (shot.driveReviewUrl.isNotBlank()) {
                Spacer(Modifier.height(20.dp))
                SecondaryAction("Open reviewed copy in Drive") { onOpenDrive(shot.driveReviewUrl) }
            }
        }
    }
}

@Composable
private fun ShotImage(shot: ShotDto, composition: CompositionDto?, source: String) {
    val grid = shot.grid
    val ratio = grid
        ?.takeIf { it.width > 0 && it.height > 0 }
        ?.let { it.width.toFloat() / it.height.toFloat() }
        ?: (4f / 3f)
    Box(
        Modifier
            .fillMaxWidth()
            .aspectRatio(ratio)
            .background(InkRaised),
    ) {
        AsyncImage(
            model = source,
            contentDescription = shot.filename,
            modifier = Modifier.fillMaxSize(),
            contentScale = if (grid == null) ContentScale.Fit else ContentScale.FillBounds,
        )
        if (grid != null && composition != null) {
            CompositionGuide(grid, composition, Modifier.fillMaxSize())
            Text(
                "${guideLabel(composition.guide.ifBlank { "thirds" })} guide",
                color = WarmWhite,
                fontSize = 10.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .background(Ink.copy(alpha = 0.78f))
                    .padding(horizontal = 8.dp, vertical = 6.dp),
            )
        }
    }
}

@Composable
private fun AnalysisState(view: ShotViewDto, onRetry: () -> Unit) {
    val shot = view.shot
    val run = view.run
    val title: String
    val detail: String
    val retry: Boolean
    when {
        shot.status == "failed" || run?.status == "terminal" -> {
            title = "Shoots could not read this Shot."
            detail = shot.error
            retry = false
        }
        run == null -> {
            title = "Analysis was interrupted."
            detail = "This Shot was accepted before Shoots recorded a Run. Resume it when you are online."
            retry = true
        }
        run.status == "retrying" -> {
            title = "Analysis is waiting to retry."
            detail = latestRunOutcome(view)
            retry = true
        }
        run.status == "completed" -> {
            title = "The Analysis record is unavailable."
            detail = "The Run finished, but this device cannot find its Analysis."
            retry = false
        }
        else -> {
            title = "Analysis is running."
            detail = "You can leave this screen. Shoots will keep working in the background."
            retry = false
        }
    }
    InkCard {
        Text(title, color = WarmWhite, fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
        if (detail.isNotBlank()) {
            Spacer(Modifier.height(6.dp))
            Text(
                detail,
                color = if (shot.status == "failed") FindingRed else MutedWhite,
                fontSize = 13.sp,
                lineHeight = 18.sp,
            )
        }
        if (retry) {
            Spacer(Modifier.height(14.dp))
            SecondaryAction("Resume analysis", onClick = onRetry)
        }
    }
}

private fun latestRunOutcome(view: ShotViewDto): String = view.run
    ?.steps
    ?.values
    ?.lastOrNull { it.outcome.isNotBlank() }
    ?.outcome
    .orEmpty()

private fun compositionInstruction(composition: CompositionDto, grid: GridSpecDto?): String {
    if (composition.suggestedCropCells.isNotEmpty()) {
        return plainCellReferences(
            composition.cropReason.ifBlank { "Try the tested crop shown on the Shot." },
            grid,
        )
    }
    val move = composition.moves.firstOrNull() ?: return ""
    val what = plainCellReferences(move.what, grid).trim().trimEnd('.')
    val reason = plainCellReferences(move.reason, grid).trim().trimEnd('.')
    return when {
        what.isNotBlank() && reason.isNotBlank() -> "$what. $reason."
        what.isNotBlank() -> "$what."
        else -> reason
    }
}

private fun detailStatus(view: ShotViewDto): String = when {
    view.analysis != null -> "read"
    view.shot.status == "failed" || view.run?.status == "terminal" -> "unreadable"
    view.run == null -> "interrupted"
    view.run.status == "retrying" -> "retrying"
    else -> "reading"
}

private fun lensCount(count: Int): String = if (count == 1) "1 lens" else "$count lenses"

private fun Modifier.clickableNoRipple(onClick: () -> Unit): Modifier = clickable(onClick = onClick)
