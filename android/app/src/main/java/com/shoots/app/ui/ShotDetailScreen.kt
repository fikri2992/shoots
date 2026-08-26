package com.shoots.app.ui

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
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
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.shoots.app.Amber
import com.shoots.app.FindingRed
import com.shoots.app.Hairline
import com.shoots.app.Ink
import com.shoots.app.InkRaised
import com.shoots.app.MutedWhite
import com.shoots.app.WarmWhite
import com.shoots.app.data.AnalysisDto
import com.shoots.app.data.CompositionDto
import com.shoots.app.data.FindingDto
import com.shoots.app.data.GridSpecDto
import com.shoots.app.data.ShotDto
import com.shoots.app.data.ShotViewDto

@Composable
fun ShotDetailScreen(
    view: ShotViewDto?,
    imageUrl: (ShotDto, Boolean) -> String,
    blobUrl: (String) -> String,
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
            BackAction("Shots", onBack)
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
        var selectedFinding by rememberSaveable(shot.id) { mutableIntStateOf(0) }
        var reviewLayer by rememberSaveable(shot.id) {
            mutableStateOf(defaultReviewLayer(analysis))
        }
        var fullAnalysis by rememberSaveable(shot.id) { mutableStateOf(false) }
        var provenance by rememberSaveable(shot.id) { mutableStateOf(false) }
        LaunchedEffect(analysis?.shotId) {
            if (analysis != null && reviewLayer == ReviewLayer.CLEAN) {
                reviewLayer = defaultReviewLayer(analysis)
            }
            selectedFinding = selectedFinding.coerceIn(0, maxOf(0, analysis?.findings?.lastIndex ?: 0))
        }
        ShotImage(
            shot = shot,
            analysis = analysis,
            source = imageUrl(shot, true),
            findingSource = blobUrl(shot.blobs["finding_marked"].orEmpty()),
            layer = reviewLayer,
            selectedFinding = selectedFinding,
            onLayer = { reviewLayer = it },
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
                val corroborated = analysis.techniques
                    .filter(::isCorroborated)
                    .sortedWith(compareByDescending<com.shoots.app.data.TechniqueEvidenceDto> { it.agreement }.thenByDescending { it.confidence })
                val instruction = compositionInstruction(analysis.composition, shot.grid)

                if (corroborated.isNotEmpty()) {
                    SectionTitle("What worked", "CORROBORATED")
                    Spacer(Modifier.height(10.dp))
                    TechniqueEvidenceCard(corroborated.first(), shot.grid)
                    Spacer(Modifier.height(22.dp))
                }

                analysis.findings.firstOrNull()?.let { finding ->
                    SectionTitle("What got in the way", "MEASURED")
                    Spacer(Modifier.height(10.dp))
                    InkCard(onClick = { selectedFinding = 0; reviewLayer = ReviewLayer.FINDING }) {
                        Text(
                            plainCellReferences(finding.what, shot.grid),
                            color = FindingRed,
                            fontSize = 15.sp,
                            lineHeight = 21.sp,
                            fontWeight = FontWeight.SemiBold,
                        )
                        if (finding.why.isNotBlank()) {
                            Spacer(Modifier.height(6.dp))
                            Text(
                                plainCellReferences(finding.why, shot.grid),
                                color = MutedWhite,
                                fontSize = 13.sp,
                                lineHeight = 18.sp,
                            )
                        }
                        Spacer(Modifier.height(8.dp))
                        Text(findingLocationCopy(finding), color = MutedWhite, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                    }
                    Spacer(Modifier.height(22.dp))
                }

                if (instruction.isNotBlank()) {
                    SectionTitle("One thing to try", "COMPANION")
                    Spacer(Modifier.height(10.dp))
                    InkCard(onClick = { reviewLayer = ReviewLayer.ACTION }) {
                        Text(instruction, color = WarmWhite, fontSize = 14.sp, lineHeight = 21.sp)
                        Spacer(Modifier.height(7.dp))
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text("Show on Shot", color = Amber, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                            ForwardChevron(Amber)
                        }
                    }
                    Spacer(Modifier.height(22.dp))
                }

                AnalysisDisclosure(
                    analysis = analysis,
                    shot = shot,
                    corroborated = corroborated,
                    expanded = fullAnalysis,
                    selectedFinding = selectedFinding,
                    reviewLayer = reviewLayer,
                    onToggle = { fullAnalysis = !fullAnalysis },
                    onFinding = { index ->
                        selectedFinding = index
                        reviewLayer = ReviewLayer.FINDING
                    },
                )
            }

            if (
                view.run != null ||
                shot.experimentId.isNotBlank() ||
                analysis?.model?.isNotBlank() == true ||
                analysis?.promptVersion?.isNotBlank() == true
            ) {
                Spacer(Modifier.height(22.dp))
                ProvenanceDisclosure(
                    view = view,
                    expanded = provenance,
                    onToggle = { provenance = !provenance },
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
private fun TechniqueEvidenceCard(
    evidence: com.shoots.app.data.TechniqueEvidenceDto,
    grid: GridSpecDto?,
) {
    InkCard {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(
                humanLabel(evidence.techniqueId),
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
                plainCellReferences(evidence.note, grid),
                color = MutedWhite,
                fontSize = 13.sp,
                lineHeight = 18.sp,
            )
        }
    }
}

@Composable
private fun AnalysisDisclosure(
    analysis: AnalysisDto,
    shot: ShotDto,
    corroborated: List<com.shoots.app.data.TechniqueEvidenceDto>,
    expanded: Boolean,
    selectedFinding: Int,
    reviewLayer: ReviewLayer,
    onToggle: () -> Unit,
    onFinding: (Int) -> Unit,
) {
    InkCard {
        DisclosureHeader(
            title = "Full Analysis",
            summary = buildList {
                if (analysis.findings.isNotEmpty()) add("${analysis.findings.size} Findings")
                if (corroborated.isNotEmpty()) add("${corroborated.size} corroborated")
            }.joinToString(" · ").ifBlank { "Evidence and model read" },
            expanded = expanded,
            onToggle = onToggle,
        )
        AnimatedVisibility(expanded) {
            Column(Modifier.fillMaxWidth().padding(top = 16.dp)) {
                if (corroborated.isEmpty()) {
                    Text(
                        "The panel did not corroborate a Technique in this Shot.",
                        color = MutedWhite,
                        fontSize = 13.sp,
                        lineHeight = 19.sp,
                    )
                } else if (corroborated.size > 1) {
                    Text("OTHER CORROBORATED TECHNIQUES", color = MutedWhite, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(7.dp))
                    corroborated.drop(1).forEach { evidence ->
                        Text(
                            "${humanLabel(evidence.techniqueId)} · ${lensCount(evidence.agreement)}",
                            color = WarmWhite,
                            fontSize = 13.sp,
                            lineHeight = 19.sp,
                        )
                    }
                }

                if (analysis.findings.isNotEmpty()) {
                    Spacer(Modifier.height(17.dp))
                    Text("MEASURED FINDINGS", color = MutedWhite, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(4.dp))
                    Text("Tap one to mark its location on the Shot.", color = MutedWhite, fontSize = 12.sp)
                    Spacer(Modifier.height(9.dp))
                    analysis.findings.forEachIndexed { index, finding ->
                        val shown = reviewLayer == ReviewLayer.FINDING && selectedFinding == index
                        Column(
                            Modifier
                                .fillMaxWidth()
                                .background(Ink, RoundedCornerShape(13.dp))
                                .border(
                                    1.dp,
                                    if (shown) FindingRed.copy(alpha = 0.6f) else Hairline,
                                    RoundedCornerShape(13.dp),
                                )
                                .clickable(role = Role.Button) { onFinding(index) }
                                .padding(13.dp),
                        ) {
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text(
                                    plainCellReferences(finding.what, shot.grid),
                                    color = FindingRed,
                                    fontSize = 14.sp,
                                    lineHeight = 19.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    modifier = Modifier.weight(1f),
                                )
                                if (shown) StatusPill("shown", red = true)
                            }
                            if (finding.why.isNotBlank()) {
                                Spacer(Modifier.height(5.dp))
                                Text(
                                    plainCellReferences(finding.why, shot.grid),
                                    color = MutedWhite,
                                    fontSize = 12.sp,
                                    lineHeight = 17.sp,
                                )
                            }
                            Spacer(Modifier.height(6.dp))
                            Text(findingLocationCopy(finding), color = MutedWhite, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                        }
                        if (index != analysis.findings.lastIndex) Spacer(Modifier.height(8.dp))
                    }
                }

                if (analysis.observations.isNotEmpty()) {
                    Spacer(Modifier.height(17.dp))
                    LabelValue(
                        "Observations",
                        analysis.observations.joinToString("\n") { "• ${plainCellReferences(it, shot.grid)}" },
                    )
                }

                if (analysis.critique.isNotBlank() || analysis.abstained.isNotBlank()) {
                    Spacer(Modifier.height(17.dp))
                    LabelValue(
                        "Panel read · model opinion",
                        plainCellReferences(analysis.abstained.ifBlank { analysis.critique }, shot.grid),
                    )
                }
            }
        }
    }
}

@Composable
private fun ProvenanceDisclosure(
    view: ShotViewDto,
    expanded: Boolean,
    onToggle: () -> Unit,
) {
    val shot = view.shot
    val run = view.run
    val analysis = view.analysis
    InkCard {
        DisclosureHeader(
            title = "Run and provenance",
            summary = run?.status?.let(::humanLabel).orEmpty().ifBlank { "Technical record" },
            expanded = expanded,
            onToggle = onToggle,
        )
        AnimatedVisibility(expanded) {
            Column(Modifier.fillMaxWidth().padding(top = 15.dp)) {
                run?.steps?.forEach { (stage, step) ->
                    Row(
                        Modifier.fillMaxWidth().padding(vertical = 5.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Text(humanLabel(stage), color = WarmWhite, fontSize = 13.sp)
                        Text(
                            humanLabel(step.state),
                            color = if (step.state == "terminal") FindingRed else MutedWhite,
                            fontSize = 11.sp,
                        )
                    }
                }
                val analysisSource = listOfNotNull(
                    analysis?.model?.takeIf(String::isNotBlank),
                    analysis?.promptVersion?.takeIf(String::isNotBlank)?.take(10),
                ).joinToString(" · ")
                if (analysisSource.isNotBlank()) {
                    Spacer(Modifier.height(12.dp))
                    LabelValue("Analysis source", analysisSource)
                }
                if (shot.experimentId.isNotBlank()) {
                    Spacer(Modifier.height(12.dp))
                    LabelValue(
                        "Experiment",
                        if (shot.captureSessionId.isNotBlank()) {
                            "Captured in an explicit Experiment session"
                        } else {
                            "Associated with an Experiment"
                        },
                    )
                }
            }
        }
    }
}

@Composable
private fun DisclosureHeader(
    title: String,
    summary: String,
    expanded: Boolean,
    onToggle: () -> Unit,
) {
    Row(
        Modifier
            .fillMaxWidth()
            .clickable(role = Role.Button, onClick = onToggle)
            .semantics(mergeDescendants = true) {
                stateDescription = if (expanded) "Expanded" else "Collapsed"
            }
            .padding(vertical = 2.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(title, color = WarmWhite, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(3.dp))
            Text(summary, color = MutedWhite, fontSize = 11.sp, lineHeight = 16.sp)
        }
        DisclosureChevron(expanded)
    }
}

@Composable
private fun ShotImage(
    shot: ShotDto,
    analysis: AnalysisDto?,
    source: String,
    findingSource: String,
    layer: ReviewLayer,
    selectedFinding: Int,
    onLayer: (ReviewLayer) -> Unit,
) {
    val grid = shot.grid
    val composition = analysis?.composition
    val finding = analysis?.findings?.getOrNull(selectedFinding)
    val ratio = grid
        ?.takeIf { it.width > 0 && it.height > 0 }
        ?.let { it.width.toFloat() / it.height.toFloat() }
        ?: (4f / 3f)
    Column(Modifier.fillMaxWidth().background(InkRaised)) {
        Box(Modifier.fillMaxWidth().aspectRatio(ratio)) {
            AnimatedContent(
                targetState = layer,
                modifier = Modifier.fillMaxSize(),
                transitionSpec = { fadeIn(tween(150)) togetherWith fadeOut(tween(110)) },
                label = "Shot review layer",
            ) { shownLayer ->
                Box(Modifier.fillMaxSize()) {
                    AsyncImage(
                        model = if (
                            shownLayer == ReviewLayer.FINDING &&
                            finding?.findingId == "blown_highlights" &&
                            findingSource.isNotBlank()
                        ) findingSource else source,
                        contentDescription = shot.filename,
                        modifier = Modifier.fillMaxSize(),
                        contentScale = if (grid == null) ContentScale.Fit else ContentScale.FillBounds,
                    )
                    if (grid != null && composition != null) {
                        CompositionGuide(
                            grid = grid,
                            composition = composition,
                            finding = finding,
                            layer = shownLayer,
                            modifier = Modifier.fillMaxSize(),
                        )
                    }
                    Text(
                        reviewLayerLabel(shownLayer, composition, finding),
                        color = if (shownLayer == ReviewLayer.FINDING) FindingRed else WarmWhite,
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
        ReviewLayerPicker(
            selected = layer,
            hasFinding = !analysis?.findings.isNullOrEmpty(),
            hasAction = composition?.let(::hasCompositionAction) == true,
            hasGuide = grid != null && composition != null,
            onLayer = onLayer,
        )
    }
}

@Composable
private fun ReviewLayerPicker(
    selected: ReviewLayer,
    hasFinding: Boolean,
    hasAction: Boolean,
    hasGuide: Boolean,
    onLayer: (ReviewLayer) -> Unit,
) {
    val layers = buildList {
        add(ReviewLayer.CLEAN)
        if (hasFinding) add(ReviewLayer.FINDING)
        if (hasAction) add(ReviewLayer.ACTION)
        if (hasGuide) add(ReviewLayer.GUIDE)
    }
    Row(
        Modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState())
            .selectableGroup()
            .padding(horizontal = 12.dp, vertical = 10.dp),
        horizontalArrangement = Arrangement.spacedBy(7.dp),
    ) {
        layers.forEach { layer ->
            val chosen = selected == layer
            val accent = if (layer == ReviewLayer.FINDING) FindingRed else Amber
            val background by animateColorAsState(
                if (chosen) accent.copy(alpha = 0.16f) else Ink,
                animationSpec = tween(160),
                label = "$layer layer",
            )
            Text(
                when (layer) {
                    ReviewLayer.CLEAN -> "Clean"
                    ReviewLayer.FINDING -> "Finding"
                    ReviewLayer.ACTION -> "Try"
                    ReviewLayer.GUIDE -> "Guide"
                },
                color = if (chosen) accent else MutedWhite,
                fontSize = 11.sp,
                fontWeight = if (chosen) FontWeight.Bold else FontWeight.Medium,
                modifier = Modifier
                    .background(background, RoundedCornerShape(99.dp))
                    .border(1.dp, if (chosen) accent.copy(alpha = 0.45f) else Hairline, RoundedCornerShape(99.dp))
                    .selectable(
                        selected = chosen,
                        role = Role.Tab,
                        onClick = { onLayer(layer) },
                    )
                    .padding(horizontal = 14.dp, vertical = 8.dp),
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

fun compositionInstruction(composition: CompositionDto, grid: GridSpecDto?): String {
    if (composition.suggestedCropCells.isNotEmpty()) {
        val rationale = composition.cropReason.substringAfter(" removes ", "").trim()
        val plainRationale = plainCellReferences(rationale, grid).trim().trimEnd('.')
        return if (plainRationale.isBlank()) {
            "Try the tested crop shown on the Shot."
        } else {
            "Try the tested crop shown on the Shot. It removes $plainRationale."
        }
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

private fun defaultReviewLayer(analysis: AnalysisDto?): ReviewLayer = when {
    analysis == null -> ReviewLayer.CLEAN
    analysis.findings.isNotEmpty() -> ReviewLayer.FINDING
    hasCompositionAction(analysis.composition) -> ReviewLayer.ACTION
    else -> ReviewLayer.GUIDE
}

private fun hasCompositionAction(composition: CompositionDto): Boolean =
    composition.suggestedCropCells.isNotEmpty() || composition.moves.any {
        it.kind == "move" && it.fromCells.isNotEmpty() && it.toCells.isNotEmpty()
    }

private fun reviewLayerLabel(
    layer: ReviewLayer,
    composition: CompositionDto?,
    finding: FindingDto?,
): String = when (layer) {
    ReviewLayer.CLEAN -> "CLEAN"
    ReviewLayer.FINDING -> "FINDING · ${findingLabel(finding?.findingId.orEmpty()).uppercase()}"
    ReviewLayer.ACTION -> if (composition?.suggestedCropCells?.isNotEmpty() == true) {
        "TRY · TESTED CROP"
    } else {
        "TRY · MOVE"
    }
    ReviewLayer.GUIDE -> "GUIDE · ${guideLabel(composition?.guide.orEmpty().ifBlank { "thirds" }).uppercase()}"
}

private fun findingLocationCopy(finding: FindingDto): String = when (finding.findingId) {
    "camera_shake" -> "WHOLE FRAME · NO HONEST LOCAL HOTSPOT"
    "colour_cast" -> "WHOLE FRAME"
    "blown_highlights" -> "PIXEL-LOCATED HIGHLIGHTS"
    "off_guide_subject" -> "SUBJECT POINT → NEAREST PLACEMENT LINE"
    "split_horizon" -> "MEASURED HORIZON LINE"
    "no_centre_of_interest" -> "LOCATED SUBJECT REGION"
    else -> if (finding.cells.isNotEmpty()) "LOCATED REGION" else "NO LOCAL REGION"
}

private fun detailStatus(view: ShotViewDto): String = when {
    view.analysis != null -> "read"
    view.shot.status == "failed" || view.run?.status == "terminal" -> "unreadable"
    view.run == null -> "interrupted"
    view.run.status == "retrying" -> "retrying"
    else -> "reading"
}

private fun lensCount(count: Int): String = if (count == 1) "1 lens" else "$count lenses"

fun isCorroborated(evidence: com.shoots.app.data.TechniqueEvidenceDto): Boolean =
    evidence.agreement >= 2 && evidence.confidence >= 0.75
