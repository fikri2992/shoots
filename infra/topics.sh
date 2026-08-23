#!/usr/bin/env bash
# Pub/Sub topics, dead-letter topics and push subscriptions for the pipeline.
# Idempotent: existing resources are left alone.
#
#   media.new       → ingest      → media.ingested
#   media.ingested  → analyst     → media.analyzed
#   media.analyzed  → cartographer (fan-out)
#   media.analyzed  → judge        (fan-out) → media.judged, quest.closed
#   media.judged    → scribe       (review written back to Drive)
#   quest.closed    → scout       → quest.issued
#   quest.issued    → director    (Veo + Lyria reference clip)
#
# Every subscription dead-letters after MAX_ATTEMPTS to <topic>.dlq so a bad
# file cannot poison the queue, and the DLQ is replayable for the demo.
set -euo pipefail

PROJECT="${GCP_PROJECT:?set GCP_PROJECT to your Google Cloud project id}"
PUSH_BASE="${PUBSUB_PUSH_BASE_URL:?set PUBSUB_PUSH_BASE_URL to the Cloud Run service URL}"
SA="${PUBSUB_PUSH_SA:?set PUBSUB_PUSH_SA to the service account email used for push auth}"
MAX_ATTEMPTS=5
ACK_DEADLINE=540  # seconds; the Analyst on a 12-frame contact sheet can take a while

TOPICS=(shoots.media.new shoots.media.ingested shoots.media.analyzed shoots.media.judged shoots.quest.closed shoots.quest.issued)

ensure_topic() {
  gcloud pubsub topics describe "$1" --project "$PROJECT" >/dev/null 2>&1 \
    || gcloud pubsub topics create "$1" --project "$PROJECT"
}

# name topic endpoint
ensure_push_sub() {
  local name="$1" topic="$2" path="$3"
  if gcloud pubsub subscriptions describe "$name" --project "$PROJECT" >/dev/null 2>&1; then
    return
  fi
  gcloud pubsub subscriptions create "$name" \
    --project "$PROJECT" \
    --topic "$topic" \
    --push-endpoint "$PUSH_BASE/pubsub/$path" \
    --push-auth-service-account "$SA" \
    --ack-deadline "$ACK_DEADLINE" \
    --dead-letter-topic "$topic.dlq" \
    --max-delivery-attempts "$MAX_ATTEMPTS" \
    --min-retry-delay 10s \
    --max-retry-delay 300s
}

for t in "${TOPICS[@]}"; do
  ensure_topic "$t"
  ensure_topic "$t.dlq"
done

ensure_push_sub shoots-ingest        shoots.media.new       ingest
ensure_push_sub shoots-analyst       shoots.media.ingested  analyst
ensure_push_sub shoots-cartographer  shoots.media.analyzed  cartographer
ensure_push_sub shoots-judge         shoots.media.analyzed  judge
ensure_push_sub shoots-scribe        shoots.media.judged    scribe
ensure_push_sub shoots-scout         shoots.quest.closed    scout
ensure_push_sub shoots-director      shoots.quest.issued    director

echo "topics and subscriptions ready on $PROJECT"
