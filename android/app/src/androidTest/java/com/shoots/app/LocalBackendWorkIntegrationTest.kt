package com.shoots.app

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkInfo
import androidx.work.WorkManager
import com.shoots.app.work.RefreshSnapshotWorker
import kotlinx.coroutines.delay
import org.junit.Assert.assertEquals
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout

/**
 * Runs only in the disposable physical-device acceptance invocation:
 * adb reverse tcp:8000 tcp:8000
 * connectedAndroidTest -Pandroid.testInstrumentationRunnerArguments.shootsDeviceToken=...
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
}
