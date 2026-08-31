# Metered five-Shot Gemini cost sample

Run on 2026-08-31 after the historical 75-file workflow test. This is a new,
separately identified estimate; it does not retroactively measure that test's bill.

## Scope

- Five unchanged still-image files from the deduped 42-file test corpus.
- Fresh local Photographer record, local file import/storage/event bus, and the
  real wired pipeline: Ingest, Analyst, Cartographer, Scout, Judge, Scribe, and
  Shoot settlement.
- Gemini 3.7 Flash through Vertex AI global. Every shared ADK model response
  emitted a `SHOOTS_MODEL_USAGE` receipt.
- Five of five Runs completed; five local reviewed outputs and three Shoot Records
  were created. No cloud deployment or production records were written.

## Observed model usage and estimate

| Measure | Result |
| --- | ---: |
| Logged responses | 26 |
| Input tokens | 134,680 |
| Cached input tokens | 0 |
| Output tokens | 13,377 |
| Reasoning tokens | 12,162 |
| Total tokens | 160,219 |
| Observed Google Search grounding calls | 0 |
| Model-only sample cost | $0.19678125 |
| Model-only mean per Shot | $0.03935625 |
| Model-only 75-Shot projection | $2.95171875 |

The 26 responses were five each from Technician, Composer, Storyteller, and
Synthesizer, plus six Crop Rater responses. Shoot settlement made no model call in
this sample. The projection is `sample cost / 5 * 75`, not an invoice or a promise
that every import costs the same.

Rates used were Gemini 3.7 Flash global standard through 2026-12-31: $0.75 per
million input tokens, $0.075 per million cached-input tokens, and $3.75 per million
response-and-reasoning tokens. Source: [Google Cloud pricing](https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing).

Excluded: Cloud Run, Firestore, Cloud Storage, Pub/Sub, logging, Google Drive
transfer, account discounts/credits, any real invoice allocation, optional
Experiment attempts, visual-story generation, and actual Camera capture.

## Reliability note

The first attempt had a Windows `PermissionError` while the isolated local file
store wrote the fifth Shot, before that Shot reached Gemini. The same Shot was
manually replayed and completed. The first harness also exposed a local
`InProcessBus.drain()` event-loop spin after four Runs completed; stack inspection
showed idle workers and the blocked drain. The recovery harness yielded the event
loop without changing product code. These local-harness issues did not alter the
recorded production 75-file result.

Raw receipts and the machine-readable report are retained locally at
`.scratch/metered-five-20260831T075035Z/` and are not a public artifact.
