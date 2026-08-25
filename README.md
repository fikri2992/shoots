# Shoots

Learn to see like yourself.

Shoots learns from every Shot, offers one personal Experiment, and tracks what changes.

It is built for the self-directed hobbyist who has enough Shots for patterns to exist but no mentor who remembers the whole archive. Shoots measures each Shot, updates a Tendency Profile and Technique Map, and offers one optional Experiment when a cited Direction exists. Explore records Variations without pass or fail. Reproduce uses fixed Criteria and a Verdict. Compare preserves alternatives and an optional photographer preference. Every type may later record comparable Change. Quality is an opinion. Behaviour is measurable.

A model may interpret a Shot. Only the photographer supplies Intent, Keeper preference, and the signal that a Change was an improvement. Unmarked Shots remain unknown rather than disliked.

Entry for the All Things Agentic Hackathon, Taskmaster track.

**The web** is three screens: **Now** for the offered or selected Experiment, **Shots** for the archive, and **Journey** for the evidence-backed longitudinal record. Drive is an optional import and export adapter.

**The Phone Source** (`android/`, Kotlin + Compose + WorkManager) keeps Android's normal camera in control. After one honest media permission, it watches only the Camera album, uploads unseen original Shots directly and idempotently, optionally associates them with the selected Experiment, survives UI exit, and shows import/retry state. Selected-media access stays manual. Pairing is the four-day authentication cut; native Google sign-in is later.

- Docs: [product](docs/product.md) · [decisions](docs/product-decisions.md) · [feature list](docs/feature-list.md) · [domain model](docs/domain-model.md) · [agents](docs/agents.md) · [build plan](docs/build-plan.md) · [codebase rules](AGENTS.md)
- Stack: Vue 3 (Options API) + Vite + Tailwind PWA · Kotlin + Compose + WorkManager (`android/`) · FastAPI + Google ADK · Firestore + GCS + Pub/Sub + Cloud Scheduler + Secret Manager + Cloud Run
- Models: `gemini-3.7-flash` (Analyst panel, Scout, Judge feedback, Journey writer, Listener) · `gemini-live-2.5-flash-native-audio` (Coach). The retained Director/Veo prototype is optional legacy code, outside the product loop.

## Prerequisites

- Python ≥ 3.12 and [uv](https://docs.astral.sh/uv/)
- Node ≥ 20
- ffmpeg and ffprobe on PATH
- A Google Cloud project with Vertex AI enabled, or an AI Studio key for local work

## Setup

```bash
cp backend/.env.example backend/.env
```

Fill in `backend/.env` (see the comments in the file). Then:

```bash
cd backend && uv sync
```

```bash
cd frontend && npm install
```

## Run

```bat
start_dev.bat
```

Backend on http://localhost:8000, frontend on http://localhost:5173 (Vite proxies `/api`, `/auth`, `/drive`).

## Verify

```bash
cd backend && uv run pytest
```

The suite uses real files, real ffmpeg, real stores, and integration contracts for retry and concurrency. Agent quality is not inferred from mocked Gemini calls; the live-model gates are `backend/scripts/check_*.py` (`check_ingest`, `check_analyst`, `check_scout`, `check_director`, `check_coach`, `check_live_ws`).

## Deploy

One Cloud Run service in `asia-southeast2`, running as the `shoots-ingest` service account, with Firestore, a GCS bucket, Secret Manager, Pub/Sub push subscriptions (one per stage, each with a dead-letter topic) and three Cloud Scheduler jobs. The image is built on Cloud Build; no local Docker needed.

```bash
./infra/enable-apis.sh
```

```bash
ENV_FILE=backend/.env ./infra/state.sh
```

```bash
./infra/deploy.sh
```

```bash
PUBSUB_PUSH_BASE_URL=https://shoots-<project-number>.asia-southeast2.run.app PUBSUB_PUSH_SA=shoots-ingest@<project>.iam.gserviceaccount.com ./infra/topics.sh
```

```bash
./infra/scheduler.sh
```

Then add `<service url>/auth/callback` to the OAuth client's redirect URIs. `deploy.sh` prints the URL; it is deterministic from the project number, so the env vars that need it are right on the first deploy.
