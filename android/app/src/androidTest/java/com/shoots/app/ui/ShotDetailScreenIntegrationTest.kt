package com.shoots.app.ui

import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import com.shoots.app.ShootsTheme
import com.shoots.app.data.AnalysisDto
import com.shoots.app.data.CompositionDto
import com.shoots.app.data.GridSpecDto
import com.shoots.app.data.FindingDto
import com.shoots.app.data.MoveDto
import com.shoots.app.data.ShotDto
import com.shoots.app.data.ShotTeachingReceiptDto
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
                        note = "The subject is visible in A1:H6, away from clutter in columns A-C.",
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
                    blobUrl = { "" },
                    onBack = {},
                    onKeeper = {},
                    onRetry = {},
                    onOpenDrive = {},
                )
            }
        }

        compose.onNodeWithContentDescription("Thirds composition guide").assertExists()
        compose.onNodeWithText("1 lens").assertDoesNotExist()
        compose.onNodeWithText("Full Analysis").performScrollTo().performClick()
        compose.onNodeWithText("The panel did not corroborate a Technique in this Shot.").assertExists()
        compose.onNodeWithText("MEASURED FINDINGS").assertDoesNotExist()
        compose.onNodeWithText("A1", substring = true).assertDoesNotExist()
        compose.onNodeWithText("H6", substring = true).assertDoesNotExist()
        compose.onNodeWithText("columns A-C", substring = true).assertDoesNotExist()
        compose.onNodeWithText("quest_internal_only", substring = true).assertDoesNotExist()
        compose.onNodeWithText("Run and provenance").performScrollTo().performClick()
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
                    blobUrl = { "" },
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

    @Test
    fun findingAndActionLayersAreChosenExplicitly() {
        val view = ShotViewDto(
            shot = ShotDto(
                id = "marked-shot",
                filename = "IMG_marked.jpg",
                status = "analyzed",
                grid = GridSpecDto(cols = 7, rows = 9, width = 900, height = 1200),
            ),
            analysis = AnalysisDto(
                shotId = "marked-shot",
                findings = listOf(
                    FindingDto(
                        findingId = "off_guide_subject",
                        what = "The subject sits on no line.",
                        why = "The nearest line is 0.08 of the frame away.",
                    )
                ),
                composition = CompositionDto(
                    subjectCells = listOf("D4"),
                    subjectX = 0.45,
                    subjectY = 0.42,
                    moves = listOf(
                        MoveDto(
                            what = "Move the subject toward the line",
                            fromCells = listOf("D4"),
                            toCells = listOf("C4"),
                        )
                    ),
                ),
            ),
        )

        compose.setContent {
            ShootsTheme {
                ShotDetailScreen(
                    view = view,
                    imageUrl = { _, _ -> "" },
                    blobUrl = { "" },
                    onBack = {},
                    onKeeper = {},
                    onRetry = {},
                    onOpenDrive = {},
                )
            }
        }

        compose.onNodeWithContentDescription("Finding Subject placement").assertExists()
        compose.onNodeWithText("Try").performClick()
        compose.onNodeWithContentDescription("Composition action").assertExists()
        compose.onNodeWithText("Clean").performClick()
        compose.onNodeWithContentDescription("Clean Shot").assertExists()
    }

    @Test
    fun teachingReceiptKeepsOneDecisionOneMoveAndOneCheckTogether() {
        val view = ShotViewDto(
            shot = ShotDto(
                id = "teaching-shot",
                filename = "IMG_teaching.jpg",
                status = "analyzed",
                grid = GridSpecDto(cols = 8, rows = 6, width = 800, height = 600),
            ),
            analysis = AnalysisDto(
                shotId = "teaching-shot",
                composition = CompositionDto(guide = "thirds"),
            ),
            teaching = ShotTeachingReceiptDto(
                keepTitle = "Negative space",
                keepProof = "Two Analyst lenses corroborated this Technique.",
                keepAuthority = "model_read",
                noticeTitle = "Fine edges are soft across the frame.",
                noticeProof = "1/15 s is below the handheld limit.",
                noticeFindingId = "camera_shake",
                noticeAuthority = "measured",
                tryText = "Lower the camera below the beam.",
                tryReason = "Keep the beam from crossing the subject.",
                tryKind = "camera",
                visibleCheck = "Zoom into one fine edge after capture; it should stay single.",
                primaryLayer = "guide",
                guide = "thirds",
            ),
        )

        compose.setContent {
            ShootsTheme {
                ShotDetailScreen(
                    view = view,
                    imageUrl = { _, _ -> "" },
                    blobUrl = { "" },
                    onBack = {},
                    onKeeper = {},
                    onRetry = {},
                    onOpenDrive = {},
                )
            }
        }

        compose.onNodeWithContentDescription("Thirds composition guide").assertExists()
        compose.onNodeWithText("KEEP · MODEL READ").performScrollTo().assertExists()
        compose.onNodeWithText("NOTICE · MEASURED").assertExists()
        compose.onNodeWithText("TRY · MOVE CAMERA").assertExists()
        compose.onNodeWithText("CHECK ON THE NEXT SHOT").assertExists()
        compose.onNodeWithText("What worked").assertDoesNotExist()
        compose.onNodeWithText("What got in the way").assertDoesNotExist()
        compose.onNodeWithText("One thing to try").assertDoesNotExist()
    }
}
