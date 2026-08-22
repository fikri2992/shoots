#!/usr/bin/env bash
# Enable every API Shoots uses. Idempotent. Run once per project.
set -euo pipefail

PROJECT="${GCP_PROJECT:-your-gcp-project}"

gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com \
  pubsub.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  drive.googleapis.com \
  gmail.googleapis.com \
  cloudtrace.googleapis.com \
  --project "$PROJECT"

echo "APIs enabled on $PROJECT"
