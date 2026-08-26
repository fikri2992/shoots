package com.shoots.app.data

import android.content.Context
import android.net.Uri
import com.shoots.app.BuildConfig
import com.shoots.app.phone.PhoneMediaStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.serialization.encodeToString
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.HttpException
import java.io.FileNotFoundException
import java.io.IOException
import java.io.File
import java.time.Instant

data class OperationFailure(
    val kind: String,
    val message: String,
    val retryable: Boolean,
)

class ShootsRepository(
    private val context: Context,
    private val api: ShootsApi,
    private val dao: ShootsDao,
    private val sessionStore: SessionStore,
    private val json: kotlinx.serialization.json.Json,
    val phoneSource: PhoneMediaStore,
) {
    val snapshot: Flow<MobileSnapshotDto?> = dao.observeResource(SNAPSHOT_KEY).map { resource ->
        resource?.payload?.let { runCatching { json.decodeFromString<MobileSnapshotDto>(it) }.getOrNull() }
    }
    val shots: Flow<List<ShotDto>> = dao.observeShots().map { rows ->
        rows.mapNotNull { runCatching { json.decodeFromString<ShotDto>(it.payload) }.getOrNull() }
    }
    val sourceState: Flow<SourceStateEntity?> = dao.observeSourceState()
    val pendingImports: Flow<List<ImportEntity>> = dao.observePendingImports()
    val latestLocalCaptureSession: Flow<LocalCaptureSessionEntity?> = dao.observeLatestCaptureSession()

    fun isSignedIn(): Boolean = sessionStore.isSignedIn()

    suspend fun createSession(idToken: String, nonce: String): UserDto {
        requireConfigured()
        val response = api.createAndroidSession(
            AndroidSessionRequest(idToken, nonce, android.os.Build.MODEL.ifBlank { "Android" })
        )
        sessionStore.putToken(response.token, response.expiresAt)
        return response.user
    }

    suspend fun refreshSnapshot(): Boolean {
        if (!isSignedIn()) return false
        requireConfigured()
        val cached = dao.resource(SNAPSHOT_KEY)
        val response = api.mobileSnapshot(cached?.etag?.takeIf(String::isNotBlank))
        val at = Instant.now().toString()
        val state = (dao.sourceState() ?: SourceStateEntity()).copy(
            lastSuccessfulSyncAt = at,
            lastError = "",
        )
        if (response.code() == 304) {
            dao.putSourceState(state)
            return false
        }
        if (!response.isSuccessful) throw HttpException(response)
        val value = response.body() ?: error("Snapshot response was empty")
        val shots = value.recentShots.map { shot -> cachedShot(shot, at) }
        dao.cacheSnapshot(
            CachedResourceEntity(
                key = SNAPSHOT_KEY,
                payload = json.encodeToString(value),
                etag = response.headers()["ETag"].orEmpty(),
                updatedAt = at,
            ),
            shots,
            state,
        )
        value.latestCaptureSession?.let { server ->
            val local = dao.captureSession(server.id)
            if (local != null) {
                dao.putCaptureSession(local.copy(state = server.status, error = ""))
            }
        }
        return true
    }

    suspend fun reserveCaptureSession(
        experimentId: String,
        variationId: String = "",
    ): LocalCaptureSessionEntity {
        require(isSignedIn()) { "Sign in is required" }
        phoneSource.prepareCaptureWatermark()
        val remote = api.reserveCaptureSession(
            CaptureSessionReserveRequest(experimentId, variationId)
        )
        val watermark = dao.sourceState() ?: SourceStateEntity()
        return LocalCaptureSessionEntity(
            id = remote.id,
            experimentId = remote.experimentId,
            variationId = remote.variationId,
            state = LocalCaptureState.RESERVED,
            baselineDateAdded = watermark.lastDateAdded,
            baselineMediaId = watermark.lastMediaId,
            reservedAt = remote.reservedAt,
            expiresAt = remote.expiresAt,
        ).also { dao.putCaptureSession(it) }
    }

    suspend fun finishCameraVisit(sessionId: String, selectedOnly: Boolean): Int {
        val session = dao.captureSession(sessionId) ?: error("Capture Session is not stored")
        if (selectedOnly) {
            dao.putCaptureSession(session.copy(state = LocalCaptureState.AWAITING_SELECTION))
            return 0
        }
        phoneSource.discover()
        val members = dao.sessionImports(sessionId)
        if (members.isEmpty()) return 0
        dao.putCaptureSession(session.copy(state = LocalCaptureState.MANIFEST_PENDING, error = ""))
        return members.size
    }

    suspend fun stageSelected(
        uris: List<Uri>,
        sessionId: String = "",
        sourceRole: String = "mine",
    ): Int {
        val inserted = phoneSource.stageSelected(uris, sessionId, sourceRole)
        if (sessionId.isNotBlank() && inserted > 0) {
            val session = dao.captureSession(sessionId) ?: error("Capture Session is not stored")
            dao.putCaptureSession(session.copy(state = LocalCaptureState.MANIFEST_PENDING, error = ""))
        }
        return inserted
    }

    suspend fun cancelCaptureSession(sessionId: String) {
        api.cancelCaptureSession(sessionId)
        val local = dao.captureSession(sessionId) ?: return
        dao.putCaptureSession(local.copy(state = LocalCaptureState.CANCELLED, error = ""))
    }

    suspend fun commitPendingManifest(): Int {
        val session = dao.activeCaptureSession()
            ?.takeIf { it.state == LocalCaptureState.MANIFEST_PENDING }
            ?: return 0
        val items = dao.sessionImports(session.id)
        if (items.isEmpty()) return 0
        try {
            api.commitCaptureManifest(
                session.id,
                CaptureManifestRequest(items.map { CaptureManifestMember(it.sourceId, it.manifestOrder) }),
            )
            dao.putCaptureSession(session.copy(state = LocalCaptureState.COMMITTED, error = ""))
            dao.setSessionImportState(session.id, ImportState.READY)
            return items.size
        } catch (exception: Exception) {
            val failure = classify(exception)
            if (failure.kind == ImportState.SESSION_CONFLICT) {
                dao.putCaptureSession(session.copy(state = LocalCaptureState.CONFLICT, error = failure.message))
                dao.setSessionImportState(session.id, ImportState.SESSION_CONFLICT, failure.message)
            } else if (failure.kind == ImportState.AUTH_REQUIRED) {
                dao.putCaptureSession(session.copy(error = failure.message))
                dao.setSessionImportState(session.id, ImportState.AUTH_REQUIRED, failure.message)
            }
            throw exception
        }
    }

    suspend fun uploadPending(): Int {
        val items = dao.importsInStates(listOf(ImportState.DISCOVERED, ImportState.READY))
        var uploaded = 0
        for (item in items) {
            dao.updateImport(item.copy(state = ImportState.UPLOADING, attemptCount = item.attemptCount + 1))
            try {
                val body = ContentUriRequestBody(
                    context.contentResolver,
                    Uri.parse(item.uri),
                    item.mimeType,
                    item.size,
                )
                val file = okhttp3.MultipartBody.Part.createFormData("file", item.displayName, body)
                val text = "text/plain".toMediaType()
                val response = api.uploadShot(
                    file,
                    item.sourceId.toRequestBody(text),
                    item.captureSessionId.takeIf(String::isNotBlank)?.toRequestBody(text),
                    item.sourceRole.toRequestBody(text),
                )
                dao.updateImport(
                    item.copy(
                        state = ImportState.UPLOADED,
                        shotId = response.shotId.ifBlank { response.inspirationId },
                        error = "",
                        attemptCount = item.attemptCount + 1,
                    )
                )
                uploaded += 1
            } catch (exception: Exception) {
                val failure = classify(exception)
                dao.updateImport(
                    item.copy(
                        state = failure.kind,
                        error = failure.message.take(300),
                        attemptCount = item.attemptCount + 1,
                    )
                )
                if (
                    failure.kind == ImportState.SESSION_CONFLICT &&
                    item.captureSessionId.isNotBlank()
                ) {
                    dao.captureSession(item.captureSessionId)?.let { session ->
                        dao.putCaptureSession(
                            session.copy(state = LocalCaptureState.CONFLICT, error = failure.message)
                        )
                    }
                }
                if (failure.retryable) throw exception
            }
        }
        return uploaded
    }

    suspend fun retryImport(sourceId: String) {
        val item = dao.importBySource(sourceId) ?: return
        dao.updateImport(item.copy(state = ImportState.DISCOVERED, error = ""))
    }

    suspend fun resumeAfterAuthentication() {
        for (item in dao.importsInStates(listOf(ImportState.AUTH_REQUIRED))) {
            val state = if (item.captureSessionId.isBlank()) {
                ImportState.DISCOVERED
            } else {
                when (dao.captureSession(item.captureSessionId)?.state) {
                    LocalCaptureState.COMMITTED, LocalCaptureState.PROCESSING -> ImportState.READY
                    else -> ImportState.MANIFEST_PENDING
                }
            }
            dao.updateImport(item.copy(state = state, error = ""))
        }
    }

    suspend fun importSessionAsFree(sessionId: String) {
        dao.detachSessionImports(sessionId)
        dao.captureSession(sessionId)?.let { session ->
            dao.putCaptureSession(
                session.copy(
                    state = LocalCaptureState.CANCELLED,
                    error = "Imported as free Shots by the photographer",
                )
            )
        }
    }

    fun observeShotDetail(id: String): Flow<ShotViewDto?> =
        dao.observeResource("shot:$id").map { resource ->
            resource?.payload?.let { runCatching { json.decodeFromString<ShotViewDto>(it) }.getOrNull() }
        }

    suspend fun refreshShot(id: String): ShotViewDto {
        return cacheShotView(api.shot(id))
    }

    suspend fun retryShot(id: String): ShotViewDto {
        return cacheShotView(api.retryShot(id))
    }

    private suspend fun cacheShotView(view: ShotViewDto): ShotViewDto {
        val at = Instant.now().toString()
        dao.putResource(CachedResourceEntity("shot:${view.shot.id}", json.encodeToString(view), updatedAt = at))
        dao.putShot(cachedShot(view.shot, at))
        return view
    }

    suspend fun loadShotPage(reset: Boolean = false): Boolean {
        val state = dao.resource(SHOTS_CURSOR_KEY)
        if (!reset && state != null && state.payload.isBlank()) return false
        val cursor = if (reset) null else state?.payload?.takeIf(String::isNotBlank)
        val response = api.shots(limit = 30, cursor = cursor)
        if (!response.isSuccessful) throw HttpException(response)
        val at = Instant.now().toString()
        val views = response.body().orEmpty()
        dao.putShots(views.map { cachedShot(it.shot, at) })
        views.forEach { view ->
            dao.putResource(
                CachedResourceEntity(
                    key = "shot:${view.shot.id}",
                    payload = json.encodeToString(view),
                    updatedAt = at,
                )
            )
        }
        val next = response.headers()["X-Next-Cursor"].orEmpty()
        dao.putResource(CachedResourceEntity(SHOTS_CURSOR_KEY, next, updatedAt = at))
        return next.isNotBlank()
    }

    suspend fun setKeeper(id: String, keeper: Boolean) {
        val shot = api.setKeeper(id, KeeperRequest(keeper))
        dao.putShot(cachedShot(shot, Instant.now().toString()))
        refreshShot(id)
    }

    suspend fun moveShotToInspiration(id: String) {
        api.setShotSourceRole(id, SourceRoleRequest("inspiration"))
        dao.deleteShot(id)
        dao.putResource(CachedResourceEntity("shot:$id", "", updatedAt = Instant.now().toString()))
        refreshSnapshot()
    }

    suspend fun moveInspirationToMine(id: String) {
        api.setInspirationSourceRole(id, SourceRoleRequest("mine"))
        refreshSnapshot()
        loadShotPage(reset = true)
    }

    suspend fun forgetPhotographerSignal(id: String) {
        api.removePhotographerSignal(id)
        refreshSnapshot()
    }

    suspend fun requestExperiment(force: Boolean): ExperimentDto? {
        val experiment = api.issueExperiment(force)
        refreshSnapshot()
        return experiment
    }

    suspend fun requestExplore(force: Boolean): ExperimentDto? {
        val experiment = api.issueExplore(force)
        refreshSnapshot()
        return experiment
    }

    suspend fun completeExplore(id: String) {
        api.completeExplore(id)
        refreshSnapshot()
    }

    suspend fun prepareDeconstruction(
        sourceType: String,
        sourceId: String,
        sourceRevision: Int,
        coverShotId: String,
    ): DeconstructionDto {
        val draft = api.prepareDeconstruction(
            DeconstructionPrepareRequest(sourceType, sourceId, sourceRevision, coverShotId)
        )
        refreshSnapshot()
        return draft
    }

    suspend fun answerScoutQuestion(
        shootId: String,
        revision: Int,
        optionId: String,
    ): ScoutAnswerDto {
        val answer = api.answerScoutQuestion(shootId, ScoutAnswerRequest(revision, optionId))
        refreshSnapshot()
        return answer
    }

    suspend fun cacheDeconstructionPages(draft: DeconstructionDto): List<File> {
        require(draft.status == "drafted" && draft.pages.isNotEmpty()) {
            "This Deconstruction has no rendered pages yet"
        }
        val folder = File(context.cacheDir, "deconstructions/${draft.id}")
        folder.mkdirs()
        folder.listFiles()?.forEach { it.delete() }
        return draft.pages.mapIndexed { index, page ->
            val target = File(folder, "page-${(index + 1).toString().padStart(2, '0')}.jpg")
            api.downloadBlob(blobUrl(page.blobPath)).byteStream().use { input ->
                target.outputStream().use(input::copyTo)
            }
            target
        }
    }

    suspend fun registerNotificationTarget(target: String) {
        if (isSignedIn()) api.setNotificationTarget(NotificationTargetRequest(target))
    }

    suspend fun connectDrive(code: String) {
        api.connectDrive(DriveAuthorizationRequest(code))
        refreshSnapshot()
    }

    suspend fun disconnectDrive() {
        api.disconnectDrive()
        refreshSnapshot()
    }

    suspend fun revokeDevice() {
        runCatching { api.revokeCurrentDevice() }
        clearLocalIdentity()
    }

    suspend fun deleteAccount(idToken: String, nonce: String) {
        api.deleteAccount(
            AndroidSessionRequest(idToken, nonce, android.os.Build.MODEL.ifBlank { "Android" })
        )
        clearLocalIdentity()
    }

    suspend fun clearLocalIdentity() {
        sessionStore.clearIdentity()
        context.getSystemService(android.app.NotificationManager::class.java).cancelAll()
        (context.applicationContext as? com.shoots.app.ShootsApplication)?.clearLocalData()
    }

    fun imageUrl(shot: ShotDto, original: Boolean = false): String {
        val path = if (original) shot.blobs["original"] else
            shot.blobs["thumb"] ?: shot.blobs["gridded"] ?: shot.blobs["original"]
        if (path.isNullOrBlank()) return ""
        return BuildConfig.SERVICE_ORIGIN.trimEnd('/') + "/api/blobs/" + path
    }

    fun blobUrl(path: String): String {
        if (path.isBlank()) return ""
        return BuildConfig.SERVICE_ORIGIN.trimEnd('/') + "/api/blobs/" + path
    }

    fun imageUrl(inspiration: InspirationDto): String {
        val path = inspiration.blobs["thumb"] ?: inspiration.blobs["original"]
        if (path.isNullOrBlank()) return ""
        return BuildConfig.SERVICE_ORIGIN.trimEnd('/') + "/api/blobs/" + path
    }

    fun classify(exception: Exception): OperationFailure {
        if (exception is HttpException) {
            val message = exception.response()?.errorBody()?.string().orEmpty()
                .takeIf(String::isNotBlank) ?: "Server returned ${exception.code()}"
            return when (exception.code()) {
                401 -> OperationFailure(ImportState.AUTH_REQUIRED, message, false)
                409 -> OperationFailure(ImportState.SESSION_CONFLICT, message, false)
                413, 415 -> OperationFailure(ImportState.UNSUPPORTED, message, false)
                in 500..599 -> OperationFailure(ImportState.DISCOVERED, message, true)
                else -> OperationFailure(ImportState.UNSUPPORTED, message, false)
            }
        }
        if (exception is SecurityException || exception is FileNotFoundException) {
            return OperationFailure(ImportState.MISSING, "Camera Shot is no longer readable", false)
        }
        if (exception is IOException) {
            return OperationFailure(ImportState.DISCOVERED, exception.message ?: "Network unavailable", true)
        }
        return OperationFailure(ImportState.UNSUPPORTED, exception.message ?: "Import stopped", false)
    }

    private fun cachedShot(shot: ShotDto, updatedAt: String) = CachedShotEntity(
        id = shot.id,
        payload = json.encodeToString(shot),
        sortTime = shot.displayTime,
        status = shot.status,
        kept = shot.keptAt != null,
        thumbPath = shot.blobs["thumb"] ?: shot.blobs["gridded"] ?: shot.blobs["original"].orEmpty(),
        updatedAt = updatedAt,
    )

    private fun requireConfigured() {
        check(BuildConfig.SERVICE_ORIGIN.isNotBlank()) {
            "This build has no HTTPS Shoots service origin"
        }
    }

    private companion object {
        const val SNAPSHOT_KEY = "mobile_snapshot"
        const val SHOTS_CURSOR_KEY = "shots_cursor"
    }
}
