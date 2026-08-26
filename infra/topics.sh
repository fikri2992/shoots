#!/usr/bin/env bash
# Pub/Sub topics, dead-letter topics and push subscriptions for the pipeline.
# Idempotent: existing resources are left alone.
#
#   media.new       → ingest      → media.ingested
#   media.ingested  → analyst     → media.analyzed
#   media.analyzed  → cartographer (fan-out)
#   media.analyzed  → judge        (fan-out) → media.judged, experiment.closed
#   media.judged    → scribe       (review written back to Drive)
#   experiment.closed    → scout
#   keeper.changed       → scout-signal
#   account.delete       → account-delete
#
# Every stage subscription owns one dead-letter topic and one pull subscription,
# so a bad file cannot poison the queue and a fan-out stage cannot mix another
# stage's failures into its replay stream.
set -euo pipefail

PROJECT="${GCP_PROJECT:?set GCP_PROJECT to your Google Cloud project id}"
PUSH_BASE="${PUBSUB_PUSH_BASE_URL:?set PUBSUB_PUSH_BASE_URL to the Cloud Run service URL}"
SA="${PUBSUB_PUSH_SA:?set PUBSUB_PUSH_SA to the service account email used for push auth}"
MAX_ATTEMPTS=5
ACK_DEADLINE=540  # seconds; the Analyst on a 12-frame contact sheet can take a while
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
PUBSUB_AGENT="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"

TOPICS=(shoots.media.new shoots.media.ingested shoots.media.analyzed shoots.media.judged shoots.experiment.closed shoots.keeper.changed shoots.account.delete)

ensure_topic() {
  gcloud pubsub topics describe "$1" --project "$PROJECT" >/dev/null 2>&1 \
    || gcloud pubsub topics create "$1" --project "$PROJECT"
}

# name topic endpoint
ensure_push_sub() {
  local name="$1" topic="$2" path="$3"
  local dlq_topic="${name}.dlq"
  local dlq_subscription="${name}-dead-letter"
  ensure_topic "$dlq_topic"

  if gcloud pubsub subscriptions describe "$name" --project "$PROJECT" >/dev/null 2>&1; then
    local current_topic
    current_topic="$(gcloud pubsub subscriptions describe "$name" \
      --project "$PROJECT" --format='value(topic)')"
    if [[ "$current_topic" != */topics/"$topic" ]]; then
      echo "$name already reads $current_topic; expected $topic" >&2
      exit 1
    fi
    gcloud pubsub subscriptions update "$name" \
      --project "$PROJECT" \
      --push-endpoint "$PUSH_BASE/pubsub/$path" \
      --push-auth-service-account "$SA" \
      --push-auth-token-audience "$PUSH_BASE" \
      --ack-deadline "$ACK_DEADLINE" \
      --dead-letter-topic "$dlq_topic" \
      --max-delivery-attempts "$MAX_ATTEMPTS" \
      --min-retry-delay 10s \
      --max-retry-delay 300s >/dev/null
  else
    gcloud pubsub subscriptions create "$name" \
      --project "$PROJECT" \
      --topic "$topic" \
      --push-endpoint "$PUSH_BASE/pubsub/$path" \
      --push-auth-service-account "$SA" \
      --push-auth-token-audience "$PUSH_BASE" \
      --ack-deadline "$ACK_DEADLINE" \
      --dead-letter-topic "$dlq_topic" \
      --max-delivery-attempts "$MAX_ATTEMPTS" \
      --min-retry-delay 10s \
      --max-retry-delay 300s
  fi

  gcloud pubsub topics add-iam-policy-binding "$dlq_topic" \
    --project "$PROJECT" \
    --member "serviceAccount:$PUBSUB_AGENT" \
    --role roles/pubsub.publisher --quiet >/dev/null
  gcloud pubsub subscriptions add-iam-policy-binding "$name" \
    --project "$PROJECT" \
    --member "serviceAccount:$PUBSUB_AGENT" \
    --role roles/pubsub.subscriber --quiet >/dev/null

  gcloud pubsub subscriptions describe "$dlq_subscription" \
    --project "$PROJECT" >/dev/null 2>&1 \
    || gcloud pubsub subscriptions create "$dlq_subscription" \
      --project "$PROJECT" --topic "$dlq_topic" >/dev/null
}

for t in "${TOPICS[@]}"; do
  ensure_topic "$t"
done

ensure_push_sub shoots-ingest        shoots.media.new       ingest
ensure_push_sub shoots-analyst       shoots.media.ingested  analyst
ensure_push_sub shoots-cartographer  shoots.media.analyzed  cartographer
ensure_push_sub shoots-judge         shoots.media.analyzed  judge
ensure_push_sub shoots-scribe        shoots.media.judged    scribe
ensure_push_sub shoots-scout         shoots.experiment.closed    scout
ensure_push_sub shoots-scout-signal  shoots.keeper.changed       scout-signal
ensure_push_sub shoots-account-delete shoots.account.delete      account-delete

echo "topics and subscriptions ready on $PROJECT"
