package com.shoots.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import com.shoots.app.data.DeconstructionDto
import com.shoots.app.data.MobileSnapshotDto
import com.shoots.app.data.ProfileDimensionDto
import com.shoots.app.data.ShotDto

@Composable
fun JourneyScreen(
    snapshot: MobileSnapshotDto?,
    imageUrl: (ShotDto) -> String,
    onShot: (String) -> Unit,
    blobUrl: (String) -> String = { "" },
    onPrepareDeconstruction: (String, String, Int, String) -> Unit = { _, _, _, _ -> },
    onShareDeconstruction: (DeconstructionDto) -> Unit = {},
    onSaveDeconstruction: (DeconstructionDto) -> Unit = {},
    onOpenShootRecord: (String, Int) -> Unit = { _, _ -> },
) {
    var section by rememberSaveable { mutableStateOf(JourneySection.UPDATE) }
    val readOnlySample = snapshot?.user?.recordMode == "sample"
    Column(
        Modifier
            .fillMaxSize()
            .background(Ink)
            .statusBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(bottom = 92.dp),
    ) {
        Column(Modifier.padding(horizontal = 20.dp, vertical = 22.dp)) {
            ScreenTitle(
                "Journey",
                if (readOnlySample) {
                    "Inspect a hand-authored Journey layout"
                } else {
                    "See what keeps showing up in your Shots"
                },
                if (readOnlySample) {
                    "These values are interface fixtures, not observations about a Photographer."
                } else {
                    "The choices you return to, the ones you can repeat on purpose, and what changed when you tried."
                },
            )
        }
        if (snapshot == null) {
            Column(Modifier.padding(20.dp)) { Text("Loading your cached Journey…", color = MutedWhite) }
            return@Column
        }
        if (snapshot.latestShootRecord != null) {
            JourneyOpeningHero(
                snapshot = snapshot,
                imageUrl = imageUrl,
                onShot = onShot,
                onOpenShootRecord = onOpenShootRecord,
                readOnlySample = readOnlySample,
            )
            Spacer(Modifier.height(22.dp))
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
                JourneySection.UPDATE -> JourneyUpdateView(
                    snapshot,
                    imageUrl,
                    blobUrl,
                    onShot,
                    onPrepareDeconstruction,
                    onShareDeconstruction,
                    onSaveDeconstruction,
                    readOnlySample,
                )
                JourneySection.TENDENCIES -> TendencyView(snapshot, readOnlySample)
                JourneySection.TECHNIQUES -> TechniqueView(snapshot, readOnlySample)
            }
        }
    }
}

@Composable
private fun JourneyOpeningHero(
    snapshot: MobileSnapshotDto,
    imageUrl: (ShotDto) -> String,
    onShot: (String) -> Unit,
    onOpenShootRecord: (String, Int) -> Unit,
    readOnlySample: Boolean,
) {
    val record = snapshot.latestShootRecord ?: return
    val members = record.shotIds
        .mapNotNull { id -> snapshot.recentShots.firstOrNull { it.id == id } }
    val preview = when {
        members.size <= 3 -> members
        else -> listOf(members.first(), members[members.lastIndex / 2], members.last())
    }
    Column(Modifier.padding(horizontal = 20.dp)) {
        Text(
            if (readOnlySample) "SAMPLE OUTING" else "YOUR LATEST OUTING",
            color = Amber,
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold,
        )
        Spacer(Modifier.height(8.dp))
        Text(
            record.receipt.repeated.firstOrNull()
                ?: record.receipt.varied.firstOrNull()
                ?: "Shoots kept this outing together.",
            color = WarmWhite,
            fontSize = 23.sp,
            lineHeight = 29.sp,
            fontWeight = FontWeight.SemiBold,
        )
        if (preview.isNotEmpty()) {
            Spacer(Modifier.height(13.dp))
            Row(
                Modifier.fillMaxWidth().height(150.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                preview.forEach { shot ->
                    AsyncImage(
                        model = imageUrl(shot),
                        contentDescription = shot.filename,
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxSize()
                            .clip(androidx.compose.foundation.shape.RoundedCornerShape(13.dp))
                            .clickable(role = Role.Button) { onShot(shot.id) },
                        contentScale = ContentScale.Crop,
                    )
                }
            }
        }
        Spacer(Modifier.height(12.dp))
        Text(
            if (readOnlySample) {
                "Fixture only · no collection, Analysis, grouping, or settlement ran."
            } else {
                val shots = if (record.receipt.shotCount == 1) "Shot" else "Shots"
                val scenes = if (record.receipt.sceneCount == 1) "Scene" else "Scenes"
                "Shoots handled ${record.receipt.shotCount} $shots across ${record.receipt.sceneCount} $scenes. " +
                    "Collected → Read → Grouped → Settled."
            },
            color = MutedWhite,
            fontSize = 12.sp,
            lineHeight = 18.sp,
        )
        Spacer(Modifier.height(12.dp))
        PrimaryAction(if (readOnlySample) "Open Sample Shoot Record" else "Open full Shoot Record") {
            onOpenShootRecord(record.shootId, record.revision)
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
    blobUrl: (String) -> String,
    onShot: (String) -> Unit,
    onPrepareDeconstruction: (String, String, Int, String) -> Unit,
    onShareDeconstruction: (DeconstructionDto) -> Unit,
    onSaveDeconstruction: (DeconstructionDto) -> Unit,
    readOnlySample: Boolean,
) {
    Column(Modifier.fillMaxWidth()) {
        val update = snapshot.journey.firstOrNull()
        if (update == null) {
            Column(Modifier.padding(horizontal = 20.dp)) {
                InkCard {
                    Text("Your record has started.", color = WarmWhite, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
                    Spacer(Modifier.height(6.dp))
                    Text(
                        "A clear pattern will appear here after Shoots has enough Shots to compare.",
                        color = MutedWhite,
                        fontSize = 14.sp,
                        lineHeight = 20.sp,
                    )
                }
            }
        } else {
            var expanded by rememberSaveable(update.id) { mutableStateOf(false) }
            var evidence by rememberSaveable(update.id) { mutableStateOf(false) }
            val fullUpdate = if (readOnlySample) {
                "This hand-authored example shows where a real Journey Update would explain what stayed and what varied. It is not evidence about a Photographer."
            } else {
                update.body.trim()
            }
            val preview = journeyPreview(fullUpdate)
            Column(Modifier.padding(horizontal = 20.dp)) {
                SectionTitle(
                    if (readOnlySample) "Sample Journey Update" else "The latest pattern",
                    if (readOnlySample) "${update.shots} SAMPLE SHOT CARDS" else "${update.shots} SHOTS",
                )
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
                            Text(
                                if (readOnlySample) "Hand-authored support lines" else "What this was read from",
                                color = MutedWhite,
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                            )
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
        if (experiment != null && !readOnlySample) {
            Spacer(Modifier.height(24.dp))
            Column(Modifier.padding(horizontal = 20.dp)) {
                SectionTitle("What happened when you tried")
                Spacer(Modifier.height(10.dp))
            }
            ExperimentHero(snapshot, experiment, imageUrl, onShot)
        }
        snapshot.recentInterventions.firstOrNull()?.takeIf { !readOnlySample }?.let { intervention ->
            Spacer(Modifier.height(24.dp))
            Column(Modifier.padding(horizontal = 20.dp)) {
                SectionTitle("What happened to the last suggestion", intervention.route.uppercase())
                Spacer(Modifier.height(10.dp))
                InkCard {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        StatusPill(intervention.attemptState)
                        if (intervention.observableOutcome != "not_applicable") {
                            StatusPill(intervention.observableOutcome, amber = true)
                        }
                    }
                    Spacer(Modifier.height(9.dp))
                    Text(
                        intervention.outcomeReason.ifBlank {
                            "There is no result to compare yet."
                        },
                        color = WarmWhite,
                        fontSize = 15.sp,
                        lineHeight = 22.sp,
                    )
                    if (intervention.resultShotIds.isNotEmpty()) {
                        Spacer(Modifier.height(7.dp))
                        Text(
                                resultSummary(
                                    intervention.resultShotIds.size,
                                    intervention.criteriaMetResults,
                                    intervention.abstentions,
                                ),
                            color = MutedWhite,
                            fontSize = 11.sp,
                        )
                    }
                }
            }
        }
        deconstructionSource(snapshot)?.let { source ->
            Spacer(Modifier.height(24.dp))
            DeconstructionCard(
                snapshot,
                source,
                imageUrl,
                blobUrl,
                onPrepareDeconstruction,
                onShareDeconstruction,
                onSaveDeconstruction,
                readOnlySample,
            )
        }
    }
}

private data class DeconstructionSourceUi(
    val type: String,
    val id: String,
    val revision: Int,
    val label: String,
    val keeperShotIds: List<String>,
    val draft: DeconstructionDto?,
)

private fun deconstructionSource(snapshot: MobileSnapshotDto): DeconstructionSourceUi? {
    val draft = snapshot.latestDeconstruction
    if (draft?.sourceType == "experiment") {
        snapshot.experiments.firstOrNull { it.id == draft.sourceId }?.let { experiment ->
            val memberIds = setOf(experiment.referenceShotId) + experiment.resultShotIds
            val keepers = snapshot.recentShots
                .filter { it.id in memberIds && it.keptAt != null }
                .map { it.id }
                .ifEmpty { draft.candidateCoverShotIds }
            return DeconstructionSourceUi(
                type = "experiment",
                id = experiment.id,
                revision = draft.sourceRevision,
                label = "Experiment",
                keeperShotIds = keepers,
                draft = draft,
            )
        }
    }
    val record = snapshot.latestShootRecord ?: return null
    val matchingDraft = draft?.takeIf {
        it.sourceType == "shoot" &&
            it.sourceId == record.shootId &&
            it.sourceRevision == record.revision
    }
    return DeconstructionSourceUi(
        type = "shoot",
        id = record.shootId,
        revision = record.revision,
        label = "Shoot",
        keeperShotIds = record.receipt.keeperShotIds,
        draft = matchingDraft,
    )
}

@Composable
private fun DeconstructionCard(
    snapshot: MobileSnapshotDto,
    source: DeconstructionSourceUi,
    imageUrl: (ShotDto) -> String,
    blobUrl: (String) -> String,
    onPrepare: (String, String, Int, String) -> Unit,
    onShare: (DeconstructionDto) -> Unit,
    onSave: (DeconstructionDto) -> Unit,
    readOnlySample: Boolean,
) {
    val draft = source.draft
    var selectedCover by rememberSaveable(source.type, source.id, source.revision) {
        mutableStateOf(
            draft?.coverShotId.orEmpty().ifBlank { source.keeperShotIds.firstOrNull().orEmpty() },
        )
    }
    Column(Modifier.padding(horizontal = 20.dp)) {
        SectionTitle(
            if (readOnlySample) "Sample visual story layout" else "Your visual story",
            if (readOnlySample) "HAND-AUTHORED" else "${source.label.uppercase()} STORY",
        )
        Spacer(Modifier.height(10.dp))
        InkCard {
            Text(
                if (readOnlySample) {
                    "No story was built and no visual thread was found by an agent. Story actions are disabled."
                } else {
                    "Shoots follows the sequence and finds the visual thread. " +
                        "You choose the marked Shot that opens the story."
                },
                color = MutedWhite,
                fontSize = 13.sp,
                lineHeight = 19.sp,
            )
            Spacer(Modifier.height(12.dp))
            if (readOnlySample) {
                Text(
                    "A real Photographer would choose a Keeper cover before Shoots drafts story pages.",
                    color = WarmWhite,
                    fontSize = 14.sp,
                    lineHeight = 20.sp,
                )
            } else if (draft?.status == "drafted" && draft.pages.isNotEmpty()) {
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(draft.pages) { page ->
                        Column(Modifier.width(220.dp)) {
                            AsyncImage(
                                model = blobUrl(page.blobPath),
                                contentDescription = page.title,
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .aspectRatio(4f / 5f)
                                    .clip(androidx.compose.foundation.shape.RoundedCornerShape(12.dp))
                                    .background(InkSoft),
                                contentScale = ContentScale.Crop,
                            )
                            Spacer(Modifier.height(6.dp))
                            Text(page.title, color = MutedWhite, fontSize = 12.sp)
                        }
                    }
                }
                Spacer(Modifier.height(12.dp))
                if (draft.suggestedCaption.isNotBlank()) {
                    Column(
                        Modifier
                            .fillMaxWidth()
                            .background(InkSoft, androidx.compose.foundation.shape.RoundedCornerShape(14.dp))
                            .padding(13.dp),
                    ) {
                        Text("READY CAPTION", color = Amber, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                        Spacer(Modifier.height(5.dp))
                        Text(
                            draft.suggestedCaption,
                            color = WarmWhite,
                            fontSize = 13.sp,
                            lineHeight = 19.sp,
                        )
                    }
                    Spacer(Modifier.height(12.dp))
                }
                PrimaryAction("Share ${draft.pages.size}-page story") { onShare(draft) }
                Spacer(Modifier.height(8.dp))
                SecondaryAction("Save story to this phone") { onSave(draft) }
            } else if (source.keeperShotIds.isEmpty()) {
                Text(
                    "Mark one Shot you care about with the bookmark, then return here to use it as the opening.",
                    color = WarmWhite,
                    fontSize = 14.sp,
                    lineHeight = 20.sp,
                )
            } else {
                Text("CHOOSE THE OPENING SHOT", color = MutedWhite, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(7.dp))
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(source.keeperShotIds) { id ->
                        val shot = snapshot.recentShots.firstOrNull { it.id == id }
                        AsyncImage(
                            model = shot?.let(imageUrl),
                            contentDescription = "Possible story cover",
                            modifier = Modifier
                                .width(92.dp)
                                .aspectRatio(1f)
                                .clip(androidx.compose.foundation.shape.RoundedCornerShape(9.dp))
                                .border(
                                    if (selectedCover == id) 2.dp else 1.dp,
                                    if (selectedCover == id) Amber else Hairline,
                                    androidx.compose.foundation.shape.RoundedCornerShape(9.dp),
                                )
                                .clickable(role = Role.Button) { selectedCover = id },
                            contentScale = ContentScale.Crop,
                        )
                    }
                }
                Spacer(Modifier.height(12.dp))
                PrimaryAction("Build my story", selectedCover.isNotBlank()) {
                    onPrepare(source.type, source.id, source.revision, selectedCover)
                }
            }
        }
    }
}

@Composable
private fun TendencyView(snapshot: MobileSnapshotDto, readOnlySample: Boolean) {
    Column(Modifier.padding(horizontal = 20.dp)) {
        SectionTitle(
            if (readOnlySample) "Sample pattern values" else "The choices you return to",
            if (readOnlySample) "HAND-AUTHORED" else "${snapshot.profile.shots} SHOTS READ",
        )
        Spacer(Modifier.height(6.dp))
        Text(
            if (readOnlySample) {
                "These values show the layout only. Shoots did not calculate them."
            } else {
                "These are patterns, not grades. Only your Keeper marks say what you care about."
            },
            color = MutedWhite,
            fontSize = 12.sp,
            lineHeight = 17.sp,
        )
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
private fun TechniqueView(snapshot: MobileSnapshotDto, readOnlySample: Boolean) {
    Column(Modifier.padding(horizontal = 20.dp)) {
        SectionTitle(
            if (readOnlySample) "Sample recurring Technique labels" else "What keeps recurring",
            if (readOnlySample) "HAND-AUTHORED" else "FROM YOUR OWN SHOTS",
        )
        Spacer(Modifier.height(10.dp))
        if (snapshot.techniques.isEmpty()) {
            Text("Nothing has appeared clearly in enough Shots yet.", color = MutedWhite, fontSize = 14.sp)
        } else {
            snapshot.techniques.forEach { technique ->
                InkCard {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(technique.name, color = WarmWhite, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
                        StatusPill(technique.status)
                    }
                    Spacer(Modifier.height(6.dp))
                    Text(
                        if (readOnlySample) {
                            "Fixture value: ${technique.corroboratedShots} sample Shot cards."
                        } else {
                            coverageEvidence(technique)
                        },
                        color = MutedWhite,
                        fontSize = 12.sp,
                    )
                    if (
                        technique.reproduceAttempts > 0 ||
                        technique.abstentions > 0
                    ) {
                        Spacer(Modifier.height(4.dp))
                        Text(
                            "${technique.reproduceAttempts} result " +
                                counted(technique.reproduceAttempts, "Shot") +
                                if (technique.abstentions > 0) {
                                    " · ${technique.abstentions} could not be checked"
                                } else {
                                    ""
                                },
                            color = MutedWhite,
                            fontSize = 12.sp,
                        )
                    }
                    Spacer(Modifier.height(8.dp))
                    Text(
                        if (readOnlySample) {
                            "SAMPLE VALUE · NO REPRODUCE SESSION"
                        } else if (technique.reproduceSessions > 0) {
                            "WHAT HAPPENED WHEN YOU TRIED"
                        } else {
                            "NOT TRIED ON PURPOSE YET"
                        },
                        color = if (technique.criteriaMetSessions > 0) Amber else MutedWhite,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Spacer(Modifier.height(3.dp))
                    Text(
                        repeatabilityEvidence(technique),
                        color = MutedWhite,
                        fontSize = 12.sp,
                        lineHeight = 17.sp,
                    )
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

private fun coverageEvidence(technique: com.shoots.app.data.TechniqueNodeDto): String =
    buildList {
        add(
            "Clear in ${technique.corroboratedShots} " +
                counted(technique.corroboratedShots, "Shot"),
        )
        if (technique.distinctScenes > 0) {
            add("${technique.distinctScenes} ${counted(technique.distinctScenes, "Scene")}")
        }
        if (technique.distinctShoots > 0) {
            add("${technique.distinctShoots} ${counted(technique.distinctShoots, "Shoot")}")
        }
    }.joinToString(" · ")

private fun repeatabilityEvidence(technique: com.shoots.app.data.TechniqueNodeDto): String =
    if (technique.reproduceSessions == 0) {
        if (technique.status == "recurring") {
            "This keeps returning in your Shots. You have not tried to repeat it on purpose yet."
        } else {
            "You have not tried to repeat this on purpose yet."
        }
    } else {
        if (technique.evaluableReproduceSessions == 0) {
            "You tried this in ${technique.reproduceSessions} " +
                counted(technique.reproduceSessions, "session") +
                ", but Shoots could not check the result."
        } else {
            "${technique.criteriaMetSessions} of ${technique.evaluableReproduceSessions} checked " +
                counted(technique.evaluableReproduceSessions, "session") +
                " matched what you set before shooting."
        }
    }

private fun counted(count: Int, noun: String): String = if (count == 1) noun else "${noun}s"

private fun resultSummary(results: Int, matched: Int, unchecked: Int): String =
    buildList {
        add("$results result ${counted(results, "Shot")}")
        add("$matched matched every check")
        if (unchecked > 0) add("$unchecked could not be checked")
    }.joinToString(" · ")

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
    val isExplore = experiment.type == "explore"
    Column(Modifier.padding(horizontal = 20.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            StatusPill(experiment.type, amber = true)
            StatusPill(if (experiment.status == "skipped") "left" else experiment.status)
        }
        Spacer(Modifier.height(10.dp))
        Text(experiment.title, color = WarmWhite, fontSize = 21.sp, lineHeight = 26.sp, fontWeight = FontWeight.Bold)
        if (isExplore) {
            Spacer(Modifier.height(8.dp))
            Text(
                "${experiment.variationObservations.map { it.variationId }.distinct().size} " +
                    "VARIATIONS OBSERVED · NO VERDICT",
                color = MutedWhite,
                fontSize = 10.sp,
                fontWeight = FontWeight.Bold,
            )
        } else {
            Spacer(Modifier.height(13.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                JourneyImage("KEEPER REFERENCE", reference, imageUrl, onShot, Modifier.weight(1f))
                JourneyImage("REPRESENTATIVE RESULT", result, imageUrl, onShot, Modifier.weight(1f))
            }
        }
        if (experiment.resultShotIds.isNotEmpty()) {
            Spacer(Modifier.height(16.dp))
            Text(
                if (isExplore) "WHAT YOU TRIED" else "EVERY RESULT",
                color = MutedWhite,
                fontSize = 10.sp,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.height(7.dp))
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                items(experiment.resultShotIds) { id ->
                    val shot = snapshot.recentShots.firstOrNull { it.id == id }
                    val verdict = experiment.verdicts.firstOrNull { it.shotId == id }
                    val observation = experiment.variationObservations.firstOrNull { it.shotId == id }
                    val variation = experiment.variations.firstOrNull { it.id == observation?.variationId }
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
                                isExplore && !observation?.abstained.isNullOrBlank() -> "UNREADABLE"
                                isExplore -> variation?.title?.uppercase() ?: "EXPLORE RESULT"
                                verdict == null -> "COULD NOT CHECK"
                                verdict.criteriaMet -> "MATCHED"
                                else -> "NOT YET"
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
