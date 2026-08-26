#!/usr/bin/env bash
# Read-only deployment preflight. It prints names and states, never credential values.
set -euo pipefail

PROJECT="${GCP_PROJECT:?set GCP_PROJECT to your Google Cloud project id}"
REGION="${GCP_LOCATION:-asia-southeast2}"
SERVICE="${SERVICE:-shoots}"
SA="${SERVICE_ACCOUNT:-shoots-ingest@${PROJECT}.iam.gserviceaccount.com}"
BUCKET="${GCS_BUCKET:-${PROJECT}-shoots}"
ENV_FILE="${ENV_FILE:-backend/.env}"

failures=0
fail() {
  echo "FAIL: $*" >&2
  failures=$((failures + 1))
}
pass() { echo "pass: $*"; }

for command in gcloud git grep; do
  command -v "$command" >/dev/null 2>&1 || fail "$command is unavailable"
done
[ "$failures" -eq 0 ] || exit 1

if ! head="$(git rev-parse --short HEAD 2>/dev/null)"; then
  fail "current directory is not a readable git checkout"
elif ! status="$(git status --porcelain 2>/dev/null)"; then
  fail "git status could not read the checkout"
elif [ -n "$status" ]; then
  fail "git checkout is dirty"
else
  pass "clean git checkout at $head"
fi

if [ ! -f "$ENV_FILE" ]; then
  fail "$ENV_FILE does not exist"
else
  pass "$ENV_FILE exists"
fi

value_of() {
  grep -E "^$1=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r"' || true
}

if [ -f "$ENV_FILE" ]; then
  for key in GOOGLE_CLIENT_ID VAPID_PUBLIC_KEY VAPID_SUBJECT ANDROID_APP_LINK_SHA256; do
    value="$(value_of "$key")"
    [ -n "$value" ] || fail "$key is empty in $ENV_FILE"
  done
  client_id="$(value_of GOOGLE_CLIENT_ID)"
  [[ "$client_id" == *.apps.googleusercontent.com ]] \
    || fail "GOOGLE_CLIENT_ID is not a Google web client id"
  vapid_subject="$(value_of VAPID_SUBJECT)"
  [[ "$vapid_subject" == mailto:* || "$vapid_subject" == https://* ]] \
    || fail "VAPID_SUBJECT must start with mailto: or https://"
  [[ "$vapid_subject" != *your-contact@example.com* ]] \
    || fail "VAPID_SUBJECT still contains the example contact"
  fingerprints="$(value_of ANDROID_APP_LINK_SHA256)"
  fingerprint_pattern='^([0-9A-Fa-f]{2}:){31}[0-9A-Fa-f]{2}(,([0-9A-Fa-f]{2}:){31}[0-9A-Fa-f]{2})*$'
  [[ "$fingerprints" =~ $fingerprint_pattern ]] \
    || fail "ANDROID_APP_LINK_SHA256 is not a comma-separated SHA-256 fingerprint list"
fi

active_account="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -1)"
if [ -z "$active_account" ]; then
  fail "gcloud has no active account"
else
  pass "gcloud has an active account"
fi

if gcloud projects describe "$PROJECT" >/dev/null 2>&1; then
  pass "project $PROJECT is readable"
  project_number="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
  url="https://${SERVICE}-${project_number}.${REGION}.run.app"
  echo "candidate service URL: $url"
else
  fail "project $PROJECT is not readable"
fi

required_apis=(
  aiplatform.googleapis.com
  run.googleapis.com
  cloudbuild.googleapis.com
  artifactregistry.googleapis.com
  firestore.googleapis.com
  storage.googleapis.com
  pubsub.googleapis.com
  cloudscheduler.googleapis.com
  secretmanager.googleapis.com
  fcm.googleapis.com
  drive.googleapis.com
)
for api in "${required_apis[@]}"; do
  if gcloud services list --enabled --project "$PROJECT" \
    --filter="config.name:$api" --format='value(config.name)' | grep -Fxq "$api"; then
    pass "API $api"
  else
    fail "API $api is not enabled"
  fi
done

gcloud iam service-accounts describe "$SA" --project "$PROJECT" >/dev/null 2>&1 \
  && pass "service account $SA" \
  || fail "service account $SA is missing"
gcloud firestore databases describe --database='(default)' --project "$PROJECT" \
  >/dev/null 2>&1 \
  && pass "Firestore default database" \
  || fail "Firestore default database is missing"
gcloud storage buckets describe "gs://$BUCKET" >/dev/null 2>&1 \
  && pass "bucket gs://$BUCKET" \
  || fail "bucket gs://$BUCKET is missing"

for secret in \
  shoots-google-client-secret \
  shoots-session-secret \
  shoots-tasks-token \
  shoots-vapid-private-key; do
  if gcloud secrets versions list "$secret" --project "$PROJECT" \
    --filter='state:ENABLED' --limit=1 --format='value(name)' | grep -q .; then
    pass "secret $secret has an enabled version"
  else
    fail "secret $secret has no enabled version"
  fi
done

if [ "$failures" -gt 0 ]; then
  echo "$failures deployment preflight failure(s)" >&2
  exit 1
fi

echo "deployment preflight passed"
