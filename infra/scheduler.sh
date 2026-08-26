#!/usr/bin/env bash
# Cloud Scheduler: the clock that makes Shoots autonomous. Idempotent.
#
#   shoots-tick     every 5 min   POST /tasks/tick            sync folders, push experiments whose light window opened
#   shoots-daily    06:00 Jakarta POST /tasks/daily           expire, decay, issue the day's experiment, renew channels
#   shoots-renew    every 12 h    POST /tasks/renew-channels  Drive push channels cap at one day
#
# Each job carries an OIDC token for the service account and the shared
# X-Tasks-Token header the endpoints check (from Secret Manager, read here once).
set -euo pipefail

PROJECT="${GCP_PROJECT:?set GCP_PROJECT to your Google Cloud project id}"
REGION="${GCP_LOCATION:-asia-southeast2}"
SERVICE="${SERVICE:-shoots}"
SA="${SERVICE_ACCOUNT:-shoots-ingest@${PROJECT}.iam.gserviceaccount.com}"
TZ_NAME="${SCHEDULE_TZ:-Asia/Jakarta}"

NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
URL="${SERVICE_URL:-https://${SERVICE}-${NUMBER}.${REGION}.run.app}"
TOKEN="$(gcloud secrets versions access latest --secret shoots-tasks-token --project "$PROJECT")"

ensure_job() {
  local name="$1" schedule="$2" path="$3"
  local verb=create
  gcloud scheduler jobs describe "$name" --location "$REGION" --project "$PROJECT" >/dev/null 2>&1 && verb=update
  gcloud scheduler jobs "$verb" http "$name" \
    --project "$PROJECT" --location "$REGION" \
    --schedule "$schedule" --time-zone "$TZ_NAME" \
    --uri "${URL}${path}" --http-method POST \
    --headers "X-Tasks-Token=${TOKEN}" \
    --oidc-service-account-email "$SA" --oidc-token-audience "$URL" \
    --attempt-deadline 540s >/dev/null
  echo "$verb $name ($schedule) -> $path"
}

ensure_job shoots-tick  "*/5 * * * *" /tasks/tick
ensure_job shoots-daily "0 6 * * *"   /tasks/daily
ensure_job shoots-renew "0 */12 * * *" /tasks/renew-channels
