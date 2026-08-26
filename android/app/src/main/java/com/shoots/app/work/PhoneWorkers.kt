package com.shoots.app.work

import android.content.Context
import android.provider.MediaStore
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequest
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import com.shoots.app.shootsApplication
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.HttpException
import java.util.concurrent.TimeUnit

class DiscoverCameraWorker(context: Context, params: WorkerParameters) :
    CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        runCatching { applicationContext.shootsApplication.container.phoneSource.discover() }
            .fold(
                onSuccess = { Result.success() },
                onFailure = { exception ->
                    if (exception is SecurityException) Result.failure() else Result.retry()
                },
            )
    }
}

class WatchCameraWorker(context: Context, params: WorkerParameters) :
    CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        runCatching { applicationContext.shootsApplication.container.phoneSource.discover() }
            .fold(
                onSuccess = {
                    PhoneSourceScheduler.enqueueProcessing(applicationContext)
                    Result.success()
                },
                onFailure = { exception ->
                    if (exception is SecurityException) Result.failure() else Result.retry()
                },
            )
    }
}

class CommitCaptureManifestWorker(context: Context, params: WorkerParameters) :
    CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val repository = applicationContext.shootsApplication.container.repository
        runCatching { repository.commitPendingManifest() }.fold(
            onSuccess = { Result.success() },
            onFailure = { exception ->
                if (repository.classify(exception as Exception).retryable) Result.retry() else Result.failure()
            },
        )
    }
}

class UploadShotsWorker(context: Context, params: WorkerParameters) :
    CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val repository = applicationContext.shootsApplication.container.repository
        runCatching { repository.uploadPending() }.fold(
            onSuccess = { Result.success() },
            onFailure = { exception ->
                if (repository.classify(exception as Exception).retryable) Result.retry() else Result.success()
            },
        )
    }
}

class RefreshSnapshotWorker(context: Context, params: WorkerParameters) :
    CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val repository = applicationContext.shootsApplication.container.repository
        runCatching { repository.refreshSnapshot() }.fold(
            onSuccess = {
                PhoneSourceScheduler.scheduleWatch(applicationContext)
                Result.success()
            },
            onFailure = { exception ->
                val retry = exception !is HttpException || exception.code() >= 500
                if (retry) Result.retry() else Result.failure()
            },
        )
    }
}

class RegisterNotificationWorker(context: Context, params: WorkerParameters) :
    CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val target = inputData.getString(TARGET).orEmpty()
        if (target.isBlank()) return@withContext Result.failure()
        val repository = applicationContext.shootsApplication.container.repository
        runCatching { repository.registerNotificationTarget(target) }.fold(
            onSuccess = { Result.success() },
            onFailure = { exception ->
                if (repository.classify(exception as Exception).retryable) Result.retry() else Result.failure()
            },
        )
    }

    companion object {
        const val TARGET = "target"
    }
}

object PhoneSourceScheduler {
    private const val SYNC_WORK = "phone-source-sync"
    private const val WATCH_WORK = "phone-source-watch"

    fun enqueueSync(context: Context) {
        val network = Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()
        val discover = request<DiscoverCameraWorker>()
        val commit = request<CommitCaptureManifestWorker>(network)
        val upload = request<UploadShotsWorker>(network)
        val snapshot = request<RefreshSnapshotWorker>(network)
        WorkManager.getInstance(context).beginUniqueWork(
            SYNC_WORK,
            ExistingWorkPolicy.APPEND_OR_REPLACE,
            discover,
        ).then(commit).then(upload).then(snapshot).enqueue()
    }

    fun enqueueProcessing(context: Context) {
        val network = Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()
        WorkManager.getInstance(context).beginUniqueWork(
            SYNC_WORK,
            ExistingWorkPolicy.APPEND_OR_REPLACE,
            request<CommitCaptureManifestWorker>(network),
        ).then(request<UploadShotsWorker>(network))
            .then(request<RefreshSnapshotWorker>(network))
            .enqueue()
    }

    suspend fun scheduleWatch(context: Context) {
        val app = context.shootsApplication
        val state = app.container.database.dao().sourceState() ?: return
        if (!state.enabled) return
        val constraints = Constraints.Builder()
            .addContentUriTrigger(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, true)
            .setTriggerContentUpdateDelay(2, TimeUnit.SECONDS)
            .setTriggerContentMaxDelay(15, TimeUnit.SECONDS)
            .build()
        WorkManager.getInstance(context).enqueueUniqueWork(
            WATCH_WORK,
            ExistingWorkPolicy.REPLACE,
            request<WatchCameraWorker>(constraints),
        )
    }

    fun registerNotificationTarget(context: Context, target: String) {
        val request = OneTimeWorkRequestBuilder<RegisterNotificationWorker>()
            .setInputData(workDataOf(RegisterNotificationWorker.TARGET to target))
            .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 15, TimeUnit.SECONDS)
            .build()
        WorkManager.getInstance(context).enqueueUniqueWork(
            "notification-target",
            ExistingWorkPolicy.REPLACE,
            request,
        )
    }

    private inline fun <reified T : androidx.work.ListenableWorker> request(
        constraints: Constraints = Constraints.Builder().build(),
    ): OneTimeWorkRequest = OneTimeWorkRequestBuilder<T>()
        .setConstraints(constraints)
        .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 15, TimeUnit.SECONDS)
        .build()
}
