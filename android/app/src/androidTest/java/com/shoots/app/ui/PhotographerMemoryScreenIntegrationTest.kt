package com.shoots.app.ui

import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.shoots.app.ShootsTheme
import com.shoots.app.data.MobileSnapshotDto
import com.shoots.app.data.PhotographerSignalDto
import com.shoots.app.data.UserDto
import com.shoots.app.phone.MediaAccess
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test

class PhotographerMemoryScreenIntegrationTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun settingsShowsAttributableMemoryAndLetsThePhotographerForgetOneFact() {
        var forgotten = ""
        val signal = PhotographerSignalDto(
            id = "signal_tripod",
            kind = "constraint",
            value = "tripod",
            source = "direct_statement",
        )
        compose.setContent {
            ShootsTheme {
                SettingsScreen(
                    snapshot = MobileSnapshotDto(
                        user = UserDto("user", "photographer@example.test"),
                        photographerSignals = listOf(signal),
                    ),
                    source = null,
                    mediaAccess = MediaAccess.NONE,
                    notificationsGranted = false,
                    busy = false,
                    onBack = {},
                    onRequestMedia = {},
                    onEnableSource = {},
                    onDisableSource = {},
                    onRequestNotifications = {},
                    onConnectDrive = {},
                    onDisconnectDrive = {},
                    onOpenDrive = {},
                    onForgetSignal = { forgotten = it },
                    onReauthenticate = {},
                    onRevoke = {},
                    onDelete = {},
                )
            }
        }

        compose.onNodeWithText("What Shoots remembers").performClick()
        compose.onNodeWithText("tripod").assertExists()
        compose.onNodeWithText("constraint · photographer").assertExists()
        compose.onNodeWithText("Forget").performClick()
        assertEquals(signal.id, forgotten)
    }
}
