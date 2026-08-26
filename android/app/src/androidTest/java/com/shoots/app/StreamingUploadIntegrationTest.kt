package com.shoots.app

import android.content.ContentValues
import android.content.Context
import android.os.Build
import android.provider.MediaStore
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.shoots.app.data.ContentUriRequestBody
import okio.Buffer
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class StreamingUploadIntegrationTest {
    @Test
    fun contentResolverOriginalStreamsIntoOkHttpRequestBody() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val expected = ByteArray(2 * 1024 * 1024) { index -> (index % 251).toByte() }
        val values = ContentValues().apply {
            put(MediaStore.Images.Media.DISPLAY_NAME, "shoots-stream-test.jpg")
            put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg")
            if (Build.VERSION.SDK_INT >= 29) {
                put(MediaStore.Images.Media.RELATIVE_PATH, "Pictures/ShootsIntegration")
                put(MediaStore.Images.Media.IS_PENDING, 1)
            }
        }
        val uri = requireNotNull(
            context.contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
        )
        try {
            context.contentResolver.openOutputStream(uri)!!.use { it.write(expected) }
            if (Build.VERSION.SDK_INT >= 29) {
                context.contentResolver.update(
                    uri,
                    ContentValues().apply { put(MediaStore.Images.Media.IS_PENDING, 0) },
                    null,
                    null,
                )
            }
            val body = ContentUriRequestBody(context.contentResolver, uri, "image/jpeg", expected.size.toLong())
            val sink = Buffer()
            body.writeTo(sink)
            assertEquals(expected.size.toLong(), body.contentLength())
            assertArrayEquals(expected, sink.readByteArray())
        } finally {
            context.contentResolver.delete(uri, null, null)
        }
    }
}
