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
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.verticalScroll
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.togetherWith
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
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
    var section by rememberSaveable { mutableStateOf(JourneySection.UPDATE) }
    Column(
        Modifier
            .fillMaxSize()
            .background(Ink)
            .statusBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(bottom = 92.dp),
    ) {
        Column(Modifier.padding(horizontal = 20.dp, vertical = 22.dp)) {
            ScreenTitle("Journey", "Your changing eye", "What repeats, what changed, and what remains unknown.")
        }
        if (snapshot == null) {
            Column(Modifier.padding(20.dp)) { Text("Loading your cached Journey…", color = MutedWhite) }
            return@Column
        }
        JourneySections(section, onSelect = { section = it })
        Spacer(Modifier.height(18.dp))
        AnimatedContent(
            targetState = section,
            transitionSpec = {
                val forward = targetState.ordinal >= initialState.ordinal
                val enter = fadeIn(tween(160)) + slideInHorizontally(tween(200)) { width ->
                    if (forward) width / 12 else -width / 12
                }
                val exit = fadeOut(tween(120)) + slideOutHorizontally(tween(170)) { width ->
                    if (forward) -width / 16 else width / 16
                }
                enter togetherWith exit
            },
            label = "Journey section",
        ) { selected ->
            when (selected) {
                JourneySection.UPDATE -> JourneyUpdateView(snapshot, imageUrl, onShot)
                JourneySection.TENDENCIES -> TendencyView(snapshot)
                JourneySection.TECHNIQUES -> TechniqueView(snapshot)
            }
        }
    }
}

private enum class JourneySection { UPDATE, TENDENCIES, TECHNIQUES }

@Composable
private fun JourneySections(selected: JourneySection, onSelect: (JourneySection) -> Unit) {
    Row(
        Modifier.fillMaxWidth().padding(horizontal = 20.dp).selectableGroup(),
        horizontalArrangement = Arrangement.spacedBy(7.dp),
    ) {
        listOf(
            JourneySection.UPDATE to "Update",
            JourneySection.TENDENCIES to "Tendencies",
            JourneySection.TECHNIQUES to "Techniques",
        ).forEach { (section, label) ->
            val active = selected == section
            val background by animateColorAsState(
                if (active) Amber.copy(alpha = 0.15f) else InkSoft,
                animationSpec = tween(160),
                label = "$label section",
            )
            Text(
                label,
                color = if (active) Amber else MutedWhite,
                fontSize = 11.sp,
                fontWeight = if (active) FontWeight.Bold else FontWeight.Medium,
                modifier = Modifier
                    .weight(1f)
                    .background(background, androidx.compose.foundation.shape.RoundedCornerShape(99.dp))
                    .selectable(
                        selected = active,
                        role = Role.Tab,
                        onClick = { onSelect(section) },
                    )
                    .padding(vertical = 9.dp),
                textAlign = androidx.compose.ui.text.style.TextAlign.Center,
            )
        }
    }
}

@Composable
private fun JourneyUpdateView(
    snapshot: MobileSnapshotDto,
    imageUrl: (ShotDto) -> String,
    onShot: (String) -> Unit,
) {
    Column(Modifier.fillMaxWidth()) {
        val update = snapshot.journey.firstOrNull()
        if (update == null) {
            Column(Modifier.padding(horizontal = 20.dp)) {
                InkCard {
                    Text("No Journey Update yet.", color = WarmWhite, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
                    Spacer(Modifier.height(6.dp))
                    Text("Shoots writes one only when the record supports a meaningful longitudinal claim.", color = MutedWhite, fontSize = 14.sp, lineHeight = 20.sp)
                }
            }
        } else {
            var expanded by rememberSaveable(update.id) { mutableStateOf(false) }
            var evidence by rememberSaveable(update.id) { mutableStateOf(false) }
            val fullUpdate = update.body.trim()
            val preview = journeyPreview(fullUpdate)
            Column(Modifier.padding(horizontal = 20.dp)) {
                SectionTitle("Latest Update", "${update.shots} SHOTS")
                Spacer(Modifier.height(10.dp))
                InkCard {
                    Text(
                        if (expanded) fullUpdate else preview,
                        color = WarmWhite,
                        fontSize = 17.sp,
                        lineHeight = 25.sp,
                        fontWeight = FontWeight.Medium,
                    )
                    if (preview != fullUpdate) {
                        Text(
                            if (expanded) "Show less" else "Read full update",
                            color = Amber,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier
                                .clickable(role = Role.Button) { expanded = !expanded }
                                .padding(top = 12.dp, bottom = 4.dp),
                        )
                    }
                    if (update.evidence.isNotEmpty()) {
                        Row(
                            Modifier
                                .fillMaxWidth()
                                .clickable(role = Role.Button) { evidence = !evidence }
                                .semantics(mergeDescendants = true) {
                                    stateDescription = if (evidence) "Expanded" else "Collapsed"
                                }
                                .padding(top = 9.dp, bottom = 2.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text("What this was read from", color = MutedWhite, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                            DisclosureChevron(evidence)
                        }
                        AnimatedVisibility(evidence) {
                            Column(Modifier.fillMaxWidth().padding(top = 7.dp)) {
                                update.evidence.take(8).forEach {
                                    Text("• $it", color = MutedWhite, fontSize = 12.sp, lineHeight = 18.sp)
                                }
                            }
                        }
                    }
                }
            }
        }

        val experiment = snapshot.experiments.firstOrNull { it.resultShotIds.isNotEmpty() }
        if (experiment != null) {
            Spacer(Modifier.height(24.dp))
            Column(Modifier.padding(horizontal = 20.dp)) {
                SectionTitle("Latest Experiment Record")
                Spacer(Modifier.height(10.dp))
            }
            ExperimentHero(snapshot, experiment, imageUrl, onShot)
        }
    }
}

@Composable
private fun TendencyView(snapshot: MobileSnapshotDto) {
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
}

@Composable
private fun TechniqueView(snapshot: MobileSnapshotDto) {
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
                        "${technique.sightings} sightings · " +
                            "${technique.corroboratedShots} corroborated Shots",
                        color = MutedWhite,
                        fontSize = 12.sp,
                    )
                    if (technique.distinctScenes > 0 || technique.distinctShoots > 0) {
                        Spacer(Modifier.height(4.dp))
                        Text(
                            "${technique.distinctScenes} ${counted(technique.distinctScenes, "Scene")} · " +
                                "${technique.distinctShoots} ${counted(technique.distinctShoots, "Shoot")}",
                            color = MutedWhite,
                            fontSize = 12.sp,
                        )
                    }
                    if (
                        technique.reproduceAttempts > 0 ||
                        technique.criteriaMetResults > 0 ||
                        technique.abstentions > 0
                    ) {
                        Spacer(Modifier.height(4.dp))
                        Text(
                            "${technique.reproduceAttempts} Reproduce results · " +
                                "${technique.criteriaMetResults} Criteria met · " +
                                "${technique.abstentions} ${counted(technique.abstentions, "abstention")}",
                            color = MutedWhite,
                            fontSize = 12.sp,
                        )
                    }
                    if (technique.positiveKeeperShots > 0) {
                        Spacer(Modifier.height(4.dp))
                        Text(
                            "${technique.positiveKeeperShots} marked Keepers",
                            color = MutedWhite,
                            fontSize = 12.sp,
                        )
                    }
                }
                Spacer(Modifier.height(8.dp))
            }
        }
    }
}

private fun counted(count: Int, noun: String): String = if (count == 1) noun else "${noun}s"

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
            StatusPill(if (experiment.status == "skipped") "left" else experiment.status)
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

private fun journeyPreview(body: String): String {
    val clean = body.trim()
    val sentenceEnd = Regex("[.!?](?=\\s|$)").find(clean)?.range?.last ?: return clean
    return clean.take(sentenceEnd + 1)
}
