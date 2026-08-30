package com.shoots.app.ui

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalConfiguration
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
import com.shoots.app.Hairline
import com.shoots.app.Ink
import com.shoots.app.InkRaised
import com.shoots.app.MutedWhite
import com.shoots.app.WarmWhite
import com.shoots.app.data.AnalysisDto
import com.shoots.app.data.CompositionDto
import com.shoots.app.data.FindingDto
import com.shoots.app.data.GridSpecDto
import com.shoots.app.data.ExperimentDirectionDto
import com.shoots.app.data.ShotDto
import com.shoots.app.data.ShotTechniqueContextDto
import com.shoots.app.data.ShotViewDto
import com.shoots.app.data.VisualMarkDto

@Composable
fun ShotDetailScreen(
    view: ShotViewDto?,
    imageUrl: (ShotDto, Boolean) -> String,
    blobUrl: (String) -> String,
    onBack: () -> Unit,
    onKeeper: (Boolean) -> Unit,
    onMoveToInspiration: () -> Unit = {},
    onRetry: () -> Unit,
    onOpenDrive: (String) -> Unit,
    experimentDirections: List<ExperimentDirectionDto> = emptyList(),
    onChooseExperimentDirection: (String, String, Boolean) -> Unit = { _, _, _ -> },
    onOpenJourney: () -> Unit = {},
    onOpenExperiment: () -> Unit = {},
    readOnlySample: Boolean = false,
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
        val story = analysis?.let { buildShotVisualStory(it, view.teaching, shot.grid) }.orEmpty()
        var selectedFinding by rememberSaveable(shot.id) { mutableIntStateOf(0) }
        var storyIndex by rememberSaveable(shot.id) { mutableIntStateOf(0) }
        var guideMode by rememberSaveable(shot.id) { mutableStateOf(false) }
        var selectedGuide by rememberSaveable(shot.id) {
            mutableStateOf(analysis?.composition?.guide?.ifBlank { "none" } ?: "none")
        }
        var guideRotation by rememberSaveable(shot.id) { mutableIntStateOf(0) }
        var showGuidePicker by rememberSaveable(shot.id) { mutableStateOf(false) }
        var fullAnalysis by rememberSaveable(shot.id) { mutableStateOf(false) }
        var provenance by rememberSaveable(shot.id) { mutableStateOf(false) }
        var confirmInspiration by rememberSaveable(shot.id) { mutableStateOf(false) }
        LaunchedEffect(analysis?.shotId, story.size) {
            storyIndex = storyIndex.coerceIn(0, maxOf(0, story.lastIndex))
            if (selectedGuide == "none" && !analysis?.composition?.guide.isNullOrBlank()) {
                selectedGuide = analysis?.composition?.guide.orEmpty()
            }
            selectedFinding = selectedFinding.coerceIn(0, maxOf(0, analysis?.findings?.lastIndex ?: 0))
        }
        val currentStep = story.getOrNull(storyIndex)
        val reviewLayer = when {
            guideMode && selectedGuide == "none" -> ReviewLayer.CLEAN
            guideMode -> ReviewLayer.GUIDE
            else -> currentStep?.layer ?: ReviewLayer.CLEAN
        }
        LaunchedEffect(storyIndex, guideMode) {
            if (!guideMode) selectedFinding = currentStep?.findingIndex ?: 0
        }
        ShotImage(
            shot = shot,
            analysis = analysis,
            source = imageUrl(shot, true),
            findingSource = blobUrl(shot.blobs["finding_marked"].orEmpty()),
            artifactSource = blobUrl,
            story = story,
            storyIndex = storyIndex,
            guideMode = guideMode,
            selectedGuide = selectedGuide,
            guideRotation = guideRotation,
            onPrevious = { if (storyIndex > 0) storyIndex -= 1 },
            onNext = { if (storyIndex < story.lastIndex) storyIndex += 1 },
            onSelectStory = { storyIndex = it.coerceIn(0, maxOf(0, story.lastIndex)) },
            onCompareGuides = { showGuidePicker = true },
            onBackToStory = { guideMode = false },
            onRotateGuide = { guideRotation = (guideRotation + 1) % 4 },
            techniqueContext = currentStep?.mark?.techniqueId
                ?.takeIf(String::isNotBlank)
                ?.let(view.techniqueContext::get),
            experimentDirection = currentStep?.mark?.techniqueId
                ?.takeIf(String::isNotBlank)
                ?.let { techniqueId ->
                    experimentDirections.firstOrNull {
                        it.sourceShotId == shot.id && it.techniqueId == techniqueId
                    }
                },
            onChooseExperimentDirection = { techniqueId, save ->
                onChooseExperimentDirection(shot.id, techniqueId, save)
            },
            onOpenJourney = onOpenJourney,
            onOpenExperiment = onOpenExperiment,
            readOnlySample = readOnlySample,
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
            if (readOnlySample) {
                Text(
                    "SAMPLE · ACTIONS DISABLED",
                    color = Amber,
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                )
            } else {
                PrimaryAction(if (shot.keptAt == null) "Mark as Keeper" else "Keeper · remove mark") {
                    onKeeper(shot.keptAt == null)
                }
            }
            Spacer(Modifier.height(22.dp))

            if (analysis == null) {
                AnalysisState(view, onRetry)
            } else {
                val corroborated = analysis.techniques
                    .filter(::isCorroborated)
                    .sortedWith(compareByDescending<com.shoots.app.data.TechniqueEvidenceDto> { it.agreement }.thenByDescending { it.confidence })
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
                        guideMode = false
                        story.indexOfFirst {
                            it.layer == ReviewLayer.FINDING && it.findingIndex == index
                        }.takeIf { it >= 0 }?.let { storyIndex = it }
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
                    readOnlySample = readOnlySample,
                )
            }
            if (shot.driveReviewUrl.isNotBlank()) {
                Spacer(Modifier.height(20.dp))
                SecondaryAction("Open reviewed copy in Drive") { onOpenDrive(shot.driveReviewUrl) }
            }
            if (!readOnlySample) {
                Spacer(Modifier.height(20.dp))
                SecondaryAction("This is Inspiration, not my Shot") {
                    confirmInspiration = true
                }
            }
        }
        if (!readOnlySample && confirmInspiration) {
            AlertDialog(
                onDismissRequest = { confirmInspiration = false },
                title = { Text("Move to Inspiration?") },
                text = {
                    Text(
                        "Shoots will keep the reference but stop using it in your Technique Map, " +
                            "Tendencies, Keepers, and Journey."
                    )
                },
                confirmButton = {
                    TextButton(
                        onClick = {
                            confirmInspiration = false
                            onMoveToInspiration()
                        }
                    ) { Text("Move") }
                },
                dismissButton = {
                    TextButton(onClick = { confirmInspiration = false }) {
                        Text("Keep as Shot")
                    }
                },
            )
        }
        if (showGuidePicker) {
            GuidePickerSheet(
                selected = selectedGuide,
                suggested = analysis?.composition?.guide.orEmpty(),
                onSelect = {
                    selectedGuide = it
                    guideMode = true
                    showGuidePicker = false
                },
                onDismiss = { showGuidePicker = false },
            )
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
            title = "Behind the read",
            summary = buildList {
                if (analysis.findings.isNotEmpty()) add("${analysis.findings.size} camera checks")
                if (corroborated.isNotEmpty()) add("${corroborated.size} clear choices")
            }.joinToString(" · ").ifBlank { "How Shoots read it" },
            expanded = expanded,
            onToggle = onToggle,
        )
        AnimatedVisibility(expanded) {
            Column(Modifier.fillMaxWidth().padding(top = 16.dp)) {
                if (corroborated.isEmpty()) {
                    Text(
                        "Shoots did not see a Technique clearly enough to name here.",
                        color = MutedWhite,
                        fontSize = 13.sp,
                        lineHeight = 19.sp,
                    )
                } else if (corroborated.size > 1) {
                    Text("OTHER CLEAR TECHNIQUES", color = MutedWhite, fontSize = 10.sp, fontWeight = FontWeight.Bold)
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
                    Text("CAMERA MEASUREMENTS", color = MutedWhite, fontSize = 10.sp, fontWeight = FontWeight.Bold)
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

                if (analysis.composition.moves.isNotEmpty()) {
                    Spacer(Modifier.height(17.dp))
                    LabelValue(
                        "Stored Moves",
                        analysis.composition.moves.joinToString("\n") { move ->
                            val challenge = move.challengesTechniqueIds
                                .joinToString(", ") { humanLabel(it) }
                                .takeIf { it.isNotBlank() }
                            buildString {
                                append("• ")
                                append(move.what)
                                append(" · ")
                                append(move.warrant.replace('_', ' '))
                                if (challenge != null) append(" · challenges $challenge")
                            }
                        },
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
    readOnlySample: Boolean,
) {
    val shot = view.shot
    val run = view.run
    val analysis = view.analysis
    InkCard {
        DisclosureHeader(
            title = if (readOnlySample) "Sample workflow layout" else "Run and provenance",
            summary = if (readOnlySample) {
                "Fixture · no agents ran"
            } else {
                run?.status?.let(::humanLabel).orEmpty().ifBlank { "Technical record" }
            },
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
    artifactSource: (String) -> String,
    story: List<ShotStoryStep>,
    storyIndex: Int,
    guideMode: Boolean,
    selectedGuide: String,
    guideRotation: Int,
    onPrevious: () -> Unit,
    onNext: () -> Unit,
    onSelectStory: (Int) -> Unit,
    onCompareGuides: () -> Unit,
    onBackToStory: () -> Unit,
    onRotateGuide: () -> Unit,
    techniqueContext: ShotTechniqueContextDto?,
    experimentDirection: ExperimentDirectionDto?,
    onChooseExperimentDirection: (String, Boolean) -> Unit,
    onOpenJourney: () -> Unit,
    onOpenExperiment: () -> Unit,
    readOnlySample: Boolean,
) {
    val grid = shot.grid
    val composition = analysis?.composition
    val step = story.getOrNull(storyIndex)
    val finding = analysis?.findings?.getOrNull(step?.findingIndex ?: 0)
    val layer = when {
        guideMode && selectedGuide == "none" -> ReviewLayer.CLEAN
        guideMode -> ReviewLayer.GUIDE
        else -> step?.layer ?: ReviewLayer.CLEAN
    }
    val ratio = grid
        ?.takeIf { it.width > 0 && it.height > 0 }
        ?.let { it.width.toFloat() / it.height.toFloat() }
        ?: (4f / 3f)
    val configuration = LocalConfiguration.current
    val naturalHeight = configuration.screenWidthDp / ratio
    val imageHeight = minOf(
        naturalHeight,
        (configuration.screenHeightDp - 360).coerceIn(320, 500).toFloat(),
    )
    val imageWidth = imageHeight * ratio
    var horizontalDrag by remember { mutableFloatStateOf(0f) }
    var showClean by remember(storyIndex, guideMode) { mutableStateOf(false) }
    Column(
        Modifier.fillMaxWidth().background(InkRaised),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            Modifier
                .width(imageWidth.dp)
                .height(imageHeight.dp)
                .pointerInput(storyIndex, story.size, guideMode) {
                    if (!guideMode) {
                        detectHorizontalDragGestures(
                            onDragStart = { horizontalDrag = 0f },
                            onHorizontalDrag = { _, amount -> horizontalDrag += amount },
                            onDragEnd = {
                                when {
                                    horizontalDrag < -80f -> onNext()
                                    horizontalDrag > 80f -> onPrevious()
                                }
                                horizontalDrag = 0f
                            },
                        )
                    }
                }
        ) {
            AnimatedContent(
                targetState = StoryRenderState(
                    layer,
                    step?.findingIndex ?: 0,
                    selectedGuide,
                    guideRotation,
                    step?.mark ?: VisualMarkDto(),
                    showClean,
                ),
                modifier = Modifier.fillMaxSize(),
                transitionSpec = { fadeIn(tween(150)) togetherWith fadeOut(tween(110)) },
                label = "Shot visual story",
            ) { rendered ->
                Box(Modifier.fillMaxSize()) {
                    val artifactPath = rendered.mark.visualArtifact?.blobPath.orEmpty()
                    val artifactOwnsLayer = visualArtifactOwnsLayer(rendered.mark.visualArtifact)
                    val renderedSource = when {
                        rendered.showClean -> source
                        artifactPath.isNotBlank() -> artifactSource(artifactPath)
                        rendered.layer == ReviewLayer.FINDING &&
                            finding?.findingId == "blown_highlights" &&
                            findingSource.isNotBlank() -> findingSource
                        else -> source
                    }
                    AsyncImage(
                        model = renderedSource,
                        contentDescription = if (
                            !rendered.showClean && artifactPath.isNotBlank()
                        ) {
                            "Visual evidence ${rendered.mark.visualArtifact?.label.orEmpty()}"
                        } else {
                            shot.filename
                        },
                        modifier = Modifier.fillMaxSize(),
                        contentScale = if (grid == null) ContentScale.Fit else ContentScale.FillBounds,
                    )
                    if (
                        !rendered.showClean &&
                        !artifactOwnsLayer &&
                        grid != null &&
                        composition != null
                    ) {
                        CompositionGuide(
                            grid = grid,
                            composition = composition,
                            finding = finding,
                            layer = rendered.layer,
                            guideOverride = if (guideMode) rendered.guide else null,
                            guideRotation = rendered.guideRotation,
                            storyMark = if (guideMode) null else rendered.mark,
                            modifier = Modifier.fillMaxSize(),
                        )
                    }
                    if (step != null) {
                        StoryHeader(
                            current = storyIndex,
                            total = story.size,
                            guideMode = guideMode,
                            onSelect = onSelectStory,
                            modifier = Modifier.align(Alignment.TopStart),
                        )
                    }
                }
            }
        }
        if (guideMode) {
            GuideStoryCard(
                selectedGuide = selectedGuide,
                suggestedGuide = composition?.guide.orEmpty(),
                onBackToStory = onBackToStory,
                onCompareGuides = onCompareGuides,
                onRotateGuide = onRotateGuide,
            )
        } else if (step != null) {
            VisualStoryCard(
                step = step,
                hasPrevious = storyIndex > 0,
                hasNext = storyIndex < story.lastIndex,
                onPrevious = onPrevious,
                onNext = onNext,
                onCompareGuides = onCompareGuides,
                showClean = showClean,
                onToggleClean = { showClean = !showClean },
                techniqueContext = techniqueContext,
                experimentDirection = experimentDirection,
                onChooseExperimentDirection = onChooseExperimentDirection,
                onOpenJourney = onOpenJourney,
                onOpenExperiment = onOpenExperiment,
                readOnlySample = readOnlySample,
            )
        }
    }
}

@Composable
private fun StoryHeader(
    current: Int,
    total: Int,
    guideMode: Boolean,
    onSelect: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier
            .fillMaxWidth()
            .background(Ink.copy(alpha = 0.78f))
            .padding(horizontal = 14.dp, vertical = 10.dp),
    ) {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(if (guideMode) "Compare guides" else "Visual story", color = WarmWhite, fontSize = 14.sp, fontWeight = FontWeight.Bold)
            Text(if (guideMode) "INSPECTION ONLY" else "${current + 1} of $total", color = MutedWhite, fontSize = 10.sp)
        }
        if (!guideMode && total > 1) {
            Spacer(Modifier.height(3.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(1.dp)) {
                repeat(total) { index ->
                    Box(
                        Modifier
                            .size(28.dp)
                            .clickable(role = Role.Button) { onSelect(index) }
                            .semantics {
                                stateDescription = if (index == current) "Selected" else "Not selected"
                            },
                        contentAlignment = Alignment.Center,
                    ) {
                        Box(
                            Modifier
                                .size(if (index == current) 7.dp else 6.dp)
                                .background(
                                    if (index == current) Amber else MutedWhite.copy(alpha = 0.4f),
                                    RoundedCornerShape(99.dp),
                                )
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun VisualStoryCard(
    step: ShotStoryStep,
    hasPrevious: Boolean,
    hasNext: Boolean,
    onPrevious: () -> Unit,
    onNext: () -> Unit,
    onCompareGuides: () -> Unit,
    showClean: Boolean,
    onToggleClean: () -> Unit,
    techniqueContext: ShotTechniqueContextDto?,
    experimentDirection: ExperimentDirectionDto?,
    onChooseExperimentDirection: (String, Boolean) -> Unit,
    onOpenJourney: () -> Unit,
    onOpenExperiment: () -> Unit,
    readOnlySample: Boolean,
) {
    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 13.dp)) {
        val labelColour = when (step.layer) {
            ReviewLayer.FINDING -> FindingRed
            ReviewLayer.ACTION -> Amber
            else -> MutedWhite
        }
        Text(step.label, color = labelColour, fontSize = 10.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(4.dp))
        Text(step.title, color = WarmWhite, fontSize = 18.sp, lineHeight = 22.sp, fontWeight = FontWeight.Bold)
        if (step.body.isNotBlank()) {
            Spacer(Modifier.height(4.dp))
            Text(
                step.body,
                color = MutedWhite,
                fontSize = 12.sp,
                lineHeight = 17.sp,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
        techniqueContext?.let { context ->
            Spacer(Modifier.height(9.dp))
            Text(
                techniqueHistoryLine(context),
                color = WarmWhite,
                fontSize = 12.sp,
                lineHeight = 17.sp,
                fontWeight = FontWeight.SemiBold,
            )
            Text(repeatabilityLine(context), color = if (context.criteriaMetSessions > 0) Amber else MutedWhite, fontSize = 11.sp, lineHeight = 16.sp)
            when {
                readOnlySample -> {
                    Text(
                        "Sample layout only. No Keeper or Experiment can be saved.",
                        color = MutedWhite,
                        fontSize = 10.sp,
                        lineHeight = 14.sp,
                    )
                }
                context.reproduceSessions > 0 -> {
                    TextButton(onClick = onOpenJourney) { Text("See where it appears again") }
                }
                experimentDirection?.state == "started" -> {
                    TextButton(onClick = onOpenExperiment) { Text("Open Experiment") }
                }
                experimentDirection?.state == "saved" -> {
                    Spacer(Modifier.height(9.dp))
                    Text("SAVED FOR ANOTHER DAY", color = Amber, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                    Text(
                        experimentDirection.question,
                        color = WarmWhite,
                        fontSize = 13.sp,
                        lineHeight = 18.sp,
                    )
                    Text("Nothing has started yet.", color = MutedWhite, fontSize = 10.sp)
                    TextButton(
                        onClick = { onChooseExperimentDirection(context.techniqueId, false) },
                    ) { Text("Delete saved question") }
                }
                experimentDirection?.state == "left" -> {
                    Text(
                        "You left this question. No Experiment was created.",
                        color = MutedWhite,
                        fontSize = 10.sp,
                        lineHeight = 14.sp,
                    )
                }
                context.positiveKeeperShots > 0 -> {
                    Spacer(Modifier.height(9.dp))
                    Text("A QUESTION FOR ANOTHER DAY", color = Amber, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                    Text(
                        "Want to try this same choice in a different Scene?",
                        color = WarmWhite,
                        fontSize = 13.sp,
                        lineHeight = 18.sp,
                    )
                    Spacer(Modifier.height(8.dp))
                    PrimaryAction("Try another day") {
                        onChooseExperimentDirection(context.techniqueId, true)
                    }
                    TextButton(
                        onClick = { onChooseExperimentDirection(context.techniqueId, false) },
                        modifier = Modifier.align(Alignment.CenterHorizontally),
                    ) { Text("Leave it", color = MutedWhite) }
                }
                else -> {
                    Text(
                        "Mark a Keeper if this is a choice you may want to try again.",
                        color = MutedWhite,
                        fontSize = 10.sp,
                        lineHeight = 14.sp,
                    )
                }
            }
        }
        step.mark.visualArtifact?.takeIf { it.status != "unresolved" }?.let { artifact ->
            Spacer(Modifier.height(7.dp))
            val authorityLine = buildList {
                add(humanLabel(artifact.authority))
                if (
                    artifact.verification != "not_run" &&
                    artifact.verification != artifact.authority
                ) add(humanLabel(artifact.verification))
            }.joinToString(" · ")
            Text(
                "$authorityLine · ${artifact.label}",
                color = WarmWhite,
                fontSize = 11.sp,
                fontWeight = FontWeight.SemiBold,
            )
            if (artifact.legend.isNotBlank()) {
                Text(
                    artifact.legend,
                    color = MutedWhite,
                    fontSize = 10.sp,
                    lineHeight = 14.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            if (artifact.metrics.isNotEmpty()) {
                Text(
                    artifact.metrics.entries.take(3).joinToString(" · ") { (key, value) ->
                        "${metricLabel(key)} ${value.toString().trim('"')}"
                    },
                    color = MutedWhite,
                    fontSize = 10.sp,
                    lineHeight = 14.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
        Spacer(Modifier.height(8.dp))
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            TextButton(onClick = onPrevious, enabled = hasPrevious, modifier = Modifier.weight(1f)) {
                Text("Previous")
            }
            TextButton(onClick = onToggleClean, modifier = Modifier.weight(1.4f)) {
                Text(if (showClean) "Show visual" else "See clean")
            }
            TextButton(onClick = onNext, enabled = hasNext, modifier = Modifier.weight(1f)) {
                Text(if (hasNext) "Next" else "End")
            }
        }
        TextButton(onClick = onCompareGuides, modifier = Modifier.align(Alignment.CenterHorizontally)) {
            Text("Compare guides")
        }
    }
}

private fun techniqueHistoryLine(context: ShotTechniqueContextDto): String {
    val keepers = context.positiveKeeperShots.takeIf { it > 0 }?.let {
        " $it ${if (it == 1) "Keeper is" else "Keepers are"} part of that."
    }.orEmpty()
    return when (context.corroboratedShots) {
        0 -> "Shoots has not seen this clearly in another Shot yet.$keepers"
        1 -> "This is the first clear sighting in your Shoots record.$keepers"
        2 -> "Shoots has seen this clearly in 2 Shots. It becomes recurring at 3.$keepers"
        else -> buildList {
            add("Shoots has seen this clearly in ${context.corroboratedShots} Shots")
            if (context.distinctShoots > 0) {
                add("from ${context.distinctShoots} ${if (context.distinctShoots == 1) "Shoot" else "Shoots"}")
            }
        }.joinToString(" ") + "." + keepers
    }
}

private fun repeatabilityLine(context: ShotTechniqueContextDto): String = when {
    context.reproduceSessions == 0 -> "You have not tried to repeat this on purpose yet."
    context.evaluableReproduceSessions == 0 ->
        "You tried this in ${context.reproduceSessions} ${if (context.reproduceSessions == 1) "session" else "sessions"}, but none could be checked."
    context.criteriaMetSessions == 0 ->
        "${context.evaluableReproduceSessions} ${if (context.evaluableReproduceSessions == 1) "session was" else "sessions were"} checked. None matched every check yet."
    else ->
        "${context.criteriaMetSessions} of ${context.evaluableReproduceSessions} checked ${if (context.evaluableReproduceSessions == 1) "session" else "sessions"} matched what you set before shooting."
}

private fun metricLabel(key: String): String = when (key) {
    "mean_luma" -> "average brightness"
    "p05_luma" -> "darkest areas"
    "p95_luma" -> "brightest areas"
    "mean_saturation_pct" -> "average saturation"
    "p95_saturation_pct" -> "strongest saturation"
    "clipped_highlights_pct" -> "pure white"
    "colour_temperature_k" -> "colour temperature"
    else -> humanLabel(key)
}

@Composable
private fun GuideStoryCard(
    selectedGuide: String,
    suggestedGuide: String,
    onBackToStory: () -> Unit,
    onCompareGuides: () -> Unit,
    onRotateGuide: () -> Unit,
) {
    Column(Modifier.fillMaxWidth().padding(16.dp)) {
        Text("COMPARE THE FRAME", color = Amber, fontSize = 10.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(6.dp))
        Text(
            if (selectedGuide == "none") "No guide" else guideLabel(selectedGuide),
            color = WarmWhite,
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold,
        )
        Spacer(Modifier.height(6.dp))
        Text(
            if (selectedGuide == suggestedGuide && suggestedGuide.isNotBlank()) {
                "Shoots suggested this guide from how it read the Shot."
            } else {
                "This guide is only for looking. It will not change Shoots' read."
            },
            color = MutedWhite,
            fontSize = 13.sp,
            lineHeight = 19.sp,
        )
        Spacer(Modifier.height(13.dp))
        if (selectedGuide == "golden_spiral") {
            SecondaryAction("Rotate spiral", onClick = onRotateGuide)
            Spacer(Modifier.height(8.dp))
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            TextButton(onClick = onBackToStory, modifier = Modifier.weight(1f)) { Text("Back to story") }
            TextButton(onClick = onCompareGuides, modifier = Modifier.weight(1f)) { Text("Change guide") }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun GuidePickerSheet(
    selected: String,
    suggested: String,
    onSelect: (String) -> Unit,
    onDismiss: () -> Unit,
) {
    val options = listOf(
        "none" to "No guide",
        "thirds" to "Rule of thirds",
        "phi" to "Phi grid",
        "golden_spiral" to "Golden spiral",
        "diagonals" to "Diagonals",
        "centre" to "Centre",
    )
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        containerColor = InkRaised,
    ) {
        Column(Modifier.fillMaxWidth().padding(bottom = 24.dp)) {
            Text("Choose a guide", color = WarmWhite, fontSize = 20.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(horizontal = 20.dp, vertical = 12.dp))
            Text("Try a guide without changing Shoots' read.", color = MutedWhite, fontSize = 13.sp, modifier = Modifier.padding(horizontal = 20.dp).padding(bottom = 10.dp))
            options.forEachIndexed { index, (id, label) ->
                Row(
                    Modifier
                        .fillMaxWidth()
                        .clickable(role = Role.Button) { onSelect(id) }
                        .padding(horizontal = 20.dp, vertical = 15.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(Modifier.weight(1f)) {
                        Text(label, color = if (selected == id) Amber else WarmWhite, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
                        if (suggested == id) Text("Shoots suggests", color = MutedWhite, fontSize = 10.sp)
                    }
                    if (selected == id) Text("Selected", color = Amber, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                }
                if (index < options.lastIndex) HorizontalDivider(color = Hairline)
            }
        }
    }
}

private data class StoryRenderState(
    val layer: ReviewLayer,
    val findingIndex: Int,
    val guide: String,
    val guideRotation: Int,
    val mark: VisualMarkDto,
    val showClean: Boolean,
)

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
