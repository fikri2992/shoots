

## Day 2 notes (2026-08-22)

- Real-Google check passed: OAuth (`drive.file`, offline) → `/drive/connect` created folder `your-drive-folder-id` and shared it with `shoots-ingest@…` → uploads as the user → reader (service account impersonated via ADC) listed + downloaded → 4 shots ingested incl. a 27 MB 120 fps video.
- The consent screen is branded "Visual QA Agent" (shared Google Auth Platform branding on the project). Left alone; changing it would rebrand Visual QA. Judges watch a video, they do not sign in.
- authlib: `access_type`/`prompt` belong in `authorize_params`, not `client_kwargs`, or no refresh token comes back.
- uvicorn `--reload` did not restart on edits here; run without it and restart by hand.
- Sync is a plain folder listing keyed by Drive file id. `changes.list` with a page token is a day-7 optimisation if listing cost shows up; with one folder per user it will not.

## Day 3 notes (2026-08-22)

- Real chain timing: `/drive/sync` → 4 shots ingested (incl. 27 MB video) → 4 analysed in 35 s wall clock, in-process bus, Vertex global endpoint.
- Analyst quality on first run: `light_trails` 0.98 justified by the 10 s shutter; `slow_motion` 0.95 from 120 fps; declined to tag `panning` on a first-person bike shot (correct). Scores 3-7, critiques specific to the frame. Cells always valid after `validate()`.
- Composition read renders well: crop dim, horizon, subject box, move arrows (`imaging/overlay.py`).
- Local dev: `FileStore` (JSON) keeps users/shots across restarts. Stop the server via the task that started it; `taskkill` on the PID does not reach it.
