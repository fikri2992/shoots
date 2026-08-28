# Cloud continuous-proof runbook

This runbook mutates Google Cloud only after explicit approval. It deploys one exact
clean commit, reconciles every stage subscription, and records enough state to prove
the unattended workflow.

## Before approval

- The candidate checkout is clean and its SHA is recorded.
- `backend/.env` contains the Web OAuth client id, VAPID public values, and Android
  release SHA-256 fingerprint.
- The four backend secret values exist locally only long enough for
  `infra/state.sh` to create Secret Manager versions.
- The Android release configuration follows [Android setup](android-setup.md).
- The prior source candidate remains available for rollback.

## Provision and preflight

Run from Bash or Cloud Shell:

```bash
export GCP_PROJECT=<project-id>
export GCP_LOCATION=asia-southeast2
export ENV_FILE=backend/.env

./infra/enable-apis.sh
ENV_FILE="$ENV_FILE" ./infra/state.sh
./infra/preflight.sh
```

On the Windows development host, run the equivalent native preflight so it reuses
the signed-in Windows Git and gcloud sessions:

```powershell
.\infra\preflight.ps1 `
  -Project <project-id> `
  -Region asia-southeast2 `
  -EnvFile C:\path\to\backend\.env
```

`preflight.sh` is read-only. It checks the clean SHA, active gcloud account, project,
required APIs, state resources, enabled secret versions, OAuth/VAPID public values,
and Android App Link fingerprint. It prints no credential value.

## Deploy and reconcile transport

```bash
./infra/deploy.sh
```

Read the deployed URL from Cloud Run rather than copying terminal history:

```bash
SERVICE_URL="$(gcloud run services describe shoots \
  --project "$GCP_PROJECT" --region "$GCP_LOCATION" \
  --format='value(status.url)')"
```

Configure Pub/Sub and Scheduler:

```bash
PUBSUB_PUSH_BASE_URL="$SERVICE_URL" \
PUBSUB_PUSH_SA="shoots-ingest@${GCP_PROJECT}.iam.gserviceaccount.com" \
./infra/topics.sh

SERVICE_URL="$SERVICE_URL" ./infra/scheduler.sh
```

Each stage subscription uses the service base URL as its explicit OIDC audience,
reconciles an existing endpoint instead of returning early, and owns one retained
dead-letter topic plus pull subscription. Pub/Sub's service agent receives only the
publisher and subscriber roles needed for dead-letter forwarding.

## Read back the deployed state

Record these outputs without tokens or personal media:

```bash
git rev-parse HEAD
gcloud run services describe shoots \
  --project "$GCP_PROJECT" --region "$GCP_LOCATION" \
  --format='yaml(status.url,status.latestReadyRevisionName,spec.template.spec.serviceAccountName)'
gcloud pubsub subscriptions list --project "$GCP_PROJECT" \
  --filter='name:shoots-' --format='table(name,topic,pushConfig.pushEndpoint,deadLetterPolicy.deadLetterTopic)'
gcloud scheduler jobs list --project "$GCP_PROJECT" --location "$GCP_LOCATION" \
  --filter='name:shoots-' --format='table(name,schedule,state,httpTarget.uri)'
```

Then check public routes:

```bash
curl --fail --show-error "$SERVICE_URL/api/health"
curl --fail --show-error "$SERVICE_URL/.well-known/assetlinks.json"
```

## Proof-of-action scenario

The first production-connected emulator proof completed on 2026-08-28. Shoots opened
the normal Android Camera, froze a MediaStore watermark, learned the Camera's
nonstandard `Pictures/` output album, accepted `IMG_20260828_215316.jpg` without a
manual picker, streamed it through direct ingress, and later read the completed Run
and four-step visual story back from the production snapshot. A following Explore
Capture Session froze one Variation, committed two Camera members, waited for both Runs,
recorded one observed Variation with no Verdict, and completed into Android Experiments
and Journey. Physical Xiaomi proof, Shoot settlement, all barriers in one run, and FCM
remain separate gates.

Use disposable records and one ordinary phone Shoot:

1. Android receives a revocable device session.
2. A normal Camera Shot enters through Phone Source without manual upload.
3. Firestore shows one Shot and one Run.
4. Pub/Sub advances Ingest, Analyst, Cartographer, Judge when applicable, and Scribe
   without duplicate terminal records.
5. Scheduler closes the natural Shoot after inactivity.
6. One Shoot Record accounts for every current member and stores the typed Scout
   route plus rejected alternatives.
7. The Photographer enters one supported Experiment through a Capture Session.
8. Every committed member settles before the Experiment and Intervention Record
   update.
9. Android reads the newest receipt and Journey from a fresh server sync, then again
   offline.
10. One FCM summary deep-links to the authoritative record.

The run fails if it needs a hidden database edit, manual Shot upload, duplicate record
cleanup, or an unstated retry. Start again with new disposable ids after a narrow fix.

Official references: [Cloud Run service URLs](https://cloud.google.com/run/docs/triggering/https-request), [authenticated Pub/Sub push](https://cloud.google.com/pubsub/docs/authenticate-push-subscriptions), [dead-letter IAM](https://cloud.google.com/pubsub/docs/dead-letter-topics), and [Cloud Scheduler OIDC](https://cloud.google.com/run/docs/triggering/using-scheduler).
