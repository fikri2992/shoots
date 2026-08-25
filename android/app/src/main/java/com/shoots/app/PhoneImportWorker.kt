package com.shoots.app

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class PhoneImportWorker(
    appContext: Context,
    params: WorkerParameters,
) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        PhoneSource.recordStarted(applicationContext, runAttemptCount)
        val pending = runCatching { PhoneSource.pending(applicationContext) }.getOrElse { exception ->
            val willRetry = exception !is SecurityException
            PhoneSource.recordRun(
                applicationContext,
                0,
                0,
                0,
                1,
                exception.message ?: exception.javaClass.simpleName,
                willRetry = willRetry,
            )
            return@withContext if (willRetry) Result.retry() else Result.failure()
        }
        var uploaded = 0
        var skipped = 0
        var failed = 0
        var error = ""
        var experimentId = PhoneSource.selectedExperiment(applicationContext)
        if (experimentId.isNotBlank()) {
            val open = Api.fetchOpenExperiment(applicationContext).getOrElse { exception ->
                PhoneSource.recordRun(
                    applicationContext,
                    pending.size,
                    uploaded,
                    skipped,
                    1,
                    exception.message ?: exception.javaClass.simpleName,
                    willRetry = true,
                )
                return@withContext Result.retry()
            }
            if (open?.id != experimentId) {
                PhoneSource.clearExperiment(applicationContext)
                experimentId = ""
            }
        }
        for (candidate in pending) {
            try {
                val bytes = applicationContext.contentResolver.openInputStream(candidate.uri)
                    ?.use { it.readBytes() }
                    ?: error("Camera Shot is no longer readable")
                val sourceId = "external:${candidate.id}:${candidate.dateAdded}:${candidate.size}"
                val imported = Api.importShot(
                    applicationContext,
                    bytes,
                    candidate.name,
                    candidate.mime,
                    sourceId,
                    experimentId,
                ).getOrThrow()
                if (imported.created) uploaded += 1 else skipped += 1
                PhoneSource.checkpoint(applicationContext, candidate)
            } catch (exception: Exception) {
                failed += 1
                error = exception.message ?: exception.javaClass.simpleName
                break
            }
        }
        PhoneSource.recordRun(
            applicationContext,
            pending.size,
            uploaded,
            skipped,
            failed,
            error,
            willRetry = failed > 0,
        )
        if (failed > 0) {
            Result.retry()
        } else {
            PhoneSource.scheduleWatch(applicationContext)
            Result.success()
        }
    }
}
