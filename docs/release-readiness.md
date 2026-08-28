# Release readiness

> Verified 2026-08-28. This records evidence, not intended configuration. Never put
> credential values in this document.

## Candidate

`main` is pushed through runtime commit
`c1068727a65535c876469e6657cf1738242cc999`, deployed after the complete local
gate and clean native-Windows Cloud preflight. The image uses the immutable short
SHA tag and the service stores the full SHA as deployment evidence.

Implemented and locally proven:

- capture-continuous Scene and Shoot membership;
- independent Run, Capture Session, and Shoot barriers;
- bounded scheduled replay of stale retrying Runs after Pub/Sub exhausts delivery,
  through each stage's ordinary idempotent handler;
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
- evidence-bound Shoot and terminal-Experiment Deconstruction preparation, 1080×1350
  rendering, photographer-owned Keeper cover, and Android multi-image sharing;
- replayable Intervention Records from offer through observable outcome, including
  automatic route adaptation after repeated comparable unchanged outcomes;
- one deterministic Shot Teaching Receipt that keeps Keep, Notice, Try, Check, and a
  single matching image layer together on Android and web;
- inspectable Visual Evidence strategies for all 57 still Techniques, including
  measured maps, bounded geometry, explicit verification state, and honest fallback;
- explicit Google Picker import as Mine or Inspiration, canonical Drive-file
  idempotency across Picker and folder reconciliation, and Android Files/Drive selection;
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
| Backend behavior | 618-test complete pytest suite plus continuous Shoot, abandoned-Run recovery, and Drive-selection acceptance | pass |
| Real-agent quality | 11 real Shot cases under report SHA-256 `5c161d5c760345e900a3b4b8307e4b90ca771c6958d794d1adc81c2b8bb1f4e3`, plus two real Journey-writer overclaim cases under prompt version `ddabb4791f14`; developer review against the locked hobbyist perspective | pass locally |
| Web client | 35 integration and domain checks plus production build | pass |
| Android debug build | `:app:assembleDebug` | pass |
| Android static analysis | `:app:lintDebug` | pass |
| Android instrumentation | full emulator suite passed with two explicit human/device gates skipped; the updated two-case source-authority UI class passed separately | pass |
| Android release guard | `verifyReleaseConfiguration` rejects blank OAuth, Firebase, HTTPS origin, App Link, and external signing inputs by name without printing values | pass; debug App Link fingerprint is deployed, production signing values remain absent |
| Android/backend integration | production-origin `RefreshSnapshotWorker` used a disposable bearer token, fetched the deployed mobile snapshot into Room, and the device was immediately revoked | pass separately |
| 390 dp Now | receipt, processing, stale-revision, and Experiment focus tests | pass |
| Cloud Run | `shoots-00003-hr5`, image digest `sha256:58efd3daba80e0a7142499c5a0c810507418e989ad07d6944904ea4b56b2c01a`, 100% traffic; health, authenticated web, production mobile snapshot, and Picker verified live; no revision errors | pass |
| Google Drive selection | authenticated production Picker opened; one selected file became exactly one `drive_picker` Inspiration and never a Photographer Shot | pass |
| Physical Xiaomi | current Shoot workflow not installed or exercised | not verified |
| Signed internal APK | Firebase Android app, OAuth, FCM, production origin, and debug certificate are configured; external release keystore and passwords remain absent | not buildable yet |

### Cloud preflight and state

The native Windows preflight passed against `agentic-system-505405` on 2026-08-28.
Required APIs, Firestore, `gs://agentic-system-505405-shoots`, the runtime service
account, and four mounted Secret Manager values are present. Pub/Sub stage pushes
have OIDC, retries, and dead-letter routes; `shoots-tick`, `shoots-daily`, and
`shoots-renew` are enabled. All 15 checked-in composite Firestore indexes required by
ordered Shoots queries are ready. The deployed App Link value is the existing debug
certificate fingerprint, not an internal-release identity.

## Deployment evidence and boundary

Shoots is live at
`https://shoots-718560154436.asia-southeast2.run.app`. Cloud Run reports revision
`shoots-00003-hr5` ready with 100% traffic and `SOURCE_SHA` equal to the recorded
runtime commit. Authenticated browser reads returned the new Drive actions and current
archive. Picker configuration returned enabled without exposing its token, and a real
selection produced one separate Inspiration receipt. A disposable Android device
session fetched `/api/mobile/snapshot` through WorkManager and was revoked. No Cloud
Run error was recorded for the revision. Revision `shoots-00002-chw` remains available
as the immediate rollback target.

This does not prove the full continuous Shot workflow. Phone Source ingestion,
Firestore Run advancement, Shoot closure, Shoot Record settlement, FCM, optional
Drive connection, and the three live barriers still require one physical end-to-end
acceptance run.

## Android production inputs

The exact setup, source of each value, release-build guard, and physical verification
commands are in [Android setup](android-setup.md). The approved Cloud sequence and
readback evidence are in [Cloud proof](cloud-proof.md).

OAuth, Firebase, HTTPS origin, and App Link values are configured outside the
repository in the user Gradle profile. These signing values remain absent:

```text
SHOOTS_SIGNING_STORE_FILE
SHOOTS_SIGNING_STORE_PASSWORD
SHOOTS_SIGNING_KEY_ALIAS
SHOOTS_SIGNING_KEY_PASSWORD
```

The debug build intentionally continues to use the adb-reversible local origin. Do not
put a client secret in the APK. Google Credential Manager needs the server client id;
Drive AuthorizationClient remains a separate optional grant.

## Physical acceptance still required

After the release signing identity and physical Xiaomi are available:

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
