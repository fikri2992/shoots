package com.shoots.app.ui

import android.app.Activity
import android.app.Application
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.google.firebase.FirebaseApp
import com.google.firebase.installations.FirebaseInstallations
import com.google.firebase.messaging.FirebaseMessaging
import com.shoots.app.data.LocalCaptureSessionEntity
import com.shoots.app.data.DeconstructionDto
import com.shoots.app.data.ImportEntity
import com.shoots.app.data.InspirationDto
import com.shoots.app.data.MobileSnapshotDto
import com.shoots.app.data.ShotDto
import com.shoots.app.data.ShotViewDto
import com.shoots.app.data.SourceStateEntity
import com.shoots.app.identity.GoogleIdentity
import com.shoots.app.phone.MediaAccess
import com.shoots.app.shootsApplication
import com.shoots.app.work.PhoneSourceScheduler
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await
import kotlinx.coroutines.withContext
import java.io.File

class MainViewModel(application: Application) : AndroidViewModel(application) {
    private val app = application.shootsApplication
    private val repository = app.container.repository

    val snapshot: StateFlow<MobileSnapshotDto?> = repository.snapshot.stateIn(
        viewModelScope,
        SharingStarted.WhileSubscribed(5_000),
        null,
    )
    val shots: StateFlow<List<ShotDto>> = repository.shots.stateIn(
        viewModelScope,
        SharingStarted.WhileSubscribed(5_000),
        emptyList(),
    )
    val sourceState: StateFlow<SourceStateEntity?> = repository.sourceState.stateIn(
        viewModelScope,
        SharingStarted.WhileSubscribed(5_000),
        null,
    )
    val localCaptureSession: StateFlow<LocalCaptureSessionEntity?> =
        repository.latestLocalCaptureSession.stateIn(
            viewModelScope,
            SharingStarted.WhileSubscribed(5_000),
            null,
        )
    val pendingImports: StateFlow<List<ImportEntity>> = repository.pendingImports.stateIn(
        viewModelScope,
        SharingStarted.WhileSubscribed(5_000),
        emptyList(),
    )
    val signedIn = MutableStateFlow(repository.isSignedIn())
    val mediaAccess = MutableStateFlow(repository.phoneSource.access())
    val busy = MutableStateFlow(false)
    val error = MutableStateFlow("")
    val notice = MutableStateFlow("")
    val canLoadMoreShots = MutableStateFlow(true)
    private var shotDetailJob: Job? = null

    init {
        if (signedIn.value) sync()
    }

    suspend fun signIn(activity: Activity): Boolean = operate {
        val proof = GoogleIdentity(activity).proof()
        repository.createSession(proof.idToken, proof.nonce)
        repository.resumeAfterAuthentication()
        signedIn.value = true
        registerNotificationsIfAvailable()
        PhoneSourceScheduler.enqueueSync(app)
    }

    fun sync() {
        PhoneSourceScheduler.enqueueSync(app)
        viewModelScope.launch(Dispatchers.IO) {
            runCatching { repository.refreshSnapshot() }
                .onFailure(::recordFailure)
        }
    }

    suspend fun enableFutureShots(): Boolean = operate {
        repository.phoneSource.enableFutureShots()
        mediaAccess.value = repository.phoneSource.access()
        PhoneSourceScheduler.enqueueSync(app)
    }

    suspend fun disableFutureShots(): Boolean = operate {
        repository.phoneSource.disableFutureShots()
        PhoneSourceScheduler.scheduleWatch(app)
    }

    fun permissionChanged() {
        mediaAccess.value = repository.phoneSource.access()
        if (mediaAccess.value == MediaAccess.FULL) {
            viewModelScope.launch { enableFutureShots() }
        }
    }

    suspend fun reserveCaptureSession(
        experimentId: String,
        variationId: String = "",
    ): String? {
        var id: String? = null
        operate { id = repository.reserveCaptureSession(experimentId, variationId).id }
        return id
    }

    suspend fun finishCameraVisit(sessionId: String): Int {
        var members = 0
        operate {
            members = repository.finishCameraVisit(
                sessionId,
                mediaAccess.value == MediaAccess.SELECTED,
            )
            if (members > 0) PhoneSourceScheduler.enqueueSync(app)
        }
        return members
    }

    suspend fun stageSelected(
        uris: List<Uri>,
        sessionId: String = "",
        sourceRole: String = "mine",
    ): Boolean = operate {
        uris.forEach { uri ->
            runCatching {
                app.contentResolver.takePersistableUriPermission(
                    uri,
                    IntentFlags.READ,
                )
            }
        }
        val inserted = repository.stageSelected(uris, sessionId, sourceRole)
        val noun = if (sourceRole == "inspiration") "Inspiration" else "Shot"
        notice.value = if (inserted == 1) "1 $noun staged" else "$inserted ${noun}s staged"
        PhoneSourceScheduler.enqueueSync(app)
    }

    suspend fun cancelCaptureSession(id: String): Boolean = operate {
        repository.cancelCaptureSession(id)
        repository.refreshSnapshot()
    }

    suspend fun importSessionAsFree(id: String): Boolean = operate {
        repository.importSessionAsFree(id)
        PhoneSourceScheduler.enqueueSync(app)
        notice.value = "Those items will import as free Shots"
    }

    fun retryImport(sourceId: String) {
        viewModelScope.launch(Dispatchers.IO) {
            repository.retryImport(sourceId)
            PhoneSourceScheduler.enqueueSync(app)
        }
    }

    fun observeShotDetail(id: String) = repository.observeShotDetail(id)

    fun loadShot(id: String) {
        shotDetailJob?.cancel()
        shotDetailJob = viewModelScope.launch(Dispatchers.IO) {
            repeat(60) {
                val result = runCatching { repository.refreshShot(id) }
                if (result.isFailure) {
                    recordFailure(requireNotNull(result.exceptionOrNull()))
                    return@launch
                }
                val view = result.getOrThrow()
                if (
                    view.analysis != null ||
                    view.run?.status !in setOf("running", "retrying")
                ) {
                    return@launch
                }
                delay(3_000)
            }
        }
    }

    suspend fun retryShot(id: String): Boolean {
        val resumed = operate { repository.retryShot(id) }
        if (resumed) loadShot(id)
        return resumed
    }

    fun loadMoreShots(reset: Boolean = false) {
        if (busy.value || (!reset && !canLoadMoreShots.value)) return
        viewModelScope.launch {
            busy.value = true
            runCatching { withContext(Dispatchers.IO) { repository.loadShotPage(reset) } }
                .onSuccess { canLoadMoreShots.value = it }
                .onFailure(::recordFailure)
            busy.value = false
        }
    }

    suspend fun setKeeper(id: String, keeper: Boolean): Boolean = operate {
        repository.setKeeper(id, keeper)
        repository.refreshSnapshot()
    }

    suspend fun moveShotToInspiration(id: String): Boolean = operate {
        repository.moveShotToInspiration(id)
        notice.value = "Moved to Inspiration. It no longer changes your record."
    }

    suspend fun moveInspirationToMine(id: String): Boolean = operate {
        repository.moveInspirationToMine(id)
        notice.value = "Restored as your Shot. Shoots will rebuild your record."
    }

    suspend fun forgetPhotographerSignal(id: String): Boolean = operate {
        repository.forgetPhotographerSignal(id)
        notice.value = "Shoots forgot that statement."
    }

    suspend fun requestExperiment(force: Boolean = false): Boolean {
        var offered = false
        val completed = operate {
            val experiment = repository.requestExperiment(force)
            offered = experiment != null
            notice.value = if (experiment == null) {
                "No supported Experiment yet. Mark a Keeper with corroborated Evidence first."
            } else if (force) {
                "A different supported Experiment is ready"
            } else {
                "Your Experiment is ready"
            }
        }
        return completed && offered
    }

    suspend fun requestExplore(force: Boolean = false): Boolean {
        var offered = false
        val completed = operate {
            offered = repository.requestExplore(force) != null
            notice.value = if (offered) {
                "Optional Variations are ready"
            } else {
                "No supported Tendency Direction is ready for Explore."
            }
        }
        return completed && offered
    }

    suspend fun completeExplore(id: String): Boolean = operate {
        repository.completeExplore(id)
        notice.value = "Explore ended. Shoots kept the Variations you tried."
    }

    suspend fun prepareDeconstruction(
        sourceType: String,
        sourceId: String,
        sourceRevision: Int,
        coverShotId: String,
    ): Boolean = operate {
        repository.prepareDeconstruction(sourceType, sourceId, sourceRevision, coverShotId)
        notice.value = "Deconstruction draft is ready"
    }

    suspend fun answerScoutQuestion(
        shootId: String,
        revision: Int,
        optionId: String,
    ): Boolean = operate {
        val answer = repository.answerScoutQuestion(shootId, revision, optionId)
        notice.value = answer.detail
    }

    suspend fun cacheDeconstructionPages(draft: DeconstructionDto): List<File> =
        withContext(Dispatchers.IO) { repository.cacheDeconstructionPages(draft) }

    fun imageUrl(shot: ShotDto, original: Boolean = false): String =
        repository.imageUrl(shot, original)

    fun imageUrl(inspiration: InspirationDto): String = repository.imageUrl(inspiration)

    fun blobUrl(path: String): String = repository.blobUrl(path)

    suspend fun connectDrive(code: String): Boolean = operate {
        check(code.isNotBlank()) { "Google returned no Drive authorization code" }
        repository.connectDrive(code)
        notice.value = "Drive connected"
    }

    suspend fun disconnectDrive(): Boolean = operate {
        repository.disconnectDrive()
        notice.value = "Drive disconnected. Your Drive files remain yours."
    }

    suspend fun revoke(activity: Activity): Boolean = operate {
        repository.revokeDevice()
        GoogleIdentity(activity).clear()
        signedIn.value = false
    }

    suspend fun deleteAccount(activity: Activity): Boolean = operate {
        val proof = GoogleIdentity(activity).proof()
        repository.deleteAccount(proof.idToken, proof.nonce)
        GoogleIdentity(activity).clear()
        signedIn.value = false
    }

    suspend fun registerNotificationsIfAvailable(): Boolean = operate(showBusy = false) {
        if (FirebaseApp.getApps(app).isEmpty()) return@operate
        FirebaseMessaging.getInstance().register().await()
        repository.registerNotificationTarget(FirebaseInstallations.getInstance().id.await())
    }

    fun clearMessage() {
        error.value = ""
        notice.value = ""
    }

    private suspend fun operate(showBusy: Boolean = true, block: suspend () -> Unit): Boolean {
        if (showBusy) busy.value = true
        error.value = ""
        return try {
            withContext(Dispatchers.IO) { block() }
            true
        } catch (exception: Exception) {
            recordFailure(exception)
            false
        } finally {
            if (showBusy) busy.value = false
        }
    }

    private fun recordFailure(exception: Throwable) {
        if (isAuthenticationFailure(exception)) signedIn.value = false
        error.value = friendlyMessage(exception)
    }

    private object IntentFlags {
        const val READ = android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION
    }
}
