package com.shoots.app.ui

import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.shoots.app.ShootsTheme
import com.shoots.app.data.AnalysisDto
import com.shoots.app.data.MobileSnapshotDto
import com.shoots.app.data.ScoutDecisionDto
import com.shoots.app.data.ScoutQuestionDto
import com.shoots.app.data.ScoutQuestionOptionDto
import com.shoots.app.data.ShootDto
import com.shoots.app.data.ShootReceiptDto
import com.shoots.app.data.ShootRecordDto
import com.shoots.app.data.ShotDto
import com.shoots.app.data.ShotViewDto
import com.shoots.app.data.SourceStateEntity
import com.shoots.app.data.TechniqueEvidenceDto
import com.shoots.app.data.UserDto
import com.shoots.app.phone.MediaAccess
import org.junit.Rule
import org.junit.Test
import org.junit.Assert.assertEquals

class NowScreenIntegrationTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun settledShootReceiptOutranksTheLatestPerShotCritique() {
        val shoot = ShootDto(
            id = "shoot-1",
            status = "settled",
            revision = 1,
            currentRecordRevision = 1,
            orderedSceneIds = listOf("scene-1"),
            orderedShotIds = listOf("shot-1", "shot-2"),
        )
        val record = ShootRecordDto(
            shootId = shoot.id,
            revision = 1,
            sceneIds = shoot.orderedSceneIds,
            shotIds = shoot.orderedShotIds,
            receipt = ShootReceiptDto(
                summary = "2 Shots across 1 Scene.",
                shotCount = 2,
                sceneCount = 1,
                repeated = listOf(
                    "2 of 2 readable Shots used portrait for how you hold the camera (measured)."
                ),
            ),
            scout = ScoutDecisionDto(route = "explain"),
        )
        val latestShot = ShotDto(id = "shot-2", status = "analyzed")
        val snapshot = snapshot(
            shoot = shoot,
            record = record,
            latestShot = ShotViewDto(
                shot = latestShot,
                analysis = AnalysisDto(
                    shotId = latestShot.id,
                    techniques = listOf(
                        TechniqueEvidenceDto(
                            techniqueId = "backlight",
                            agreement = 2,
                        )
                    ),
                ),
            ),
        )

        compose.setContent { NowTestContent(snapshot) }

        compose.onNodeWithText("YOUR SHOOT").assertExists()
        compose.onNodeWithText(record.receipt.repeated.first()).assertExists()
        compose.onNodeWithText("Open Shots").assertExists()
        compose.onNodeWithText("Two lenses found Backlight.").assertDoesNotExist()
    }

    @Test
    fun closingShootOutranksAStaleEarlierRecord() {
        val current = ShootDto(
            id = "shoot-1",
            status = "closing",
            revision = 2,
            currentRecordRevision = 2,
            orderedSceneIds = listOf("scene-2"),
            orderedShotIds = listOf("shot-1", "shot-2", "shot-3"),
        )
        val stale = ShootRecordDto(
            shootId = current.id,
            revision = 1,
            receipt = ShootReceiptDto(
                summary = "Old receipt",
                repeated = listOf("This superseded line must not be shown."),
            ),
        )

        compose.setContent { NowTestContent(snapshot(current, stale)) }

        compose.onNodeWithText("Accounting for every Shot.").assertExists()
        compose.onNodeWithText("This superseded line must not be shown.").assertDoesNotExist()
    }

    @Test
    fun keeperBackedRouteMakesTheExperimentTheOnlyAmberPrimaryAction() {
        val shoot = ShootDto(
            id = "shoot-2",
            status = "settled",
            currentRecordRevision = 1,
            orderedSceneIds = listOf("scene-1"),
            orderedShotIds = listOf("keeper-1"),
        )
        val record = ShootRecordDto(
            shootId = shoot.id,
            receipt = ShootReceiptDto(
                shotCount = 1,
                sceneCount = 1,
                repeated = listOf("Backlight was corroborated in one Shot (model read)."),
            ),
            scout = ScoutDecisionDto(route = "reproduce", experimentId = "experiment-1"),
        )

        compose.setContent { NowTestContent(snapshot(shoot, record)) }

        compose.onNodeWithText("EXPERIMENT OFFERED FROM YOUR KEEPER").assertExists()
        compose.onNodeWithText("Open Experiment").assertExists()
        compose.onNodeWithText("Open Shots").assertExists()
    }

    @Test
    fun consequentialScoutQuestionRecordsOneExplicitChoice() {
        var selected = ""
        val shoot = ShootDto(
            id = "shoot-ask",
            status = "settled",
            currentRecordRevision = 1,
            orderedShotIds = listOf("shot-1", "shot-2"),
        )
        val record = ShootRecordDto(
            shootId = shoot.id,
            revision = 1,
            receipt = ShootReceiptDto(
                shotCount = 2,
                sceneCount = 1,
                repeated = listOf("Two decisions repeated together."),
            ),
            scout = ScoutDecisionDto(
                route = "ask",
                question = ScoutQuestionDto(
                    id = "question-1",
                    prompt = "Which decision were you exploring in this Shoot?",
                    options = listOf(
                        ScoutQuestionOptionDto("technique_backlight", "Backlight", "backlight"),
                        ScoutQuestionOptionDto("just_shooting", "I was just shooting"),
                    ),
                ),
            ),
        )

        compose.setContent {
            NowTestContent(snapshot(shoot, record)) { _, _, option -> selected = option }
        }

        compose.onNodeWithText("Which decision were you exploring in this Shoot?").assertExists()
        compose.onNodeWithText("Backlight").performClick()
        assertEquals("technique_backlight", selected)
    }

    @androidx.compose.runtime.Composable
    private fun NowTestContent(
        snapshot: MobileSnapshotDto,
        onAnswer: (String, Int, String) -> Unit = { _, _, _ -> },
    ) {
        ShootsTheme {
            NowScreen(
                snapshot = snapshot,
                source = SourceStateEntity(
                    enabled = true,
                    lastSuccessfulSyncAt = "2026-08-27T01:00:00Z",
                ),
                localSession = null,
                mediaAccess = MediaAccess.FULL,
                busy = false,
                imageUrl = { "" },
                onRequestMedia = {},
                onEnableSource = {},
                onOpenFreeCamera = {},
                onChooseFreeShots = {},
                onContinueSession = {},
                onFinishSession = {},
                onCancelSession = {},
                onImportSessionAsFree = {},
                onOpenShot = {},
                onOpenShots = {},
                onOpenExperiments = {},
                onAnswerScoutQuestion = onAnswer,
                onOpenSettings = {},
            )
        }
    }

    private fun snapshot(
        shoot: ShootDto,
        record: ShootRecordDto,
        latestShot: ShotViewDto? = null,
    ) = MobileSnapshotDto(
        user = UserDto(id = "user-1", email = "photographer@example.test"),
        latestShoot = shoot,
        latestShootRecord = record,
        latestShot = latestShot,
    )
}
