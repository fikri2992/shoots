package com.shoots.app

import android.Manifest
import android.content.ContentUris
import android.content.Context
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.MediaStore
import androidx.core.content.ContextCompat
import androidx.work.Constraints
import androidx.work.BackoffPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import java.time.Instant
import java.util.concurrent.TimeUnit

object PhoneSource {
    private const val PREFS = "phone_source"
    private const val ENABLED = "enabled"
    private const val LAST_DATE = "last_date"
    private const val LAST_ID = "last_id"
    private const val DISCOVERED = "discovered"
    private const val UPLOADED = "uploaded"
    private const val SKIPPED = "skipped"
    private const val FAILED = "failed"
    private const val LAST_RUN = "last_run"
    private const val LAST_ACTIVITY = "last_activity"
    private const val ERROR = "error"
    private const val RUN_STATE = "run_state"
    private const val ATTEMPT = "attempt"
    private const val EXPERIMENT_ID = "experiment_id"
    private const val WATCH_WORK = "phone-source-watch"

    enum class Access { NONE, SELECTED, FULL }
    enum class RunState { IDLE, SCANNING, RETRYING }

    data class Status(
        val enabled: Boolean,
        val access: Access,
        val discovered: Int,
        val uploaded: Int,
        val skipped: Int,
        val failed: Int,
        val lastScan: String,
        val lastActivity: String,
        val error: String,
        val runState: RunState,
        val attempt: Int,
    )

    data class Candidate(
        val uri: Uri,
        val id: Long,
        val dateAdded: Long,
        val size: Long,
        val name: String,
        val mime: String,
    )

    fun access(context: Context): Access = when {
        Build.VERSION.SDK_INT >= 34 && granted(context, Manifest.permission.READ_MEDIA_IMAGES) ->
            Access.FULL
        Build.VERSION.SDK_INT >= 34 &&
            granted(context, Manifest.permission.READ_MEDIA_VISUAL_USER_SELECTED) -> Access.SELECTED
        Build.VERSION.SDK_INT >= 33 && granted(context, Manifest.permission.READ_MEDIA_IMAGES) ->
            Access.FULL
        Build.VERSION.SDK_INT <= 32 &&
            granted(context, Manifest.permission.READ_EXTERNAL_STORAGE) -> Access.FULL
        else -> Access.NONE
    }

    fun status(context: Context): Status {
        val prefs = prefs(context)
        return Status(
            enabled = prefs.getBoolean(ENABLED, false),
            access = access(context),
            discovered = prefs.getInt(DISCOVERED, 0),
            uploaded = prefs.getInt(UPLOADED, 0),
            skipped = prefs.getInt(SKIPPED, 0),
            failed = prefs.getInt(FAILED, 0),
            lastScan = prefs.getString(LAST_RUN, "").orEmpty(),
            lastActivity = prefs.getString(LAST_ACTIVITY, "").orEmpty(),
            error = prefs.getString(ERROR, "").orEmpty(),
            runState = runCatching {
                RunState.valueOf(prefs.getString(RUN_STATE, RunState.IDLE.name).orEmpty())
            }.getOrDefault(RunState.IDLE),
            attempt = prefs.getInt(ATTEMPT, 0),
        )
    }

    fun enable(context: Context) {
        val latest = latestCameraItem(context)
        prefs(context).edit()
            .putBoolean(ENABLED, true)
            .putLong(LAST_DATE, latest?.dateAdded ?: 0L)
            .putLong(LAST_ID, latest?.id ?: 0L)
            .putString(ERROR, "")
            .apply()
        scanNow(context)
    }

    fun disable(context: Context) {
        prefs(context).edit().putBoolean(ENABLED, false).apply()
        WorkManager.getInstance(context).cancelUniqueWork(WATCH_WORK)
    }

    fun selectedExperiment(context: Context): String =
        prefs(context).getString(EXPERIMENT_ID, "").orEmpty()

    fun selectExperiment(context: Context, experimentId: String) {
        prefs(context).edit().putString(EXPERIMENT_ID, experimentId).apply()
    }

    fun clearExperiment(context: Context) {
        prefs(context).edit().remove(EXPERIMENT_ID).apply()
    }

    fun scheduleWatch(context: Context) {
        if (!status(context).enabled || access(context) != Access.FULL) return
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .setRequiresBatteryNotLow(true)
            .addContentUriTrigger(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, true)
            .setTriggerContentUpdateDelay(2, TimeUnit.SECONDS)
            .setTriggerContentMaxDelay(15, TimeUnit.SECONDS)
            .build()
        val request = OneTimeWorkRequestBuilder<PhoneImportWorker>()
            .setConstraints(constraints)
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 15, TimeUnit.SECONDS)
            .build()
        WorkManager.getInstance(context).enqueueUniqueWork(
            WATCH_WORK,
            ExistingWorkPolicy.APPEND_OR_REPLACE,
            request,
        )
    }

    fun scanNow(context: Context) {
        if (!status(context).enabled || access(context) != Access.FULL) return
        val request = OneTimeWorkRequestBuilder<PhoneImportWorker>()
            .setConstraints(
                Constraints.Builder()
                    .setRequiredNetworkType(NetworkType.CONNECTED)
                    .setRequiresBatteryNotLow(true)
                    .build()
            )
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 15, TimeUnit.SECONDS)
            .build()
        WorkManager.getInstance(context).enqueueUniqueWork(
            WATCH_WORK,
            ExistingWorkPolicy.REPLACE,
            request,
        )
    }

    fun pending(context: Context): List<Candidate> {
        if (access(context) != Access.FULL) return emptyList()
        val state = prefs(context)
        return queryCamera(
            context,
            state.getLong(LAST_DATE, 0L),
            state.getLong(LAST_ID, 0L),
        )
    }

    fun checkpoint(context: Context, candidate: Candidate) {
        prefs(context).edit()
            .putLong(LAST_DATE, candidate.dateAdded)
            .putLong(LAST_ID, candidate.id)
            .apply()
    }

    fun recordRun(
        context: Context,
        discovered: Int,
        uploaded: Int,
        skipped: Int,
        failed: Int,
        error: String = "",
        willRetry: Boolean = false,
    ) {
        val at = Instant.now().toString()
        val editor = prefs(context).edit()
            .putString(LAST_RUN, at)
            .putString(ERROR, error.take(300))
            .putString(RUN_STATE, if (willRetry) RunState.RETRYING.name else RunState.IDLE.name)
        if (discovered > 0 || failed > 0) {
            editor
                .putInt(DISCOVERED, discovered)
                .putInt(UPLOADED, uploaded)
                .putInt(SKIPPED, skipped)
                .putInt(FAILED, failed)
                .putString(LAST_ACTIVITY, at)
        }
        editor.apply()
    }

    fun recordStarted(context: Context, attempt: Int) {
        prefs(context).edit()
            .putString(RUN_STATE, if (attempt > 0) RunState.RETRYING.name else RunState.SCANNING.name)
            .putInt(ATTEMPT, attempt)
            .apply()
    }

    fun describe(context: Context, uri: Uri): Candidate? {
        val projection = arrayOf(
            MediaStore.Images.Media._ID,
            MediaStore.Images.Media.DISPLAY_NAME,
            MediaStore.Images.Media.MIME_TYPE,
            MediaStore.Images.Media.DATE_ADDED,
            MediaStore.Images.Media.SIZE,
        )
        return context.contentResolver.query(uri, projection, null, null, null)?.use { cursor ->
            if (!cursor.moveToFirst()) return@use null
            Candidate(
                uri = uri,
                id = cursor.long(MediaStore.Images.Media._ID),
                dateAdded = cursor.long(MediaStore.Images.Media.DATE_ADDED),
                size = cursor.long(MediaStore.Images.Media.SIZE),
                name = cursor.string(MediaStore.Images.Media.DISPLAY_NAME, "shot.jpg"),
                mime = cursor.string(MediaStore.Images.Media.MIME_TYPE, "image/jpeg"),
            )
        }
    }

    private fun latestCameraItem(context: Context): Candidate? =
        queryCamera(context, 0L, 0L, limitOne = true).firstOrNull()

    private fun queryCamera(
        context: Context,
        afterDate: Long,
        afterId: Long,
        limitOne: Boolean = false,
    ): List<Candidate> {
        val projection = buildList {
            add(MediaStore.Images.Media._ID)
            add(MediaStore.Images.Media.DISPLAY_NAME)
            add(MediaStore.Images.Media.MIME_TYPE)
            add(MediaStore.Images.Media.DATE_ADDED)
            add(MediaStore.Images.Media.SIZE)
            add(MediaStore.Images.Media.BUCKET_DISPLAY_NAME)
            if (Build.VERSION.SDK_INT >= 29) add(MediaStore.Images.Media.RELATIVE_PATH)
        }.toTypedArray()
        val selection = "(${MediaStore.Images.Media.DATE_ADDED} > ? OR " +
            "(${MediaStore.Images.Media.DATE_ADDED} = ? AND ${MediaStore.Images.Media._ID} > ?))"
        val order = if (limitOne) {
            "${MediaStore.Images.Media.DATE_ADDED} DESC, ${MediaStore.Images.Media._ID} DESC"
        } else {
            "${MediaStore.Images.Media.DATE_ADDED} ASC, ${MediaStore.Images.Media._ID} ASC"
        }
        val rows = mutableListOf<Candidate>()
        context.contentResolver.query(
            MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
            projection,
            selection,
            arrayOf(afterDate.toString(), afterDate.toString(), afterId.toString()),
            order,
        )?.use { cursor ->
            while (cursor.moveToNext()) {
                val bucket = cursor.string(MediaStore.Images.Media.BUCKET_DISPLAY_NAME, "")
                val relative = if (Build.VERSION.SDK_INT >= 29) {
                    cursor.string(MediaStore.Images.Media.RELATIVE_PATH, "")
                } else ""
                if (!bucket.equals("Camera", ignoreCase = true) &&
                    !relative.startsWith("DCIM/Camera", ignoreCase = true)
                ) continue
                val id = cursor.long(MediaStore.Images.Media._ID)
                rows += Candidate(
                    uri = ContentUris.withAppendedId(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, id),
                    id = id,
                    dateAdded = cursor.long(MediaStore.Images.Media.DATE_ADDED),
                    size = cursor.long(MediaStore.Images.Media.SIZE),
                    name = cursor.string(MediaStore.Images.Media.DISPLAY_NAME, "shot.jpg"),
                    mime = cursor.string(MediaStore.Images.Media.MIME_TYPE, "image/jpeg"),
                )
                if (limitOne) break
            }
        }
        return if (limitOne) rows.take(1) else rows
    }

    private fun android.database.Cursor.long(column: String): Long =
        getLong(getColumnIndexOrThrow(column))

    private fun android.database.Cursor.string(column: String, fallback: String): String {
        val index = getColumnIndex(column)
        return if (index < 0 || isNull(index)) fallback else getString(index).orEmpty().ifBlank { fallback }
    }

    private fun granted(context: Context, permission: String): Boolean =
        ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED

    private fun prefs(context: Context) =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
}
