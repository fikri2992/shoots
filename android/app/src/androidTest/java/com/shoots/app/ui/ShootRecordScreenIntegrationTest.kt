package com.shoots.app.ui

import android.graphics.Bitmap
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.onAllNodesWithContentDescription
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTouchInput
import androidx.compose.ui.test.swipeUp
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.test.platform.app.InstrumentationRegistry
import com.shoots.app.ShootsTheme
import com.shoots.app.data.ShootReceiptDto
import com.shoots.app.data.ShootRecordDto
import com.shoots.app.data.ShotDto
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import java.io.File

class ShootRecordScreenIntegrationTest {
    @get:Rule
    val compose = createComposeRule()

    private val fixtureUrl = "android.resource://com.shoots.app/drawable/visual_story_fixture"

    @Test
    fun completeRecordShowsTheWorkAndKeepsThePhotographerDecisionSmall() {
        var keeperChange = ""
        val shot = ShotDto(
            id = "shot-1",
            filename = "IMG_0001.jpg",
            status = "analyzed",
            ingestedAt = "2026-08-31T01:00:00Z",
        )
        val record = ShootRecordDto(
            shootId = "shoot-1",
            revision = 2,
            shotIds = listOf(shot.id),
            runOutcomes = mapOf(shot.id to "completed"),
            receipt = ShootReceiptDto(
                summary = "1 Shot across 1 Scene.",
                shotCount = 1,
                sceneCount = 1,
                readableShotCount = 1,
                repeated = listOf("The frame stayed quiet around the subject."),
                varied = listOf("You changed the distance once."),
            ),
            settledAt = "2026-08-31T01:03:00Z",
        )

        compose.setContent {
            ShootsTheme {
                ShootRecordScreen(
                    record = record,
                    shoot = null,
                    shots = listOf(shot),
                    interventions = emptyList(),
                    answers = emptyList(),
                    imageUrl = { fixtureUrl },
                    onBack = {},
                    onShot = {},
                    onKeeper = { id, keep -> keeperChange = "$id:$keep" },
                )
            }
        }

        waitForImage("IMG_0001.jpg")
        saveScreenshot("shoot-record-opening.png")
        compose.onNodeWithText("The work Shoots finished").performScrollTo().assertExists()
        compose.onNodeWithText("Collected").assertExists()
        compose.onNodeWithText("Read").assertExists()
        compose.onNodeWithText("Grouped").assertExists()
        compose.onNodeWithText("Revision 2 was stored only after every run reached an outcome.").assertExists()
        compose.onNodeWithText("Who did what").performScrollTo().assertExists()
        compose.onNodeWithText("No Keeper mark or Experiment choice was required.").assertExists()
        compose.onNodeWithText("Every Shot in this Shoot").performScrollTo().assertIsDisplayed()
        compose.onRoot().performTouchInput { swipeUp() }
        saveScreenshot("shoot-record-keeper.png")
        compose.onNodeWithContentDescription("Mark as Keeper").assertIsDisplayed().performClick()
        assertEquals("shot-1:true", keeperChange)
    }

    private fun waitForImage(contentDescription: String) {
        compose.waitUntil(timeoutMillis = 5_000) {
            runCatching {
                val bitmap = compose.onAllNodesWithContentDescription(contentDescription)[0]
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
