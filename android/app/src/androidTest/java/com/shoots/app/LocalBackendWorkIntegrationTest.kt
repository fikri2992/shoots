package com.shoots.app

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkInfo
import androidx.work.WorkManager
import com.shoots.app.ui.MainViewModel
import com.shoots.app.ui.friendlyMessage
import com.shoots.app.work.RefreshSnapshotWorker
import kotlinx.coroutines.delay
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.IOException
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout

/**
 * Runs only with a disposable device token. Local acceptance uses adb reverse.
 * Production acceptance also supplies SHOOTS_DEBUG_SERVICE_ORIGIN so a debug
 * build does not intentionally use its localhost default.
 */
@RunWith(AndroidJUnit4::class)
class LocalBackendWorkIntegrationTest {
    @Test
    fun workManagerRefreshesRoomThroughTheRunningBackend() = runBlocking {
        val token = InstrumentationRegistry.getArguments().getString("shootsDeviceToken").orEmpty()
        assumeTrue("Pass a disposable device token for the adb-reversed backend", token.isNotBlank())
        val context = ApplicationProvider.getApplicationContext<Context>()
        val app = context.shootsApplication
        app.container.sessions.putToken(token, "")
        val request = OneTimeWorkRequestBuilder<RefreshSnapshotWorker>().build()
        val manager = WorkManager.getInstance(context)
        manager.enqueue(request).result.get(20, TimeUnit.SECONDS)
        val state = withTimeout(20_000) {
            var current: WorkInfo
            do {
                current = requireNotNull(
                    manager.getWorkInfoById(request.id).get(2, TimeUnit.SECONDS)
                )
                if (!current.state.isFinished) delay(100)
            } while (!current.state.isFinished)
            current
        }
        assertEquals(WorkInfo.State.SUCCEEDED, state.state)
        val snapshot = app.container.database.dao().resource("mobile_snapshot")
        assumeTrue("Backend returned a mobile snapshot", snapshot != null)
    }

    @Test
    fun successfulBackgroundRefreshClearsAStaleConnectivityError() = runBlocking {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val app = context.shootsApplication
        val suppliedToken =
            InstrumentationRegistry.getArguments().getString("shootsDeviceToken").orEmpty()
        if (suppliedToken.isNotBlank()) app.container.sessions.putToken(suppliedToken, "")
        assumeTrue("Run on a signed-in acceptance device", app.container.sessions.isSignedIn())

        val viewModel = MainViewModel(app)
        val firstSyncAt = withTimeout(20_000) {
            var value: String
            do {
                value = app.container.database.dao().sourceState()?.lastSuccessfulSyncAt.orEmpty()
                if (value.isBlank()) delay(100)
            } while (value.isBlank())
            value
        }
        delay(500)
        viewModel.error.value = friendlyMessage(IOException("Network is unreachable"))

        val request = OneTimeWorkRequestBuilder<RefreshSnapshotWorker>().build()
        val manager = WorkManager.getInstance(context)
        manager.enqueue(request).result.get(20, TimeUnit.SECONDS)
        val state = withTimeout(20_000) {
            var current: WorkInfo
            do {
                current = requireNotNull(manager.getWorkInfoById(request.id).get(2, TimeUnit.SECONDS))
                if (!current.state.isFinished) delay(100)
            } while (!current.state.isFinished)
            current
        }

        assertEquals(WorkInfo.State.SUCCEEDED, state.state)
        withTimeout(5_000) {
            while (viewModel.error.value.isNotBlank()) delay(50)
        }
        assertEquals("", viewModel.error.value)
        val refreshedAt = app.container.database.dao().sourceState()?.lastSuccessfulSyncAt.orEmpty()
        assertNotEquals(firstSyncAt, refreshedAt)
    }
}
