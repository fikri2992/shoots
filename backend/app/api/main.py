import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.api import auth, deps, drive, live, pairing, pubsub, push, quests, shots, tasks
from app.config import settings

logger = logging.getLogger("app.api")

app = FastAPI(title="Shoots", version="0.1.0")

app.add_middleware(SessionMiddleware, secret_key=settings.session_secret, same_site="lax")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception) -> JSONResponse:
    """Say what actually broke instead of "Internal Server Error". The traceback
    goes to the log; the one-line summary crosses the wire."""
    logger.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": f"{type(exc).__name__}: {exc}".strip()[:2000]},
    )


app.include_router(auth.router)
app.include_router(drive.router)
app.include_router(shots.router)
app.include_router(pairing.router)
app.include_router(quests.router)
app.include_router(tasks.router)
app.include_router(push.router)
app.include_router(live.router)
app.include_router(pubsub.router)


def mount_frontend(application: FastAPI, dist: "Path | None" = None) -> bool:
    """Serve the built Vue app from this service when it was bundled into the image.

    One service, one origin: no CORS, the session cookie simply works. Unknown paths
    fall back to index.html so client routes survive a refresh; /api, /auth, /drive
    and /pubsub are left alone so a mistyped path 404s instead of returning HTML.
    """
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    dist = (dist or Path(__file__).resolve().parents[2] / "static").resolve()
    index = dist / "index.html"
    if not index.exists():
        return False

    if (dist / "assets").is_dir():
        application.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @application.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        if path.startswith(("api/", "auth/", "drive/", "pubsub/", "tasks/")):
            raise HTTPException(404, "not found")
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(dist):
            return FileResponse(candidate)
        return FileResponse(index)

    return True


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "models": {
            "flash": settings.model_flash,
            "video": settings.model_video,
            "live": settings.model_live,
        },
        "pipeline": "in-process" if settings.in_process_pipeline else "pubsub",
        "region": settings.gcp_location,
        "ports": deps.describe(),
    }


# Registered last: the SPA catch-all must not shadow the API routes above.
mount_frontend(app)
