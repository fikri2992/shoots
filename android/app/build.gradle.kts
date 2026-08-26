import java.net.URI

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.kotlin.plugin.serialization")
    id("com.google.devtools.ksp")
}

fun quoted(value: String): String = "\"${value.replace("\\", "\\\\").replace("\"", "\\\"")}\""

fun configured(name: String): String =
    providers.gradleProperty(name).orNull
        ?: providers.environmentVariable(name).orNull
        ?: ""

val signingStoreFile = configured("SHOOTS_SIGNING_STORE_FILE")
val signingStorePassword = configured("SHOOTS_SIGNING_STORE_PASSWORD")
val signingKeyAlias = configured("SHOOTS_SIGNING_KEY_ALIAS")
val signingKeyPassword = configured("SHOOTS_SIGNING_KEY_PASSWORD")
val googleServerClientId = configured("SHOOTS_GOOGLE_SERVER_CLIENT_ID")
val firebaseApplicationId = configured("SHOOTS_FIREBASE_APPLICATION_ID")
val firebaseApiKey = configured("SHOOTS_FIREBASE_API_KEY")
val firebaseProjectId = configured("SHOOTS_FIREBASE_PROJECT_ID")
val firebaseSenderId = configured("SHOOTS_FIREBASE_SENDER_ID")
val serviceOrigin = configured("SHOOTS_SERVICE_ORIGIN")
val appLinkHost = configured("SHOOTS_APP_LINK_HOST")
val internalSigningReady = listOf(
    signingStoreFile,
    signingStorePassword,
    signingKeyAlias,
    signingKeyPassword,
).all(String::isNotBlank)

android {
    namespace = "com.shoots.app"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.shoots.app"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.1"

        buildConfigField("String", "GOOGLE_SERVER_CLIENT_ID", quoted(googleServerClientId))
        buildConfigField("String", "FIREBASE_APPLICATION_ID", quoted(firebaseApplicationId))
        buildConfigField("String", "FIREBASE_API_KEY", quoted(firebaseApiKey))
        buildConfigField("String", "FIREBASE_PROJECT_ID", quoted(firebaseProjectId))
        buildConfigField("String", "FIREBASE_SENDER_ID", quoted(firebaseSenderId))
        manifestPlaceholders["shootsAppLinkHost"] =
            appLinkHost.ifBlank { "unconfigured.invalid" }

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    signingConfigs {
        if (internalSigningReady) {
            create("internal") {
                storeFile = file(signingStoreFile)
                storePassword = signingStorePassword
                keyAlias = signingKeyAlias
                keyPassword = signingKeyPassword
            }
        }
    }

    buildTypes {
        debug {
            buildConfigField(
                "String",
                "SERVICE_ORIGIN",
                quoted(configured("SHOOTS_DEBUG_SERVICE_ORIGIN").ifBlank { "http://127.0.0.1:8000" }),
            )
        }
        release {
            isMinifyEnabled = false
            buildConfigField("String", "SERVICE_ORIGIN", quoted(serviceOrigin))
            signingConfig = signingConfigs.findByName("internal")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }

    packaging {
        resources.excludes += "/META-INF/{AL2.0,LGPL2.1}"
    }
}

val verifyReleaseConfiguration by tasks.registering {
    group = "verification"
    description = "Refuse an unsigned or unconfigured internal release APK."
    doLast {
        val values = mapOf(
            "SHOOTS_GOOGLE_SERVER_CLIENT_ID" to googleServerClientId,
            "SHOOTS_FIREBASE_APPLICATION_ID" to firebaseApplicationId,
            "SHOOTS_FIREBASE_API_KEY" to firebaseApiKey,
            "SHOOTS_FIREBASE_PROJECT_ID" to firebaseProjectId,
            "SHOOTS_FIREBASE_SENDER_ID" to firebaseSenderId,
            "SHOOTS_SERVICE_ORIGIN" to serviceOrigin,
            "SHOOTS_APP_LINK_HOST" to appLinkHost,
            "SHOOTS_SIGNING_STORE_FILE" to signingStoreFile,
            "SHOOTS_SIGNING_STORE_PASSWORD" to signingStorePassword,
            "SHOOTS_SIGNING_KEY_ALIAS" to signingKeyAlias,
            "SHOOTS_SIGNING_KEY_PASSWORD" to signingKeyPassword,
        )
        val missing = values.filterValues(String::isBlank).keys.sorted()
        check(missing.isEmpty()) { "Missing release configuration: ${missing.joinToString()}" }
        check(googleServerClientId.endsWith(".apps.googleusercontent.com")) {
            "SHOOTS_GOOGLE_SERVER_CLIENT_ID must be a Google web client id"
        }
        val origin = URI(serviceOrigin)
        check(origin.scheme == "https" && !origin.host.isNullOrBlank()) {
            "SHOOTS_SERVICE_ORIGIN must be a valid HTTPS origin"
        }
        check(origin.host == appLinkHost) {
            "SHOOTS_APP_LINK_HOST must match SHOOTS_SERVICE_ORIGIN"
        }
        val store = file(signingStoreFile).canonicalFile
        check(store.isFile) { "SHOOTS_SIGNING_STORE_FILE does not exist" }
        val repositoryRoot = rootProject.projectDir.parentFile.canonicalFile
        check(!store.toPath().startsWith(repositoryRoot.toPath())) {
            "The release keystore must stay outside the repository"
        }
    }
}

tasks.matching { it.name == "preReleaseBuild" }.configureEach {
    dependsOn(verifyReleaseConfiguration)
}

ksp {
    arg("room.schemaLocation", "$projectDir/schemas")
}

dependencies {
    implementation("androidx.core:core-ktx:1.16.0")
    implementation("androidx.activity:activity-compose:1.10.1")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.navigation:navigation-compose:2.9.8")
    implementation("androidx.work:work-runtime-ktx:2.11.2")

    implementation("androidx.room:room-runtime:2.8.4")
    implementation("androidx.room:room-ktx:2.8.4")
    ksp("androidx.room:room-compiler:2.8.4")

    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
    implementation("com.jakewharton.retrofit:retrofit2-kotlinx-serialization-converter:1.0.0")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-play-services:1.9.0")

    implementation("androidx.credentials:credentials:1.6.0")
    implementation("androidx.credentials:credentials-play-services-auth:1.6.0")
    implementation("com.google.android.libraries.identity.googleid:googleid:1.2.0")
    implementation("com.google.android.gms:play-services-auth:21.6.0")

    implementation(platform("com.google.firebase:firebase-bom:34.18.0"))
    implementation("com.google.firebase:firebase-messaging")
    implementation("com.google.firebase:firebase-installations")

    implementation("io.coil-kt:coil-compose:2.7.0")
    implementation("io.coil-kt:coil:2.7.0")

    implementation(platform("androidx.compose:compose-bom:2024.12.01"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")

    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test:core:1.6.1")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test:rules:1.6.1")
    androidTestImplementation("androidx.room:room-testing:2.8.4")
    androidTestImplementation("androidx.work:work-testing:2.11.2")
    androidTestImplementation(platform("androidx.compose:compose-bom:2024.12.01"))
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}
