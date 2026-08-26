package com.shoots.app.ui

import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import com.shoots.app.ShootsTheme
import com.shoots.app.data.DeconstructionDto
import com.shoots.app.data.DeconstructionPageDto
import com.shoots.app.data.MobileSnapshotDto
import com.shoots.app.data.ProfileDto
import com.shoots.app.data.ShootReceiptDto
import com.shoots.app.data.ShootRecordDto
import com.shoots.app.data.ShotDto
import com.shoots.app.data.TechniqueNodeDto
import com.shoots.app.data.UserDto
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test

class JourneyScreenIntegrationTest {
    @get:Rule
    val compose = createComposeRule()

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
        compose.onNodeWithText("Tendency Profile").assertExists()
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
                    abstentions = 1,
                    positiveKeeperShots = 2,
                )
            ),
        )
        compose.setContent {
            ShootsTheme {
                JourneyScreen(snapshot, imageUrl = { _ -> "" }, onShot = { _ -> })
            }
        }

        compose.onNodeWithText("Techniques").performClick()
        compose.onNodeWithText("4 sightings · 3 corroborated Shots").assertExists()
        compose.onNodeWithText("2 Scenes · 1 Shoot").assertExists()
        compose.onNodeWithText("3 Reproduce results · 1 Criteria met · 1 abstention").assertExists()
        compose.onNodeWithText("2 marked Keepers").assertExists()
    }

    @Test
    fun photographerChoosesKeeperCoverBeforeCreatingDeconstruction() {
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

        compose.onNodeWithText("Create Deconstruction").performScrollTo().performClick()
        assertEquals("shoot:shoot-1:2:keeper-1", prepared)
    }

    @Test
    fun draftedDeconstructionOffersOneMultiPageShareAction() {
        var shared = ""
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
                )
            }
        }

        compose.onNodeWithText("Share 2-page carousel").performScrollTo().performClick()
        assertEquals("draft-1", shared)
    }
}
