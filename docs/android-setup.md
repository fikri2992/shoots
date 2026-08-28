# Android internal-release setup

This is the production configuration contract for the Shoots Android client. Debug
builds keep using `adb reverse` and `http://127.0.0.1:8000`. Release builds refuse to
start until every value below is present and the signing keystore is outside the
repository.

## 1. Create the signing identity

Create one internal-release keystore outside the checkout:

```powershell
keytool -genkeypair -v `
  -keystore C:\Users\<you>\AndroidKeys\shoots-internal.jks `
  -alias shoots-internal `
  -keyalg RSA -keysize 3072 -validity 3650
```

Record the SHA-1 and SHA-256 certificate fingerprints without storing the passwords
in the repository:

```powershell
keytool -list -v `
  -keystore C:\Users\<you>\AndroidKeys\shoots-internal.jks `
  -alias shoots-internal
```

The SHA-1 identifies the Android OAuth client. The SHA-256 goes to the Firebase
Android app and `ANDROID_APP_LINK_SHA256` on the backend.

## 2. Configure Google identity and Drive authority

Use one Google Cloud project for Cloud Run, OAuth, and Firebase.

1. Create a Web OAuth client.
2. Add `<service origin>/auth/callback` as an authorized redirect URI.
3. Put that Web client id in both backend `GOOGLE_CLIENT_ID` and Android
   `SHOOTS_GOOGLE_SERVER_CLIENT_ID`.
4. Create an Android OAuth client for package `com.shoots.app` and the internal
   certificate SHA-1.
5. Add the test account to the OAuth consent screen while the app remains in testing.
6. Keep `drive.file` as the optional Drive scope. Drive authorization is separate
   from sign-in and the APK contains no client secret.

Credential Manager returns an ID token for the Web client audience. The backend
verifies signature, issuer, audience, expiry, nonce, and verified email before it
issues a revocable device session.

## 3. Configure Firebase Cloud Messaging

Add Firebase to the same Google Cloud project, then add an Android app with package
`com.shoots.app`, SHA-1, and SHA-256. Enable the FCM HTTP v1 API. The Cloud Run
service account needs `roles/firebasecloudmessaging.admin`; `infra/state.sh` grants
that role.

Copy these non-secret Firebase Android values from the app configuration:

| Gradle property | Firebase value |
|---|---|
| `SHOOTS_FIREBASE_APPLICATION_ID` | mobile SDK app id |
| `SHOOTS_FIREBASE_API_KEY` | API key |
| `SHOOTS_FIREBASE_PROJECT_ID` | project id |
| `SHOOTS_FIREBASE_SENDER_ID` | project number / messaging sender id |

Shoots initializes Firebase from these fields and does not require a committed
`google-services.json`.

## 4. Configure HTTPS and App Links

For a service origin such as
`https://shoots-123456789.asia-southeast2.run.app`, set:

```text
SHOOTS_SERVICE_ORIGIN=https://shoots-123456789.asia-southeast2.run.app
```

The manifest derives its App Link host from that origin. `SHOOTS_APP_LINK_HOST`
is an optional explicit override; the release guard rejects it when it differs
from the service-origin host.

Set the backend value to the internal certificate SHA-256:

```text
ANDROID_APP_LINK_SHA256=AA:BB:...:FF
```

The backend serves `/.well-known/assetlinks.json`. The release build fails if the
App Link host differs from the service-origin host.

## 5. Store local release values outside the repository

Put non-secret build values and keystore paths in the user-level
`%USERPROFILE%\.gradle\gradle.properties`. Keep passwords in environment variables
or another local secret source.

```properties
SHOOTS_GOOGLE_SERVER_CLIENT_ID=<web-client-id>.apps.googleusercontent.com
SHOOTS_FIREBASE_APPLICATION_ID=<firebase-app-id>
SHOOTS_FIREBASE_API_KEY=<firebase-api-key>
SHOOTS_FIREBASE_PROJECT_ID=<project-id>
SHOOTS_FIREBASE_SENDER_ID=<project-number>
SHOOTS_SERVICE_ORIGIN=https://<service-host>
SHOOTS_SIGNING_STORE_FILE=C:\\Users\\<you>\\AndroidKeys\\shoots-internal.jks
SHOOTS_SIGNING_KEY_ALIAS=shoots-internal
```

Set signing passwords only for the build process:

```powershell
$env:SHOOTS_SIGNING_STORE_PASSWORD = '<local secret>'
$env:SHOOTS_SIGNING_KEY_PASSWORD = '<local secret>'
```

## 6. Build and verify

```powershell
cd android
.\gradlew.bat verifyReleaseConfiguration :app:assembleRelease
```

Then verify the produced certificate and install the exact APK:

```powershell
apksigner verify --verbose --print-certs app\build\outputs\apk\release\app-release.apk
adb install -r app\build\outputs\apk\release\app-release.apk
adb shell pm get-app-links com.shoots.app
```

Verify the matching server statement:

```powershell
Invoke-RestMethod https://<service-host>/.well-known/assetlinks.json
```

## 7. Physical acceptance boundary

The APK is not accepted until one continuous Xiaomi run proves:

1. native Google sign-in;
2. automatic future Camera import under full media access;
3. selected-only access remains manual;
4. process death and network recovery preserve the outbox and Capture Session;
5. one FCM summary opens the authoritative native record;
6. Drive connects and disconnects separately from identity;
7. device revocation removes server access and local cached authority;
8. offline Now, Shots, Experiment, and Journey reads still work.

Official references: [Credential Manager Google sign-in](https://developer.android.com/identity/sign-in/credential-manager-siwg-implementation), [Google authorization](https://developer.android.com/identity/authorization), [Firebase Admin sending](https://firebase.google.com/docs/cloud-messaging/send/admin-sdk), and [Android App Links](https://developer.android.com/training/app-links/verify-android-applinks).
