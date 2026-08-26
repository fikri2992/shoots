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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.shoots.app.Amber
import com.shoots.app.Hairline
import com.shoots.app.Ink
import com.shoots.app.InkSoft
import com.shoots.app.MutedWhite
import com.shoots.app.WarmWhite
import com.shoots.app.data.ExperimentDto
import com.shoots.app.data.MobileSnapshotDto
import com.shoots.app.data.ProfileDimensionDto
import com.shoots.app.data.ShotDto

@Composable
fun JourneyScreen(
    snapshot: MobileSnapshotDto?,
    imageUrl: (ShotDto) -> String,
    onShot: (String) -> Unit,
) {
    Column(
        Modifier
            .fillMaxSize()
            .background(Ink)
            .statusBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(bottom = 92.dp),
    ) {
        Column(Modifier.padding(horizontal = 20.dp, vertical = 22.dp)) {
            ScreenTitle("Journey", "What is becoming repeatable?", "Your own Keepers, Experiments, and measured Change. No universal score.")
        }
        if (snapshot == null) {
            Column(Modifier.padding(20.dp)) { Text("Loading your cached Journey…", color = MutedWhite) }
            return@Column
        }
        val experiment = snapshot.experiments.firstOrNull { it.resultShotIds.isNotEmpty() }
        if (experiment != null) {
            ExperimentHero(snapshot, experiment, imageUrl, onShot)
        } else {
            Column(Modifier.padding(horizontal = 20.dp)) {
                InkCard {
                    Text("No completed Reproduce yet.", color = WarmWhite, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
                    Spacer(Modifier.height(6.dp))
                    Text("When you try an Experiment, its Keeper reference and every explicit result will stay here.", color = MutedWhite, fontSize = 14.sp, lineHeight = 20.sp)
                }
            }
        }

        snapshot.journey.firstOrNull()?.let { update ->
            Spacer(Modifier.height(24.dp))
            Column(Modifier.padding(horizontal = 20.dp)) {
                SectionTitle("Latest Journey Update", "${update.shots} SHOTS")
                Spacer(Modifier.height(10.dp))
                InkCard {
                    Text(update.body, color = WarmWhite, fontSize = 17.sp, lineHeight = 25.sp, fontWeight = FontWeight.Medium)
                    if (update.evidence.isNotEmpty()) {
                        Spacer(Modifier.height(13.dp))
                        Text("READ FROM", color = MutedWhite, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                        Spacer(Modifier.height(5.dp))
                        update.evidence.take(5).forEach {
                            Text("• $it", color = MutedWhite, fontSize = 12.sp, lineHeight = 18.sp)
                        }
                    }
                }
            }
        }

        Spacer(Modifier.height(24.dp))
        Column(Modifier.padding(horizontal = 20.dp)) {
            SectionTitle("Tendency Profile", "${snapshot.profile.shots} SHOTS READ")
            Spacer(Modifier.height(6.dp))
            Text("Counts describe what keeps appearing. They do not say it is good or bad.", color = MutedWhite, fontSize = 12.sp, lineHeight = 17.sp)
            Spacer(Modifier.height(12.dp))
            snapshot.profile.dimensions.forEach { dimension ->
                DimensionCard(dimension)
                Spacer(Modifier.height(8.dp))
            }
            if (snapshot.profile.blindSpots.isNotEmpty()) {
                Spacer(Modifier.height(6.dp))
                LabelValue("Still unknown", snapshot.profile.blindSpots.joinToString(" · "))
            }
        }

        Spacer(Modifier.height(24.dp))
        Column(Modifier.padding(horizontal = 20.dp)) {
            SectionTitle("Technique Map", "EVIDENCE, NOT LEVELS")
            Spacer(Modifier.height(10.dp))
            if (snapshot.techniques.isEmpty()) {
                Text("No corroborated Technique Evidence cached yet.", color = MutedWhite, fontSize = 14.sp)
            } else {
                snapshot.techniques.forEach { technique ->
                    InkCard {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text(technique.name, color = WarmWhite, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
                            StatusPill(technique.status)
                        }
                        Spacer(Modifier.height(6.dp))
                        Text(
                            "${technique.attempts} observed · ${technique.corroborated} corroborated",
                            color = MutedWhite,
                            fontSize = 12.sp,
                        )
                    }
                    Spacer(Modifier.height(8.dp))
                }
            }
        }

        Spacer(Modifier.height(24.dp))
        Column(Modifier.padding(horizontal = 20.dp)) {
            SectionTitle("Previous Experiments")
            Spacer(Modifier.height(10.dp))
            snapshot.experiments.forEach { previous ->
                InkCard {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(previous.title, color = WarmWhite, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                        Spacer(Modifier.width(8.dp))
                        StatusPill(previous.status, amber = previous.status == "open")
                    }
                    previous.change?.let { change ->
                        Spacer(Modifier.height(6.dp))
                        Text(change.outcome.ifBlank { change.state }, color = MutedWhite, fontSize = 12.sp, lineHeight = 17.sp)
                    }
                }
                Spacer(Modifier.height(8.dp))
            }
        }
    }
}

@Composable
private fun ExperimentHero(
    snapshot: MobileSnapshotDto,
    experiment: ExperimentDto,
    imageUrl: (ShotDto) -> String,
    onShot: (String) -> Unit,
) {
    val reference = snapshot.recentShots.firstOrNull { it.id == experiment.referenceShotId }
    val representativeId = snapshot.latestCaptureSession
        ?.takeIf { it.experimentId == experiment.id }
        ?.representativeResultShotId
        .orEmpty()
        .ifBlank { experiment.verdicts.firstOrNull { it.criteriaMet }?.shotId.orEmpty() }
        .ifBlank { experiment.resultShotIds.lastOrNull().orEmpty() }
    val result = snapshot.recentShots.firstOrNull { it.id == representativeId }
    Column(Modifier.padding(horizontal = 20.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            StatusPill(experiment.type, amber = true)
            StatusPill(experiment.status)
        }
        Spacer(Modifier.height(10.dp))
        Text(experiment.title, color = WarmWhite, fontSize = 21.sp, lineHeight = 26.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(13.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            JourneyImage("KEEPER REFERENCE", reference, imageUrl, onShot, Modifier.weight(1f))
            JourneyImage("REPRESENTATIVE RESULT", result, imageUrl, onShot, Modifier.weight(1f))
        }
        if (experiment.resultShotIds.isNotEmpty()) {
            Spacer(Modifier.height(16.dp))
            Text("ALL BATCH RESULTS", color = MutedWhite, fontSize = 10.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(7.dp))
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                items(experiment.resultShotIds) { id ->
                    val shot = snapshot.recentShots.firstOrNull { it.id == id }
                    val verdict = experiment.verdicts.firstOrNull { it.shotId == id }
                    Column(Modifier.width(112.dp)) {
                        AsyncImage(
                            model = shot?.let(imageUrl),
                            contentDescription = "Experiment result",
                            modifier = Modifier.fillMaxWidth().aspectRatio(1f).background(InkSoft).clickableShot(shot, onShot),
                            contentScale = ContentScale.Crop,
                        )
                        Spacer(Modifier.height(5.dp))
                        Text(
                            when {
                                verdict == null -> "ABSTENTION"
                                verdict.criteriaMet -> "CRITERIA MET"
                                else -> "NOT MET"
                            },
                            color = if (verdict?.criteriaMet == true) Amber else MutedWhite,
                            fontSize = 9.sp,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                }
            }
        }
        experiment.change?.let { change ->
            Spacer(Modifier.height(17.dp))
            InkCard {
                Text("WHAT CHANGED", color = MutedWhite, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(7.dp))
                Text(change.outcome.ifBlank { change.state }, color = WarmWhite, fontSize = 15.sp, lineHeight = 22.sp)
                if (change.comparability != "comparable") {
                    Spacer(Modifier.height(5.dp))
                    Text(change.comparability, color = MutedWhite, fontSize = 11.sp)
                }
            }
        }
    }
}

@Composable
private fun JourneyImage(
    label: String,
    shot: ShotDto?,
    imageUrl: (ShotDto) -> String,
    onShot: (String) -> Unit,
    modifier: Modifier,
) {
    Column(modifier) {
        Text(label, color = MutedWhite, fontSize = 9.sp, fontWeight = FontWeight.Bold, lineHeight = 12.sp)
        Spacer(Modifier.height(5.dp))
        AsyncImage(
            model = shot?.let(imageUrl),
            contentDescription = label,
            modifier = Modifier.fillMaxWidth().aspectRatio(1f).background(InkSoft).clickableShot(shot, onShot),
            contentScale = ContentScale.Crop,
        )
    }
}

@Composable
private fun DimensionCard(dimension: ProfileDimensionDto) {
    val total = dimension.buckets.sumOf { it.count }.coerceAtLeast(1)
    InkCard {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(dimension.label, color = WarmWhite, fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
            Text(if (dimension.readable) dimension.dominant else "not enough evidence", color = MutedWhite, fontSize = 11.sp)
        }
        Spacer(Modifier.height(9.dp))
        dimension.buckets.filter { it.count > 0 }.forEach { bucket ->
            Row(Modifier.fillMaxWidth().padding(vertical = 3.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(bucket.bucket, color = MutedWhite, fontSize = 11.sp, modifier = Modifier.width(76.dp))
                Box(Modifier.weight(1f).height(5.dp).clip(androidx.compose.foundation.shape.RoundedCornerShape(99.dp)).background(Hairline)) {
                    Box(Modifier.fillMaxWidth(bucket.count.toFloat() / total).height(5.dp).background(WarmWhite.copy(alpha = 0.7f)))
                }
                Text(bucket.count.toString(), color = MutedWhite, fontSize = 10.sp, modifier = Modifier.padding(start = 7.dp))
            }
        }
    }
}

private fun Modifier.clickableShot(shot: ShotDto?, onShot: (String) -> Unit): Modifier =
    if (shot == null) this else clickable { onShot(shot.id) }
