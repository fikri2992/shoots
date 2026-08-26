package com.shoots.app.ui

import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.shoots.app.ShootsTheme
import com.shoots.app.data.MobileSnapshotDto
import com.shoots.app.data.ProfileDto
import com.shoots.app.data.TechniqueNodeDto
import com.shoots.app.data.UserDto
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
}
