package com.shoots.app

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.util.Size
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.core.resolutionselector.ResolutionSelector
import androidx.camera.core.resolutionselector.ResolutionStrategy
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
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
import java.util.concurrent.Executors

/** The zebra colour faultmark.py stripes reviews with, live this time. */
private val ZEBRA = Color(0xFFFF4040)

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            var granted by remember {
                mutableStateOf(
                    ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) ==
                        PackageManager.PERMISSION_GRANTED
                )
            }
            val ask = androidx.activity.compose.rememberLauncherForActivityResult(
                ActivityResultContracts.RequestPermission()
            ) { granted = it }
            androidx.compose.runtime.LaunchedEffect(Unit) {
                if (!granted) ask.launch(Manifest.permission.CAMERA)
            }
            if (granted) Viewfinder() else NeedsCamera()
        }
    }
}

@Composable
private fun NeedsCamera() {
    Box(Modifier.fillMaxSize().background(Color.Black), contentAlignment = Alignment.Center) {
        Text("Shoots needs the camera.", color = Color.White)
    }
}

@Composable
private fun Viewfinder() {
    val context = LocalContext.current
    var blown by remember { mutableStateOf<Tone.BlownMap?>(null) }

    Box(Modifier.fillMaxSize().background(Color.Black)) {
        AndroidView(
            modifier = Modifier.fillMaxSize(),
            factory = { ctx ->
                val previewView = PreviewView(ctx).apply {
                    scaleType = PreviewView.ScaleType.FILL_CENTER
                }
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
                        blown = Tone.rotated(map, it.imageInfo.rotationDegrees)
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
                            ctx as ComponentActivity,
                            CameraSelector.DEFAULT_BACK_CAMERA,
                            preview,
                            analysis,
                        )
                    }, ContextCompat.getMainExecutor(ctx))
                }
                previewView
            },
        )

        ZebraOverlay(blown)
        ThirdsGrid()
        Readout(blown)
    }
}

/**
 * Stripes over every blown block, drawn to match a FILL_CENTER preview:
 * the grid is scaled to cover the canvas and centred, like the image is.
 */
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
        val w = size.width
        val h = size.height
        val grid = Color.White.copy(alpha = 0.35f)
        for (f in listOf(1f / 3f, 2f / 3f)) {
            drawLine(grid, Offset(w * f, 0f), Offset(w * f, h), strokeWidth = 2f)
            drawLine(grid, Offset(0f, h * f), Offset(w, h * f), strokeWidth = 2f)
        }
    }
}

/** The figure, not an opinion: percent of the frame above CLIP_HIGH. */
@Composable
private fun Readout(map: Tone.BlownMap?) {
    val share = map?.sharePct ?: 0f
    val hot = share >= Tone.BLOWN_SHARE_PCT
    Box(Modifier.fillMaxSize().padding(top = 48.dp), contentAlignment = Alignment.TopCenter) {
        Text(
            text = if (hot) "blown highlights %.1f%%".format(share)
            else "clipped %.1f%%".format(share),
            color = if (hot) ZEBRA else Color.White.copy(alpha = 0.8f),
            fontSize = 16.sp,
            fontWeight = if (hot) FontWeight.Bold else FontWeight.Normal,
        )
    }
}
