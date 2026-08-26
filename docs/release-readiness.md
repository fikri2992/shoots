# Release readiness

> Verified 2026-08-27. This records evidence, not intended configuration. Never put
> credential values in this document.

## Candidate

The protected Shoot workflow remains available at `6ea693f` on
`codex/shoot-record`. The candidate-protected continuation through `9e4a856` on
`codex/learning-memory` passed the complete local gate. Neither branch exists on the
remote yet.

Implemented and locally proven:

- capture-continuous Scene and Shoot membership;
- independent Run, Capture Session, and Shoot barriers;
- late-media Shoot Record revision without history rewrite;
- deterministic evidence-labelled Shoot receipt with no quality score;
- typed Scout `explain`, Keeper-backed `reproduce`, or `silence`, including exact
  warrants and rejected unavailable routes;
- rebuildable Technique Map evidence axes, Mine/Inspiration correction, and scoped
  Photographer memory;
- corrected Explore with immutable per-session Variations, observations, and no
  Criteria or Verdict;
- evidence-bound Deconstruction preparation, 1080×1350 rendering, photographer-owned
  Keeper cover, and Android multi-image sharing;
- cached mobile snapshot and Now focal order;
- offline receipt recovery after Room database reopen;
- one real emulator WorkManager request through adb reverse, bearer authentication,
  backend snapshot, and Room write.

The complete local evidence and the test-harness correction are recorded in
[implementation order](implementation-order.md#checkpoint-result--2026-08-27).

## Current gates

| Gate | Evidence | State |
|---|---|---|
| Backend format and lint | Ruff over `app` and `tests` | pass |
| Backend behavior | complete pytest suite plus continuous Shoot acceptance | pass |
| Android debug build | `:app:assembleDebug` | pass |
| Android static analysis | `:app:lintDebug` | pass |
| Android instrumentation | 30 emulator tests passed; two hardware-only tests skipped | pass |
| Android/backend integration | authenticated `RefreshSnapshotWorker` produced a real `GET /api/mobile/snapshot` and cached it | pass separately |
| 390 dp Now | receipt, processing, stale-revision, and Experiment focus tests | pass |
| Cloud Run | project `agentic-system-505405` has `sh-api` and `visual-qa`; `sh-api` serves a different Scene Hunter app, so no Shoots service was found in `asia-southeast2` | not deployed |
| Physical Xiaomi | current Shoot workflow not installed or exercised | not verified |
| Signed internal APK | production identity, Firebase, service origin, and signing inputs unavailable | not buildable yet |

## Deployment boundary

Deployment requires explicit Photographer/developer approval. A push is not a
deployment. After approval:

1. select the exact clean candidate SHA;
2. load the existing backend environment without copying secrets into the worktree;
3. run the complete local gates once more;
4. deploy that exact source to Cloud Run;
5. verify ready revision, public health, auth, Firestore writes, Pub/Sub retries,
   Scheduler closure, and all three barriers;
6. record the live revision and keep the prior revision available if one exists.

No Shoots Cloud Run service currently exists, so there is no prior Shoots revision to
call a fallback. The protected `6ea693f` branch remains the source fallback only.

## Android production inputs

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
