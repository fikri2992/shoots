package com.shoots.app

import android.content.Context
import android.net.Uri
import android.provider.MediaStore
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.shoots.app.data.ImportState
import com.shoots.app.work.PhoneSourceScheduler
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class CorpusImportIntegrationTest {
    @Test
    fun stagesThePhotographyCorpusAsInspirationAndStartsRealWork() = runBlocking {
        assumeTrue(
            "Pass shootsImportCorpus=true only on the disposable emulator corpus",
            InstrumentationRegistry.getArguments().getString("shootsImportCorpus") == "true",
        )
        val context = ApplicationProvider.getApplicationContext<Context>()
        val app = context.shootsApplication
        assumeTrue("Sign in before importing the corpus", app.container.sessions.isSignedIn())

        val selected = corpusUris(context)
        assertEquals(CORPUS_NAMES, selected.keys.toList())

        val inserted = app.container.repository.stageSelected(
            selected.values.toList(),
            sourceRole = "inspiration",
        )
        assertTrue("Expected a first import or an idempotent rerun", inserted in 0..CORPUS_NAMES.size)

        val imports = app.container.database.dao().importsInStates(ALL_IMPORT_STATES)
            .filter { it.displayName in CORPUS_NAMES }
        assertEquals(CORPUS_NAMES.size, imports.size)
        assertTrue(imports.all { it.sourceRole == "inspiration" })

        PhoneSourceScheduler.enqueueSync(context)
    }

    private fun corpusUris(context: Context): LinkedHashMap<String, Uri> {
        val result = linkedMapOf<String, Uri>()
        val projection = arrayOf(
            MediaStore.Images.Media._ID,
            MediaStore.Images.Media.DISPLAY_NAME,
        )
        context.contentResolver.query(
            MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
            projection,
            "${MediaStore.Images.Media.RELATIVE_PATH} = ?",
            arrayOf("Pictures/ShootsTestCorpus/"),
            "${MediaStore.Images.Media.DISPLAY_NAME} ASC",
        )?.use { cursor ->
            val idIndex = cursor.getColumnIndexOrThrow(MediaStore.Images.Media._ID)
            val nameIndex = cursor.getColumnIndexOrThrow(MediaStore.Images.Media.DISPLAY_NAME)
            while (cursor.moveToNext()) {
                val name = cursor.getString(nameIndex)
                if (name in CORPUS_NAMES) {
                    result[name] = Uri.withAppendedPath(
                        MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
                        cursor.getLong(idIndex).toString(),
                    )
                }
            }
        }
        return LinkedHashMap(result.toSortedMap())
    }

    private companion object {
        val CORPUS_NAMES = (1..13).map { index ->
            when (index) {
                1 -> "01-panning-cyclist.jpg"
                2 -> "02-leading-lines-road.jpg"
                3 -> "03-window-portrait.jpg"
                4 -> "04-sunset-silhouette.jpg"
                5 -> "05-blue-hour-city.jpg"
                6 -> "06-complementary-colors.jpg"
                7 -> "07-rainy-night-street.jpg"
                8 -> "08-window-shadow.jpg"
                9 -> "09-flower-bokeh.jpg"
                10 -> "10-frame-within-frame.jpg"
                11 -> "11-intent-doorway-hard-light.png"
                12 -> "12-intent-panning-cyclist.png"
                else -> "13-intent-color-market.png"
            }
        }
        val ALL_IMPORT_STATES = listOf(
            ImportState.DISCOVERED,
            ImportState.MANIFEST_PENDING,
            ImportState.READY,
            ImportState.UPLOADING,
            ImportState.UPLOADED,
            ImportState.AUTH_REQUIRED,
            ImportState.SESSION_CONFLICT,
            ImportState.UNSUPPORTED,
            ImportState.MISSING,
        )
    }
}
