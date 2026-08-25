package com.shoots.app

import android.content.Context
import android.util.Size
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.core.resolutionselector.ResolutionSelector
import androidx.camera.core.resolutionselector.ResolutionStrategy
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.clipRect
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.LocalLifecycleOwner
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import java.util.concurrent.Executors
import kotlin.coroutines.resume
import kotlin.coroutines.suspendCoroutine

/** The colour `imaging/findingmark.py` stripes finished reviews with, live. */
val ZEBRA = Color(0xFFFF4040)
private val AMBER = Color(0xFFFFC857)

/**
 * The fast loop and the slow one, in one screen.
 *
 * Everything painted here is arithmetic running on the device at frame rate,
 * with no model anywhere in it: the zebras use the same CLIP_HIGH as
 * `imaging/tone.py`, the guide is thirds, and the pitch is read off gravity.
 * Everything *said* — the verdict pulse — comes back from the panel after the
 * shutter. What is painted is measured; what is claimed is the model's.
 */
@Composable
fun Viewfinder(onUnpair: () -> Unit) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val scope = rememberCoroutineScope()

    var blown by remember { mutableStateOf<Tone.BlownMap?>(null) }
    var experiment by remember { mutableStateOf<Api.Experiment?>(null) }
    var pulse by remember { mutableStateOf<Api.Pulse?>(null) }
    var shotId by remember { mutableStateOf("") }
    var sending by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf("") }

    val capture = remember { ImageCapture.Builder().build() }
    val pitch = remember { Pitch(context) }
    var pitchDeg by remember { mutableStateOf<Int?>(null) }

    DisposableEffect(Unit) {
        pitch.start()
        onDispose { pitch.stop() }
    }
    LaunchedEffect(Unit) {
        experiment = withContext(Dispatchers.IO) { Api.openQuest(context) }
        while (true) {
            kotlinx.coroutines.delay(200)
            pitchDeg = pitch.rounded()
        }
    }

    Box(Modifier.fillMaxSize().background(Color.Black)) {
        AndroidView(
            modifier = Modifier.fillMaxSize(),
            factory = { ctx -> cameraView(ctx, lifecycleOwner, capture) { blown = it } },
        )

        ZebraOverlay(blown)
        ThirdsGrid()
        TopReadout(blown, pitchDeg, experiment, error, onUnpair)

        ShutterRow(
            experiment = experiment,
            pulse = pulse,
            sending = sending,
            shotId = shotId,
            onShoot = {
                if (!sending) {
                    sending = true
                    pulse = null
                    error = ""
                    scope.launch {
                        val jpeg = runCatching { takePhoto(context, capture) }.getOrNull()
                        if (jpeg == null) {
                            error = "could not take the picture"
                            sending = false
                            return@launch
                        }
                        val name = "shoots_${System.currentTimeMillis()}.jpg"
                        val sent = withContext(Dispatchers.IO) {
                            Api.shoot(context, jpeg, name, experiment?.id.orEmpty(), pitch.degrees)
                        }
                        sending = false
                        sent.fold(
                            onSuccess = { id ->
                                shotId = id
                                scope.launch {
                                    pulse = awaitPulse(context, id)
                                    // A closed experiment means the next one is
                                    // already waiting; ask for it.
                                    experiment = withContext(Dispatchers.IO) { Api.openQuest(context) }
                                }
                            },
                            onFailure = { error = it.message.orEmpty().take(90) },
                        )
                    }
                }
            },
            onKeep = {
                val id = shotId
                if (id.isNotEmpty()) {
                    val was = pulse?.keeper ?: false
                    val next = !was
                    pulse = pulse?.copy(keeper = next)
                    scope.launch {
                        val ok = withContext(Dispatchers.IO) { Api.setKeeper(context, id, next) }
                        // The only taste signal in the system, so it may not be
                        // faked. If the server did not take it, put the button
                        // back and say so rather than leaving a mark on screen
                        // that no profile will ever see.
                        if (!ok) {
                            pulse = pulse?.copy(keeper = was)
                            error = "could not save that"
                        }
                    }
                }
            },
        )
    }
}

private fun cameraView(
    ctx: Context,
    lifecycleOwner: androidx.lifecycle.LifecycleOwner,
    capture: ImageCapture,
    onBlown: (Tone.BlownMap) -> Unit,
): PreviewView {
    val previewView = PreviewView(ctx).apply { scaleType = PreviewView.ScaleType.FILL_CENTER }
    val executor = Executors.newSingleThreadExecutor()
    var lumaBuf = ByteArray(0)

    val analysis = ImageAnalysis.Builder()
        .setResolutionSelector(
            ResolutionSelector.Builder()
                .setResolutionStrategy(
                    ResolutionStrategy(
                        Size(640, 480),
                        ResolutionStrategy.FALLBACK_RULE_CLOSEST_LOWER_THEN_HIGHER,
                    )
                )
                .build()
        )
        .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
        .build()
    analysis.setAnalyzer(executor) { image ->
        image.use {
            val plane = it.planes[0]
            val needed = plane.buffer.remaining()
            if (lumaBuf.size < needed) lumaBuf = ByteArray(needed)
            plane.buffer.get(lumaBuf, 0, needed)
            val map = Tone.blownMap(lumaBuf, it.width, it.height, plane.rowStride)
            onBlown(Tone.rotated(map, it.imageInfo.rotationDegrees))
        }
    }

    ProcessCameraProvider.getInstance(ctx).apply {
        addListener({
            val provider = get()
            val preview = Preview.Builder().build().also { p ->
                p.surfaceProvider = previewView.surfaceProvider
            }
            provider.unbindAll()
            provider.bindToLifecycle(
                lifecycleOwner,
                CameraSelector.DEFAULT_BACK_CAMERA,
                preview,
                analysis,
                capture,
            )
        }, ContextCompat.getMainExecutor(ctx))
    }
    return previewView
}

private suspend fun takePhoto(context: Context, capture: ImageCapture): ByteArray =
    suspendCoroutine { cont ->
        capture.takePicture(
            ContextCompat.getMainExecutor(context),
            object : ImageCapture.OnImageCapturedCallback() {
                override fun onCaptureSuccess(image: ImageProxy) {
                    image.use {
                        val buffer = it.planes[0].buffer
                        val bytes = ByteArray(buffer.remaining())
                        buffer.get(bytes)
                        cont.resume(bytes)
                    }
                }

                override fun onError(exception: ImageCaptureException) {
                    cont.resumeWith(Result.failure(exception))
                }
            },
        )
    }

/** Stripes over every blown block, matching a FILL_CENTER preview. */
@Composable
private fun ZebraOverlay(map: Tone.BlownMap?) {
    Canvas(Modifier.fillMaxSize()) {
        val m = map ?: return@Canvas
        val cell = maxOf(size.width / m.cols, size.height / m.rows)
        val ox = (size.width - cell * m.cols) / 2f
        val oy = (size.height - cell * m.rows) / 2f
        val stripe = cell / 2.5f
        for (i in m.blocks.indices) {
            if (!m.blocks[i]) continue
            val x = ox + (i % m.cols) * cell
            val y = oy + (i / m.cols) * cell
            clipRect(x, y, x + cell, y + cell) {
                var d = -cell
                while (d < cell * 2) {
                    drawLine(
                        ZEBRA,
                        Offset(x + d, y + cell),
                        Offset(x + d + cell, y),
                        strokeWidth = stripe * 0.45f,
                        alpha = 0.75f,
                    )
                    d += stripe
                }
            }
        }
    }
}

@Composable
private fun ThirdsGrid() {
    Canvas(Modifier.fillMaxSize()) {
        val grid = Color.White.copy(alpha = 0.32f)
        for (f in listOf(1f / 3f, 2f / 3f)) {
            drawLine(grid, Offset(size.width * f, 0f), Offset(size.width * f, size.height), 2f)
            drawLine(grid, Offset(0f, size.height * f), Offset(size.width, size.height * f), 2f)
        }
    }
}

/**
 * Figures, not opinions: the share of the frame above CLIP_HIGH and how far
 * from level the camera is aimed. Eye level is stated plainly rather than
 * warned about — it is a tendency, not a finding (decision 39).
 */
@Composable
private fun TopReadout(
    map: Tone.BlownMap?,
    pitchDeg: Int?,
    experiment: Api.Experiment?,
    error: String,
    onUnpair: () -> Unit,
) {
    val share = map?.sharePct ?: 0f
    val hot = share >= Tone.BLOWN_SHARE_PCT
    Column(
        Modifier.fillMaxSize().padding(top = 44.dp, start = 16.dp, end = 16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = if (hot) "blown %.1f%%".format(share) else "clipped %.1f%%".format(share),
                color = if (hot) ZEBRA else Color.White.copy(alpha = 0.8f),
                fontSize = 14.sp,
                fontWeight = if (hot) FontWeight.Bold else FontWeight.Normal,
            )
            Text(
                text = pitchDeg?.let { "${it}° from level" } ?: "",
                color = Color.White.copy(alpha = 0.8f),
                fontSize = 14.sp,
            )
            TextButton(onClick = onUnpair) {
                Text("unpair", color = Color.White.copy(alpha = 0.45f), fontSize = 12.sp)
            }
        }
        if (experiment != null) {
            Spacer(Modifier.height(10.dp))
            Column(
                Modifier
                    .fillMaxWidth()
                    .background(Color.Black.copy(alpha = 0.55f), RoundedCornerShape(10.dp))
                    .padding(12.dp)
            ) {
                Text(experiment.title, color = AMBER, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                if (experiment.whyNow.isNotEmpty()) {
                    Spacer(Modifier.height(4.dp))
                    Text(
                        experiment.whyNow,
                        color = Color.White.copy(alpha = 0.75f),
                        fontSize = 12.sp,
                    )
                }
            }
        }
        if (error.isNotEmpty()) {
            Spacer(Modifier.height(10.dp))
            Text(error, color = ZEBRA, fontSize = 12.sp)
        }
    }
}
