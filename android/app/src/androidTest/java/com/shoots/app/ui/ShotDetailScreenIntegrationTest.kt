package com.shoots.app.ui

import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import com.shoots.app.ShootsTheme
import com.shoots.app.data.AnalysisDto
import com.shoots.app.data.CompositionDto
import com.shoots.app.data.GridSpecDto
import com.shoots.app.data.ShotDto
import com.shoots.app.data.ShotViewDto
import com.shoots.app.data.TechniqueEvidenceDto
import org.junit.Rule
import org.junit.Test

class ShotDetailScreenIntegrationTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun analyzedShotShowsTheHumanGuideWithoutInternalCoordinatesOrIds() {
        val grid = GridSpecDto(cols = 7, rows = 9, width = 900, height = 1200)
        val view = ShotViewDto(
            shot = ShotDto(
                id = "shot-1",
                filename = "IMG_guide.jpg",
                status = "analyzed",
                grid = grid,
                experimentId = "quest_internal_only",
            ),
            analysis = AnalysisDto(
                shotId = "shot-1",
                techniques = listOf(
                    TechniqueEvidenceDto(
                        techniqueId = "rule_of_thirds",
                        cells = listOf("A1"),
                        note = "The subject is visible in A1.",
                        agreement = 1,
                    )
                ),
                composition = CompositionDto(
                    subjectCells = listOf("A1"),
                    subjectX = 0.1,
                    subjectY = 0.1,
                    guide = "thirds",
                ),
            ),
        )

        compose.setContent {
            ShootsTheme {
                ShotDetailScreen(
                    view = view,
                    imageUrl = { _, _ -> "" },
                    onBack = {},
                    onKeeper = {},
                    onRetry = {},
                    onOpenDrive = {},
                )
            }
        }

        compose.onNodeWithContentDescription("Thirds composition guide").assertExists()
        compose.onNodeWithText("1 lens").assertExists()
        compose.onNodeWithText("A1", substring = true).assertDoesNotExist()
        compose.onNodeWithText("quest_internal_only", substring = true).assertDoesNotExist()
        compose.onNodeWithText("Associated with an Experiment").assertExists()
    }

    @Test
    fun acceptedShotWithoutARunOffersTruthfulRecovery() {
        val view = ShotViewDto(
            shot = ShotDto(
                id = "legacy-shot",
                filename = "IMG_legacy.jpg",
                status = "ingested",
            ),
        )

        compose.setContent {
            ShootsTheme {
                ShotDetailScreen(
                    view = view,
                    imageUrl = { _, _ -> "" },
                    onBack = {},
                    onKeeper = {},
                    onRetry = {},
                    onOpenDrive = {},
                )
            }
        }

        compose.onNodeWithText("Analysis was interrupted.").assertExists()
        compose.onNodeWithText("Resume analysis").assertExists()
        compose.onNodeWithText("Analysis is still running.").assertDoesNotExist()
    }
}
