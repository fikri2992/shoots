package com.shoots.app.media

import android.content.ContentUris
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color
import android.os.Build
import android.provider.MediaStore
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.shoots.app.data.DeconstructionDto
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class StoryMediaSaverIntegrationTest {
    private val context = ApplicationProvider.getApplicationContext<Context>()
    private val createdUris = mutableListOf<android.net.Uri>()

    @After
    fun removeSavedTestPages() {
        createdUris.forEach { context.contentResolver.delete(it, null, null) }
    }

    @Test
    fun draftedPagesAreWrittenToPublicPicturesAndRemainReadable() {
        assumeTrue(Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q)
        val uniqueId = "media-test-${System.nanoTime()}"
        val files = listOf(
            jpegFile("$uniqueId-source-1.jpg", Color.RED),
            jpegFile("$uniqueId-source-2.jpg", Color.BLUE),
        )
        val draft = DeconstructionDto(
            id = uniqueId,
            sourceType = "shoot",
            sourceId = "shoot-1",
            sourceRevision = 1,
            status = "drafted",
        )

        assertEquals(2, StoryMediaSaver.save(context, draft, files))

        val expectedNames = files.indices.map { index ->
            "Shoots-$uniqueId-${(index + 1).toString().padStart(2, '0')}.jpg"
        }
        val observed = querySavedPages(expectedNames)
        assertEquals(expectedNames.toSet(), observed.keys)
        observed.forEach { (_, page) ->
            assertTrue(page.relativePath.contains("Pictures/Shoots"))
            assertTrue(page.bytes > 0)
            context.contentResolver.openInputStream(page.uri).use { input ->
                val bitmap = BitmapFactory.decodeStream(input)
                assertEquals(12, bitmap.width)
                assertEquals(12, bitmap.height)
            }
        }
    }

    private fun jpegFile(name: String, colour: Int): File =
        File(context.cacheDir, name).also { file ->
            file.outputStream().use { output ->
                Bitmap.createBitmap(12, 12, Bitmap.Config.ARGB_8888).apply {
                    eraseColor(colour)
                    compress(Bitmap.CompressFormat.JPEG, 95, output)
                    recycle()
                }
            }
        }

    private fun querySavedPages(names: List<String>): Map<String, SavedPage> {
        val projection = arrayOf(
            MediaStore.Images.Media._ID,
            MediaStore.Images.Media.DISPLAY_NAME,
            MediaStore.Images.Media.RELATIVE_PATH,
            MediaStore.Images.Media.SIZE,
        )
        val placeholders = names.joinToString(",") { "?" }
        val result = linkedMapOf<String, SavedPage>()
        context.contentResolver.query(
            MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
            projection,
            "${MediaStore.Images.Media.DISPLAY_NAME} IN ($placeholders)",
            names.toTypedArray(),
            null,
        )?.use { cursor ->
            val idColumn = cursor.getColumnIndexOrThrow(MediaStore.Images.Media._ID)
            val nameColumn = cursor.getColumnIndexOrThrow(MediaStore.Images.Media.DISPLAY_NAME)
            val pathColumn = cursor.getColumnIndexOrThrow(MediaStore.Images.Media.RELATIVE_PATH)
            val sizeColumn = cursor.getColumnIndexOrThrow(MediaStore.Images.Media.SIZE)
            while (cursor.moveToNext()) {
                val uri = ContentUris.withAppendedId(
                    MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
                    cursor.getLong(idColumn),
                )
                createdUris += uri
                result[cursor.getString(nameColumn)] = SavedPage(
                    uri = uri,
                    relativePath = cursor.getString(pathColumn),
                    bytes = cursor.getLong(sizeColumn),
                )
            }
        }
        return result
    }
}

private data class SavedPage(
    val uri: android.net.Uri,
    val relativePath: String,
    val bytes: Long,
)
