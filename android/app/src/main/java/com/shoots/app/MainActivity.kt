package com.shoots.app

import android.Manifest
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.provider.MediaStore
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            ShootsTheme {
                val context = LocalContext.current
                var paired by remember { mutableStateOf(Api.isPaired(context)) }
                if (!paired) {
                    PairScreen { paired = true }
                } else {
                    PhoneSourceScreen(
                        onUnpair = {
                            Api.forget(context)
                            PhoneSource.disable(context)
                            paired = false
                        }
                    )
                }
            }
        }
    }
}

@Composable
private fun PhoneSourceScreen(onUnpair: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var status by remember { mutableStateOf(PhoneSource.status(context)) }
    var experiment by remember { mutableStateOf<Api.Experiment?>(null) }
    var latestRun by remember { mutableStateOf<Api.RunReceipt?>(null) }
    var selectedExperiment by remember { mutableStateOf(PhoneSource.selectedExperiment(context)) }
    val permission = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) {
        status = PhoneSource.status(context)
        if (status.access == PhoneSource.Access.FULL && !status.enabled) {
            PhoneSource.enable(context)
            status = PhoneSource.status(context)
        }
    }
    val picker = rememberLauncherForActivityResult(
        ActivityResultContracts.PickMultipleVisualMedia(50)
    ) { uris ->
        scope.launch {
            if (uris.isEmpty()) return@launch
            var uploaded = 0
            var skipped = 0
            var failed = 0
            var error = ""
            PhoneSource.recordStarted(context, 0)
            var uploadExperiment = selectedExperiment
            withContext(Dispatchers.IO) {
                if (uploadExperiment.isNotBlank()) {
                    val open = Api.fetchOpenExperiment(context).getOrElse { exception ->
                        failed = 1
                        error = exception.message ?: exception.javaClass.simpleName
                        return@withContext
                    }
                    if (open?.id != uploadExperiment || open?.type != "reproduce") {
                        PhoneSource.clearExperiment(context)
                        uploadExperiment = ""
                    }
                }
                if (failed > 0) return@withContext
                for (uri in uris) {
                    try {
                        val item = PhoneSource.describe(context, uri) ?: continue
                        val bytes = context.contentResolver.openInputStream(uri)
                            ?.use { it.readBytes() }
                            ?: error("Selected Shot is no longer readable")
                        val source = "selected:${uri.authority}:${item.id}:${item.dateAdded}:${item.size}"
                        val result = Api.importShot(
                            context,
                            bytes,
                            item.name,
                            item.mime,
                            source,
                            uploadExperiment,
                        )
                            .getOrThrow()
                        if (result.created) uploaded += 1 else skipped += 1
                    } catch (exception: Exception) {
                        failed += 1
                        error = exception.message ?: exception.javaClass.simpleName
                    }
                }
            }
            if (selectedExperiment.isNotBlank() && uploadExperiment.isBlank() && failed == 0) {
                selectedExperiment = ""
            }
            PhoneSource.recordRun(context, uris.size, uploaded, skipped, failed, error)
            status = PhoneSource.status(context)
        }
    }

    LaunchedEffect(status.enabled, status.access) {
        if (status.enabled && status.access == PhoneSource.Access.FULL) {
            PhoneSource.scanNow(context)
        }
        while (true) {
            val open = withContext(Dispatchers.IO) { Api.fetchOpenExperiment(context) }
            if (open.isSuccess) {
                experiment = open.getOrNull()
                if (
                    selectedExperiment.isNotBlank() &&
                    (experiment?.id != selectedExperiment || experiment?.type != "reproduce")
                ) {
                    PhoneSource.clearExperiment(context)
                    selectedExperiment = ""
                }
            }
            val run = withContext(Dispatchers.IO) { Api.fetchLatestRun(context) }
            if (run.isSuccess) latestRun = run.getOrNull()
            delay(10_000)
            status = PhoneSource.status(context)
        }
    }

    Column(
        Modifier
            .fillMaxSize()
            .background(Ink)
            .statusBarsPadding()
            .navigationBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 24.dp, vertical = 28.dp),
        verticalArrangement = Arrangement.Top,
    ) {
        Text("SHOOTS PHONE SOURCE", color = Amber, fontSize = 12.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(18.dp))
        Text(
            "Your Camera roll, remembered.",
            color = WarmWhite,
            fontSize = 31.sp,
            lineHeight = 36.sp,
            fontWeight = FontWeight.Bold,
        )
        Spacer(Modifier.height(12.dp))
        Text(
            when (status.access) {
                PhoneSource.Access.FULL -> if (status.enabled) {
                    "Automatic import is on. Keep using your normal camera. New Camera Shots enter Shoots in the background."
                } else {
                    "Allow future Camera Shots once. Existing media stays untouched."
                }
                PhoneSource.Access.SELECTED ->
                    "Android granted selected-media access. Choose Shots explicitly; automatic future import is off."
                PhoneSource.Access.NONE ->
                    "Shoots needs media access to notice new Camera Shots. It ignores screenshots, downloads, and messaging folders."
            },
            color = MutedWhite,
            fontSize = 16.sp,
            lineHeight = 23.sp,
        )
        Spacer(Modifier.height(28.dp))

        if (experiment?.type == "reproduce") {
            Text(
                experiment?.type?.uppercase().orEmpty() + " EXPERIMENT",
                color = Amber,
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.height(5.dp))
            Text(
                experiment?.title.orEmpty(),
                color = WarmWhite,
                fontSize = 18.sp,
                lineHeight = 24.sp,
                fontWeight = FontWeight.SemiBold,
            )
            if (!experiment?.whyNow.isNullOrBlank()) {
                Spacer(Modifier.height(5.dp))
                Text(experiment?.whyNow.orEmpty(), color = MutedWhite, fontSize = 13.sp, lineHeight = 18.sp)
            }
            TextButton(
                onClick = {
                    val id = experiment?.id.orEmpty()
                    if (selectedExperiment == id) {
                        PhoneSource.clearExperiment(context)
                        selectedExperiment = ""
                    } else {
                        PhoneSource.selectExperiment(context, id)
                        selectedExperiment = id
                    }
                },
            ) {
                Text(
                    if (selectedExperiment == experiment?.id) {
                        "New Camera Shots will join this · Pause"
                    } else {
                        "Use new Camera Shots for this"
                    },
                    color = if (selectedExperiment == experiment?.id) Amber else WarmWhite,
                    fontWeight = FontWeight.Bold,
                )
            }
            Spacer(Modifier.height(12.dp))
        } else if (experiment != null) {
            Text("LEGACY EXPERIMENT", color = Amber, fontSize = 11.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(5.dp))
            Text(
                "Open Shoots on the web and leave this retired Experiment. Phone Source will not attach Shots to it.",
                color = MutedWhite,
                fontSize = 14.sp,
                lineHeight = 20.sp,
            )
            Spacer(Modifier.height(12.dp))
        }

        if (status.access != PhoneSource.Access.FULL) {
            Button(
                onClick = { permission.launch(mediaPermissions()) },
                modifier = Modifier.fillMaxWidth().height(54.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Amber, contentColor = Ink),
                shape = RoundedCornerShape(14.dp),
            ) { Text("Allow Camera Shots", fontWeight = FontWeight.Bold) }
            Spacer(Modifier.height(10.dp))
            TextButton(
                onClick = {
                    picker.launch(
                        PickVisualMediaRequest(
                            ActivityResultContracts.PickVisualMedia.ImageOnly
                        )
                    )
                },
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Choose Shots instead", color = WarmWhite) }
        } else if (!status.enabled) {
            Button(
                onClick = {
                    PhoneSource.enable(context)
                    status = PhoneSource.status(context)
                },
                modifier = Modifier.fillMaxWidth().height(54.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Amber, contentColor = Ink),
                shape = RoundedCornerShape(14.dp),
            ) { Text("Start with future Shots", fontWeight = FontWeight.Bold) }
        } else {
            Button(
                onClick = {
                    runCatching {
                        context.startActivity(Intent(MediaStore.INTENT_ACTION_STILL_IMAGE_CAMERA))
                    }
                },
                modifier = Modifier.fillMaxWidth().height(54.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Amber, contentColor = Ink),
                shape = RoundedCornerShape(14.dp),
            ) { Text("Open normal camera", fontWeight = FontWeight.Bold) }
            Spacer(Modifier.height(18.dp))
            Text(
                when (status.runState) {
                    PhoneSource.RunState.SCANNING -> "Checking Camera…"
                    PhoneSource.RunState.RETRYING ->
                        "Retrying in background · attempt ${status.attempt + 1}"
                    PhoneSource.RunState.IDLE -> if (status.lastActivity.isBlank()) {
                        "No new Camera Shots imported yet."
                    } else {
                        "Last import  ${status.discovered} found · ${status.uploaded} uploaded · ${status.skipped} known · ${status.failed} failed"
                    }
                },
                color = WarmWhite,
                fontSize = 14.sp,
                lineHeight = 20.sp,
            )
            if (status.lastScan.isNotBlank()) {
                Spacer(Modifier.height(5.dp))
                Text("Last checked ${displayTime(status.lastScan)}", color = MutedWhite, fontSize = 12.sp)
            }
            if (status.error.isNotBlank()) {
                Spacer(Modifier.height(8.dp))
                Text(status.error, color = FindingRed, fontSize = 13.sp, lineHeight = 18.sp)
            }
            if (latestRun != null) {
                Spacer(Modifier.height(14.dp))
                Text(
                    "SHOOTS ${latestRun?.status?.uppercase()}",
                    color = if (latestRun?.status == "retrying") Amber else MutedWhite,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                )
                if (!latestRun?.scoutOutcome.isNullOrBlank()) {
                    Spacer(Modifier.height(4.dp))
                    Text(
                        latestRun?.scoutOutcome.orEmpty(),
                        color = MutedWhite,
                        fontSize = 13.sp,
                        lineHeight = 18.sp,
                    )
                }
            }
            Spacer(Modifier.height(12.dp))
            TextButton(
                onClick = { PhoneSource.scanNow(context) },
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Check Camera now", color = MutedWhite) }
        }
        Spacer(Modifier.height(22.dp))
        TextButton(onClick = onUnpair, modifier = Modifier.fillMaxWidth()) {
            Text("Disconnect this phone", color = MutedWhite, fontSize = 13.sp)
        }
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

@Composable
private fun PairScreen(onPaired: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var base by remember { mutableStateOf("http://192.168.1.10:8000") }
    var code by remember { mutableStateOf("") }
    var error by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }

    Column(
        Modifier
            .fillMaxSize()
            .background(Ink)
            .statusBarsPadding()
            .navigationBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 24.dp, vertical = 32.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Text("SHOOTS PHONE SOURCE", color = Amber, fontSize = 12.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(18.dp))
        Text(
            "Connect your Camera roll.",
            color = WarmWhite,
            fontSize = 32.sp,
            lineHeight = 37.sp,
            fontWeight = FontWeight.Bold,
        )
        Spacer(Modifier.height(12.dp))
        Text(
            "Open Shoots on the web, create a pairing code, then enter it here once.",
            color = MutedWhite,
            fontSize = 16.sp,
            lineHeight = 23.sp,
        )
        Spacer(Modifier.height(28.dp))
        OutlinedTextField(
            value = base,
            onValueChange = { base = it },
            label = { Text("Server address") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
            colors = fieldColours(),
            shape = RoundedCornerShape(14.dp),
        )
        Spacer(Modifier.height(12.dp))
        OutlinedTextField(
            value = code,
            onValueChange = { code = it.uppercase().filter(Char::isLetterOrDigit).take(6) },
            label = { Text("6-character code") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Characters),
            modifier = Modifier.fillMaxWidth(),
            colors = fieldColours(),
            shape = RoundedCornerShape(14.dp),
        )
        if (error.isNotEmpty()) {
            Spacer(Modifier.height(10.dp))
            Text(error, color = FindingRed, fontSize = 14.sp)
        }
        Spacer(Modifier.height(20.dp))
        Button(
            onClick = {
                busy = true
                scope.launch {
                    val result = withContext(Dispatchers.IO) { Api.pair(context, base, code) }
                    busy = false
                    result.fold(
                        onSuccess = { onPaired() },
                        onFailure = { error = it.message ?: "Could not connect." },
                    )
                }
            },
            enabled = !busy && code.length == 6 && base.isNotBlank(),
            modifier = Modifier.fillMaxWidth().height(54.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Amber, contentColor = Ink),
            shape = RoundedCornerShape(14.dp),
        ) { Text(if (busy) "Connecting…" else "Connect phone", fontWeight = FontWeight.Bold) }
    }
}

@Composable
private fun fieldColours() = OutlinedTextFieldDefaults.colors(
    focusedTextColor = WarmWhite,
    unfocusedTextColor = WarmWhite,
    focusedBorderColor = Amber,
    unfocusedBorderColor = Hairline,
    focusedLabelColor = Amber,
    unfocusedLabelColor = MutedWhite,
    cursorColor = Amber,
)

private fun displayTime(value: String): String = runCatching {
    DateTimeFormatter.ofPattern("d MMM, HH:mm")
        .withZone(ZoneId.systemDefault())
        .format(Instant.parse(value))
}.getOrDefault(value)
