# AGENTS.md — Codebase rules

Read `docs/domain-model.md` first. Its vocabulary (Photographer, Shot, Scene, Shoot, Shoot Record, Scene Probe, Live Scene Session, Evidence, Finding, Technique, Technique Map, Tendency, Keeper, Experiment, Variation, Experiment Record, Inspiration, Deconstruction, Criteria, Verdict, Change, Journey Update, Intent, Companion; the agents Ingest, Analyst, Cartographer, Scout, Judge, Scribe, Coach) is the ubiquitous language. Use these exact names in new code, APIs, prompts, and UI copy. Do not use "photo" for Shot, "skill" for Technique, "habit" for Tendency, "Quest" or "challenge" for Experiment, "Fault" for Finding, "passed" for a Verdict that only answers Criteria, or "Progress" for unqualified Change. The `skills` storage key and `TechniqueState` are the last migration targets, tracked in `docs/feature-list.md`, and are not precedent for new names.

## What this is

Shoots is an autonomous photography Companion for hobbyists. It learns from every Shot, offers one optional personal Experiment, and tracks what changes. Android and web are clients of one Photographer record. Android sends Shots directly; Google Drive is an optional import and export adapter. The current per-Shot Run and Reproduce path is built; the target Taskmaster work unit is one settled Shoot Record across a natural Camera period. Explore uses Variations and no Verdict. Reproduce alone uses Criteria and a Verdict. Compare preserves alternatives and an optional photographer preference. Hackathon entry for the Taskmaster track of the All Things Agentic Hackathon (deadline 2026-08-31 17:00 PDT). See `docs/product.md` and `docs/build-plan.md`.

The hackathon submission and current roadmap are still-image only. Gemini Live, Live Scene Sessions, Scene Probes, the post-Shot Coach, a custom viewfinder, and video Analysis are parked. Do not add them to Devpost copy, demo plans, architecture claims, or future-work sections unless the user explicitly reopens that scope. `silence` remains an internal Scout fallback, not a submission differentiator.

## Repo layout

```
backend/
  app/
    domain/    # PURE logic, zero I/O: grid math, taxonomy, entities, Criteria checks, Technique Map transitions
    imaging/   # Pillow + ffmpeg: exif, grid overlay, contact sheets, overlays (file I/O only)
    agents/    # ADK agents + prompts/ (prompts as .md files next to the agent)
    services/  # one module per pipeline stage; orchestrates domain + imaging + infra
    api/       # FastAPI routers: auth, drive webhook, pubsub push, dashboard API, SSE
    infra/     # Firestore, GCS, Pub/Sub, Drive, Secret Manager adapters
  tests/       # mirrors app/ structure
frontend/
  src/
    pages/     # route-level components
    components/
    stores/    # Pinia, options syntax
infra/         # gcloud scripts: apis, topics, scheduler, deploy. No Terraform.
docs/
```

## Frontend rules (Vue 3 + Vite + Tailwind)

- Options API only. No `<script setup>`, no Composition API. Pinia stores use options syntax (`state/getters/actions`).
- SFCs, one component per file, PascalCase filenames.
- Tailwind utility classes in templates; `style.css` holds tokens only.
- Cross-component state lives in a Pinia store; props/emits otherwise. No event buses.
- API calls only in store actions, never in components. One `api.js` wraps fetch + SSE.
- No component libraries. Tailwind + hand-rolled. Icons: lucide static SVGs.
- Phone first. Every screen is designed at 390px wide before it is designed at 1280px.

## Backend rules (Python 3.12 + FastAPI + ADK)

- uv for deps, ruff for lint+format, full type hints, pydantic v2 for every agent output and API schema.
- `app/domain/` is sacred: pure functions, no imports from infra/agents/api/imaging, fully unit-tested.
- Agents return pydantic-validated structured output. The model never emits pixels: cell refs only, `domain/grid.py` converts.
- The model never emits a technique id outside `domain/taxonomy.py`. Unknown ids are dropped and logged, not stored.
- Prompts live in versioned `.md` files beside their agent, never inline strings.
- Firestore via official SDK directly, no ORM. Blob paths built in `infra/storage.py` only.
- All model ids, caps, topic names, regions in `config.py`. Never scattered literals.
- Every pipeline stage is idempotent on `shot_id`. Pub/Sub delivers at least once; a redelivery must be a no-op.
- Every stage writes an `ActivityEvent`. The feed is a view of Firestore, not a separate truth.
- Local dev runs the same stage code in-process (`settings.in_process_pipeline`). Pub/Sub is a transport, not a behaviour.

## Testing: no mock theater

Banned: tests that mock the collaborators of the thing under test to assert the mock was called. If a test needs 3+ mocks, it is testing the mocks. Delete it.

1. Real unit tests on pure logic (`domain/`): grid math, criteria checks against real Exif values, skill transitions, taxonomy invariants. Exhaustive where cheap.
2. Real imaging tests: Pillow and ffmpeg on fixture files, assert measurable properties. Skipped visibly when ffmpeg is absent.
3. Integration tests (`api/` + `infra/`): TestClient with real requests and real stores. `InMemoryStore`/`FirestoreStore` and `LocalBlobStore`/`GcsBlobStore` share contract suites; Firestore joins when `FIRESTORE_EMULATOR_HOST` is set.
4. Agents are not unit tested with a mocked Gemini. Agent quality is checked by `scripts/check_*.py` against real calls on a small labelled set.

## Git

- `main` stays deployable. Small commits, imperative messages. No AI attribution trailers anywhere.
- Never commit `.env`, tokens, service-account keys, or demo media over 5 MB.
- Never deploy to Cloud Run on your own initiative. Deploy only when the user asks.

## Golden rules

1. Cell refs, not pixels, at every model boundary.
2. Technique ids from the taxonomy, nowhere else.
3. EXIF is hard evidence; vision is soft evidence with a confidence. The Judge checks hard first.
4. Only the Judge records a Verdict against explicit Reproduce Criteria. Explore and Compare never receive a Verdict.
5. The system camera owns capture. Phone Source observes only approved Camera media. Only an explicit Experiment id associates a Shot; capture time never implies participation.
6. The system Camera owns capture and the photographer controls the shutter. Temporary or legacy Scene media never becomes a Shot.
7. A Shoot groups natural Camera activity. A Capture Session records explicit Experiment participation. The memberships are orthogonal.
8. Approved Camera media defaults to the Photographer's Shot. Ambiguous manual imports must distinguish Mine from Inspiration before longitudinal writes. Inspiration never updates Photographer memory.
9. A Deconstruction is a draft from stored Evidence. The photographer chooses the Keeper cover, export, and posting.
10. If a behaviour is not in `docs/domain-model.md`, it does not exist. Update the doc first.
