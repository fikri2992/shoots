# Shoots

An autonomous photography coach. You shoot. It watches your Google Drive folder, reads every photo and video, maps what techniques you have actually used, finds the gap, researches the next technique, issues a daily quest with machine-checkable criteria and a generated reference clip, and judges what you shoot for it.

Entry for the All Things Agentic Hackathon, Taskmaster track.

- Docs: [domain model](docs/domain-model.md) · [build plan](docs/build-plan.md) · [codebase rules](AGENTS.md)
- Stack: Vue 3 (Options API) + Vite + Tailwind PWA · FastAPI + Google ADK · Firestore + GCS + Pub/Sub + Cloud Scheduler + Secret Manager + Cloud Run
- Models: `gemini-3.7-flash` (Analyst, Scout, Judge, Director storyboard) · `veo-3.1-fast` + `lyria-3-clip` (Director: the reference clip under every quest) · `gemini-live-2.5-flash-native-audio` (Coach: voice review of a shot from the phone)

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

See `infra/`. Architecture diagram and Cloud Run proof: TODO (day 7).
