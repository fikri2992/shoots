package com.shoots.app.media

import android.Manifest
import android.content.ContentValues
import android.content.Context
import android.content.pm.PackageManager
import android.media.MediaScannerConnection
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import androidx.core.content.ContextCompat
import com.shoots.app.data.DeconstructionDto
import java.io.File

object StoryMediaSaver {
    fun save(context: Context, draft: DeconstructionDto, files: List<File>): Int {
        require(files.isNotEmpty()) { "This story has no finished pages yet" }
        val safeId = draft.id.replace(Regex("[^A-Za-z0-9._-]"), "-")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val inserted = mutableListOf<android.net.Uri>()
            try {
                files.forEachIndexed { index, file ->
                    val values = ContentValues().apply {
                        put(
                            MediaStore.Images.Media.DISPLAY_NAME,
                            displayName(safeId, index),
                        )
                        put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg")
                        put(
                            MediaStore.Images.Media.RELATIVE_PATH,
                            "${Environment.DIRECTORY_PICTURES}/Shoots",
                        )
                        put(MediaStore.Images.Media.IS_PENDING, 1)
                    }
                    val uri = context.contentResolver.insert(
                        MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
                        values,
                    ) ?: error("Android could not create a Pictures entry")
                    inserted += uri
                    context.contentResolver.openOutputStream(uri)?.use { output ->
                        file.inputStream().use { input -> input.copyTo(output) }
                    } ?: error("Android could not open the Pictures entry")
                    check(
                        context.contentResolver.update(
                            uri,
                            ContentValues().apply { put(MediaStore.Images.Media.IS_PENDING, 0) },
                            null,
                            null,
                        ) == 1,
                    ) { "Android could not finish the Pictures entry" }
                }
            } catch (exception: Exception) {
                inserted.forEach { context.contentResolver.delete(it, null, null) }
                throw exception
            }
            return files.size
        }

        check(
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.WRITE_EXTERNAL_STORAGE,
            ) == PackageManager.PERMISSION_GRANTED,
        ) { "Allow storage access to save this story to Pictures/Shoots" }
        @Suppress("DEPRECATION")
        val folder = File(
            Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES),
            "Shoots",
        )
        check(folder.isDirectory || folder.mkdirs()) {
            "Android could not create Pictures/Shoots"
        }
        val targets = files.mapIndexed { index, file ->
            File(folder, displayName(safeId, index))
                .also { target -> file.copyTo(target, overwrite = true) }
        }
        MediaScannerConnection.scanFile(
            context,
            targets.map(File::getAbsolutePath).toTypedArray(),
            Array(targets.size) { "image/jpeg" },
            null,
        )
        return targets.size
    }

    private fun displayName(safeId: String, index: Int): String =
        "Shoots-$safeId-${(index + 1).toString().padStart(2, '0')}.jpg"
}
