# Shoots

Learn to see like yourself.

Shoots learns from every Shot, closes each Shoot into a learning record, offers one personal Experiment, and tracks what changes.

It is built for the self-directed phone photographer who knows some Techniques but cannot tell whether their decisions are becoming deliberate or they are just getting lucky. Shoots intercepts ordinary Camera media, analyses each Shot, and is being extended to group Scenes into one natural Shoot, record what repeated or varied, update longitudinal memory, and choose one justified explanation, question, Experiment, or silence. It does not score artistic quality.

A model may interpret a Shot. Only the photographer supplies Intent, Keeper preference, and the signal that a Change was an improvement. Unmarked Shots remain unknown rather than disliked.

Entry for the All Things Agentic Hackathon, Taskmaster track.

**The web** remains the detailed audit desk. **Android** is the daily client: Now, Shots, Experiments, Journey, and Settings. Drive is an optional import and export adapter.

**The Phone Source** (`android/`, Kotlin + Compose + WorkManager) keeps Android's normal camera in control. After one honest media permission, it watches only approved Camera media, streams unseen originals directly and idempotently, freezes explicit Capture Session membership, survives UI exit, and shows import/retry state. Selected-media access stays manual. Native Google identity and revocable device sessions are implemented; configured OAuth/FCM and full physical-device acceptance remain incomplete. Pairing endpoints remain only for older APKs.

The current implementation has per-Shot Runs, Reproduce Capture Sessions, Technique Map, Tendency Profile, Change, Journey, persisted Scene/Shoot grouping, revisioned terminal Shoot Records, a deterministic evidence-labelled Shoot receipt, and stored Scout routes for explain, Keeper-backed Reproduce, or evidenced silence. Client delivery of the receipt, Ask, corrected Explore, Mine/Inspiration authority, and Deconstruction remain incomplete.

- Docs: [product](docs/product.md) · [decisions](docs/product-decisions.md) · [feature list](docs/feature-list.md) · [implementation order](docs/implementation-order.md) · [learning path](docs/learning-path.md) · [domain model](docs/domain-model.md) · [agents](docs/agents.md) · [memory contract](docs/final-memory.md) · [Deconstruction](docs/deconstruction.md) · [build diary](docs/build-plan.md) · [codebase rules](AGENTS.md)
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
