# Release readiness

> Verified 2026-08-28. This records evidence, not intended configuration. Never put
> credential values in this document.

## Candidate

`main` is pushed through Android commit
`3e0bdd6b782b86d27786d532b912750265b797f7`. Cloud Run remains at runtime commit
`e535a48db3de8f8d435c350517d1595dc1888505`, deployed after the complete local
gate and clean native-Windows Cloud preflight. The later commit changes only the
Android Phone Source and its contract, so no service redeploy is required.

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
- native Drive connect, provider selection as Inspiration and Mine, reviewed output,
  disconnect with owned files preserved, and refresh-token-bearing reconnect;
- one 11-case real-agent report under prompt digest `1c738851cdfb`: 180 automatic
  checks passed, zero failed, 12 remained explicit human-review questions, and no
  case errored;
- cached mobile snapshot and Now focal order;
- offline receipt recovery after Room database reopen;
- one real emulator WorkManager request through adb reverse, bearer authentication,
  backend snapshot, and Room write;
- one normal emulator system-Camera Shot saved outside `DCIM/Camera/`, learned as
  the approved `Pictures/` album, streamed to production without manual upload,
  completed by the deployed Run, and returned as a four-step native visual story;
- one two-Shot Explore Capture Session with a frozen Variation, settled member Runs,
  no Verdict, explicit completion, and type-correct Experiments and Journey records.

The current dependency order and acceptance boundaries are recorded in
[implementation order](implementation-order.md#ordered-phases).

## Current gates

| Gate | Evidence | State |
|---|---|---|
| Backend format and lint | Ruff over `app` and `tests` | pass |
| Backend behavior | 618-test complete pytest suite plus continuous Shoot, abandoned-Run recovery, and Drive-selection acceptance | pass |
| Real-agent quality | 11 real Shot cases under report SHA-256 `5c161d5c760345e900a3b4b8307e4b90ca771c6958d794d1adc81c2b8bb1f4e3`, plus two real Journey-writer overclaim cases under prompt version `ddabb4791f14`; developer review against the locked hobbyist perspective | pass locally |
| Web client | 37 integration and domain checks plus production build | pass |
| Android debug build | `:app:assembleDebug` | pass |
| Android static analysis | `:app:lintDebug` | pass |
| Android instrumentation | 43 tests finished with zero failures and two explicit environment-only skips; the real MediaStore tests include learning a non-`DCIM/Camera/` album from an explicit Camera visit. The seven-case Journey class and five-case Experiments class then passed with no skips after live Experiment records exposed type and retry-feedback defects | pass |
| Android release guard | `verifyReleaseConfiguration` rejects blank OAuth, Firebase, HTTPS origin, App Link, and external signing inputs by name without printing values | pass; debug App Link fingerprint is deployed, production signing values remain absent |
| Android/backend integration | The signed-in emulator opened the normal system Camera, learned its `Pictures/` output album, automatically uploaded `IMG_20260828_215316.jpg`, and read the completed production Analysis back into Room after restart | pass on emulator; physical pending |
| 390 dp Now | receipt, processing, stale-revision, and Experiment focus tests | pass |
| Cloud Run | `shoots-00006-mzn`, image digest `sha256:a13c558a55dd450e49278ac99faffa0e234339ce7d9538b36dcf1a8bbe79aaaa`, 100% traffic; health, authenticated web visual story, production mobile snapshot, Picker, and scheduled Run repair verified live; no revision errors | pass |
| Google Drive selection | Authenticated production web Picker created one `drive_picker` Inspiration. Android then connected natively, selected a provider file as Inspiration without changing the 16-Shot Journey, selected another as Mine and completed its Run at 17 Shots, exposed the reviewed Drive copy, disconnected with the owned folder still visible, and reconnected after replacing the deleted offline token | pass on web and emulator; physical pending |
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
`shoots-00006-mzn` ready with 100% traffic and `SOURCE_SHA` equal to the recorded
runtime commit. Authenticated browser reads returned the new Drive actions and current
archive. Picker configuration returned enabled without exposing its token, and a real
selection produced one separate Inspiration receipt. A disposable Android device
session fetched `/api/mobile/snapshot` through WorkManager and was revoked. A manually
triggered production scheduler tick found three Runs abandoned after Analyst delivery
exhaustion; all three re-entered the ordinary Analyst handler, stored Analysis, and
settled every Run stage. The deployed web visual story loaded the stored rendered path
artifact for `02-leading-lines-road.jpg`; the legacy market Shot omitted its unsupported
line claim instead of drawing a box. No Cloud Run error was recorded for the revision.
Revision `shoots-00005-tb6` remains available as the immediate rollback target.

This proves durable production Run recovery, the continuous Camera-to-completed-Run
Phone Source path, one multi-member Capture Session, one settled three-Shot/two-Scene
Shoot Record, and the native Drive lifecycle on the emulator. FCM and all three barriers
in one physical run remain unverified.

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
