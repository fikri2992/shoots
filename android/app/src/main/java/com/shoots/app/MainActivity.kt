package com.shoots.app

import android.Manifest
import android.content.ClipData
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.MediaStore
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.IntentSenderRequest
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.shoots.app.identity.DriveAuthorization
import com.shoots.app.phone.MediaAccess
import com.shoots.app.ui.AppActions
import com.shoots.app.ui.MainViewModel
import com.shoots.app.ui.ShootsApp
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    private val viewModel: MainViewModel by viewModels()
    private val deepRoute = MutableStateFlow("")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        deepRoute.value = routeFrom(intent)
        enableEdgeToEdge()
        setContent {
            ShootsTheme {
                val scope = rememberCoroutineScope()
                val currentDeepRoute by deepRoute.collectAsStateWithLifecycle()
                val access by viewModel.mediaAccess.collectAsStateWithLifecycle()
                var cameraSessionId by remember { mutableStateOf("") }
                var pickerSessionId by remember { mutableStateOf("") }
                var pickerSourceRole by remember { mutableStateOf("mine") }
                var chooseSourceRole by remember { mutableStateOf(false) }
                var notificationsGranted by remember { mutableStateOf(hasNotificationPermission()) }
                val drive = remember { DriveAuthorization(this) }

                val picker = rememberLauncherForActivityResult(
                    ActivityResultContracts.PickMultipleVisualMedia(50)
                ) { uris ->
                    val session = pickerSessionId
                    val sourceRole = pickerSourceRole
                    pickerSessionId = ""
                    pickerSourceRole = "mine"
                    if (uris.isNotEmpty()) {
                        scope.launch { viewModel.stageSelected(uris, session, sourceRole) }
                    }
                }
                val camera = rememberLauncherForActivityResult(
                    ActivityResultContracts.StartActivityForResult()
                ) {
                    val session = cameraSessionId
                    cameraSessionId = ""
                    if (session.isNotBlank()) {
                        scope.launch {
                            viewModel.finishCameraVisit(session)
                            if (access == MediaAccess.SELECTED) {
                                pickerSessionId = session
                                pickerSourceRole = "mine"
                                picker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
                            }
                        }
                    } else if (access == MediaAccess.SELECTED) {
                        pickerSessionId = ""
                        pickerSourceRole = "mine"
                        picker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
                    } else {
                        viewModel.sync()
                    }
                }
                val mediaPermission = rememberLauncherForActivityResult(
                    ActivityResultContracts.RequestMultiplePermissions()
                ) {
                    viewModel.permissionChanged()
                }
                val notificationPermission = rememberLauncherForActivityResult(
                    ActivityResultContracts.RequestPermission()
                ) { granted ->
                    notificationsGranted = granted
                    if (granted) scope.launch { viewModel.registerNotificationsIfAvailable() }
                }
                val driveResolution = rememberLauncherForActivityResult(
                    ActivityResultContracts.StartIntentSenderForResult()
                ) { result ->
                    scope.launch {
                        runCatching { drive.finish(result.data) }
                            .onSuccess { viewModel.connectDrive(it) }
                            .onFailure { viewModel.error.value = it.message ?: "Drive authorization stopped" }
                    }
                }

                fun launchCamera(sessionId: String = "") {
                    cameraSessionId = sessionId
                    runCatching {
                        camera.launch(Intent(MediaStore.INTENT_ACTION_STILL_IMAGE_CAMERA))
                    }.onFailure {
                        cameraSessionId = ""
                        viewModel.error.value = "No system camera is available"
                    }
                }

                if (chooseSourceRole) {
                    AlertDialog(
                        onDismissRequest = { chooseSourceRole = false },
                        title = { Text("What are you adding?") },
                        text = {
                            Text(
                                "My Shots change your learning record. Inspiration stays separate " +
                                    "and is only a reference."
                            )
                        },
                        confirmButton = {
                            TextButton(
                                onClick = {
                                    chooseSourceRole = false
                                    pickerSessionId = ""
                                    pickerSourceRole = "mine"
                                    picker.launch(
                                        PickVisualMediaRequest(
                                            ActivityResultContracts.PickVisualMedia.ImageOnly
                                        )
                                    )
                                }
                            ) { Text("My Shots") }
                        },
                        dismissButton = {
                            TextButton(
                                onClick = {
                                    chooseSourceRole = false
                                    pickerSessionId = ""
                                    pickerSourceRole = "inspiration"
                                    picker.launch(
                                        PickVisualMediaRequest(
                                            ActivityResultContracts.PickVisualMedia.ImageOnly
                                        )
                                    )
                                }
                            ) { Text("Inspiration") }
                        },
                    )
                }

                ShootsApp(
                    viewModel,
                    AppActions(
                        signIn = { scope.launch { viewModel.signIn(this@MainActivity) } },
                        requestMedia = { mediaPermission.launch(mediaPermissions()) },
                        enableSource = { scope.launch { viewModel.enableFutureShots() } },
                        disableSource = { scope.launch { viewModel.disableFutureShots() } },
                        openFreeCamera = { launchCamera() },
                        chooseFreeShots = { chooseSourceRole = true },
                        requestExperiment = { force ->
                            scope.launch { viewModel.requestExperiment(force) }
                        },
                        requestExplore = { force ->
                            scope.launch { viewModel.requestExplore(force) }
                        },
                        startExperiment = { experimentId, variationId ->
                            scope.launch {
                                viewModel.reserveCaptureSession(experimentId, variationId)
                                    ?.let(::launchCamera)
                            }
                        },
                        completeExplore = { experimentId ->
                            scope.launch { viewModel.completeExplore(experimentId) }
                        },
                        prepareDeconstruction = { sourceType, sourceId, revision, coverShotId ->
                            scope.launch {
                                viewModel.prepareDeconstruction(
                                    sourceType,
                                    sourceId,
                                    revision,
                                    coverShotId,
                                )
                            }
                        },
                        answerScoutQuestion = { shootId, revision, optionId ->
                            scope.launch {
                                viewModel.answerScoutQuestion(shootId, revision, optionId)
                            }
                        },
                        shareDeconstruction = { draft ->
                            scope.launch {
                                runCatching { viewModel.cacheDeconstructionPages(draft) }
                                    .onSuccess { files ->
                                        val uris = ArrayList(files.map { file ->
                                            FileProvider.getUriForFile(
                                                this@MainActivity,
                                                "$packageName.files",
                                                file,
                                            )
                                        })
                                        if (uris.isEmpty()) return@onSuccess
                                        val share = Intent(Intent.ACTION_SEND_MULTIPLE).apply {
                                            type = "image/jpeg"
                                            putParcelableArrayListExtra(Intent.EXTRA_STREAM, uris)
                                            putExtra(Intent.EXTRA_TEXT, draft.suggestedCaption)
                                            clipData = ClipData.newUri(
                                                contentResolver,
                                                "Shoots Deconstruction",
                                                uris.first(),
                                            ).also { clips ->
                                                uris.drop(1).forEach { clips.addItem(ClipData.Item(it)) }
                                            }
                                            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                                        }
                                        startActivity(Intent.createChooser(share, "Share Deconstruction"))
                                    }
                                    .onFailure {
                                        viewModel.error.value =
                                            it.message ?: "Could not prepare share files"
                                    }
                            }
                        },
                        continueSession = ::launchCamera,
                        finishSession = { sessionId ->
                            scope.launch {
                                viewModel.finishCameraVisit(sessionId)
                                if (access == MediaAccess.SELECTED) {
                                    pickerSessionId = sessionId
                                    pickerSourceRole = "mine"
                                    picker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
                                }
                            }
                        },
                        cancelSession = { scope.launch { viewModel.cancelCaptureSession(it) } },
                        importSessionAsFree = { scope.launch { viewModel.importSessionAsFree(it) } },
                        requestNotifications = {
                            if (Build.VERSION.SDK_INT >= 33) {
                                notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
                            } else {
                                notificationsGranted = true
                                scope.launch { viewModel.registerNotificationsIfAvailable() }
                            }
                        },
                        connectDrive = {
                            scope.launch {
                                runCatching { drive.start() }
                                    .onSuccess { start ->
                                        when {
                                            start.resolution != null -> driveResolution.launch(
                                                IntentSenderRequest.Builder(start.resolution.intentSender).build()
                                            )
                                            start.serverCode.isNotBlank() -> viewModel.connectDrive(start.serverCode)
                                            else -> viewModel.error.value = "Google returned no Drive authorization"
                                        }
                                    }
                                    .onFailure { viewModel.error.value = it.message ?: "Drive authorization stopped" }
                            }
                        },
                        disconnectDrive = { scope.launch { viewModel.disconnectDrive() } },
                        openUrl = ::openUrl,
                        revoke = { scope.launch { viewModel.revoke(this@MainActivity) } },
                        deleteAccount = { scope.launch { viewModel.deleteAccount(this@MainActivity) } },
                    ),
                    notificationsGranted,
                    currentDeepRoute,
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        deepRoute.value = routeFrom(intent)
    }

    private fun openUrl(value: String) {
        runCatching { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(value))) }
            .onFailure { viewModel.error.value = "No app can open that link" }
    }

    private fun hasNotificationPermission(): Boolean =
        Build.VERSION.SDK_INT < 33 ||
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) ==
            PackageManager.PERMISSION_GRANTED

    private fun routeFrom(intent: Intent): String {
        val segments = intent.data?.pathSegments.orEmpty()
        return segments.dropWhile { it == "mobile" }.joinToString("/")
    }
}

private fun mediaPermissions(): Array<String> = when {
    Build.VERSION.SDK_INT >= 34 -> arrayOf(
        Manifest.permission.READ_MEDIA_IMAGES,
        Manifest.permission.READ_MEDIA_VISUAL_USER_SELECTED,
    )
    Build.VERSION.SDK_INT >= 33 -> arrayOf(Manifest.permission.READ_MEDIA_IMAGES)
    else -> arrayOf(Manifest.permission.READ_EXTERNAL_STORAGE)
}
