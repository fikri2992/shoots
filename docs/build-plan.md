# Build plan

Hackathon: All Things Agentic Hackathon, Taskmaster track. Deadline 2026-08-31 17:00 PDT. Solo. Started 2026-08-22.

Judging: 40% autonomous high-value action with minimal hand-holding, 30% architecture (decoupling, state, credentials, failure handling), 30% demo and reproducibility with visible proof of Google Cloud.

Required: Gemini 3.5+ (gemini-3.7-flash), a Google agent framework (ADK), a GCP service (Cloud Run, Firestore, Pub/Sub, Scheduler, GCS, Secret Manager). Bonus: Veo, Lyria. Separate prizes: Best Multimodal UX (Gemini Live stretch), Individual/Hobbyist.

GCP project: `your-gcp-project`, region asia-southeast2.

## Reused from visual-qa-agent

grid.py, canvas.py, grid_overlay.py, contact_sheet.py, video.py, runtime.py, retry.py, store.py, storage.py, events.py, auth.py, config shape, Dockerfile, frontend shell (App, style tokens, router, auth store, api.js, LoginPage), ReviewCanvas.vue as the base for ShotCanvas.

## Days

| Day | Date | Deliver | Done |
|---|---|---|---|
| 1 | Aug 22 | Repo scaffold from Visual QA base, domain (entities, taxonomy), docs, GCP APIs enabled, Pub/Sub topics, OAuth client `shoots-local`, service account `shoots-ingest` | x |
| 2 | Aug 23 | Connect: create + share folder with the service account. Ingest: changes.list sync, webhook, download, EXIF, ffprobe, contact sheet, gridded frame, blobs. `media.new` → `media.ingested` | |
| 3 | Aug 24 | Analyst agent: prompt, structured output, unknown-id filter. Overlay renderer for moves. ShotCanvas in Vue | |
| 4 | Aug 25 | Cartographer (pure) + Scout: gap ranking, Search grounding, quest with criteria, Web Push delivery | |
| 5 | Aug 26 | Judge (pure checks + feedback), Scheduler jobs, backfill job. Loop closed end to end locally | |
| 6 | Aug 27 | Dashboard: skill graph, shot timeline with overlays, quest card, activity feed. Phone-first. PWA manifest + Shoot button | |
| 7 | Aug 28 | Deploy to Cloud Run, Pub/Sub push + DLQ, Secret Manager, idempotency checks, Veo reference clips, OTel traces | |
| 8 | Aug 29 | Stretch: Gemini Live voice review, Lyria for video quests. Load demo data. Architecture diagram | |
| 9 | Aug 30 | README with reproducible setup, demo video (~4 min, unedited), blog post + #AllThingsAgenticHackathon, submit | |
| buffer | Aug 31 | | |

Cut order if behind: Lyria, Gemini Live, Capacitor APK, OTel, Veo, dashboard polish. Never cut: the loop, Pub/Sub + DLQ, README, demo.

## Demo script

1. Dashboard on laptop: skill graph built from ~40 backfilled shots, today's quest open ("Panning: shutter 1/15-1/60, subject sharp, background streaked").
2. Phone: open Shoots PWA, tap Shoot, take the photo. It uploads to Drive.
3. Laptop: activity feed ticks Ingest → Analyst → Judge. Cloud Run logs visible in a second tab.
4. Quest flips to passed with the Judge's feedback. Skill node moves to attempted. Scout issues tomorrow's quest with a Veo clip.
5. Show the DLQ: replay a poisoned message, show idempotency.

## Demo data

- Phone shots taken daily from Aug 22. Phones keep shutter/aperture/ISO/focal in EXIF.
- Flickr Creative Commons originals (EXIF intact) to backfill ~40 shots across families.
- Never stock sites: they strip EXIF.

## Demo data status (2026-08-22)

- `data/demo/commons/`: 26 CC-licensed originals from Wikimedia Commons with real EXIF, 11 techniques (panning, long exposure, light trails, silhouette, golden hour, shallow DOF, leading lines, reflections, macro, freeze action, astro). Sidecar `.json` per file holds licence, artist and source page. Fetched by `backend/scripts/fetch_commons_demo.py`. Telephoto compression returned nothing with EXIF; re-query later.
- `data/demo/mine/`: the user's own phone shots pulled from Google Photos (originals keep EXIF). Most of the recent library is screenshots; real camera shots exist from Jul 21, Jul 26, Aug 5, Aug 6 plus a few videos.
- Ingest edge case: manual lenses report `FNumber=0` and `FocalLength=0` (seen on `shallow_dof_1.jpg`). Treat 0 as unknown, never as f/0.
