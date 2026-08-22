# Shoots

An autonomous photography coach. You shoot. It watches your Google Drive folder, reads every photo and video, maps what techniques you have actually used, finds the gap, researches the next technique, issues a daily quest with machine-checkable criteria and a generated reference clip, and judges what you shoot for it.

Entry for the All Things Agentic Hackathon, Taskmaster track.

- Docs: [domain model](docs/domain-model.md) · [build plan](docs/build-plan.md) · [codebase rules](AGENTS.md)
- Stack: Vue 3 (Options API) + Vite + Tailwind PWA · FastAPI + Google ADK · Firestore + GCS + Pub/Sub + Cloud Scheduler + Secret Manager + Cloud Run
- Models: `gemini-3.7-flash` (Analyst, Scout, Judge) · `veo-3.1-fast` (quest reference clips) · `lyria-3-clip` (optional) · `gemini-live-2.5-flash-native-audio` (voice review, stretch)

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

## Deploy

See `infra/`. Architecture diagram and Cloud Run proof: TODO (day 7).
