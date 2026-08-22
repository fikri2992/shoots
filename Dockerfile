# Single image: the Vue app is built and served by the FastAPI service, so the
# deployment is one Cloud Run service on one origin. No CORS, no second URL, and
# the session cookie works without any cross-site configuration.

# --- build the frontend ---------------------------------------------------
FROM node:22-slim AS frontend

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- runtime --------------------------------------------------------------
FROM python:3.12-slim

# ffmpeg: contact sheets and ffprobe for video shots. The old Visual QA image
# forgot this and video only ever worked on dev machines.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies first, so application edits do not invalidate the layer.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/app ./app
COPY backend/scripts ./scripts
RUN uv sync --frozen --no-dev

COPY --from=frontend /build/dist ./static

# Cloud Run supplies PORT and terminates TLS. One worker: the pipeline is
# IO-bound on model calls and the SSE event bus is per-process, so extra workers
# would split subscribers across processes that cannot see each other's events.
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "uv run uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
