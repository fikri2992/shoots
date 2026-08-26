package com.shoots.app

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.shoots.app.data.ImportEntity
import com.shoots.app.data.LegacyStateMigrator
import com.shoots.app.data.LocalCaptureSessionEntity
import com.shoots.app.data.LocalCaptureState
import com.shoots.app.data.SessionStore
import com.shoots.app.data.ShootsDatabase
import com.shoots.app.data.SourceStateEntity
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class RoomQueueIntegrationTest {
    private lateinit var context: Context
    private lateinit var database: ShootsDatabase
    private val databaseName = "shoots-queue-integration.db"

    @Before
    fun setUp() {
        context = ApplicationProvider.getApplicationContext()
        context.deleteDatabase(databaseName)
        database = Room.databaseBuilder(context, ShootsDatabase::class.java, databaseName).build()
    }

    @After
    fun tearDown() {
        database.close()
        context.deleteDatabase(databaseName)
    }

    @Test
    fun discoveryAdvancesWatermarkAndFreezesFirstAssignmentInOneDatabase() = runBlocking {
        val dao = database.dao()
        dao.putCaptureSession(
            LocalCaptureSessionEntity(
                id = "capture-a",
                experimentId = "experiment-a",
                state = LocalCaptureState.RESERVED,
                baselineDateAdded = 10,
                baselineMediaId = 1,
                reservedAt = "2026-08-26T00:00:00Z",
                expiresAt = "2026-08-26T02:00:00Z",
            )
        )
        val first = ImportEntity(
            sourceId = "device:external:2:11:4096",
            uri = "content://media/external/images/media/2",
            mediaId = 2,
            dateAdded = 11,
            size = 4096,
            displayName = "IMG_2.jpg",
            mimeType = "image/jpeg",
        )
        val inserted = dao.discoverAndAdvance(
            listOf(first),
            SourceStateEntity(enabled = true, lastDateAdded = 11, lastMediaId = 2),
            "capture-a",
            "experiment-a",
        )
        assertEquals(1, inserted)
        assertEquals(11, dao.sourceState()?.lastDateAdded)
        assertEquals("capture-a", dao.importBySource(first.sourceId)?.captureSessionId)
        assertEquals(0, dao.importBySource(first.sourceId)?.manifestOrder)

        dao.putCaptureSession(
            LocalCaptureSessionEntity(
                id = "capture-b",
                experimentId = "experiment-b",
                state = LocalCaptureState.RESERVED,
                baselineDateAdded = 11,
                baselineMediaId = 2,
                reservedAt = "2026-08-26T03:00:00Z",
                expiresAt = "2026-08-26T05:00:00Z",
            )
        )
        dao.discoverAndAdvance(
            listOf(first),
            SourceStateEntity(enabled = true, lastDateAdded = 12, lastMediaId = 3),
            "capture-b",
            "experiment-b",
        )
        assertEquals("capture-a", dao.importBySource(first.sourceId)?.captureSessionId)

        database.close()
        database = Room.databaseBuilder(context, ShootsDatabase::class.java, databaseName).build()
        assertEquals("capture-a", database.dao().importBySource(first.sourceId)?.captureSessionId)
        assertEquals(12, database.dao().sourceState()?.lastDateAdded)
    }

    @Test
    fun legacyDeviceIdAndCameraWatermarkMigrateWithoutExperimentPreference() = runBlocking {
        val phone = context.getSharedPreferences("phone_source", Context.MODE_PRIVATE)
        val identity = context.getSharedPreferences("shoots", Context.MODE_PRIVATE)
        phone.edit()
            .putBoolean("enabled", true)
            .putLong("last_date", 321)
            .putLong("last_id", 654)
            .putString("experiment_id", "must-not-migrate")
            .commit()
        identity.edit().putString("device_id", "legacy-device-id").commit()

        LegacyStateMigrator(context, database.dao()).migrate()
        val sessions = SessionStore(context)

        assertEquals("legacy-device-id", sessions.deviceId())
        assertEquals(321, database.dao().sourceState()?.lastDateAdded)
        assertEquals(654, database.dao().sourceState()?.lastMediaId)
        assertTrue(database.dao().activeCaptureSession() == null)

        phone.edit().clear().commit()
        identity.edit().clear().commit()
    }
}
