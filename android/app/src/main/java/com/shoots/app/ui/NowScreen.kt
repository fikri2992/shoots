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
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
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
import com.shoots.app.data.ExperimentDirectionDto
import com.shoots.app.data.InterventionRecordDto
import com.shoots.app.data.MobileSnapshotDto
import com.shoots.app.data.ShootDto
import com.shoots.app.data.ShootRecordDto
import com.shoots.app.data.ScoutAnswerDto
import com.shoots.app.data.ScoutRecommendationOptionDto
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
    onOpenShots: () -> Unit,
    onOpenShootRecord: (String, Int) -> Unit = { _, _ -> },
    onOpenExperiments: () -> Unit,
    onStartSavedDirection: (String) -> Unit,
    onLeaveSavedDirection: (String, String) -> Unit,
    onRespondScoutRecommendation: (String, Int, String, String) -> Unit = { _, _, _, _ -> },
    onOpenSettings: () -> Unit,
    availableShots: List<ShotDto> = snapshot?.recentShots.orEmpty(),
) {
    val allShots = (snapshot?.recentShots.orEmpty() + availableShots).distinctBy(ShotDto::id)
    val active = localSession?.takeIf { it.state in ACTIVE_SESSION_STATES }
    val latest = snapshot?.recentShots?.firstOrNull()
    val latestView = snapshot?.latestShot
    val latestShoot = snapshot?.latestShoot
    val readOnlySample = snapshot?.user?.recordMode == "sample"
    val savedDirection = snapshot?.experimentDirections?.firstOrNull { it.state == "saved" }
    val directionSource = savedDirection?.let { direction ->
        allShots.firstOrNull { it.id == direction.sourceShotId }
    }
    val latestRecord = snapshot?.latestShootRecord?.takeIf { record ->
        latestShoot == null || (
            latestShoot.status == "settled" &&
                record.shootId == latestShoot.id &&
                record.revision == latestShoot.currentRecordRevision
            )
    }
    val latestIntervention = latestRecord?.let { record ->
        snapshot?.recentInterventions?.firstOrNull {
            it.shootId == record.shootId && it.shootRevision == record.revision
        }
    }
    val focus = when {
        readOnlySample && latestRecord != null -> "sample-receipt"
        active != null -> "session"
        latestShoot?.status in setOf("open", "closing") -> "shoot-processing"
        snapshot?.openExperiment == null && savedDirection != null -> "saved-direction"
        latestRecord != null -> "shoot-receipt"
        latestView?.analysis != null -> "legacy-insight"
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
        NowHeader(snapshot, onOpenSettings, readOnlySample)
        Spacer(Modifier.height(26.dp))

        AnimatedContent(
            targetState = focus,
            transitionSpec = { fadeIn(tween(180)) togetherWith fadeOut(tween(120)) },
            label = "Now focus",
        ) { state ->
            when (state) {
                "sample-receipt" -> SampleShootReceiptHero(
                    record = requireNotNull(latestRecord),
                    onOpenShots = onOpenShots,
                    onOpenShootRecord = onOpenShootRecord,
                )
                "session" -> CaptureSessionCard(
                    session = requireNotNull(active),
                    busy = busy,
                    onContinue = onContinueSession,
                    onFinish = onFinishSession,
                    onCancel = onCancelSession,
                    onImportAsFree = onImportSessionAsFree,
                )
                "shoot-processing" -> ShootProcessingHero(
                    shoot = requireNotNull(latestShoot),
                    lastSyncedAt = source?.lastSuccessfulSyncAt.orEmpty(),
                    onOpenCamera = onOpenFreeCamera,
                    onOpenShots = onOpenShots,
                )
                "saved-direction" -> SavedDirectionHero(
                    direction = requireNotNull(savedDirection),
                    sourceShot = directionSource,
                    imageUrl = imageUrl,
                    busy = busy,
                    onTryToday = onStartSavedDirection,
                    onShootFreely = onOpenFreeCamera,
                    onLeave = onLeaveSavedDirection,
                    onOpenShot = onOpenShot,
                )
                "shoot-receipt" -> ShootReceiptHero(
                    record = requireNotNull(latestRecord),
                    answer = snapshot?.recentScoutAnswers?.firstOrNull {
                        it.shootId == latestRecord.shootId && it.shootRevision == latestRecord.revision
                    },
                    intervention = latestIntervention,
                    members = allShots.filter { it.id in latestRecord.shotIds },
                    imageUrl = imageUrl,
                    busy = busy,
                    lastSyncedAt = source?.lastSuccessfulSyncAt.orEmpty(),
                    onOpenShots = onOpenShots,
                    onOpenShot = onOpenShot,
                    onOpenShootRecord = onOpenShootRecord,
                    onOpenExperiments = onOpenExperiments,
                    onRespondRecommendation = onRespondScoutRecommendation,
                )
                "legacy-insight" -> LatestInsightHero(
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

        snapshot?.openExperiment?.takeIf { !readOnlySample && it.canStartReproduce }?.let { experiment ->
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

        if (focus == "shoot-processing" || (focus == "camera" && latest != null)) {
            Spacer(Modifier.height(26.dp))
            SectionTitle("From your last Shot")
            Spacer(Modifier.height(10.dp))
            latest?.let { shot ->
                LatestShotReceipt(shot, imageUrl(shot)) { onOpenShot(shot.id) }
            }
        }
    }
}

@Composable
private fun SampleShootReceiptHero(
    record: ShootRecordDto,
    onOpenShots: () -> Unit,
    onOpenShootRecord: (String, Int) -> Unit,
) {
    val receipt = record.receipt
    Column(
        Modifier
            .fillMaxWidth()
            .background(InkRaised, RoundedCornerShape(24.dp))
            .border(1.dp, Hairline, RoundedCornerShape(24.dp))
            .padding(20.dp),
    ) {
        Text("SAMPLE SHOOT LAYOUT", color = Amber, fontSize = 10.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(9.dp))
        Text(
            "${receipt.shotCount} Shot cards across ${receipt.sceneCount} sample Scene groups.",
            color = WarmWhite,
            fontSize = 23.sp,
            lineHeight = 29.sp,
            fontWeight = FontWeight.Bold,
        )
        Spacer(Modifier.height(9.dp))
        Text(
            "These values were hand-authored. No ingestion, Analysis, grouping, settlement, or Scout decision ran.",
            color = MutedWhite,
            fontSize = 14.sp,
            lineHeight = 20.sp,
        )
        Spacer(Modifier.height(16.dp))
        PrimaryAction("Open Sample Shoot Record") {
            onOpenShootRecord(record.shootId, record.revision)
        }
        Spacer(Modifier.height(8.dp))
        SecondaryAction("Inspect Sample Shots", onClick = onOpenShots)
        Text(
            "READ ONLY · KEEPER AND EXPERIMENT ACTIONS DISABLED",
            color = MutedWhite,
            fontSize = 9.sp,
            modifier = Modifier.align(Alignment.CenterHorizontally).padding(top = 10.dp),
        )
    }
}

@Composable
private fun SavedDirectionHero(
    direction: ExperimentDirectionDto,
    sourceShot: ShotDto?,
    imageUrl: (ShotDto) -> String,
    busy: Boolean,
    onTryToday: (String) -> Unit,
    onShootFreely: () -> Unit,
    onLeave: (String, String) -> Unit,
    onOpenShot: (String) -> Unit,
) {
    Column(
        Modifier
            .fillMaxWidth()
            .background(InkRaised, RoundedCornerShape(24.dp))
            .border(1.dp, Hairline, RoundedCornerShape(24.dp))
            .padding(18.dp),
    ) {
        Text("BEFORE OPENING THE CAMERA", color = Amber, fontSize = 10.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(7.dp))
        Text(
            "Does this question fit today?",
            color = WarmWhite,
            fontSize = 25.sp,
            lineHeight = 29.sp,
            fontWeight = FontWeight.Bold,
        )
        Spacer(Modifier.height(7.dp))
        Text("Try it, or shoot normally. Neither choice is a failure.", color = MutedWhite, fontSize = 13.sp, lineHeight = 19.sp)
        Spacer(Modifier.height(16.dp))
        Row(
            Modifier
                .fillMaxWidth()
                .background(InkSoft, RoundedCornerShape(18.dp))
                .border(1.dp, Hairline, RoundedCornerShape(18.dp))
                .then(
                    if (sourceShot == null) Modifier else Modifier.clickable(role = Role.Button) {
                        onOpenShot(sourceShot.id)
                    },
                ),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (sourceShot != null) {
                AsyncImage(
                    model = imageUrl(sourceShot),
                    contentDescription = "Source Shot for saved question",
                    modifier = Modifier.size(94.dp).clip(RoundedCornerShape(topStart = 18.dp, bottomStart = 18.dp)),
                    contentScale = ContentScale.Crop,
                )
            }
            Column(Modifier.weight(1f).padding(14.dp)) {
                Text("SAVED QUESTION", color = MutedWhite, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(5.dp))
                Text(direction.question, color = WarmWhite, fontSize = 14.sp, lineHeight = 19.sp)
                Spacer(Modifier.height(5.dp))
                Text(
                    "Shoots saw this clearly in ${direction.corroboratedShots} Shots across ${direction.distinctShoots} Shoots.",
                    color = MutedWhite,
                    fontSize = 10.sp,
                )
            }
        }
        Spacer(Modifier.height(16.dp))
        PrimaryAction("Try it today", enabled = !busy) { onTryToday(direction.id) }
        Spacer(Modifier.height(9.dp))
        SecondaryAction("Shoot freely", enabled = !busy, onClick = onShootFreely)
        Text(
            "Only Try it today creates an Experiment.",
            color = MutedWhite,
            fontSize = 10.sp,
            modifier = Modifier.align(Alignment.CenterHorizontally).padding(top = 10.dp),
        )
        TextButton(
            onClick = { onLeave(direction.sourceShotId, direction.techniqueId) },
            enabled = !busy,
            modifier = Modifier.align(Alignment.CenterHorizontally),
        ) { Text("Delete saved question", color = MutedWhite) }
    }
}

@Composable
private fun ShootProcessingHero(
    shoot: ShootDto,
    lastSyncedAt: String,
    onOpenCamera: () -> Unit,
    onOpenShots: () -> Unit,
) {
    val shots = shoot.orderedShotIds.size
    val scenes = shoot.orderedSceneIds.size
    Column(
        Modifier
            .fillMaxWidth()
            .background(InkRaised, RoundedCornerShape(24.dp))
            .border(1.dp, Hairline, RoundedCornerShape(24.dp))
            .padding(20.dp),
    ) {
        Text("THIS SHOOT", color = MutedWhite, fontSize = 10.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(9.dp))
        Text(
            if (shoot.status == "closing") "Finishing this Shoot."
            else "Still watching this Shoot.",
            color = WarmWhite,
            fontSize = 24.sp,
            lineHeight = 29.sp,
            fontWeight = FontWeight.Bold,
        )
        Spacer(Modifier.height(9.dp))
        Text(
            "$shots ${countLabel(shots, "Shot")} across $scenes ${countLabel(scenes, "Scene")}. " +
                if (shoot.status == "closing") {
                    "Your summary appears after Shoots finishes reading every Shot."
                } else {
                    "New Camera media may still join it."
                },
            color = MutedWhite,
            fontSize = 14.sp,
            lineHeight = 20.sp,
        )
        Spacer(Modifier.height(15.dp))
        WorkflowStageStrip(settled = false, closing = shoot.status == "closing")
        Spacer(Modifier.height(19.dp))
        if (shoot.status == "open") {
            PrimaryAction("Keep shooting", onClick = onOpenCamera)
            Spacer(Modifier.height(8.dp))
        }
        SecondaryAction("Open Shots", onClick = onOpenShots)
        SyncedLabel(lastSyncedAt)
    }
}

@Composable
private fun ShootReceiptHero(
    record: ShootRecordDto,
    answer: ScoutAnswerDto?,
    intervention: InterventionRecordDto?,
    members: List<ShotDto>,
    imageUrl: (ShotDto) -> String,
    busy: Boolean,
    lastSyncedAt: String,
    onOpenShots: () -> Unit,
    onOpenShot: (String) -> Unit,
    onOpenShootRecord: (String, Int) -> Unit,
    onOpenExperiments: () -> Unit,
    onRespondRecommendation: (String, Int, String, String) -> Unit,
) {
    var expanded by rememberSaveable(record.shootId, record.revision) { mutableStateOf(false) }
    val receipt = record.receipt
    val lead = receipt.repeated.firstOrNull()
        ?: receipt.varied.firstOrNull()
            ?: "Every Shot from this outing is here."
    Column(
        Modifier
            .fillMaxWidth()
            .background(InkRaised, RoundedCornerShape(24.dp))
            .border(1.dp, Hairline, RoundedCornerShape(24.dp))
            .padding(20.dp),
    ) {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("YOUR SHOOT", color = MutedWhite, fontSize = 10.sp, fontWeight = FontWeight.Bold)
            Text(
                "${receipt.sceneCount} ${countLabel(receipt.sceneCount, "Scene")} · " +
                    "${receipt.shotCount} ${countLabel(receipt.shotCount, "Shot")}",
                color = MutedWhite,
                fontSize = 11.sp,
            )
        }
        Spacer(Modifier.height(10.dp))
        Text(
            lead,
            color = WarmWhite,
            fontSize = 23.sp,
            lineHeight = 29.sp,
            fontWeight = FontWeight.Bold,
        )
        val secondary = receipt.varied.firstOrNull { it != lead }
            ?: receipt.repeated.drop(1).firstOrNull()
        if (!secondary.isNullOrBlank()) {
            Spacer(Modifier.height(9.dp))
            Text(secondary, color = MutedWhite, fontSize = 14.sp, lineHeight = 20.sp)
        }
        Spacer(Modifier.height(15.dp))
        WorkflowStageStrip(settled = true, closing = true)
        Spacer(Modifier.height(16.dp))
        val recommendationResolved = intervention?.experimentId?.isNotBlank() == true ||
            intervention?.attemptState in setOf("accepted", "entered", "left", "completed")
        val recommendationOptions = recommendationOptions(record)
        when {
            record.scout.route in setOf("recommend", "ask") &&
                answer == null && !recommendationResolved && recommendationOptions.isNotEmpty() -> {
                ScoutRecommendationBlock(
                    record = record,
                    options = recommendationOptions,
                    members = members,
                    imageUrl = imageUrl,
                    busy = busy,
                    onOpenShot = onOpenShot,
                    onRespond = onRespondRecommendation,
                )
            }
            record.scout.route in setOf("recommend", "ask") &&
                answer == null && recommendationResolved -> {
                Text(
                    intervention?.outcomeReason.orEmpty().ifBlank {
                        "Shoots left this recommendation open without guessing your intent."
                    },
                    color = MutedWhite,
                    fontSize = 14.sp,
                    lineHeight = 20.sp,
                )
                if (intervention?.experimentId?.isNotBlank() == true) {
                    Spacer(Modifier.height(10.dp))
                    PrimaryAction("Open Experiment", onClick = onOpenExperiments)
                }
            }
            record.scout.route == "reproduce" -> {
                Text(
                    "EXPERIMENT OFFERED FROM YOUR KEEPER",
                    color = Amber,
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(Modifier.height(8.dp))
                PrimaryAction("Open Experiment", onClick = onOpenExperiments)
                Spacer(Modifier.height(8.dp))
                SecondaryAction("Open Shots", onClick = onOpenShots)
            }
            record.scout.route == "explain" -> PrimaryAction("Open Shots", onClick = onOpenShots)
            record.scout.route == "ask" -> {
                if (answer != null) {
                    Text(answer.detail, color = MutedWhite, fontSize = 14.sp, lineHeight = 20.sp)
                    Spacer(Modifier.height(10.dp))
                    if (answer.experimentId.isNotBlank()) {
                        PrimaryAction("Open your Explore", onClick = onOpenExperiments)
                    } else {
                        SecondaryAction("Open Shots", onClick = onOpenShots)
                    }
                } else {
                    Text(
                        "Shoots could not support one useful recommendation from this Shoot, so it stopped.",
                        color = MutedWhite,
                        fontSize = 14.sp,
                        lineHeight = 20.sp,
                    )
                    Spacer(Modifier.height(10.dp))
                    SecondaryAction("Open Shots", onClick = onOpenShots)
                }
            }
            else -> SecondaryAction("Open Shots", onClick = onOpenShots)
        }
        Spacer(Modifier.height(10.dp))
        SecondaryAction("Open full Shoot Record") {
            onOpenShootRecord(record.shootId, record.revision)
        }
        val hasDetails = receipt.repeated.size + receipt.varied.size > 1 ||
            receipt.blindSpots.isNotEmpty() || receipt.techniques.isNotEmpty()
        if (hasDetails) {
            Spacer(Modifier.height(12.dp))
            Text(
                if (expanded) "Hide evidence" else "Show evidence",
                color = Amber,
                fontSize = 13.sp,
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier
                    .semantics { contentDescription = if (expanded) "Hide Shoot evidence" else "Show Shoot evidence" }
                    .clickable(role = Role.Button) { expanded = !expanded }
                    .padding(vertical = 6.dp),
            )
            AnimatedVisibility(visible = expanded) {
                Column {
                    receipt.repeated.drop(1).forEach { EvidenceLine("Repeated", it) }
                    receipt.varied.filter { it != secondary }.forEach { EvidenceLine("Varied", it) }
                    receipt.techniques.filter { it.corroboratedShotIds.isNotEmpty() }.forEach {
                        EvidenceLine(
                            "Shoots' visual read",
                            "${it.name} appeared clearly in ${it.corroboratedShotIds.size} " +
                                countLabel(it.corroboratedShotIds.size, "Shot") + ".",
                        )
                    }
                    receipt.blindSpots.forEach { EvidenceLine("Could not read", it) }
                }
            }
        }
        SyncedLabel(lastSyncedAt)
    }
}

@Composable
private fun WorkflowStageStrip(settled: Boolean, closing: Boolean) {
    val completed = when {
        settled -> 4
        closing -> 1
        else -> 0
    }
    val current = when {
        settled -> -1
        closing -> 1
        else -> 0
    }
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(5.dp)) {
        listOf("Collected", "Read", "Grouped", "Settled").forEachIndexed { index, label ->
            Column(Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                Box(
                    Modifier
                        .size(8.dp)
                        .background(
                            when {
                                index < completed -> Amber
                                index == current -> MutedWhite
                                else -> Hairline
                            },
                            CircleShape,
                        ),
                )
                Spacer(Modifier.height(5.dp))
                Text(
                    when {
                        index != current -> label
                        index == 0 -> "Collecting…"
                        index == 1 -> "Reading…"
                        else -> "$label…"
                    },
                    color = if (index < completed || index == current) WarmWhite else MutedWhite,
                    fontSize = 9.sp,
                    maxLines = 1,
                )
            }
        }
    }
}

@Composable
private fun ScoutRecommendationBlock(
    record: ShootRecordDto,
    options: List<ScoutRecommendationOptionDto>,
    members: List<ShotDto>,
    imageUrl: (ShotDto) -> String,
    busy: Boolean,
    onOpenShot: (String) -> Unit,
    onRespond: (String, Int, String, String) -> Unit,
) {
    val primaryIndex = options.indexOfFirst { it.id == record.scout.recommendation.primaryOptionId }
        .takeIf { it >= 0 }
        ?: 0
    var optionIndex by rememberSaveable(record.shootId, record.revision) {
        mutableIntStateOf(primaryIndex)
    }
    var tuneOpen by rememberSaveable(record.shootId, record.revision, "tune") {
        mutableStateOf(false)
    }
    val option = options[optionIndex.coerceIn(options.indices)]
    val evidenceIds = (listOf(option.referenceShotId) + option.warrantShotIds)
        .filter(String::isNotBlank)
        .distinct()
    val evidence = evidenceIds.mapNotNull { id -> members.firstOrNull { it.id == id } }.take(3)
    val evidenceCount = option.warrantShotIds.distinct().size
    val evidenceCopy = if (evidenceCount > 0) {
        "It appeared clearly in $evidenceCount ${countLabel(evidenceCount, "Shot")}"
    } else {
        "Shoots stored supporting evidence for this direction"
    }

    Spacer(Modifier.height(15.dp))
    evidence.firstOrNull()?.let { shot ->
        Box(
            Modifier
                .fillMaxWidth()
                .height(210.dp)
                .clip(RoundedCornerShape(18.dp))
                .background(InkSoft)
                .clickable(role = Role.Button) { onOpenShot(shot.id) },
        ) {
            AsyncImage(
                model = imageUrl(shot),
                contentDescription = "Supporting Shot for ${option.techniqueName}",
                modifier = Modifier.fillMaxSize(),
                contentScale = ContentScale.Crop,
            )
            Text(
                "Open supporting Shot · $evidenceCount ${countLabel(evidenceCount, "Shot")}",
                color = WarmWhite,
                fontSize = 11.sp,
                modifier = Modifier
                    .align(Alignment.BottomStart)
                    .fillMaxWidth()
                    .background(Ink.copy(alpha = 0.8f))
                    .padding(10.dp),
            )
        }
    }
    if (evidence.size > 1) {
        Spacer(Modifier.height(8.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            evidence.drop(1).forEach { shot ->
                AsyncImage(
                    model = imageUrl(shot),
                    contentDescription = "Another supporting Shot",
                    modifier = Modifier
                        .size(66.dp)
                        .clip(RoundedCornerShape(11.dp))
                        .clickable(role = Role.Button) { onOpenShot(shot.id) },
                    contentScale = ContentScale.Crop,
                )
            }
        }
    }
    Spacer(Modifier.height(16.dp))
    Text("ONE IDEA FOR YOUR NEXT OUTING", color = Amber, fontSize = 10.sp, fontWeight = FontWeight.Bold)
    Spacer(Modifier.height(7.dp))
    Text(option.title, color = WarmWhite, fontSize = 22.sp, lineHeight = 28.sp, fontWeight = FontWeight.Bold)
    Spacer(Modifier.height(8.dp))
    Text(option.whyNow, color = MutedWhite, fontSize = 14.sp, lineHeight = 20.sp)
    Spacer(Modifier.height(12.dp))
    Text(
        "$evidenceCopy. This is a recommendation, not a claim about what you intended.",
        color = MutedWhite,
        fontSize = 12.sp,
        lineHeight = 18.sp,
    )
    Spacer(Modifier.height(16.dp))
    PrimaryAction("Try this Experiment", enabled = !busy) {
        onRespond(record.shootId, record.revision, "accept", option.id)
    }
    if (options.size > 1) {
        Spacer(Modifier.height(8.dp))
        SecondaryAction("Show another idea", enabled = !busy) {
            optionIndex = (optionIndex + 1) % options.size
            tuneOpen = false
        }
    }
    TextButton(
        onClick = { onRespond(record.shootId, record.revision, "not_today", "") },
        enabled = !busy,
        modifier = Modifier.fillMaxWidth(),
    ) { Text("Not today", color = MutedWhite) }
    TextButton(
        onClick = { tuneOpen = !tuneOpen },
        modifier = Modifier.fillMaxWidth(),
    ) { Text(if (tuneOpen) "Close" else "Help Shoots understand", color = MutedWhite) }
    AnimatedVisibility(tuneOpen) {
        Column(
            Modifier
                .fillMaxWidth()
                .background(InkSoft, RoundedCornerShape(14.dp))
                .padding(12.dp),
        ) {
            Text(
                "Only answer if it helps. You do not need to classify your Shoot.",
                color = MutedWhite,
                fontSize = 12.sp,
                lineHeight = 17.sp,
            )
            Spacer(Modifier.height(8.dp))
            SecondaryAction("I was just shooting", enabled = !busy) {
                onRespond(record.shootId, record.revision, "just_shooting", "")
            }
        }
    }
}

private fun recommendationOptions(record: ShootRecordDto): List<ScoutRecommendationOptionDto> {
    val stored = record.scout.recommendation.options
    if (stored.isNotEmpty()) return stored
    return record.scout.question.options
        .filter { it.techniqueId.isNotBlank() }
        .map { legacy ->
            val warrant = record.scout.warrant.firstOrNull { it.techniqueId == legacy.techniqueId }
            val ids = warrant?.shotIds.orEmpty()
            val count = ids.distinct().size
            ScoutRecommendationOptionDto(
                id = "explore_${legacy.techniqueId}",
                techniqueId = legacy.techniqueId,
                techniqueName = legacy.label,
                experimentType = "explore",
                title = "Try ${legacy.label} on purpose",
                whyNow = "$count ${countLabel(count, "Shot")} in this Shoot showed ${legacy.label}. " +
                    "Try that choice on purpose in a different Scene.",
                warrantShotIds = ids,
                referenceShotId = warrant?.referenceShotId.orEmpty(),
            )
        }
        .sortedWith(compareByDescending<ScoutRecommendationOptionDto> { it.warrantShotIds.distinct().size }
            .thenBy { it.techniqueId })
}

@Composable
private fun EvidenceLine(label: String, value: String) {
    Spacer(Modifier.height(13.dp))
    Text(label.uppercase(), color = MutedWhite, fontSize = 9.sp, fontWeight = FontWeight.Bold)
    Spacer(Modifier.height(3.dp))
    Text(value, color = WarmWhite, fontSize = 13.sp, lineHeight = 18.sp)
}

@Composable
private fun SyncedLabel(value: String) {
    if (value.isBlank()) return
    Spacer(Modifier.height(14.dp))
    Text("Last synced ${displayTime(value)}", color = MutedWhite, fontSize = 10.sp)
}

private fun countLabel(count: Int, noun: String): String = if (count == 1) noun else "${noun}s"

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
private fun NowHeader(
    snapshot: MobileSnapshotDto?,
    onOpenSettings: () -> Unit,
    readOnlySample: Boolean,
) {
    val name = snapshot?.user?.name.orEmpty().trim().substringBefore(' ').ifBlank { "there" }
    Row(
        Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column {
            Text("SHOOTS", color = Amber, fontSize = 11.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(4.dp))
            Text(
                if (readOnlySample) "Sample Record · read only." else "Ready when you are, $name.",
                color = WarmWhite,
                fontSize = 23.sp,
                lineHeight = 28.sp,
                fontWeight = FontWeight.Bold,
            )
        }
        if (readOnlySample) {
            Text("FIXTURE", color = Amber, fontSize = 10.sp, fontWeight = FontWeight.Bold)
        } else {
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
