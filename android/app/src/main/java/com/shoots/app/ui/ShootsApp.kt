package com.shoots.app.ui

import android.app.Activity
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.shoots.app.Amber
import com.shoots.app.Hairline
import com.shoots.app.Ink
import com.shoots.app.InkRaised
import com.shoots.app.MutedWhite
import com.shoots.app.WarmWhite
import com.shoots.app.phone.MediaAccess
import kotlinx.coroutines.launch

data class AppActions(
    val signIn: () -> Unit,
    val requestMedia: () -> Unit,
    val enableSource: () -> Unit,
    val disableSource: () -> Unit,
    val openFreeCamera: () -> Unit,
    val chooseFreeShots: () -> Unit,
    val startExperiment: (String) -> Unit,
    val continueSession: (String) -> Unit,
    val finishSession: (String) -> Unit,
    val cancelSession: (String) -> Unit,
    val importSessionAsFree: (String) -> Unit,
    val requestNotifications: () -> Unit,
    val connectDrive: () -> Unit,
    val disconnectDrive: () -> Unit,
    val openUrl: (String) -> Unit,
    val revoke: () -> Unit,
    val deleteAccount: () -> Unit,
)

@Composable
fun ShootsApp(
    viewModel: MainViewModel,
    actions: AppActions,
    notificationsGranted: Boolean,
    deepRoute: String,
) {
    val signedIn by viewModel.signedIn.collectAsStateWithLifecycle()
    val snapshot by viewModel.snapshot.collectAsStateWithLifecycle()
    val shots by viewModel.shots.collectAsStateWithLifecycle()
    val source by viewModel.sourceState.collectAsStateWithLifecycle()
    val session by viewModel.localCaptureSession.collectAsStateWithLifecycle()
    val pendingImports by viewModel.pendingImports.collectAsStateWithLifecycle()
    val access by viewModel.mediaAccess.collectAsStateWithLifecycle()
    val busy by viewModel.busy.collectAsStateWithLifecycle()
    val error by viewModel.error.collectAsStateWithLifecycle()
    val notice by viewModel.notice.collectAsStateWithLifecycle()
    val canLoadMoreShots by viewModel.canLoadMoreShots.collectAsStateWithLifecycle()
    val scope = rememberCoroutineScope()

    if (!signedIn) {
        SignInScreen(busy, error, actions.signIn, viewModel::clearMessage)
        return
    }

    val nav = rememberNavController()
    val backStack by nav.currentBackStackEntryAsState()
    val route = backStack?.destination?.route.orEmpty()
    val showNavigation = !route.startsWith("shot/")

    LaunchedEffect(deepRoute) {
        val destination = when (deepRoute.substringBefore('/')) {
            "journey" -> "journey"
            "shots", "shot" -> "shots"
            "settings" -> "settings"
            else -> "now"
        }
        if (deepRoute.isNotBlank()) nav.navigate(destination) { launchSingleTop = true }
    }

    Box(Modifier.fillMaxSize().background(Ink)) {
        NavHost(navController = nav, startDestination = "now", modifier = Modifier.fillMaxSize()) {
            composable("now") {
                NowScreen(
                    snapshot,
                    source,
                    session,
                    access,
                    busy,
                    imageUrl = { viewModel.imageUrl(it) },
                    onRequestMedia = actions.requestMedia,
                    onEnableSource = actions.enableSource,
                    onOpenFreeCamera = actions.openFreeCamera,
                    onChooseFreeShots = actions.chooseFreeShots,
                    onStartExperiment = actions.startExperiment,
                    onContinueSession = actions.continueSession,
                    onFinishSession = actions.finishSession,
                    onCancelSession = actions.cancelSession,
                    onImportSessionAsFree = actions.importSessionAsFree,
                    onSync = viewModel::sync,
                )
            }
            composable("shots") {
                LaunchedEffect(Unit) { viewModel.loadMoreShots(reset = true) }
                ShotsScreen(
                    shots,
                    pendingImports,
                    canLoadMoreShots,
                    busy,
                    { viewModel.imageUrl(it) },
                    { nav.navigate("shot/$it") },
                    { viewModel.loadMoreShots() },
                    viewModel::retryImport,
                    actions.signIn,
                )
            }
            composable("shot/{id}") { entry ->
                val id = entry.arguments?.getString("id").orEmpty()
                val detail by viewModel.observeShotDetail(id).collectAsStateWithLifecycle(initialValue = null)
                LaunchedEffect(id) { viewModel.loadShot(id) }
                ShotDetailScreen(
                    detail,
                    snapshot?.latestRun,
                    imageUrl = { shot, original -> viewModel.imageUrl(shot, original) },
                    onBack = nav::popBackStack,
                    onKeeper = { keeper ->
                        scope.launch { viewModel.setKeeper(id, keeper) }
                    },
                    onOpenDrive = actions.openUrl,
                )
            }
            composable("journey") {
                JourneyScreen(snapshot, { viewModel.imageUrl(it) }) { nav.navigate("shot/$it") }
            }
            composable("settings") {
                SettingsScreen(
                    snapshot,
                    source,
                    access,
                    notificationsGranted,
                    busy,
                    actions.requestMedia,
                    actions.enableSource,
                    actions.disableSource,
                    actions.requestNotifications,
                    actions.connectDrive,
                    actions.disconnectDrive,
                    actions.openUrl,
                    actions.signIn,
                    actions.revoke,
                    actions.deleteAccount,
                )
            }
        }

        if (error.isNotBlank() || notice.isNotBlank()) {
            Box(Modifier.align(Alignment.TopCenter).statusBarsPadding().padding(horizontal = 14.dp, vertical = 12.dp)) {
                MessageBanner(error.ifBlank { notice }, error.isNotBlank(), viewModel::clearMessage)
            }
        }
        if (showNavigation) {
            BottomNavigation(
                current = route,
                modifier = Modifier.align(Alignment.BottomCenter),
                onNavigate = { destination ->
                    nav.navigate(destination) {
                        popUpTo(nav.graph.findStartDestination().id) { saveState = true }
                        launchSingleTop = true
                        restoreState = true
                    }
                },
            )
        }
    }
}

@Composable
private fun BottomNavigation(current: String, modifier: Modifier, onNavigate: (String) -> Unit) {
    Row(
        modifier
            .fillMaxWidth()
            .background(InkRaised.copy(alpha = 0.98f), RoundedCornerShape(topStart = 18.dp, topEnd = 18.dp))
            .navigationBarsPadding()
            .padding(horizontal = 8.dp, vertical = 10.dp),
        horizontalArrangement = Arrangement.SpaceAround,
    ) {
        listOf("now" to "Now", "shots" to "Shots", "journey" to "Journey", "settings" to "Settings").forEach { (route, label) ->
            val selected = current == route
            Column(
                Modifier.clickable { onNavigate(route) }.padding(horizontal = 11.dp, vertical = 5.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text(label, color = if (selected) Amber else MutedWhite, fontSize = 12.sp, fontWeight = if (selected) FontWeight.Bold else FontWeight.Normal)
                Text(if (selected) "●" else "·", color = if (selected) Amber else Hairline, fontSize = 8.sp)
            }
        }
    }
}
