package com.shoots.app

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val context = LocalContext.current
            var paired by remember { mutableStateOf(Api.isPaired(context)) }
            var granted by remember {
                mutableStateOf(
                    ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) ==
                        PackageManager.PERMISSION_GRANTED
                )
            }
            val ask = rememberLauncherForActivityResult(
                ActivityResultContracts.RequestPermission()
            ) { granted = it }
            LaunchedEffect(Unit) { if (!granted) ask.launch(Manifest.permission.CAMERA) }

            when {
                !granted -> Message("Shoots needs the camera.")
                !paired -> PairScreen { paired = true }
                else -> Viewfinder(onUnpair = {
                    Api.forget(context)
                    paired = false
                })
            }
        }
    }
}

@Composable
private fun Message(text: String) {
    Box(Modifier.fillMaxSize().background(Color.Black), contentAlignment = Alignment.Center) {
        Text(text, color = Color.White)
    }
}

/**
 * The camera has no way to sign in on its own, and giving it one would mean
 * shipping a client secret to a device. So it is handed an identity instead:
 * the signed-in web page shows a code, the photographer types it here once,
 * and the phone keeps its own token from then on.
 */
@Composable
private fun PairScreen(onPaired: () -> Unit) {
    val context = LocalContext.current
    val scope = androidx.compose.runtime.rememberCoroutineScope()
    var base by remember { mutableStateOf("http://192.168.1.10:8000") }
    var code by remember { mutableStateOf("") }
    var error by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }

    Column(
        Modifier.fillMaxSize().background(Color.Black).padding(28.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Text("Pair this camera", color = Color.White, fontSize = 26.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(8.dp))
        Text(
            "Open Shoots on the web, sign in, and ask for a pairing code.",
            color = Color.White.copy(alpha = 0.7f),
            fontSize = 15.sp,
        )
        Spacer(Modifier.height(28.dp))
        OutlinedTextField(
            value = base,
            onValueChange = { base = it },
            label = { Text("Server address") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
            colors = fieldColours(),
        )
        Spacer(Modifier.height(14.dp))
        OutlinedTextField(
            value = code,
            onValueChange = { code = it.uppercase().take(6) },
            label = { Text("Code") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Characters),
            modifier = Modifier.fillMaxWidth(),
            colors = fieldColours(),
        )
        if (error.isNotEmpty()) {
            Spacer(Modifier.height(12.dp))
            Text(error, color = ZEBRA, fontSize = 14.sp)
        }
        Spacer(Modifier.height(24.dp))
        Button(
            onClick = {
                busy = true
                error = ""
                scope.launch {
                    val result = withContext(Dispatchers.IO) { Api.pair(context, base, code) }
                    busy = false
                    result.fold(
                        onSuccess = { onPaired() },
                        onFailure = { error = it.message ?: "could not pair" },
                    )
                }
            },
            enabled = !busy && code.length == 6 && base.isNotBlank(),
            modifier = Modifier.fillMaxWidth().height(52.dp),
            shape = RoundedCornerShape(12.dp),
        ) {
            Text(if (busy) "Pairing…" else "Pair")
        }
    }
}

@Composable
private fun fieldColours() = androidx.compose.material3.OutlinedTextFieldDefaults.colors(
    focusedTextColor = Color.White,
    unfocusedTextColor = Color.White,
    focusedBorderColor = Color.White.copy(alpha = 0.6f),
    unfocusedBorderColor = Color.White.copy(alpha = 0.3f),
    focusedLabelColor = Color.White.copy(alpha = 0.7f),
    unfocusedLabelColor = Color.White.copy(alpha = 0.5f),
    cursorColor = Color.White,
)

/** The shutter, the experiment it answers, and what came back. */
@Composable
fun ShutterRow(
    experiment: Api.Experiment?,
    pulse: Api.Pulse?,
    sending: Boolean,
    shotId: String,
    onShoot: () -> Unit,
    onKeep: () -> Unit,
) {
    Column(
        Modifier.fillMaxSize().padding(bottom = 36.dp),
        verticalArrangement = Arrangement.Bottom,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        if (pulse != null) {
            PulseCard(pulse, shotId, onKeep)
            Spacer(Modifier.height(16.dp))
        }
        Box(
            Modifier
                .size(74.dp)
                .background(
                    if (sending) Color.White.copy(alpha = 0.35f) else Color.White,
                    CircleShape,
                ),
            contentAlignment = Alignment.Center,
        ) {
            TextButton(onClick = onShoot, enabled = !sending, contentPadding = PaddingValues(0.dp)) {
                Text(
                    if (sending) "…" else "",
                    color = Color.Black,
                    fontSize = 22.sp,
                )
            }
        }
        Spacer(Modifier.height(10.dp))
        Text(
            experiment?.title ?: "no open challenge",
            color = Color.White.copy(alpha = 0.75f),
            fontSize = 13.sp,
            textAlign = TextAlign.Center,
        )
    }
}

/**
 * What the panel found, in the hand that took the picture. Praise first and
 * only what a second lens actually corroborated, then the finding with its
 * figure — the same order the review uses, for the same reason.
 */
@Composable
private fun PulseCard(pulse: Api.Pulse, shotId: String, onKeep: () -> Unit) {
    // Follows the pulse rather than latching, so a mark the server refused puts
    // the button back instead of showing "kept" for a frame that is not.
    val kept = pulse.keeper
    Column(
        Modifier
            .fillMaxWidth(0.9f)
            .background(Color.Black.copy(alpha = 0.72f), RoundedCornerShape(14.dp))
            .padding(16.dp),
    ) {
        if (pulse.praise.isNotEmpty()) {
            Text(
                "two lenses agreed: ${pulse.praise}",
                color = Color.White,
                fontSize = 15.sp,
                fontWeight = FontWeight.Bold,
            )
        } else {
            Text("read, nothing corroborated", color = Color.White, fontSize = 15.sp)
        }
        if (pulse.finding.isNotEmpty()) {
            Spacer(Modifier.height(6.dp))
            Text(pulse.finding, color = ZEBRA, fontSize = 13.sp)
        }
        Spacer(Modifier.height(10.dp))
        TextButton(onClick = onKeep, contentPadding = PaddingValues(0.dp)) {
            Text(
                if (kept) "kept" else "keep this one",
                color = if (kept) Color(0xFFFFC857) else Color.White.copy(alpha = 0.8f),
                fontSize = 14.sp,
            )
        }
    }
}

/** Poll until the panel has finished. It takes about half a minute. */
suspend fun awaitPulse(context: android.content.Context, shotId: String): Api.Pulse? {
    repeat(40) {
        delay(3_000)
        val pulse = withContext(Dispatchers.IO) { Api.pulse(context, shotId) }
        if (pulse != null) return pulse
    }
    return null
}
