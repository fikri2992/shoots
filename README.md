# Shoots

Photography apps judge single shots. Shoots remembers all of yours and shows how your eye is changing.

You shoot. It reads every photo — from your Google Drive folder or from its own camera — measures about forty things about each one, and keeps the record no photographer can keep about themselves: what you tend to shoot, what has become reliable, what you never try, and whether any of that has moved since last month. From that it writes you a challenge, cites the counts that earned it, judges what you bring back, and afterwards checks whether its own advice changed anything.

It is built for the hobbyist rather than the professional, so it describes before it corrects, and it says plainly what it cannot see. Quality is an opinion; behaviour is measurable — every number it shows can be re-derived from the file it came from.

Entry for the All Things Agentic Hackathon, Taskmaster track.

**The web** is three screens: **Now** (the one thing to do), **Frames** (everything it has read), **Journey** (the agent's current conclusion about you, the Tendency Profile behind it, and what the agents did). Reviews are written back into Drive, so the app is optional for reading one.

**The camera** (`android/`, Kotlin + CameraX) is the fast half: zebras over blown highlights and a level readout computed on the device at frame rate with no model involved, the open challenge pinned in the viewfinder, and the panel's verdict back in your hand about half a minute after the shutter. Pair it once with a code from the web.

- Docs: [product](docs/product.md) · [domain model](docs/domain-model.md) · [agents](docs/agents.md) · [build plan](docs/build-plan.md) · [codebase rules](AGENTS.md)
- Stack: Vue 3 (Options API) + Vite + Tailwind PWA · Kotlin + CameraX + Compose (native camera, `android/`) · FastAPI + Google ADK · Firestore + GCS + Pub/Sub + Cloud Scheduler + Secret Manager + Cloud Run
- Models: `gemini-3.7-flash` (Analyst panel of three lenses + synthesizer on ADK workflow agents, Scout, Judge, Director storyboard, Listener) · `veo-3.1-fast` (Director: the reference clip under every quest) · `gemini-live-2.5-flash-native-audio` (Coach: voice review of a shot from the phone)

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

The suite uses real files, real ffmpeg and real stores, never a mocked model. The agents themselves are checked against the live models with `backend/scripts/check_*.py` (`check_ingest`, `check_analyst`, `check_scout`, `check_director`, `check_coach`, `check_live_ws`); each prints what the model did and leaves its output in `backend/.blobs` for the dashboard.

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
