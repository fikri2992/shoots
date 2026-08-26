package com.shoots.app.ui

import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.shoots.app.ShootsTheme
import com.shoots.app.data.MobileSnapshotDto
import com.shoots.app.data.ProfileDto
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
}
