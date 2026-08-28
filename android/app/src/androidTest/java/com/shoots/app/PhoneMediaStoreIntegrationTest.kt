package com.shoots.app

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.provider.MediaStore
import androidx.core.content.ContextCompat
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.rule.GrantPermissionRule
import com.shoots.app.data.ImportState
import com.shoots.app.data.SessionStore
import com.shoots.app.data.ShootsDatabase
import com.shoots.app.data.SourceStateEntity
import com.shoots.app.phone.PhoneMediaStore
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class PhoneMediaStoreIntegrationTest {
    @get:Rule
    val mediaPermission: GrantPermissionRule = if (Build.VERSION.SDK_INT >= 33) {
        GrantPermissionRule.grant(Manifest.permission.READ_MEDIA_IMAGES)
    } else {
        GrantPermissionRule.grant(Manifest.permission.READ_EXTERNAL_STORAGE)
    }

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

    @Test
    fun learnsOneCameraAlbumFromAnExplicitVisitOutsideDcim() = runBlocking {
        val source = PhoneMediaStore(context, database.dao(), SessionStore(context))
        val projection = arrayOf(
            MediaStore.Images.Media._ID,
            MediaStore.Images.Media.DATE_ADDED,
            MediaStore.Images.Media.RELATIVE_PATH,
        )
        val cameraItem = context.contentResolver.query(
            MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
            projection,
            null,
            null,
            "${MediaStore.Images.Media.DATE_ADDED} DESC, ${MediaStore.Images.Media._ID} DESC",
        )?.use { cursor ->
            if (!cursor.moveToFirst()) null else Triple(
                cursor.getLong(cursor.getColumnIndexOrThrow(MediaStore.Images.Media._ID)),
                cursor.getLong(cursor.getColumnIndexOrThrow(MediaStore.Images.Media.DATE_ADDED)),
                cursor.getString(cursor.getColumnIndexOrThrow(MediaStore.Images.Media.RELATIVE_PATH)),
            )
        }
        assumeTrue("Capture one system Camera still first", cameraItem != null)
        val (mediaId, dateAdded, relativePath) = requireNotNull(cameraItem)
        assumeTrue(
            "The latest system Camera still already uses the conventional album",
            !relativePath.startsWith("DCIM/Camera/", ignoreCase = true),
        )
        database.dao().putSourceState(
            SourceStateEntity(
                enabled = true,
                cameraVisitActive = true,
                cameraVisitDateAdded = dateAdded,
                cameraVisitMediaId = (mediaId - 1).coerceAtLeast(0),
            )
        )

        assertTrue(source.completeCameraVisit() >= 1)

        val imports = database.dao().importsInStates(listOf(ImportState.DISCOVERED))
        assertTrue(imports.any { it.mediaId == mediaId })
        assertFalse(relativePath.startsWith("DCIM/Camera/", ignoreCase = true))
        assertTrue(database.dao().sourceState()?.approvedCameraPath == relativePath)
    }
}
