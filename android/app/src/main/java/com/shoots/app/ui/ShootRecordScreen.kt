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
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.shoots.app.Amber
import com.shoots.app.Hairline
import com.shoots.app.Ink
import com.shoots.app.InkRaised
import com.shoots.app.InkSoft
import com.shoots.app.MutedWhite
import com.shoots.app.WarmWhite
import com.shoots.app.data.InterventionRecordDto
import com.shoots.app.data.ScoutAnswerDto
import com.shoots.app.data.ShootDto
import com.shoots.app.data.ShootRecordDto
import com.shoots.app.data.ShotDto

@Composable
fun ShootRecordScreen(
    record: ShootRecordDto?,
    shoot: ShootDto?,
    shots: List<ShotDto>,
    interventions: List<InterventionRecordDto>,
    answers: List<ScoutAnswerDto>,
    imageUrl: (ShotDto) -> String,
    onBack: () -> Unit,
    onShot: (String) -> Unit,
    onKeeper: (String, Boolean) -> Unit,
    readOnlySample: Boolean = false,
    loading: Boolean = false,
) {
    Column(
        Modifier
            .fillMaxSize()
            .background(Ink)
            .statusBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(bottom = 44.dp),
    ) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            BackAction("Now", onBack)
            StatusPill(if (readOnlySample) "sample" else "settled", amber = !readOnlySample)
        }
        if (record == null) {
            Column(Modifier.padding(20.dp)) {
                ScreenTitle(
                    "Shoot Record",
                    if (loading) "Loading the Shoot Record…" else "A newer version is available.",
                )
                Spacer(Modifier.height(8.dp))
                Text(
                    if (loading) {
                        "Shoots is reading the current Photographer record."
                    } else {
                        "Shoots found another Camera Shot or a later correction. Return to Now for the current record."
                    },
                    color = MutedWhite,
                    fontSize = 14.sp,
                    lineHeight = 20.sp,
                )
            }
            return@Column
        }

        val members = record.shotIds.mapNotNull { id -> shots.firstOrNull { it.id == id } }
        val preview = when {
            members.size <= 3 -> members
            else -> listOf(members.first(), members[(members.lastIndex) / 2], members.last())
        }
        val receipt = record.receipt
        val primaryDiscovery = receipt.repeated.firstOrNull()
            ?: receipt.varied.firstOrNull()
            ?: receipt.summary.ifBlank { "Shoots accounted for this outing." }
        val settledRuns = record.runOutcomes.values.count { it in setOf("completed", "terminal") }
        val intervention = interventions.firstOrNull {
            it.shootId == record.shootId && it.shootRevision == record.revision
        }
        val answer = answers.firstOrNull {
            it.shootId == record.shootId && it.shootRevision == record.revision
        }
        val keepers = members.count { it.keptAt != null }

        Column(Modifier.padding(horizontal = 20.dp)) {
            ScreenTitle(
                if (readOnlySample) "Sample Shoot Record" else "Your Shoot · ready",
                displayTime(shoot?.startedAt ?: record.settledAt).ifBlank { "Settled Shoot" },
                if (readOnlySample) {
                    "Hand-authored layout. No agents ran and actions are disabled."
                } else {
                    "One complete record of what Shoots handled and what you chose."
                },
            )
            Spacer(Modifier.height(20.dp))
            ShootPreview(preview, imageUrl, onShot)
            Spacer(Modifier.height(16.dp))
            InkCard {
                Text(
                    if (readOnlySample) "HAND-AUTHORED EXAMPLE" else "ONE THING WORTH NOTICING",
                    color = Amber,
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(Modifier.height(7.dp))
                Text(
                    primaryDiscovery,
                    color = WarmWhite,
                    fontSize = 22.sp,
                    lineHeight = 28.sp,
                    fontWeight = FontWeight.SemiBold,
                )
                if (receipt.summary.isNotBlank() && receipt.summary != primaryDiscovery) {
                    Spacer(Modifier.height(7.dp))
                    Text(receipt.summary, color = MutedWhite, fontSize = 13.sp, lineHeight = 19.sp)
                }
                Spacer(Modifier.height(16.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    RecordNumber(
                        receipt.shotCount,
                        if (readOnlySample) "Shot cards" else "Shots read",
                        Modifier.weight(1f),
                    )
                    RecordNumber(
                        receipt.sceneCount,
                        if (readOnlySample) "Scene groups" else "Scenes grouped",
                        Modifier.weight(1f),
                    )
                    RecordNumber(settledRuns, "Accounted for", Modifier.weight(1f))
                }
            }

            if (receipt.repeated.isNotEmpty() || receipt.varied.isNotEmpty()) {
                Spacer(Modifier.height(16.dp))
                InkCard {
                    if (receipt.repeated.isNotEmpty()) {
                        LabelValue("What stayed", receipt.repeated.joinToString("\n") { "• $it" })
                    }
                    if (receipt.varied.isNotEmpty()) {
                        Spacer(Modifier.height(14.dp))
                        LabelValue("What varied", receipt.varied.joinToString("\n") { "• $it" })
                    }
                }
            }

            Spacer(Modifier.height(16.dp))
            SectionTitle("The work Shoots finished", "AUDITABLE")
            Spacer(Modifier.height(9.dp))
            InkCard {
                ShootStage("Collected", "${record.shotIds.size} ${recordNoun(record.shotIds.size, "Shot")} joined this Shoot.", true)
                ShootStage(
                    "Read",
                    "${receipt.readableShotCount} readable · ${record.unreadableShotIds.size} recorded as unreadable.",
                    true,
                )
                ShootStage("Grouped", "${receipt.sceneCount} ${recordNoun(receipt.sceneCount, "Scene")} kept the outing together.", true)
                ShootStage("Settled", "Revision ${record.revision} was stored only after every run reached an outcome.", true)
            }

            Spacer(Modifier.height(16.dp))
            SectionTitle("Who did what", "COMPANION RECEIPT")
            Spacer(Modifier.height(9.dp))
            InkCard {
                ReceiptLine(
                    "Shoots handled",
                    "All ${receipt.shotCount} ${recordNoun(receipt.shotCount, "Shot")} were accounted for across ${receipt.sceneCount} ${recordNoun(receipt.sceneCount, "Scene")}.",
                )
                ReceiptLine(
                    "You decided",
                    when {
                        answer != null -> answer.detail.ifBlank { "You answered one optional question for this Shoot." }
                        intervention?.attemptState == "accepted" -> "You accepted the optional Experiment."
                        intervention?.attemptState == "left" -> "You left the recommendation for today."
                        keepers > 0 -> "$keepers ${recordNoun(keepers, "Shot")} marked as ${if (keepers == 1) "a Keeper" else "Keepers"}."
                        else -> "No Keeper mark or Experiment choice was required."
                    },
                )
                ReceiptLine(
                    "The result",
                    intervention?.outcomeReason.orEmpty().ifBlank {
                        if (keepers > 0) {
                            "Keeper marks now tell Shoots which Shots mattered to you."
                        } else {
                            "The background work finished without creating another chore."
                        }
                    },
                )
                ReceiptLine(
                    "Next",
                    record.scout.reason.ifBlank { "Shoots kept the record and stopped without guessing." },
                    last = true,
                )
            }

            if (receipt.blindSpots.isNotEmpty()) {
                Spacer(Modifier.height(16.dp))
                InkCard {
                    LabelValue("What Shoots could not claim", receipt.blindSpots.joinToString("\n") { "• $it" })
                }
            }

            Spacer(Modifier.height(20.dp))
            SectionTitle("Every Shot in this Shoot", "${members.size}/${record.shotIds.size} LOADED")
            Spacer(Modifier.height(9.dp))
            if (members.isEmpty()) {
                InkCard { Text("Loading member Shots…", color = MutedWhite, fontSize = 13.sp) }
            } else {
                LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    items(members, key = ShotDto::id) { shot ->
                        ShootMemberCard(
                            shot = shot,
                            imageUrl = imageUrl(shot),
                            onShot = onShot,
                            onKeeper = onKeeper,
                            readOnlySample = readOnlySample,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ShootPreview(
    shots: List<ShotDto>,
    imageUrl: (ShotDto) -> String,
    onShot: (String) -> Unit,
) {
    Row(
        Modifier
            .fillMaxWidth()
            .height(300.dp)
            .background(InkRaised, RoundedCornerShape(20.dp))
            .border(1.dp, Hairline, RoundedCornerShape(20.dp))
            .padding(6.dp),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        when (shots.size) {
            0 -> PreviewImage(null, imageUrl, onShot, Modifier.fillMaxSize())
            1 -> PreviewImage(shots[0], imageUrl, onShot, Modifier.fillMaxSize())
            2 -> {
                PreviewImage(shots[0], imageUrl, onShot, Modifier.weight(1f).fillMaxSize())
                PreviewImage(shots[1], imageUrl, onShot, Modifier.weight(1f).fillMaxSize())
            }
            else -> {
                PreviewImage(shots[0], imageUrl, onShot, Modifier.weight(1.08f).fillMaxSize())
                Column(Modifier.weight(0.92f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    PreviewImage(shots[1], imageUrl, onShot, Modifier.weight(1f).fillMaxWidth())
                    PreviewImage(shots[2], imageUrl, onShot, Modifier.weight(1f).fillMaxWidth())
                }
            }
        }
    }
}

@Composable
private fun PreviewImage(
    shot: ShotDto?,
    imageUrl: (ShotDto) -> String,
    onShot: (String) -> Unit,
    modifier: Modifier,
) {
    Box(
        modifier
            .clip(RoundedCornerShape(15.dp))
            .background(InkSoft)
            .then(if (shot == null) Modifier else Modifier.clickable(role = Role.Button) { onShot(shot.id) }),
    ) {
        if (shot != null) {
            AsyncImage(
                model = imageUrl(shot),
                contentDescription = shot.filename,
                modifier = Modifier.fillMaxSize(),
                contentScale = ContentScale.Crop,
            )
        }
    }
}

@Composable
private fun RecordNumber(value: Int, label: String, modifier: Modifier = Modifier) {
    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = modifier) {
        Text(value.toString(), color = WarmWhite, fontSize = 22.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(2.dp))
        Text(
            label,
            color = MutedWhite,
            fontSize = 10.sp,
            lineHeight = 13.sp,
            maxLines = 2,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth(),
        )
    }
}

@Composable
private fun ShootStage(label: String, detail: String, complete: Boolean) {
    Row(Modifier.fillMaxWidth().padding(vertical = 8.dp), verticalAlignment = Alignment.Top) {
        Box(
            Modifier
                .padding(top = 3.dp)
                .size(13.dp)
                .background(if (complete) Amber else Hairline, CircleShape),
        )
        Spacer(Modifier.width(10.dp))
        Column(Modifier.weight(1f)) {
            Text(label, color = WarmWhite, fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
            Text(detail, color = MutedWhite, fontSize = 12.sp, lineHeight = 17.sp)
        }
    }
}

@Composable
private fun ReceiptLine(label: String, value: String, last: Boolean = false) {
    Row(Modifier.fillMaxWidth().padding(bottom = if (last) 0.dp else 15.dp), verticalAlignment = Alignment.Top) {
        Text("✓", color = Amber, fontSize = 15.sp, modifier = Modifier.width(24.dp))
        Column(Modifier.weight(1f)) {
            Text(label.uppercase(), color = MutedWhite, fontSize = 9.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(3.dp))
            Text(value, color = WarmWhite, fontSize = 13.sp, lineHeight = 18.sp)
        }
    }
}

@Composable
private fun ShootMemberCard(
    shot: ShotDto,
    imageUrl: String,
    onShot: (String) -> Unit,
    onKeeper: (String, Boolean) -> Unit,
    readOnlySample: Boolean,
) {
    Column(
        Modifier
            .width(164.dp)
            .background(InkRaised, RoundedCornerShape(16.dp))
            .border(1.dp, Hairline, RoundedCornerShape(16.dp))
            .clip(RoundedCornerShape(16.dp)),
    ) {
        Box(
            Modifier
                .fillMaxWidth()
                .aspectRatio(1f)
                .background(InkSoft)
                .clickable(role = Role.Button) { onShot(shot.id) },
        ) {
            AsyncImage(
                model = imageUrl,
                contentDescription = shot.filename,
                modifier = Modifier.fillMaxSize(),
                contentScale = ContentScale.Crop,
            )
            Box(Modifier.align(Alignment.TopEnd).padding(7.dp)) {
                KeeperButton(
                    kept = shot.keptAt != null,
                    enabled = !readOnlySample,
                ) { onKeeper(shot.id, shot.keptAt == null) }
            }
        }
        Column(Modifier.padding(10.dp)) {
            Text(
                shot.filename,
                color = WarmWhite,
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(displayTime(shot.displayTime), color = MutedWhite, fontSize = 10.sp)
        }
    }
}

private fun recordNoun(count: Int, noun: String): String = if (count == 1) noun else "${noun}s"
