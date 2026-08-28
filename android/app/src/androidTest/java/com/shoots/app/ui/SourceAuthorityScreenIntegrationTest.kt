package com.shoots.app.ui

import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import com.shoots.app.ShootsTheme
import com.shoots.app.data.InspirationDto
import com.shoots.app.data.ShotDto
import com.shoots.app.data.ShotViewDto
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

class SourceAuthorityScreenIntegrationTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun archiveSeparatesInspirationAndOffersExplicitRestoration() {
        var restored = ""
        var addRequested = false
        val shot = ShotDto(id = "mine", filename = "mine.jpg", status = "analyzed")
        val inspiration = InspirationDto(id = "reference", filename = "reference.jpg")

        compose.setContent {
            ShootsTheme {
                ShotsScreen(
                    shots = listOf(shot),
                    inspirations = listOf(inspiration),
                    pendingImports = emptyList(),
                    canLoadMore = false,
                    busy = false,
                    imageUrl = { "" },
                    inspirationUrl = { "" },
                    onShot = {},
                    onLoadMore = {},
                    onRetryImport = {},
                    onRestoreInspiration = { restored = it },
                    onReauthenticate = {},
                    onAdd = { addRequested = true },
                )
            }
        }

        compose.onNodeWithText("Add from gallery, Files, or Google Drive").performClick()
        assertTrue(addRequested)
        compose.onNodeWithText("References Shoots does not count as your work.")
            .performScrollTo()
            .assertExists()
        compose.onNodeWithText("Tap only if this is your Shot").performClick()
        assertEquals(inspiration.id, restored)
    }

    @Test
    fun shotRoleCorrectionExplainsItsMemoryEffectBeforeApplying() {
        var moved = false
        compose.setContent {
            ShootsTheme {
                ShotDetailScreen(
                    view = ShotViewDto(
                        shot = ShotDto(
                            id = "mine",
                            filename = "mine.jpg",
                            status = "analyzed",
                        )
                    ),
                    imageUrl = { _, _ -> "" },
                    blobUrl = { "" },
                    onBack = {},
                    onKeeper = {},
                    onMoveToInspiration = { moved = true },
                    onRetry = {},
                    onOpenDrive = {},
                )
            }
        }

        compose.onNodeWithText("This is Inspiration, not my Shot")
            .performScrollTo()
            .performClick()
        compose.onNodeWithText("Move to Inspiration?").assertExists()
        compose.onNodeWithText(
            "Shoots will keep the reference but stop using it in your Technique Map, Tendencies, Keepers, and Journey."
        ).assertExists()
        compose.onNodeWithText("Move").performClick()
        assertTrue(moved)
    }
}
