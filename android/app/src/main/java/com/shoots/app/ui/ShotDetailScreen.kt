package com.shoots.app.ui

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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.shoots.app.Amber
import com.shoots.app.FindingRed
import com.shoots.app.Ink
import com.shoots.app.MutedWhite
import com.shoots.app.WarmWhite
import com.shoots.app.data.RunDto
import com.shoots.app.data.ShotViewDto

@Composable
fun ShotDetailScreen(
    view: ShotViewDto?,
    run: RunDto?,
    imageUrl: (com.shoots.app.data.ShotDto, Boolean) -> String,
    onBack: () -> Unit,
    onKeeper: (Boolean) -> Unit,
    onOpenDrive: (String) -> Unit,
) {
    val shot = view?.shot
    Column(
        Modifier.fillMaxSize().background(Ink).statusBarsPadding().verticalScroll(rememberScrollState()).padding(bottom = 40.dp),
    ) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text("‹ Shots", color = WarmWhite, fontSize = 15.sp, modifier = Modifier.clickableNoRipple(onBack))
            shot?.let { StatusPill(it.status, amber = it.status in listOf("new", "ingesting", "analysing"), red = it.status == "failed") }
        }
        if (shot == null) {
            Column(Modifier.padding(20.dp)) { Text("Loading Shot…", color = MutedWhite) }
            return@Column
        }
        AsyncImage(
            model = imageUrl(shot, true),
            contentDescription = shot.filename,
            modifier = Modifier.fillMaxWidth().aspectRatio(4f / 3f).background(com.shoots.app.InkRaised),
            contentScale = ContentScale.Fit,
        )
        Column(Modifier.padding(horizontal = 20.dp, vertical = 20.dp)) {
            Text(shot.filename, color = WarmWhite, fontSize = 23.sp, lineHeight = 28.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(5.dp))
            Text(displayTime(shot.displayTime), color = MutedWhite, fontSize = 12.sp)
            Spacer(Modifier.height(15.dp))
            PrimaryAction(if (shot.keptAt == null) "Mark as Keeper" else "Keeper · remove mark") {
                onKeeper(shot.keptAt == null)
            }
            Spacer(Modifier.height(22.dp))

            val analysis = view.analysis
            if (analysis == null) {
                InkCard {
                    Text(
                        if (shot.status == "failed") "Shoots could not read this Shot." else "Analysis is still running.",
                        color = WarmWhite,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.SemiBold,
                    )
                    if (shot.error.isNotBlank()) {
                        Spacer(Modifier.height(6.dp))
                        Text(shot.error, color = FindingRed, fontSize = 13.sp)
                    }
                }
            } else {
                SectionTitle("What worked")
                Spacer(Modifier.height(10.dp))
                if (analysis.techniques.isEmpty()) {
                    Text("The panel did not corroborate a Technique in this Shot.", color = MutedWhite, fontSize = 14.sp, lineHeight = 20.sp)
                } else {
                    analysis.techniques.sortedByDescending { it.agreement }.forEach { evidence ->
                        InkCard {
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text(evidence.techniqueId.replace('_', ' '), color = WarmWhite, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
                                Text("${evidence.agreement} lenses", color = Amber, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                            }
                            if (evidence.note.isNotBlank()) {
                                Spacer(Modifier.height(6.dp))
                                Text(evidence.note, color = MutedWhite, fontSize = 13.sp, lineHeight = 18.sp)
                            }
                            if (evidence.cells.isNotEmpty()) {
                                Spacer(Modifier.height(5.dp))
                                Text("Visible in ${evidence.cells.joinToString()}", color = MutedWhite, fontSize = 11.sp)
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
                            Text(finding.what, color = WarmWhite, fontSize = 15.sp, lineHeight = 20.sp, fontWeight = FontWeight.SemiBold)
                            Spacer(Modifier.height(5.dp))
                            Text(finding.why, color = Amber, fontSize = 12.sp, lineHeight = 17.sp)
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
                            analysis.abstained.ifBlank { analysis.critique },
                            color = WarmWhite,
                            fontSize = 14.sp,
                            lineHeight = 21.sp,
                        )
                        Spacer(Modifier.height(8.dp))
                        Text("${analysis.model} · ${analysis.promptVersion.take(10)}", color = MutedWhite, fontSize = 10.sp)
                    }
                }
            }

            run?.takeIf { it.shotId == shot.id }?.let {
                Spacer(Modifier.height(22.dp))
                SectionTitle("Run receipt", it.status.uppercase())
                Spacer(Modifier.height(10.dp))
                InkCard {
                    it.steps.forEach { (stage, step) ->
                        Row(Modifier.fillMaxWidth().padding(vertical = 5.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text(stage.replaceFirstChar(Char::uppercase), color = WarmWhite, fontSize = 13.sp)
                            Text(step.state, color = if (step.state == "terminal") FindingRed else MutedWhite, fontSize = 11.sp)
                        }
                    }
                }
            }

            if (shot.experimentId.isNotBlank()) {
                Spacer(Modifier.height(20.dp))
                LabelValue("Experiment association", shot.experimentId)
                if (shot.captureSessionId.isNotBlank()) {
                    Spacer(Modifier.height(9.dp))
                    LabelValue("Capture Session", shot.captureSessionId)
                }
            }
            if (shot.driveReviewUrl.isNotBlank()) {
                Spacer(Modifier.height(20.dp))
                SecondaryAction("Open reviewed copy in Drive") { onOpenDrive(shot.driveReviewUrl) }
            }
        }
    }
}

private fun Modifier.clickableNoRipple(onClick: () -> Unit): Modifier =
    clickable(onClick = onClick)
