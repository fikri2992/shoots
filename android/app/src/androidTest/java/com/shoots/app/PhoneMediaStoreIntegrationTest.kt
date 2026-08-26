package com.shoots.app

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import androidx.core.content.ContextCompat
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.shoots.app.data.SessionStore
import com.shoots.app.data.ShootsDatabase
import com.shoots.app.phone.PhoneMediaStore
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class PhoneMediaStoreIntegrationTest {
    private lateinit var context: Context
    private lateinit var database: ShootsDatabase
    private val databaseName = "shoots-media-integration.db"

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
    fun enablingFutureShotsQueriesTheRealCameraProvider() = runBlocking {
        assumeTrue(
            "Grant full image access for the physical-device acceptance run",
            ContextCompat.checkSelfPermission(context, Manifest.permission.READ_MEDIA_IMAGES) ==
                PackageManager.PERMISSION_GRANTED,
        )
        val source = PhoneMediaStore(context, database.dao(), SessionStore(context))

        source.enableFutureShots()

        assertTrue(database.dao().sourceState()?.enabled == true)
    }
}
