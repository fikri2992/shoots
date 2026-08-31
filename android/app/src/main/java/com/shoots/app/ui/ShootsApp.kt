package com.shoots.app.ui

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.Role
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
import com.shoots.app.Ink
import com.shoots.app.InkRaised
import com.shoots.app.MutedWhite
import com.shoots.app.R
import com.shoots.app.data.DeconstructionDto
import kotlinx.coroutines.launch

data class AppActions(
    val signIn: () -> Unit,
    val requestMedia: () -> Unit,
    val enableSource: () -> Unit,
    val disableSource: () -> Unit,
    val openFreeCamera: () -> Unit,
    val chooseFreeShots: () -> Unit,
    val requestExperiment: (Boolean) -> Unit,
    val requestExplore: (Boolean, String) -> Unit,
    val startExperiment: (String, String) -> Unit,
    val startSavedDirection: (String) -> Unit,
    val completeExplore: (String) -> Unit,
    val prepareDeconstruction: (String, String, Int, String) -> Unit,
    val shareDeconstruction: (DeconstructionDto) -> Unit,
    val saveDeconstruction: (DeconstructionDto) -> Unit,
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
    val preparingStory by viewModel.preparingStory.collectAsStateWithLifecycle()
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
    val showNavigation = route in setOf("now", "shots", "experiments", "journey")

    LaunchedEffect(deepRoute) {
        val destination = when (deepRoute.substringBefore('/')) {
            "journey" -> "journey"
            "experiments" -> "experiments"
            "shots", "shot" -> "shots"
            "shoot-record" -> "now"
            "settings" -> "settings"
            else -> "now"
        }
        if (deepRoute.isNotBlank()) nav.navigate(destination) { launchSingleTop = true }
    }

    Box(Modifier.fillMaxSize().background(Ink)) {
        NavHost(
            navController = nav,
            startDestination = "now",
            modifier = Modifier.fillMaxSize(),
            enterTransition = {
                val forward = routeRank(targetState.destination.route) >= routeRank(initialState.destination.route)
                fadeIn(tween(170)) + slideInHorizontally(tween(220)) { width ->
                    if (forward) width / 10 else -width / 10
                }
            },
            exitTransition = {
                val forward = routeRank(targetState.destination.route) >= routeRank(initialState.destination.route)
                fadeOut(tween(130)) + slideOutHorizontally(tween(190)) { width ->
                    if (forward) -width / 16 else width / 16
                }
            },
            popEnterTransition = {
                fadeIn(tween(170)) + slideInHorizontally(tween(220)) { width -> -width / 10 }
            },
            popExitTransition = {
                fadeOut(tween(130)) + slideOutHorizontally(tween(190)) { width -> width / 16 }
            },
        ) {
            composable("now") {
                LaunchedEffect(
                    snapshot?.latestShootRecord?.shootId,
                    snapshot?.latestShootRecord?.revision,
                ) {
                    snapshot?.latestShootRecord?.let {
                        viewModel.loadShootRecordMembers(it.shotIds)
                    }
                }
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
                    onContinueSession = actions.continueSession,
                    onFinishSession = actions.finishSession,
                    onCancelSession = actions.cancelSession,
                    onImportSessionAsFree = actions.importSessionAsFree,
                    onOpenShot = { nav.navigate("shot/$it") },
                    onOpenShots = { nav.navigate("shots") },
                    onOpenShootRecord = { shootId, revision ->
                        nav.navigate("shoot-record/$shootId/$revision")
                    },
                    onOpenExperiments = { nav.navigate("experiments") },
                    onStartSavedDirection = actions.startSavedDirection,
                    onLeaveSavedDirection = { sourceShotId, techniqueId ->
                        scope.launch {
                            viewModel.chooseExperimentDirection(sourceShotId, techniqueId, false)
                        }
                    },
                    onRespondScoutRecommendation = { shootId, revision, action, optionId ->
                        scope.launch {
                            val handled = viewModel.respondScoutRecommendation(
                                shootId,
                                revision,
                                action,
                                optionId,
                            )
                            if (handled && action == "accept") nav.navigate("experiments")
                        }
                    },
                    onOpenSettings = { nav.navigate("settings") },
                    availableShots = shots,
                )
            }
            composable("shots") {
                LaunchedEffect(Unit) { viewModel.loadMoreShots(reset = true) }
                ShotsScreen(
                    shots = shots,
                    inspirations = snapshot?.recentInspirations.orEmpty(),
                    pendingImports = pendingImports,
                    canLoadMore = canLoadMoreShots,
                    busy = busy,
                    imageUrl = { viewModel.imageUrl(it) },
                    inspirationUrl = { viewModel.imageUrl(it) },
                    onShot = { nav.navigate("shot/$it") },
                    onLoadMore = { viewModel.loadMoreShots() },
                    onRetryImport = viewModel::retryImport,
                    onRestoreInspiration = { id ->
                        scope.launch { viewModel.moveInspirationToMine(id) }
                    },
                    onReauthenticate = actions.signIn,
                    onAdd = actions.chooseFreeShots,
                    readOnlySample = snapshot?.user?.recordMode == "sample",
                    snapshot = snapshot,
                    onOpenShootRecord = { shootId, revision ->
                        nav.navigate("shoot-record/$shootId/$revision")
                    },
                    onKeeper = { id, keeper ->
                        scope.launch { viewModel.setKeeper(id, keeper) }
                    },
                )
            }
            composable("shot/{id}") { entry ->
                val id = entry.arguments?.getString("id").orEmpty()
                val detail by viewModel.observeShotDetail(id).collectAsStateWithLifecycle(initialValue = null)
                LaunchedEffect(id) { viewModel.loadShot(id) }
                ShotDetailScreen(
                    detail,
                    imageUrl = { shot, original -> viewModel.imageUrl(shot, original) },
                    blobUrl = viewModel::blobUrl,
                    onBack = nav::popBackStack,
                    onKeeper = { keeper ->
                        scope.launch { viewModel.setKeeper(id, keeper) }
                    },
                    onMoveToInspiration = {
                        scope.launch {
                            if (viewModel.moveShotToInspiration(id)) nav.popBackStack()
                        }
                    },
                    onRetry = { scope.launch { viewModel.retryShot(id) } },
                    onOpenDrive = actions.openUrl,
                    experimentDirections = snapshot?.experimentDirections.orEmpty(),
                    onChooseExperimentDirection = { sourceShotId, techniqueId, save ->
                        scope.launch {
                            viewModel.chooseExperimentDirection(sourceShotId, techniqueId, save)
                        }
                    },
                    onOpenJourney = { nav.navigate("journey") },
                    onOpenExperiment = { nav.navigate("experiments") },
                    readOnlySample = snapshot?.user?.recordMode == "sample",
                )
            }
            composable("shoot-record/{shootId}/{revision}") { entry ->
                val shootId = entry.arguments?.getString("shootId").orEmpty()
                val revision = entry.arguments?.getString("revision")?.toIntOrNull() ?: 0
                val record = snapshot?.latestShootRecord?.takeIf {
                    it.shootId == shootId && it.revision == revision
                }
                LaunchedEffect(record?.shootId, record?.revision) {
                    record?.let { viewModel.loadShootRecordMembers(it.shotIds) }
                }
                ShootRecordScreen(
                    record = record,
                    shoot = snapshot?.latestShoot?.takeIf { it.id == shootId },
                    shots = shots,
                    interventions = snapshot?.recentInterventions.orEmpty(),
                    answers = snapshot?.recentScoutAnswers.orEmpty(),
                    imageUrl = { viewModel.imageUrl(it) },
                    onBack = nav::popBackStack,
                    onShot = { nav.navigate("shot/$it") },
                    onKeeper = { id, keeper ->
                        scope.launch { viewModel.setKeeper(id, keeper) }
                    },
                    readOnlySample = snapshot?.user?.recordMode == "sample",
                    loading = snapshot == null,
                )
            }
            composable("journey") {
                JourneyScreen(
                    snapshot = snapshot,
                    preparingStory = preparingStory,
                    imageUrl = { viewModel.imageUrl(it) },
                    blobUrl = viewModel::blobUrl,
                    onShot = { nav.navigate("shot/$it") },
                    onPrepareDeconstruction = actions.prepareDeconstruction,
                    onShareDeconstruction = actions.shareDeconstruction,
                    onSaveDeconstruction = actions.saveDeconstruction,
                    onOpenShootRecord = { shootId, revision ->
                        nav.navigate("shoot-record/$shootId/$revision")
                    },
                )
            }
            composable("experiments") {
                ExperimentsScreen(
                    snapshot = snapshot,
                    localSession = session,
                    busy = busy,
                    imageUrl = { viewModel.imageUrl(it) },
                    onRequestExperiment = actions.requestExperiment,
                    onRequestExplore = actions.requestExplore,
                    onStartExperiment = actions.startExperiment,
                    onCompleteExplore = actions.completeExplore,
                    onContinueSession = actions.continueSession,
                    onFinishSession = actions.finishSession,
                    onCancelSession = actions.cancelSession,
                    onImportSessionAsFree = actions.importSessionAsFree,
                    onShot = { nav.navigate("shot/$it") },
                )
            }
            composable("settings") {
                SettingsScreen(
                    snapshot = snapshot,
                    source = source,
                    mediaAccess = access,
                    notificationsGranted = notificationsGranted,
                    busy = busy,
                    onBack = nav::popBackStack,
                    onRequestMedia = actions.requestMedia,
                    onEnableSource = actions.enableSource,
                    onDisableSource = actions.disableSource,
                    onRequestNotifications = actions.requestNotifications,
                    onConnectDrive = actions.connectDrive,
                    onDisconnectDrive = actions.disconnectDrive,
                    onOpenDrive = actions.openUrl,
                    onForgetSignal = { signalId ->
                        scope.launch { viewModel.forgetPhotographerSignal(signalId) }
                    },
                    onReauthenticate = actions.signIn,
                    onRevoke = actions.revoke,
                    onDelete = actions.deleteAccount,
                )
            }
        }

        if (snapshot?.user?.recordMode == "sample") {
            Box(
                Modifier
                    .align(Alignment.TopCenter)
                    .fillMaxWidth()
                    .background(Amber)
                    .padding(horizontal = 16.dp, vertical = 10.dp),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    "SAMPLE RECORD · Hand-authored, read-only UI fixture. No agents ran.",
                    color = Ink,
                    fontSize = 11.sp,
                    lineHeight = 15.sp,
                    fontWeight = FontWeight.Bold,
                )
            }
        }

        if (error.isNotBlank() || notice.isNotBlank()) {
            Box(
                Modifier
                    .align(Alignment.BottomCenter)
                    .navigationBarsPadding()
                    .padding(horizontal = 14.dp)
                    .padding(bottom = if (showNavigation) 86.dp else 14.dp),
            ) {
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
            .padding(horizontal = 8.dp, vertical = 7.dp)
            .selectableGroup(),
        horizontalArrangement = Arrangement.SpaceAround,
    ) {
        listOf(
            NavigationItem("now", "Now", R.drawable.ic_now),
            NavigationItem("shots", "Shots", R.drawable.ic_shots),
            NavigationItem("experiments", "Experiments", R.drawable.ic_experiments),
            NavigationItem("journey", "Journey", R.drawable.ic_journey),
        ).forEach { item ->
            val selected = current == item.route
            val background by animateColorAsState(
                if (selected) Amber.copy(alpha = 0.13f) else InkRaised.copy(alpha = 0f),
                animationSpec = tween(180),
                label = "${item.label} navigation indicator",
            )
            val scale by animateFloatAsState(
                if (selected) 1f else 0.92f,
                animationSpec = tween(180),
                label = "${item.label} navigation icon",
            )
            Column(
                Modifier
                    .weight(1f)
                    .padding(horizontal = 3.dp)
                    .selectable(
                        selected = selected,
                        role = Role.Tab,
                        onClick = { onNavigate(item.route) },
                    )
                    .padding(vertical = 3.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Box(
                    Modifier
                        .size(width = 56.dp, height = 31.dp)
                        .background(background, RoundedCornerShape(99.dp)),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        painter = painterResource(item.icon),
                        contentDescription = null,
                        tint = if (selected) Amber else MutedWhite,
                        modifier = Modifier.size(21.dp).graphicsLayer { scaleX = scale; scaleY = scale },
                    )
                }
                Text(
                    item.label,
                    color = if (selected) Amber else MutedWhite,
                    fontSize = 10.sp,
                    fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium,
                )
            }
        }
    }
}

private data class NavigationItem(val route: String, val label: String, val icon: Int)

private fun routeRank(route: String?): Int = when (route?.substringBefore('/')) {
    "now" -> 0
    "shots" -> 1
    "experiments" -> 2
    "journey" -> 3
    "shot", "shoot-record", "settings" -> 4
    else -> 0
}
