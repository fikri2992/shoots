#!/usr/bin/env bash
# One-time state and identity for the Cloud Run service. Idempotent.
#
#   Firestore (native, asia-southeast2)   -> users, shots, analyses, skills, quests, events, push
#   GCS bucket                            -> originals, gridded frames, sheets, clips
#   Secret Manager                        -> one secret per user for the Drive refresh token,
#                                            plus the app secrets deploy.sh mounts as env vars
#   shoots-ingest service account         -> the service identity; reads shared Drive folders
set -euo pipefail

PROJECT="${GCP_PROJECT:-your-gcp-project}"
REGION="${GCP_LOCATION:-asia-southeast2}"
SA="${SERVICE_ACCOUNT:-shoots-ingest@${PROJECT}.iam.gserviceaccount.com}"
BUCKET="${GCS_BUCKET:-${PROJECT}-shoots}"

if ! gcloud iam service-accounts describe "$SA" --project "$PROJECT" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${SA%%@*}" --project "$PROJECT" \
    --display-name "Shoots service identity (reads shared Drive folders, runs the pipeline)"
fi

# Firestore: one native database per project; creating it twice is an error, so check first.
if ! gcloud firestore databases describe --database="(default)" --project "$PROJECT" >/dev/null 2>&1; then
  gcloud firestore databases create --location="$REGION" --type=firestore-native --project "$PROJECT"
fi

if ! gcloud storage buckets describe "gs://$BUCKET" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://$BUCKET" --project "$PROJECT" --location "$REGION" \
    --uniform-bucket-level-access --public-access-prevention
fi

# What the service identity may do. Secret Manager admin because the token store
# creates one secret per user at sign-in; scope it down after the hackathon.
for role in \
  roles/datastore.user \
  roles/secretmanager.admin \
  roles/pubsub.publisher \
  roles/aiplatform.user \
  roles/logging.logWriter \
  roles/cloudtrace.agent; do
  gcloud projects add-iam-policy-binding "$PROJECT" \
    --member "serviceAccount:$SA" --role "$role" --condition=None --quiet >/dev/null
done
gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" \
  --member "serviceAccount:$SA" --role roles/storage.objectAdmin --quiet >/dev/null

# Pub/Sub push and Cloud Scheduler call the service with an OIDC token minted
# for this same account, so it must be allowed to invoke the service (deploy.sh
# binds run.invoker once the service exists) and to mint tokens.
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member "serviceAccount:service-$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')@gcp-sa-pubsub.iam.gserviceaccount.com" \
  --role roles/iam.serviceAccountTokenCreator --condition=None --quiet >/dev/null

# App secrets the service mounts as env vars. Values come from the local .env
# (never from the shell history): run with ENV_FILE=backend/.env.
ENV_FILE="${ENV_FILE:-}"
ensure_secret() {
  local name="$1" value="$2"
  [ -n "$value" ] || { echo "skip $name (empty)"; return; }
  if ! gcloud secrets describe "$name" --project "$PROJECT" >/dev/null 2>&1; then
    gcloud secrets create "$name" --project "$PROJECT" --replication-policy automatic >/dev/null
  fi
  printf '%s' "$value" | gcloud secrets versions add "$name" --project "$PROJECT" --data-file=- >/dev/null
  gcloud secrets add-iam-policy-binding "$name" --project "$PROJECT" \
    --member "serviceAccount:$SA" --role roles/secretmanager.secretAccessor --quiet >/dev/null
  echo "secret $name: new version"
}
if [ -n "$ENV_FILE" ]; then
  value_of() { grep -E "^$1=" "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '\r"'; }
  ensure_secret shoots-google-client-secret "$(value_of GOOGLE_CLIENT_SECRET)"
  ensure_secret shoots-session-secret "$(value_of SESSION_SECRET)"
  ensure_secret shoots-tasks-token "$(value_of TASKS_TOKEN)"
  ensure_secret shoots-vapid-private-key "$(value_of VAPID_PRIVATE_KEY)"
fi

echo "state ready: firestore (default) in $REGION, gs://$BUCKET, $SA"
