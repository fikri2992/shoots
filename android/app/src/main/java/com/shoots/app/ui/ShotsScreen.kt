package com.shoots.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.shoots.app.Amber
import com.shoots.app.FindingRed
import com.shoots.app.Hairline
import com.shoots.app.Ink
import com.shoots.app.InkRaised
import com.shoots.app.MutedWhite
import com.shoots.app.WarmWhite
import com.shoots.app.data.ShotDto
import com.shoots.app.data.ImportEntity
import com.shoots.app.data.ImportState

@Composable
fun ShotsScreen(
    shots: List<ShotDto>,
    pendingImports: List<ImportEntity>,
    canLoadMore: Boolean,
    busy: Boolean,
    imageUrl: (ShotDto) -> String,
    onShot: (String) -> Unit,
    onLoadMore: () -> Unit,
    onRetryImport: (String) -> Unit,
    onReauthenticate: () -> Unit,
) {
    Column(Modifier.fillMaxSize().background(Ink).statusBarsPadding()) {
        Column(Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 22.dp)) {
            ScreenTitle("Shots", "Your record, frame by frame.", "Imported originals stay yours. Shoots records what it could and could not read.")
        }
        if (shots.isEmpty() && pendingImports.isEmpty()) {
            Column(Modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.Center) {
                InkCard {
                    Text("No Shots cached yet.", color = WarmWhite, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
                    Spacer(Modifier.height(6.dp))
                    Text("Open the normal camera from Now. Future Camera Shots will appear after import.", color = MutedWhite, fontSize = 14.sp, lineHeight = 20.sp)
                }
            }
        } else {
            LazyVerticalGrid(
                columns = GridCells.Fixed(2),
                modifier = Modifier.fillMaxSize(),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(start = 16.dp, end = 16.dp, bottom = 92.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(pendingImports, key = { "local:${it.sourceId}" }) { item ->
                    PendingImportTile(item) {
                        if (item.state == ImportState.AUTH_REQUIRED) {
                            onReauthenticate()
                        } else {
                            onRetryImport(item.sourceId)
                        }
                    }
                }
                items(shots, key = { it.id }) { shot ->
                    ShotTile(shot, imageUrl(shot)) { onShot(shot.id) }
                }
                if (canLoadMore) {
                    item(span = { GridItemSpan(maxLineSpan) }) {
                        Column(Modifier.fillMaxWidth().padding(vertical = 14.dp)) {
                            SecondaryAction(if (busy) "Loading…" else "Load older Shots", onClick = onLoadMore)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun PendingImportTile(item: ImportEntity, onRetry: () -> Unit) {
    Box(
        Modifier
            .fillMaxWidth()
            .aspectRatio(1f)
            .background(InkRaised)
            .clickable(enabled = item.state in listOf(ImportState.DISCOVERED, ImportState.AUTH_REQUIRED), onClick = onRetry),
    ) {
        AsyncImage(
            model = item.uri,
            contentDescription = item.displayName,
            modifier = Modifier.fillMaxSize(),
            contentScale = ContentScale.Crop,
        )
        Text(
            item.state.replace('_', ' ').uppercase(),
            color = when (item.state) {
                ImportState.UNSUPPORTED, ImportState.MISSING, ImportState.SESSION_CONFLICT -> FindingRed
                ImportState.MANIFEST_PENDING, ImportState.UPLOADING -> Amber
                else -> WarmWhite
            },
            fontSize = 9.sp,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.align(Alignment.TopStart).background(Ink.copy(alpha = 0.82f)).padding(6.dp),
        )
        Text(
            item.error.ifBlank {
                when (item.state) {
                    ImportState.MANIFEST_PENDING -> "Waiting for the batch manifest"
                    ImportState.AUTH_REQUIRED -> "Sign in again to resume"
                    ImportState.DISCOVERED -> "Tap to retry"
                    else -> "Queued locally"
                }
            },
            color = WarmWhite,
            fontSize = 10.sp,
            lineHeight = 14.sp,
            maxLines = 3,
            modifier = Modifier.align(Alignment.BottomStart).fillMaxWidth().background(Ink.copy(alpha = 0.82f)).padding(7.dp),
        )
    }
}

@Composable
private fun ShotTile(shot: ShotDto, url: String, onClick: () -> Unit) {
    Box(
        Modifier
            .fillMaxWidth()
            .aspectRatio(1f)
            .background(InkRaised)
            .clickable(onClick = onClick),
    ) {
        AsyncImage(
            model = url,
            contentDescription = shot.filename,
            modifier = Modifier.fillMaxSize(),
            contentScale = ContentScale.Crop,
        )
        Row(
            Modifier
                .align(Alignment.TopStart)
                .fillMaxWidth()
                .padding(7.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text(
                when (shot.status) {
                    "analyzed" -> "READ"
                    "failed" -> "UNREADABLE"
                    "analysing" -> "READING"
                    "ingested" -> "WAITING"
                    else -> "PREPARING"
                },
                color = if (shot.status == "failed") FindingRed else WarmWhite,
                fontSize = 9.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.background(Ink.copy(alpha = 0.75f)).padding(horizontal = 6.dp, vertical = 4.dp),
            )
            if (shot.keptAt != null) {
                Text("KEEPER", color = Amber, fontSize = 9.sp, fontWeight = FontWeight.Bold, modifier = Modifier.background(Ink.copy(alpha = 0.8f)).padding(4.dp))
            }
        }
        if (shot.error.isNotBlank()) {
            Text(
                shot.error,
                color = WarmWhite,
                fontSize = 10.sp,
                maxLines = 2,
                modifier = Modifier.align(Alignment.BottomStart).fillMaxWidth().background(FindingRed.copy(alpha = 0.88f)).padding(7.dp),
            )
        } else {
            Text(
                displayTime(shot.displayTime),
                color = MutedWhite,
                fontSize = 9.sp,
                modifier = Modifier.align(Alignment.BottomStart).background(Ink.copy(alpha = 0.78f)).padding(6.dp),
            )
        }
    }
}
