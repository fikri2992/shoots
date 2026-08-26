#!/usr/bin/env bash
# Build on Cloud Build, deploy to Cloud Run. Idempotent; re-run to ship a new image.
#
#   ./infra/deploy.sh                      build + deploy
#   SKIP_BUILD=1 ./infra/deploy.sh         redeploy the last image (env/secret changes only)
#
# Needs: infra/enable-apis.sh and infra/state.sh run once; backend/.env with
# GOOGLE_CLIENT_ID, VAPID_PUBLIC_KEY, VAPID_SUBJECT and the release certificate
# fingerprint (non-secret values copied into the service env); the secrets are
# mounted from Secret Manager.
set -euo pipefail

PROJECT="${GCP_PROJECT:?set GCP_PROJECT to your Google Cloud project id}"
REGION="${GCP_LOCATION:-asia-southeast2}"
SERVICE="${SERVICE:-shoots}"
SA="${SERVICE_ACCOUNT:-shoots-ingest@${PROJECT}.iam.gserviceaccount.com}"
BUCKET="${GCS_BUCKET:-${PROJECT}-shoots}"
REPO="shoots"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/app"
ENV_FILE="${ENV_FILE:-backend/.env}"

value_of() {
  grep -E "^$1=" "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '\r"' || true
}

GCP_PROJECT="$PROJECT" GCP_LOCATION="$REGION" SERVICE="$SERVICE" \
  SERVICE_ACCOUNT="$SA" GCS_BUCKET="$BUCKET" ENV_FILE="$ENV_FILE" \
  bash infra/preflight.sh

if ! gcloud artifacts repositories describe "$REPO" --location "$REGION" --project "$PROJECT" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPO" --repository-format docker \
    --location "$REGION" --project "$PROJECT" --description "Shoots images"
fi

if [ -z "${SKIP_BUILD:-}" ]; then
  gcloud builds submit . --tag "$IMAGE" --project "$PROJECT" --region "$REGION"
fi

# Cloud Run's deterministic URL, known before the first deploy, so the OAuth
# redirect, Pub/Sub push and Drive webhook settings are right on the first try.
NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
URL="${SERVICE_URL:-https://${SERVICE}-${NUMBER}.${REGION}.run.app}"

gcloud run deploy "$SERVICE" \
  --project "$PROJECT" --region "$REGION" \
  --image "$IMAGE" \
  --service-account "$SA" \
  --allow-unauthenticated \
  --min-instances 0 --max-instances 3 --concurrency 40 \
  --cpu 2 --memory 2Gi --timeout 600 \
  --set-env-vars "^|^USE_VERTEX_AI=true|GCP_PROJECT=${PROJECT}|GCP_LOCATION=${REGION}|CLOUD_STATE=true|GCS_BUCKET=${BUCKET}|PUBSUB_PUSH_BASE_URL=${URL}|PUBSUB_PUSH_AUDIENCE=${URL}|DRIVE_WEBHOOK_URL=${URL}/drive/notify|OAUTH_REDIRECT_URI=${URL}/auth/callback|FRONTEND_ORIGIN=${URL}|GOOGLE_CLIENT_ID=$(value_of GOOGLE_CLIENT_ID)|VAPID_PUBLIC_KEY=$(value_of VAPID_PUBLIC_KEY)|VAPID_SUBJECT=$(value_of VAPID_SUBJECT)|ANDROID_APP_LINK_SHA256=$(value_of ANDROID_APP_LINK_SHA256)|DRIVE_SERVICE_ACCOUNT=${SA}" \
  --set-secrets "GOOGLE_CLIENT_SECRET=shoots-google-client-secret:latest,SESSION_SECRET=shoots-session-secret:latest,TASKS_TOKEN=shoots-tasks-token:latest,VAPID_PRIVATE_KEY=shoots-vapid-private-key:latest"

# Pub/Sub push and Scheduler authenticate as the service account.
gcloud run services add-iam-policy-binding "$SERVICE" --project "$PROJECT" --region "$REGION" \
  --member "serviceAccount:$SA" --role roles/run.invoker --quiet >/dev/null

echo
ACTUAL_URL="$(gcloud run services describe "$SERVICE" --project "$PROJECT" \
  --region "$REGION" --format='value(status.url)')"
if [ "$ACTUAL_URL" != "$URL" ]; then
  echo "Cloud Run reported $ACTUAL_URL; predicted $URL" >&2
  echo "Set SERVICE_URL explicitly and reconcile OAuth, Pub/Sub and Scheduler before use." >&2
  exit 1
fi

echo "deployed: $ACTUAL_URL"
echo "OAuth: add ${URL}/auth/callback to the OAuth client's redirect URIs."
echo "Next: PUBSUB_PUSH_BASE_URL=$URL PUBSUB_PUSH_SA=$SA ./infra/topics.sh && ./infra/scheduler.sh"
