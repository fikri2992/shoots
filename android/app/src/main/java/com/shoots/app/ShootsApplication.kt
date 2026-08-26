package com.shoots.app

import android.app.Application
import androidx.work.WorkManager
import coil.ImageLoader
import coil.ImageLoaderFactory
import coil.imageLoader
import com.google.firebase.FirebaseApp
import com.google.firebase.FirebaseOptions
import com.google.firebase.installations.FirebaseInstallations
import com.google.firebase.messaging.FirebaseMessaging
import com.shoots.app.data.ApiFactory
import com.shoots.app.data.LegacyStateMigrator
import com.shoots.app.data.SessionStore
import com.shoots.app.data.ShootsDatabase
import com.shoots.app.data.ShootsRepository
import com.shoots.app.phone.PhoneMediaStore
import com.shoots.app.work.PhoneSourceScheduler
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.tasks.await
import kotlinx.serialization.json.Json

class AppContainer(application: Application) {
    val json = Json {
        ignoreUnknownKeys = true
        explicitNulls = false
        encodeDefaults = true
    }
    val database = ShootsDatabase.build(application)
    val sessions = SessionStore(application)
    val apiFactory = ApiFactory(
        BuildConfig.SERVICE_ORIGIN,
        sessions,
        json,
        BuildConfig.DEBUG,
    )
    val phoneSource = PhoneMediaStore(application, database.dao(), sessions)
    val repository = ShootsRepository(
        application,
        apiFactory.api,
        database.dao(),
        sessions,
        json,
        phoneSource,
    )

    init {
        runBlocking(Dispatchers.IO) {
            LegacyStateMigrator(application, database.dao()).migrate()
        }
    }
}

class ShootsApplication : Application(), ImageLoaderFactory {
    lateinit var container: AppContainer
        private set
    private val applicationScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
        initializeFirebase()
        applicationScope.launch { PhoneSourceScheduler.scheduleWatch(this@ShootsApplication) }
    }

    override fun newImageLoader(): ImageLoader = ImageLoader.Builder(this)
        .okHttpClient(container.apiFactory.okHttp)
        .crossfade(true)
        .respectCacheHeaders(true)
        .build()

    @OptIn(coil.annotation.ExperimentalCoilApi::class)
    suspend fun clearLocalData() {
        WorkManager.getInstance(this).cancelAllWork().result.get()
        container.database.clearAllTables()
        imageLoader.memoryCache?.clear()
        imageLoader.diskCache?.clear()
        if (FirebaseApp.getApps(this).isNotEmpty()) {
            runCatching { FirebaseMessaging.getInstance().unregister().await() }
            runCatching { FirebaseInstallations.getInstance().delete().await() }
        }
    }

    private fun initializeFirebase() {
        if (
            listOf(
                BuildConfig.FIREBASE_APPLICATION_ID,
                BuildConfig.FIREBASE_API_KEY,
                BuildConfig.FIREBASE_PROJECT_ID,
                BuildConfig.FIREBASE_SENDER_ID,
            ).any(String::isBlank)
        ) {
            return
        }
        if (FirebaseApp.getApps(this).isNotEmpty()) return
        val options = FirebaseOptions.Builder()
            .setApplicationId(BuildConfig.FIREBASE_APPLICATION_ID)
            .setApiKey(BuildConfig.FIREBASE_API_KEY)
            .setProjectId(BuildConfig.FIREBASE_PROJECT_ID)
            .setGcmSenderId(BuildConfig.FIREBASE_SENDER_ID)
            .build()
        FirebaseApp.initializeApp(this, options)
    }
}

val android.content.Context.shootsApplication: ShootsApplication
    get() = applicationContext as ShootsApplication
