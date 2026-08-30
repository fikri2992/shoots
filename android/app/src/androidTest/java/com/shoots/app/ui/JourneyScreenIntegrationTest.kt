package com.shoots.app.ui

import android.graphics.Bitmap
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.test.platform.app.InstrumentationRegistry
import com.shoots.app.ShootsTheme
import com.shoots.app.data.DeconstructionDto
import com.shoots.app.data.DeconstructionPageDto
import com.shoots.app.data.ExperimentDto
import com.shoots.app.data.MobileSnapshotDto
import com.shoots.app.data.InterventionRecordDto
import com.shoots.app.data.ProfileDto
import com.shoots.app.data.ShootReceiptDto
import com.shoots.app.data.ShootRecordDto
import com.shoots.app.data.ShotDto
import com.shoots.app.data.TechniqueNodeDto
import com.shoots.app.data.UserDto
import com.shoots.app.data.VariationDto
import com.shoots.app.data.VariationObservationDto
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import java.io.File

class JourneyScreenIntegrationTest {
    @get:Rule
    val compose = createComposeRule()

    private val fixtureUrl = "android.resource://com.shoots.app/drawable/visual_story_fixture"

    @Test
    fun sectionTabsExposeSelectionAndSwitchTheVisibleRecord() {
        val snapshot = MobileSnapshotDto(
            user = UserDto(id = "user-1", email = "photographer@example.com"),
            profile = ProfileDto(shots = 12),
        )
        compose.setContent {
            ShootsTheme {
                JourneyScreen(snapshot, imageUrl = { _ -> "" }, onShot = { _ -> })
            }
        }

        compose.onNodeWithText("Update").assertExists()
        compose.onNodeWithText("Tendencies").performClick()
        compose.onNodeWithText("The choices you return to").assertExists()
    }

    @Test
    fun techniqueMapKeepsRecurrenceCoverageAndReproductionAsSeparateFigures() {
        val snapshot = MobileSnapshotDto(
            user = UserDto(id = "user-1", email = "photographer@example.com"),
            techniques = listOf(
                TechniqueNodeDto(
                    techniqueId = "panning",
                    name = "Panning",
                    family = "video",
                    status = "recurring",
                    attempts = 4,
                    corroborated = 3,
                    sightings = 4,
                    corroboratedShots = 3,
                    distinctScenes = 2,
                    distinctShoots = 1,
                    reproduceAttempts = 3,
                    criteriaMetResults = 1,
                    reproduceSessions = 2,
                    evaluableReproduceSessions = 2,
                    criteriaMetSessions = 1,
                    abstentions = 1,
                    positiveKeeperShots = 2,
                ),
                TechniqueNodeDto(
                    techniqueId = "rule_of_thirds",
                    name = "Rule of thirds",
                    family = "composition",
                    status = "recurring",
                    attempts = 3,
                    corroborated = 3,
                    sightings = 3,
                    corroboratedShots = 3,
                    distinctScenes = 2,
                    distinctShoots = 2,
                ),
            ),
        )
        compose.setContent {
            ShootsTheme {
                JourneyScreen(snapshot, imageUrl = { _ -> "" }, onShot = { _ -> })
            }
        }

        compose.onNodeWithText("Techniques").performClick()
        compose.onNodeWithText("Clear in 3 Shots · 2 Scenes · 1 Shoot").assertExists()
        compose.onNodeWithText("3 result Shots · 1 could not be checked").assertExists()
        compose.onNodeWithText("WHAT HAPPENED WHEN YOU TRIED").assertExists()
        compose.onNodeWithText(
            "1 of 2 checked sessions matched what you set before shooting.",
        ).assertExists()
        compose.onNodeWithText(
            "This keeps returning in your Shots. You have not tried to repeat it on purpose yet.",
        ).assertExists()
        compose.onNodeWithText("2 marked Keepers").assertExists()
    }

    @Test
    fun photographerChoosesOpeningShotBeforeBuildingStory() {
        var prepared = ""
        val snapshot = MobileSnapshotDto(
            user = UserDto(id = "user-1", email = "photographer@example.com"),
            recentShots = listOf(ShotDto(id = "keeper-1", keptAt = "2026-08-27T00:00:00Z")),
            latestShootRecord = ShootRecordDto(
                shootId = "shoot-1",
                revision = 2,
                receipt = ShootReceiptDto(keeperShotIds = listOf("keeper-1")),
            ),
        )
        compose.setContent {
            ShootsTheme {
                JourneyScreen(
                    snapshot,
                    imageUrl = { _ -> "" },
                    onShot = { _ -> },
                    onPrepareDeconstruction = { type, id, revision, cover ->
                        prepared = "$type:$id:$revision:$cover"
                    },
                )
            }
        }

        compose.onNodeWithText("Build my story").performScrollTo().performClick()
        assertEquals("shoot:shoot-1:2:keeper-1", prepared)
    }

    @Test
    fun draftedStoryOffersOneMultiPageShareAction() {
        var shared = ""
        var saved = ""
        val draft = DeconstructionDto(
            id = "draft-1",
            sourceType = "shoot",
            sourceId = "shoot-1",
            sourceRevision = 1,
            status = "drafted",
            coverShotId = "keeper-1",
            pages = listOf(
                DeconstructionPageDto("cover", "Cover", "Claim", blobPath = "page-1.jpg"),
                DeconstructionPageDto("record", "Record", "Claim", blobPath = "page-2.jpg"),
            ),
            suggestedCaption = "Rain, motion, and the choices that kept returning.",
        )
        val snapshot = MobileSnapshotDto(
            user = UserDto(id = "user-1", email = "photographer@example.com"),
            latestShootRecord = ShootRecordDto(
                shootId = "shoot-1",
                revision = 1,
                receipt = ShootReceiptDto(keeperShotIds = listOf("keeper-1")),
            ),
            latestDeconstruction = draft,
        )
        compose.setContent {
            ShootsTheme {
                JourneyScreen(
                    snapshot,
                    imageUrl = { _ -> "" },
                    onShot = { _ -> },
                    onShareDeconstruction = { shared = it.id },
                    onSaveDeconstruction = { saved = it.id },
                )
            }
        }

        compose.onNodeWithText(draft.suggestedCaption).performScrollTo().assertExists()
        compose.onNodeWithText("Share 2-page story").performScrollTo().performClick()
        assertEquals("draft-1", shared)
        compose.onNodeWithText("Save story to this phone").performScrollTo().performClick()
        assertEquals("draft-1", saved)
    }

    @Test
    fun journeyOpensWithTheLatestShootBenefitBeforeTheTabs() {
        var opened = ""
        val shots = listOf(
            ShotDto(id = "shot-1", filename = "one.jpg"),
            ShotDto(id = "shot-2", filename = "two.jpg"),
        )
        val snapshot = MobileSnapshotDto(
            user = UserDto(id = "user-1", email = "photographer@example.com"),
            recentShots = shots,
            latestShootRecord = ShootRecordDto(
                shootId = "shoot-1",
                revision = 3,
                shotIds = shots.map(ShotDto::id),
                receipt = ShootReceiptDto(
                    shotCount = 2,
                    sceneCount = 1,
                    repeated = listOf("You kept returning to the edge of the frame."),
                ),
            ),
        )

        compose.setContent {
            ShootsTheme {
                JourneyScreen(
                    snapshot = snapshot,
                    imageUrl = { fixtureUrl },
                    onShot = {},
                    onOpenShootRecord = { id, revision -> opened = "$id:$revision" },
                )
            }
        }

        compose.onNodeWithText("YOUR LATEST OUTING").assertExists()
        compose.onNodeWithText("Collected → Read → Grouped → Settled.", substring = true).assertExists()
        waitForImage("one.jpg")
        saveScreenshot("journey-latest-shoot.png")
        compose.onNodeWithText("Open full Shoot Record").performClick()
        assertEquals("shoot-1:3", opened)
    }

    @Test
    fun terminalExperimentDraftUsesItsOwnKeeperAndSource() {
        var prepared = ""
        val experiment = ExperimentDto(
            id = "experiment-1",
            techniqueId = "negative_space",
            type = "reproduce",
            title = "Repeat negative space",
            referenceShotId = "keeper-1",
            resultShotIds = listOf("result-1"),
            status = "completed",
        )
        val snapshot = MobileSnapshotDto(
            user = UserDto(id = "user-1", email = "photographer@example.com"),
            recentShots = listOf(ShotDto(id = "keeper-1", keptAt = "2026-08-27T00:00:00Z")),
            experiments = listOf(experiment),
            latestDeconstruction = DeconstructionDto(
                id = "experiment-draft",
                sourceType = "experiment",
                sourceId = experiment.id,
                sourceRevision = 1,
                candidateCoverShotIds = listOf("keeper-1"),
            ),
        )
        compose.setContent {
            ShootsTheme {
                JourneyScreen(
                    snapshot,
                    imageUrl = { _ -> "" },
                    onShot = { _ -> },
                    onPrepareDeconstruction = { type, id, revision, cover ->
                        prepared = "$type:$id:$revision:$cover"
                    },
                )
            }
        }

        compose.onNodeWithText("Shoots follows the sequence and finds the visual thread.", substring = true)
            .performScrollTo()
            .assertExists()
        compose.onNodeWithText("Build my story").performScrollTo().performClick()
        assertEquals("experiment:experiment-1:1:keeper-1", prepared)
    }

    @Test
    fun exploreRecordShowsVariationsWithoutAReproduceReferenceOrAbstention() {
        val experiment = ExperimentDto(
            id = "explore-1",
            techniqueId = "frame_within_frame",
            type = "explore",
            title = "Explore Frame within a frame",
            referenceShotId = "legacy-reference-that-must-not-render",
            resultShotIds = listOf("result-1"),
            status = "completed",
            variations = listOf(
                VariationDto("obvious", "Make it obvious", "Let the frame dominate."),
                VariationDto("quiet", "Use it quietly", "Let the frame support."),
            ),
            variationObservations = listOf(
                VariationObservationDto("obvious", "result-1"),
            ),
        )
        val snapshot = MobileSnapshotDto(
            user = UserDto(id = "user-1", email = "photographer@example.com"),
            recentShots = listOf(
                ShotDto(id = "legacy-reference-that-must-not-render"),
                ShotDto(id = "result-1"),
            ),
            experiments = listOf(experiment),
        )
        compose.setContent {
            ShootsTheme {
                JourneyScreen(snapshot, imageUrl = { _ -> "" }, onShot = { _ -> })
            }
        }

        compose.onNodeWithText("1 VARIATIONS OBSERVED · NO VERDICT").performScrollTo().assertExists()
        compose.onNodeWithText("WHAT YOU TRIED").performScrollTo().assertExists()
        compose.onNodeWithText("MAKE IT OBVIOUS").performScrollTo().assertExists()
        compose.onAllNodesWithText("KEEPER REFERENCE").assertCountEquals(0)
        compose.onAllNodesWithText("ABSTENTION").assertCountEquals(0)
    }

    @Test
    fun interventionReceiptSeparatesAttemptFromObservableChange() {
        val snapshot = MobileSnapshotDto(
            user = UserDto(id = "user-1", email = "photographer@example.com"),
            recentInterventions = listOf(
                InterventionRecordDto(
                    id = "intervention-1",
                    shootId = "shoot-1",
                    shootRevision = 1,
                    route = "reproduce",
                    attemptState = "completed",
                    observableOutcome = "unchanged",
                    resultShotIds = listOf("result-1", "result-2"),
                    criteriaMetResults = 1,
                    abstentions = 1,
                    outcomeReason = "The comparable placement distribution did not change.",
                )
            ),
        )
        compose.setContent {
            ShootsTheme {
                JourneyScreen(snapshot, imageUrl = { _ -> "" }, onShot = { _ -> })
            }
        }

        compose.onNodeWithText("What happened to the last suggestion").performScrollTo().assertExists()
        compose.onNodeWithText("The comparable placement distribution did not change.").assertExists()
        compose.onNodeWithText(
            "2 result Shots · 1 matched every check · 1 could not be checked",
        ).assertExists()
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
        File(directory, name).outputStream().use { output ->
            compose.onRoot().captureToImage().asAndroidBitmap().compress(
                Bitmap.CompressFormat.PNG,
                100,
                output,
            )
        }
    }
}
