package com.shoots.app.ui

import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.test.platform.app.InstrumentationRegistry
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
import com.shoots.app.data.VisualEvidenceArtifactDto
import com.shoots.app.data.VisualMarkDto
import com.shoots.app.data.VisualPathDto
import com.shoots.app.data.VisualRegionDto
import org.junit.Rule
import org.junit.Test
import android.graphics.Bitmap
import java.io.File

class ShotDetailScreenIntegrationTest {
    @get:Rule
    val compose = createComposeRule()

    private val fixtureUrl = "android.resource://com.shoots.app/drawable/visual_story_fixture"
    private val marketFixtureUrl =
        "android.resource://com.shoots.app.test/drawable/intent_color_market_fixture"
    private val measuredHueArtifactUrl =
        "android.resource://com.shoots.app.test/drawable/measured_hue_artifact"

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
                    imageUrl = { _, _ -> fixtureUrl },
                    blobUrl = { "" },
                    onBack = {},
                    onKeeper = {},
                    onRetry = {},
                    onOpenDrive = {},
                )
            }
        }

        compose.onNodeWithText("Visual story").assertExists()
        compose.onNodeWithText("1 of 1").assertExists()
        compose.onNodeWithContentDescription("Visual mark region").assertExists()
        compose.onNodeWithText("Compare guides").performScrollTo().performClick()
        compose.onNodeWithText("Rule of thirds").performClick()
        compose.onNodeWithContentDescription("Thirds composition guide").assertExists()
        compose.onNodeWithText("Change guide").performClick()
        compose.onNodeWithText("Golden spiral").performClick()
        compose.onNodeWithContentDescription("Golden spiral composition guide").assertExists()
        compose.onNodeWithText("Rotate spiral").performClick()
        compose.onNodeWithContentDescription("Golden spiral composition guide").assertExists()
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
                    imageUrl = { _, _ -> fixtureUrl },
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
                    imageUrl = { _, _ -> fixtureUrl },
                    blobUrl = { "" },
                    onBack = {},
                    onKeeper = {},
                    onRetry = {},
                    onOpenDrive = {},
                )
            }
        }

        compose.onNodeWithText("Visual story").assertExists()
        compose.onNodeWithText("1 of 3").assertExists()
        compose.onNodeWithText("Next").performClick()
        compose.onNodeWithContentDescription("Visual mark finding").assertExists()
        compose.onNodeWithText("Next").performClick()
        compose.onNodeWithContentDescription("Visual mark move").assertExists()
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
                findings = listOf(
                    FindingDto(
                        findingId = "camera_shake",
                        what = "Fine edges are soft across the frame.",
                        why = "1/15 s is below the handheld limit.",
                    )
                ),
                composition = CompositionDto(
                    subjectCells = listOf("E2", "E3", "F2", "F3"),
                    subjectX = 0.67,
                    subjectY = 0.55,
                    guide = "thirds",
                ),
            ),
            teaching = ShotTeachingReceiptDto(
                keepTitle = "Negative space",
                keepProof = "Two Analyst lenses corroborated this Technique.",
                keepAuthority = "model_read",
                keepCells = listOf("E2", "E3", "F2", "F3"),
                keepMark = VisualMarkDto(
                    kind = "region",
                    cells = listOf("E2", "E3", "F2", "F3"),
                    techniqueId = "negative_space",
                ),
                noticeTitle = "Fine edges are soft across the frame.",
                noticeProof = "1/15 s is below the handheld limit.",
                noticeFindingId = "camera_shake",
                noticeAuthority = "measured",
                noticeMark = VisualMarkDto(kind = "finding", findingId = "camera_shake"),
                tryText = "Lower the camera below the beam.",
                tryReason = "Keep the beam from crossing the subject.",
                tryKind = "camera",
                tryMark = VisualMarkDto(
                    kind = "line",
                    cells = listOf("A1", "B1", "C1", "D1", "E1", "F1", "G1", "H1"),
                ),
                visibleCheck = "Zoom into one fine edge after capture; it should stay single.",
                checkMark = VisualMarkDto(
                    kind = "line",
                    cells = listOf("A1", "B1", "C1", "D1", "E1", "F1", "G1", "H1"),
                ),
                primaryLayer = "guide",
                guide = "thirds",
            ),
        )

        compose.setContent {
            ShootsTheme {
                ShotDetailScreen(
                    view = view,
                    imageUrl = { _, _ -> fixtureUrl },
                    blobUrl = { "" },
                    onBack = {},
                    onKeeper = {},
                    onRetry = {},
                    onOpenDrive = {},
                )
            }
        }

        compose.onNodeWithText("WHAT HOLDS THE FRAME").assertExists()
        compose.onNodeWithContentDescription("Visual mark region").assertExists()
        compose.onNodeWithText("1 of 4").assertExists()
        compose.onNodeWithText("Next").performClick()
        compose.onNodeWithText("WHAT SHOOTS MEASURED").assertExists()
        compose.onNodeWithContentDescription("Visual mark finding").assertExists()
        compose.onNodeWithText("Next").performClick()
        compose.onNodeWithText("WHAT TO CHANGE").assertExists()
        compose.onNodeWithContentDescription("Visual mark line").assertExists()
        compose.onNodeWithText("Next").performClick()
        compose.onNodeWithText("CHECK THE NEXT SHOT").assertExists()
        compose.onNodeWithText("Compare guides").performScrollTo().performClick()
        compose.onNodeWithText("Rule of thirds").performClick()
        compose.onNodeWithContentDescription("Thirds composition guide").assertExists()
        compose.onNodeWithText("What worked").assertDoesNotExist()
        compose.onNodeWithText("What got in the way").assertDoesNotExist()
        compose.onNodeWithText("One thing to try").assertDoesNotExist()
    }

    @Test
    fun eachMarketStorySentenceSelectsItsOwnVisualMark() {
        val lineCells = listOf("D9", "D7", "D5", "G9", "F7", "E5")
        val linePaths = listOf(
            VisualPathDto(
                points = listOf("D9", "D7", "D5"),
                leadsTo = listOf("D4", "E4"),
                role = "boundary",
            ),
            VisualPathDto(
                points = listOf("G9", "F7", "E5"),
                leadsTo = listOf("D4", "E4"),
                role = "boundary",
            ),
        )
        val tarpCells = listOf(
            "A5", "B5", "C5", "D5",
            "A6", "B6", "C6", "D6",
            "A7", "B7", "C7", "D7",
            "A8", "B8", "C8", "D8",
            "A9", "B9", "C9", "D9",
        )
        val view = ShotViewDto(
            shot = ShotDto(
                id = "market-story",
                filename = "13-intent-color-market.png",
                status = "analyzed",
                grid = GridSpecDto(cols = 7, rows = 9, width = 1122, height = 1402),
            ),
            analysis = AnalysisDto(
                shotId = "market-story",
                composition = CompositionDto(
                    subjectCells = listOf("D3", "E3", "D4", "E4"),
                    subjectX = 0.6,
                    subjectY = 0.41,
                ),
            ),
            teaching = ShotTeachingReceiptDto(
                keepTitle = "Leading lines",
                keepProof = "The wet corridor draws the eye toward the person.",
                keepTechniqueId = "leading_lines",
                keepCells = lineCells,
                keepMark = VisualMarkDto(
                    kind = "line",
                    cells = lineCells,
                    paths = linePaths,
                    techniqueId = "leading_lines",
                ),
                noticeTitle = "The teal tarp fills the foreground.",
                noticeProof = "One Analyst observation; not a measured Finding.",
                noticeAuthority = "model_read",
                noticeCells = tarpCells,
                noticeMark = VisualMarkDto(kind = "region", cells = tarpCells),
                tryText = "Step forward past the tarp.",
                tryReason = "Reduce the teal foreground without inventing an arrow.",
                tryKind = "camera",
                tryMark = VisualMarkDto(kind = "region", cells = tarpCells),
                visibleCheck = "Check that the corridor reaches the subject without the tarp dominating it.",
                checkMark = VisualMarkDto(kind = "region", cells = tarpCells),
            ),
        )

        compose.setContent {
            ShootsTheme {
                ShotDetailScreen(
                    view = view,
                    imageUrl = { _, _ -> marketFixtureUrl },
                    blobUrl = { "" },
                    onBack = {},
                    onKeeper = {},
                    onRetry = {},
                    onOpenDrive = {},
                )
            }
        }

        compose.onNodeWithText("Leading lines").assertExists()
        compose.onNodeWithContentDescription("Visual mark line").assertExists()
        compose.onNodeWithText("Next").performClick()
        compose.onNodeWithText("The teal tarp fills the foreground.").assertExists()
        compose.onNodeWithContentDescription("Visual mark region").assertExists()
        saveScreenshot("market-story-tarp-region.png")
        compose.onNodeWithText("Previous").performClick()
        compose.onNodeWithContentDescription("Visual mark line").assertExists()
        saveScreenshot("market-story-leading-line.png")
        compose.onNodeWithText("Next").performClick()
        saveScreenshot("market-story-tarp-region.png")
        compose.onNodeWithText("Next").performClick()
        compose.onNodeWithText("Step forward past the tarp.").assertExists()
        compose.onNodeWithContentDescription("Visual mark region").assertExists()
        compose.onNodeWithText("Next").performClick()
        compose.onNodeWithText(
            "Check that the corridor reaches the subject without the tarp dominating it."
        ).assertExists()
        compose.onNodeWithContentDescription("Visual mark region").assertExists()
    }

    @Test
    fun measuredArtifactSwitchesBetweenVisualAndCleanShot() {
        val artifact = VisualEvidenceArtifactDto(
            kind = "hue_mask",
            authority = "measured",
            blobPath = "visual-complementary.jpg",
            label = "Where the colour lives",
            legend = "Cyan and violet mark measured hue groups.",
        )
        val cells = listOf("A1", "B1", "A2", "B2")
        val view = ShotViewDto(
            shot = ShotDto(
                id = "artifact-shot",
                filename = "IMG_artifact.jpg",
                status = "analyzed",
                grid = GridSpecDto(cols = 8, rows = 6, width = 800, height = 600),
            ),
            analysis = AnalysisDto(
                shotId = "artifact-shot",
                techniques = listOf(
                    TechniqueEvidenceDto(
                        techniqueId = "complementary",
                        confidence = 0.9,
                        agreement = 2,
                        cells = cells,
                        visualArtifact = artifact,
                    )
                ),
            ),
            teaching = ShotTeachingReceiptDto(
                keepTitle = "Complementary colours",
                keepProof = "Two Analyst lenses located the colour relationship.",
                keepTechniqueId = "complementary",
                keepMark = VisualMarkDto(
                    kind = "region",
                    cells = cells,
                    visualArtifact = artifact,
                    techniqueId = "complementary",
                ),
            ),
        )

        compose.setContent {
            ShootsTheme {
                ShotDetailScreen(
                    view = view,
                    imageUrl = { _, _ -> fixtureUrl },
                    blobUrl = { if (it == artifact.blobPath) measuredHueArtifactUrl else "" },
                    onBack = {},
                    onKeeper = {},
                    onRetry = {},
                    onOpenDrive = {},
                )
            }
        }

        compose.onNodeWithContentDescription("Visual evidence Where the colour lives").assertExists()
        compose.onNodeWithText("Measured · Where the colour lives").assertExists()
        waitForImage("Visual evidence Where the colour lives")
        compose.mainClock.advanceTimeBy(500)
        compose.waitForIdle()
        saveScreenshot("measured-artifact.png")
        compose.onNodeWithText("See clean").performClick()
        compose.onNodeWithContentDescription("IMG_artifact.jpg").assertExists()
        compose.onNodeWithText("Show visual").performClick()
        compose.onNodeWithContentDescription("Visual evidence Where the colour lives").assertExists()
    }

    @Test
    fun relationalTechniqueKeepsBothRegionsVisible() {
        val regions = listOf(
            VisualRegionDto(
                cells = listOf("D3", "E3", "D4", "E4"),
                role = "warm",
                order = 0,
            ),
            VisualRegionDto(
                cells = listOf("A5", "B5", "C5", "A6", "B6", "C6", "A7", "B7", "C7"),
                role = "cool",
                order = 1,
            ),
        )
        val mark = VisualMarkDto(
            kind = "pair",
            cells = regions.flatMap { it.cells },
            regions = regions,
            techniqueId = "warm_cool",
        )
        val view = ShotViewDto(
            shot = ShotDto(
                id = "pair-shot",
                filename = "IMG_pair.jpg",
                status = "analyzed",
                grid = GridSpecDto(cols = 7, rows = 9, width = 1122, height = 1402),
            ),
            analysis = AnalysisDto(
                shotId = "pair-shot",
                techniques = listOf(
                    TechniqueEvidenceDto(
                        techniqueId = "layering",
                        name = "Foreground, midground, background",
                        confidence = 0.9,
                        agreement = 2,
                        cells = listOf("A7", "B7", "D4", "E4", "D1", "E1"),
                        regions = listOf(
                            VisualRegionDto(
                                cells = listOf("A7", "B7", "A8", "B8", "A9", "B9"),
                                role = "foreground",
                                order = 0,
                            ),
                            VisualRegionDto(
                                cells = listOf("D4", "E4", "D5", "E5"),
                                role = "midground",
                                order = 1,
                            ),
                            VisualRegionDto(
                                cells = listOf("D1", "E1", "D2", "E2"),
                                role = "background",
                                order = 2,
                            ),
                        ),
                    ),
                    TechniqueEvidenceDto(
                        techniqueId = "patterns",
                        name = "Patterns and repetition",
                        confidence = 0.86,
                        agreement = 2,
                        cells = listOf("F5", "G5", "F6", "G6", "F7", "G7"),
                        regions = listOf(
                            VisualRegionDto(cells = listOf("F5"), role = "repeat", order = 0),
                            VisualRegionDto(cells = listOf("G5"), role = "repeat", order = 1),
                            VisualRegionDto(cells = listOf("F6"), role = "repeat", order = 2),
                            VisualRegionDto(cells = listOf("G6"), role = "repeat", order = 3),
                        ),
                    ),
                ),
            ),
            teaching = ShotTeachingReceiptDto(
                keepTitle = "Warm against cool",
                keepProof = "The red umbrella and teal foreground form two separate colour regions.",
                keepTechniqueId = "warm_cool",
                keepMark = mark,
            ),
        )

        compose.setContent {
            ShootsTheme {
                ShotDetailScreen(
                    view = view,
                    imageUrl = { _, _ -> marketFixtureUrl },
                    blobUrl = { "" },
                    onBack = {},
                    onKeeper = {},
                    onRetry = {},
                    onOpenDrive = {},
                )
            }
        }

        compose.onNodeWithContentDescription("Visual mark pair").assertExists()
        compose.onNodeWithText("Warm against cool").assertExists()
        compose.onNodeWithText("1 of 3").assertExists()
        waitForImage("IMG_pair.jpg")
        compose.mainClock.advanceTimeBy(500)
        compose.waitForIdle()
        saveScreenshot("pair-regions.png")
        compose.onNodeWithText("Next").performClick()
        compose.onNodeWithContentDescription("Visual mark planes").assertExists()
        compose.onNodeWithText("Foreground, midground, background").assertExists()
        compose.onNodeWithText("Next").performClick()
        compose.onNodeWithContentDescription("Visual mark instances").assertExists()
        compose.onNodeWithText("Patterns and repetition").assertExists()
    }

    private fun waitForImage(contentDescription: String) {
        compose.waitUntil(timeoutMillis = 5_000) {
            runCatching {
                val bitmap = compose.onNodeWithContentDescription(contentDescription)
                    .captureToImage()
                    .asAndroidBitmap()
                val colours = buildSet {
                    for (x in 1..4) {
                        for (y in 1..4) {
                            add(bitmap.getPixel(bitmap.width * x / 5, bitmap.height * y / 5))
                        }
                    }
                }
                colours.size >= 5
            }.getOrDefault(false)
        }
    }

    private fun saveScreenshot(name: String) {
        val directory = InstrumentationRegistry.getInstrumentation().targetContext.externalCacheDir
            ?: error("External cache unavailable")
        val file = File(directory, name)
        file.outputStream().use { output ->
            compose.onRoot().captureToImage().asAndroidBitmap().compress(
                Bitmap.CompressFormat.PNG,
                100,
                output,
            )
        }
    }
}
