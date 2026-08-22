



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



## Day 4 notes (2026-08-22)



- `/api/skills/rebuild` re-derived 11 techniques from the 4 stored analyses; then `/api/quests/issue` produced `golden_hour` ("Catch the golden hour glow", 6 steps, why-now referencing the user's own shots, 3 grounded references). ~25 s for research + write.

- Grounding chunk titles are bare domains (adobe.com, slrlounge.com) and URLs are `vertexaisearch.cloud.google.com/grounding-api-redirect/...` redirects. Acceptable; the dashboard shows the domain as the label.

- Scout research uses google-genai directly with the Search tool because ADK disables tools when `output_schema` is set; the write step is an ADK agent. Worth one sentence in the architecture doc.

- Day 5 next: Judge (pure EXIF checks + vision threshold, model feedback only), daily tick, backfill job.

## Day 5 notes (2026-08-23)

- Full autonomous loop verified: `POST /tasks/daily` → sync found the submission → ingest → Analyst (`golden_hour` 0.92) → Cartographer + Judge (passed; feedback named the fence and suggested f/2.8-4) → `quest.closed` → Scout issued `monochrome` ("Strip away all color"). 17:14:42 to 17:16:04, no human step.
- Decision 6 refined: a failed attempt keeps the quest open with a verdict; `QuestStatus.FAILED` removed.
- Docs had mixed cp1252/UTF-8 bytes from earlier Windows-default writes; normalised to UTF-8. Always pass `encoding="utf-8"` in patch scripts.
- Remaining for the Taskmaster story: Drive push channel + renewal (day 7), Pub/Sub + DLQ (day 7), PWA + Web Push (day 6), Veo clip per quest (day 7).

## Day 6 notes (2026-08-23)

- PWA served from `backend/static` (same as the Cloud Run image): quest card, skill map, shots grid, shot page with SVG overlay in cell units (`viewBox = cols rows`, no pixel math in the browser), activity feed, bottom tab bar with floating Shoot. Checked at 412 px and 1280 px in Chrome.
- Shoot button → `POST /drive/shoot` → user's Drive folder via their `drive.file` token → shot tagged with `quest_id` → pipeline starts without waiting for sync.
- Web Push: pywebpush + VAPID; `/api/push/key|subscribe|test`; Scout and Judge push. Verified to the browser permission prompt; delivery is checked on a device with the `/api/push/test` that runs on subscribe.
- Dashboard polls `/api/events` every 5 s while visible and refetches the rest when the newest event changes. SSE was available from Visual QA but polling is one less thing to break across Cloud Run instances.
- `FRONTEND_ORIGIN` is `http://localhost:8000` locally now: the backend serves the built app, so sign-in lands on the app.

## Day 7 notes (2026-08-23), features first, deploy after

- Veo 3.1 fast on Vertex us-central1: 4-6 s 9:16 720p clip in 32-60 s, bytes returned inline (no GCS hop). Lyria 3 clip preview is served from the `global` endpoint only and needs `response_modalities=["AUDIO","TEXT"]` (the us-central1 publisher entry 404s on every method); 30 s mp3 in 16 s. Gemini Live native audio: us-central1 only, first audio in ~6 s.
- Director stage: `quest.issued` -> storyboard (ADK, schema) -> Veo -> Lyria -> ffmpeg mux -> `quest.reference_clip`. Real run on the monochrome quest: 80 s, and the frame is exactly the brief (hard B&W, silhouette stepping through diagonal shadow). Quest card plays it inline, muted, tap for sound.
- Coach: WebSocket relay to Gemini Live, briefed with the gridded frame and the Analyst's read. Typed-question check through the real app wiring (`check_live_ws.py`): opening line names the strongest thing in the frame, answer references cells ("hitting the child's face in D2 and E2"), event recorded with the transcript. Mic path is the same socket plus PCM frames; checked on the phone after deploy.
- Pub/Sub push: handlers register by stage name, `/pubsub/<stage>` verifies the OIDC token (service-account email + audience) and delivers to that one handler. Drive push: `files.watch` per folder on Connect and from the daily tick, `/tasks/renew-channels` twice a day, `/drive/notify` checks token and channel id. Both can only be exercised with a public HTTPS URL; that is day 7b.
- FileStore caveat: two processes on one `store.json` lose writes to each other (a check script ran while the dev server was up and the server's next flush dropped the clip path). Stop the server before running a `check_*` script that writes, or accept a manual fix. Firestore has no such problem.
- Day 7b (deploy): Cloud Run asia-southeast2 with identity shoots-ingest, Firestore + GCS + Secret Manager via `cloud_state`/`gcs_bucket`, `infra/topics.sh` with the service URL, Scheduler jobs for `/tasks/daily`, `/tasks/sync`, `/tasks/renew-channels`, VAPID + OAuth redirect on the real origin, push delivery and the Coach on the phone.

## Day 7c notes (2026-08-23), the step back

- Re-centred on "redefining interaction": the agent lives in the user's Drive and notifications, the app is the audit trail. Four moves, all shipped and checked on the real stack:
  - **Scribe**: after the Judge, the review is written back into `Shoots/Reviewed/` as the user: overlay baked in, caption band with critique, moves and verdict, file named `✔/✘ <name> — <score> of 10.jpg`. Verified in Drive (two files).
  - **Timing**: techniques carry a light window (`taxonomy.LIGHT`), the user's location is the GPS of their newest frame (`Exif.latitude/longitude`, `User.last_*`), `domain/sun.py` + `domain/timing.py` pick `deliver_at` and a reason; the push waits for the five-minute tick (`/tasks/tick`). Location picked up from a Xiaomi phone frame on the first sync.
  - **Coach memory**: the Listener extracts `missing_gear` and notes from the transcript; Scout ranking and brief respect them; Coach is briefed with them. Real-model check: "only have my phone" → no tripod/telephoto/macro/flash.
  - **Today**: the home tab is the quest with why-now and why-then; verdicts link to "Ask the Coach why".
- Cut Lyria: Veo 3.1 generates its own ambient audio (`generate_audio=True`); the mux step and the music model are gone.
- Judge now publishes `media.judged` on every shot so the Scribe runs after it; stage order is deterministic, no fan-out race for the verdict.
- `scripts/call_as_user.py` calls the running dev server with a minted session cookie, for demos and checks that must not touch `store.json` while the server is up.
