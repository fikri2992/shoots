package com.shoots.app.phone

import android.Manifest
import android.content.ContentResolver
import android.content.ContentUris
import android.content.Context
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.MediaStore
import androidx.core.content.ContextCompat
import com.shoots.app.data.ImportEntity
import com.shoots.app.data.LocalCaptureState
import com.shoots.app.data.SessionStore
import com.shoots.app.data.ShootsDao
import com.shoots.app.data.SourceStateEntity
import java.security.MessageDigest

enum class MediaAccess { NONE, SELECTED, FULL }

data class CameraItem(
    val uri: Uri,
    val id: Long,
    val dateAdded: Long,
    val size: Long,
    val displayName: String,
    val mimeType: String,
)

class PhoneMediaStore(
    private val context: Context,
    private val dao: ShootsDao,
    private val sessions: SessionStore,
) {
    fun access(): MediaAccess = when {
        Build.VERSION.SDK_INT >= 34 && granted(Manifest.permission.READ_MEDIA_IMAGES) ->
            MediaAccess.FULL
        Build.VERSION.SDK_INT >= 34 &&
            granted(Manifest.permission.READ_MEDIA_VISUAL_USER_SELECTED) -> MediaAccess.SELECTED
        Build.VERSION.SDK_INT >= 33 && granted(Manifest.permission.READ_MEDIA_IMAGES) ->
            MediaAccess.FULL
        Build.VERSION.SDK_INT <= 32 && granted(Manifest.permission.READ_EXTERNAL_STORAGE) ->
            MediaAccess.FULL
        else -> MediaAccess.NONE
    }

    suspend fun enableFutureShots() {
        check(access() == MediaAccess.FULL) { "Full Camera media access is required" }
        val latest = query(0, 0, newestFirst = true, limit = 1).firstOrNull()
        val state = dao.sourceState() ?: SourceStateEntity()
        dao.putSourceState(
            state.copy(
                enabled = true,
                lastDateAdded = latest?.dateAdded ?: state.lastDateAdded,
                lastMediaId = latest?.id ?: state.lastMediaId,
                lastError = "",
            )
        )
    }

    suspend fun disableFutureShots() {
        val state = dao.sourceState() ?: SourceStateEntity()
        dao.putSourceState(state.copy(enabled = false))
    }

    suspend fun discover(): Int {
        if (access() != MediaAccess.FULL) return 0
        val state = dao.sourceState() ?: SourceStateEntity()
        val active = dao.activeCaptureSession()
        if (!state.enabled && active?.state != LocalCaptureState.RESERVED) return 0
        val items = query(state.lastDateAdded, state.lastMediaId)
        if (items.isEmpty()) return 0
        val session = active?.takeIf { it.state == LocalCaptureState.RESERVED }
        val imports = items.map(::cameraImport)
        val last = items.last()
        return dao.discoverAndAdvance(
            imports,
            state.copy(lastDateAdded = last.dateAdded, lastMediaId = last.id, lastError = ""),
            session?.id.orEmpty(),
            session?.experimentId.orEmpty(),
        )
    }

    suspend fun prepareCaptureWatermark() {
        if (access() != MediaAccess.FULL) return
        val state = dao.sourceState() ?: SourceStateEntity()
        if (state.enabled) discover()
        val current = dao.sourceState() ?: state
        val latest = query(0, 0, newestFirst = true, limit = 1).firstOrNull() ?: return
        if (
            latest.dateAdded > current.lastDateAdded ||
            (latest.dateAdded == current.lastDateAdded && latest.id > current.lastMediaId)
        ) {
            dao.putSourceState(
                current.copy(lastDateAdded = latest.dateAdded, lastMediaId = latest.id)
            )
        }
    }

    suspend fun stageSelected(
        uris: List<Uri>,
        sessionId: String = "",
        sourceRole: String = "mine",
    ): Int {
        val localSession = sessionId.takeIf(String::isNotBlank)?.let { dao.captureSession(it) }
        val imports = uris.mapNotNull { uri ->
            describe(uri)?.let { selectedImport(it, sourceRole) }
        }
        return dao.insertSelectedImports(
            imports,
            localSession?.id.orEmpty(),
            localSession?.experimentId.orEmpty(),
        )
    }

    fun describe(uri: Uri): CameraItem? {
        val projection = arrayOf(
            MediaStore.Images.Media._ID,
            MediaStore.Images.Media.DISPLAY_NAME,
            MediaStore.Images.Media.MIME_TYPE,
            MediaStore.Images.Media.DATE_ADDED,
            MediaStore.Images.Media.SIZE,
        )
        return context.contentResolver.query(uri, projection, null, null, null)?.use { cursor ->
            if (!cursor.moveToFirst()) return@use null
            CameraItem(
                uri = uri,
                id = cursor.long(MediaStore.Images.Media._ID),
                dateAdded = cursor.long(MediaStore.Images.Media.DATE_ADDED),
                size = cursor.long(MediaStore.Images.Media.SIZE),
                displayName = cursor.string(MediaStore.Images.Media.DISPLAY_NAME, "Shot.jpg"),
                mimeType = cursor.string(MediaStore.Images.Media.MIME_TYPE, "image/jpeg"),
            )
        }
    }

    private fun cameraImport(item: CameraItem): ImportEntity {
        val source = "${sessions.deviceId()}:external:${item.id}:${item.dateAdded}:${item.size}"
        return item.toImport(source)
    }

    private fun selectedImport(item: CameraItem, sourceRole: String): ImportEntity {
        val digest = MessageDigest.getInstance("SHA-256")
            .digest("${item.uri}:${item.size}:${item.dateAdded}".toByteArray())
            .take(12)
            .joinToString("") { "%02x".format(it) }
        return item.toImport("${sessions.deviceId()}:selected:$digest").copy(sourceRole = sourceRole)
    }

    private fun CameraItem.toImport(source: String) = ImportEntity(
        sourceId = source,
        uri = uri.toString(),
        mediaId = id,
        dateAdded = dateAdded,
        size = size,
        displayName = displayName,
        mimeType = mimeType,
    )

    private fun query(
        afterDate: Long,
        afterId: Long,
        newestFirst: Boolean = false,
        limit: Int = 500,
    ): List<CameraItem> {
        val projection = arrayOf(
            MediaStore.Images.Media._ID,
            MediaStore.Images.Media.DISPLAY_NAME,
            MediaStore.Images.Media.MIME_TYPE,
            MediaStore.Images.Media.DATE_ADDED,
            MediaStore.Images.Media.SIZE,
        )
        val date = MediaStore.Images.Media.DATE_ADDED
        val id = MediaStore.Images.Media._ID
        val cameraClause = if (Build.VERSION.SDK_INT >= 29) {
            "${MediaStore.Images.Media.RELATIVE_PATH} LIKE ?"
        } else {
            "${MediaStore.Images.Media.BUCKET_DISPLAY_NAME} = ?"
        }
        val cameraValue = if (Build.VERSION.SDK_INT >= 29) "DCIM/Camera/%" else "Camera"
        val selection = "($date > ? OR ($date = ? AND $id > ?)) AND $cameraClause"
        val arguments = arrayOf(afterDate.toString(), afterDate.toString(), afterId.toString(), cameraValue)
        val order = if (newestFirst) "$date DESC, $id DESC" else "$date ASC, $id ASC"
        val queryArguments = Bundle().apply {
            putString(ContentResolver.QUERY_ARG_SQL_SELECTION, selection)
            putStringArray(ContentResolver.QUERY_ARG_SQL_SELECTION_ARGS, arguments)
            putString(ContentResolver.QUERY_ARG_SQL_SORT_ORDER, order)
            putInt(ContentResolver.QUERY_ARG_LIMIT, limit)
        }
        val result = mutableListOf<CameraItem>()
        context.contentResolver.query(
            MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
            projection,
            queryArguments,
            null,
        )?.use { cursor ->
            while (cursor.moveToNext()) {
                val mediaId = cursor.long(MediaStore.Images.Media._ID)
                result += CameraItem(
                    uri = ContentUris.withAppendedId(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, mediaId),
                    id = mediaId,
                    dateAdded = cursor.long(MediaStore.Images.Media.DATE_ADDED),
                    size = cursor.long(MediaStore.Images.Media.SIZE),
                    displayName = cursor.string(MediaStore.Images.Media.DISPLAY_NAME, "Shot.jpg"),
                    mimeType = cursor.string(MediaStore.Images.Media.MIME_TYPE, "image/jpeg"),
                )
            }
        }
        return result
    }

    private fun granted(permission: String): Boolean =
        ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED

    private fun android.database.Cursor.long(column: String): Long = getLong(getColumnIndexOrThrow(column))

    private fun android.database.Cursor.string(column: String, fallback: String): String =
        getString(getColumnIndexOrThrow(column)) ?: fallback
}
