# Model-written social Deconstruction check

Implemented locally on 2026-08-31. Not committed or deployed by this task.

The later [visual artifact integration check](deconstruction-visual-artifacts-2026-08-31.md)
extends this implementation. The runs below describe the earlier original/detail-only export.

## What changed

One bounded Gemini writer inside Scribe replaces the fixed Shoot-count templates.
It receives the selected Shot, stored visual Evidence, and previews of the exact
detail crops it may choose. The output is an opening with caption, one to five
supported story beats, and the same Shot without added text or cropping.

Code validates references and copy constraints, persists a writing checkpoint,
and renders the JPEGs. Concurrent requests use a bounded lease. Rendering retries
reuse the writing; a failed rebuild preserves the previously usable images.
Web and Android label the result as a model-written draft for review.

## Actual model runs, final implementation

The input set was three isolated copies of existing Shots and their stored
Analyses, not a new ingest or full Photographer journey. The live source store
and source image bytes were unchanged. `gemini-3.7-flash` was confirmed in each
real response's usage receipt.

| Input | Pages, including clean ending | Full prepare time | Same-input cached request |
|---|---:|---:|---:|
| Paddy, IMG_20251212_060321.jpg | 5 | 14.797 s | 0.016 s |
| Moon, IMG_20251206_053335.jpg | 4 | 11.984 s | 0.016 s |
| Road, IMG_20251206_052515.jpg | 5 | 14.328 s | 0.016 s |

No model request failed or timed out in this final three-case run. This small
sample is not a reliability rate or a production latency guarantee. Cached
requests made no additional model call. Raw token receipts are saved with the
local report; currency cost was not calculated.

Captioned pages: 1080x1350 JPEG. Clean ending: 1200x1600, matching the stored
original's orientation and dimensions, with no visible additions. Maximum
mean-channel pixel difference after JPEG re-encoding was below 0.58 on a 0-255
scale. The clean file is not byte-identical to the original or a camera RAW file.

An earlier iteration guessed time-of-day wording such as dawn from visual reads.
The prompt and structural validation now reject those claims. Another iteration
rendered thin detail strips; grid math now adds surrounding context without
cutting away the located region. The final contact sheets were visually reviewed.
No output captions were manually rewritten for these examples.

## Verification

- 12 backend API/real-store/Pillow integration cases passed. Coverage includes
  ownership, explicit cover choice, three-to-seven-page output, landscape clean
  endings, Explore without a Verdict, active and expired leases, invalid
  references, invented first-person Intent, inferred time, missing-file repair,
  and real filesystem-write failures with checkpoint recovery. A failed cover
  change retains the previous draft and its downloadable files.
- Offline integration cases use explicitly hand-authored persisted checkpoint
  fixtures. They do not mock Gemini or count as model-quality evidence. The real
  model checks above exercise fresh writing through the actual service path.
- 13 frontend checks passed, including real-router/Pinia integration for standard
  Journey and variants A/B/C. Individual JPEG links, download busy state, and the
  uncropped clean preview were checked. Production frontend build passed.
- In-app browser against an isolated loopback account: all five download-all
  requests reported completion, in order 01-05. The individual clean-image link
  also completed. No ZIP interaction or browser-permission change was needed.
- Android Kotlin compilation passed after the DTO, clean preview, rebuild,
  progress, and duplicate-request guard changes. No emulator or Android share-
  destination test was performed in this task.
- Ruff and `git diff --check` passed. Existing SDK/ADK/test-client deprecation
  warnings remain; they did not prevent these checks.

## Limits and artifacts

Reference checks establish provenance and structure, not the semantic truth of
every sentence. The writer can still misinterpret a Shot or cite incompletely.
The photographer must review the draft. No platform posting or platform-specific
carousel crop was tested. Social platforms may crop the clean ending when it is
uploaded alongside portrait pages; it can be posted separately.

Local reproducible report and actual image files:
`.scratch/deconstruction-social-check-20260831-v3/report.json` and sibling
`story_check_*` directories. `preview.md` links the generated images. Earlier
iteration reports remain in the corresponding unversioned and `-v2` directories.
These local artifacts are ignored, not deployed content or submission evidence
of a complete autonomous ingest run.

Re-run from `backend` using `uv run python -m scripts.check_deconstruction_quality`
with `--store`, `--blobs`, repeatable `--shot`, and an isolated `--out` directory.
