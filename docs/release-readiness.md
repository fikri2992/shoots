# Release readiness

> Verified 2026-08-27. This records evidence, not intended configuration. Never put
> credential values in this document.

## Candidate

The protected Shoot workflow remains available at `6ea693f` on
`codex/shoot-record`. The current clean `codex/learning-memory` head, including
on-demand Technique Explore, passed the complete local gate. Resolve and record its
exact SHA immediately before any approved deployment. Neither branch exists on the
remote yet.

Implemented and locally proven:

- capture-continuous Scene and Shoot membership;
- independent Run, Capture Session, and Shoot barriers;
- late-media Shoot Record revision without history rewrite;
- deterministic evidence-labelled Shoot receipt with no quality score;
- typed Scout `explain`, consequential `ask`, corrected `explore`, Keeper-backed
  `reproduce`, or `silence`, including exact warrants and rejected routes;
- rebuildable Technique Map evidence axes, Mine/Inspiration correction, and scoped
  Photographer memory;
- separate natural recurrence from settled, evaluable, and Criteria-met Reproduce
  session evidence so one successful burst cannot claim repeatability;
- corrected Explore with immutable per-session Variations, observations, and no
  Criteria or Verdict;
- evidence-bound Deconstruction preparation, 1080×1350 rendering, photographer-owned
  Keeper cover, and Android multi-image sharing;
- replayable Intervention Records from offer through observable outcome, including
  automatic route adaptation after repeated comparable unchanged outcomes;
- one deterministic Shot Teaching Receipt that keeps Keep, Notice, Try, Check, and a
  single matching image layer together on Android and web;
- one 11-case real-agent report under prompt digest `1c738851cdfb`: 180 automatic
  checks passed, zero failed, 12 remained explicit human-review questions, and no
  case errored;
- cached mobile snapshot and Now focal order;
- offline receipt recovery after Room database reopen;
- one real emulator WorkManager request through adb reverse, bearer authentication,
  backend snapshot, and Room write.

The current dependency order and acceptance boundaries are recorded in
[implementation order](implementation-order.md#ordered-phases).

## Current gates

| Gate | Evidence | State |
|---|---|---|
| Backend format and lint | Ruff over `app` and `tests` | pass |
| Backend behavior | complete pytest suite plus continuous Shoot acceptance | pass |
| Real-agent quality | 11 real Gemini cases, report SHA-256 `5c161d5c760345e900a3b4b8307e4b90ca771c6958d794d1adc81c2b8bb1f4e3`; developer review against the locked hobbyist perspective | pass locally |
| Web client | 34 integration and domain checks plus production build | pass |
| Android debug build | `:app:assembleDebug` | pass |
| Android static analysis | `:app:lintDebug` | pass |
| Android instrumentation | 34 emulator tests passed after a clean emulator reboot; two hardware-only tests skipped. One prior run ended in an emulator system crash during Activity teardown; both interrupted cases and the full suite then passed unchanged | pass |
| Android release guard | `verifyReleaseConfiguration` rejects blank OAuth, Firebase, HTTPS origin, App Link, and external signing inputs by name without printing values | pass; production values absent |
| Android/backend integration | authenticated `RefreshSnapshotWorker` produced a real `GET /api/mobile/snapshot` and cached it | pass separately |
| 390 dp Now | receipt, processing, stale-revision, and Experiment focus tests | pass |
| Cloud Run | project `agentic-system-505405` has `sh-api` and `visual-qa`; `sh-api` serves a different Scene Hunter app, so no Shoots service was found in `asia-southeast2` | not deployed |
| Physical Xiaomi | current Shoot workflow not installed or exercised | not verified |
| Signed internal APK | production identity, Firebase, service origin, and signing inputs unavailable | not buildable yet |

### Read-only Cloud preflight

The native Windows preflight ran against `agentic-system-505405` on 2026-08-27. It
confirmed an active gcloud account, readable project, service account, Firestore
database, and every required API except FCM. It found eight concrete blockers:

- `VAPID_SUBJECT` is empty;
- `ANDROID_APP_LINK_SHA256` is empty because no internal release certificate is
  configured;
- `fcm.googleapis.com` is not enabled;
- `gs://agentic-system-505405-shoots` does not exist;
- the four mounted backend secrets have no enabled versions.

The approved `enable-apis.sh` and `state.sh` runs create the API, bucket, and Secret
Manager state. The contact value and release certificate require explicit developer
input. No Cloud resource changed during this preflight.

## Deployment boundary

Deployment requires explicit Photographer/developer approval. A push is not a
deployment. After approval:

1. select and record the exact clean `codex/learning-memory` candidate SHA;
2. load the existing backend environment without copying secrets into the worktree;
3. run the complete local gates once more;
4. deploy that exact source to Cloud Run;
5. verify ready revision, public health, auth, Firestore writes, Pub/Sub retries,
   Scheduler closure, and all three barriers;
6. record the live revision and keep the prior revision available if one exists.

No Shoots Cloud Run service currently exists, so there is no prior Shoots revision to
call a fallback. The protected `6ea693f` branch remains the source fallback only.

## Android production inputs

The exact setup, source of each value, release-build guard, and physical verification
commands are in [Android setup](android-setup.md). The approved Cloud sequence and
readback evidence are in [Cloud proof](cloud-proof.md).

These values were absent from both process environment and checked Gradle property
locations during the audit:

```text
SHOOTS_GOOGLE_SERVER_CLIENT_ID
SHOOTS_FIREBASE_APPLICATION_ID
SHOOTS_FIREBASE_API_KEY
SHOOTS_FIREBASE_PROJECT_ID
SHOOTS_FIREBASE_SENDER_ID
SHOOTS_SERVICE_ORIGIN
SHOOTS_SIGNING_STORE_FILE
SHOOTS_SIGNING_STORE_PASSWORD
SHOOTS_SIGNING_KEY_ALIAS
SHOOTS_SIGNING_KEY_PASSWORD
```

The debug build intentionally continues to use the adb-reversible local origin. Do not
put a client secret in the APK. Google Credential Manager needs the server client id;
Drive AuthorizationClient remains a separate optional grant.

## Physical acceptance still required

After Cloud and Android credentials exist:

1. native Google sign-in;
2. full Camera media permission and automatic free Shot ingestion;
3. a natural Shoot with at least two Scenes;
4. a settled current Shoot receipt and offline reopen;
5. Keeper-backed Reproduce reservation and multi-Shot Capture Session;
6. corrected Explore across at least two Variations with no Verdict;
7. Deconstruction cover selection and multi-image share target receipt;
8. network loss and recovery;
9. one FCM summary;
10. Drive connect, reviewed output, and disconnect with files preserved;
11. device revoke and disposable account deletion;
12. production-signed APK verification with the keystore outside the repository.

Until those steps pass, say “local emulator candidate,” not “release-ready Android
app” or “deployed product.”
