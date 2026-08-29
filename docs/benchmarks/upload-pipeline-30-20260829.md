# Production upload-to-Run benchmark, 30 still Shots

Run on 2026-08-29 against Cloud Run revision `shoots-00006-mzn` and
`gemini-3.7-flash` through the production Pub/Sub pipeline.

## Method

- Created one disposable Photographer and device directly in the production store.
- Uploaded 30 still Shots sequentially through `POST /api/ingress/shots`.
- Used 13 varied corpus images, repeated with unique source references until 30 uploads.
- Polled each authoritative `GET /api/shots/{id}` Run until `completed` or `terminal`.
- Deleted the exact benchmark Photographer, device, Firestore records, and GCS prefix.
- Independently verified that the user, devices, and blobs no longer existed.

The 30 files totalled 53,115,453 bytes, with a mean size of 1,770,515 bytes.
Uploads took 104.266 seconds sequentially. Processing overlapped while later files
were still uploading.

## Result

| Measurement | Mean | p50 | p90 | Maximum |
| --- | ---: | ---: | ---: | ---: |
| HTTP upload to accepted | 3.476 s | 2.422 s | 3.703 s | 16.953 s |
| Authoritative server Run | 42.360 s | 38.488 s | 54.553 s | 70.561 s |
| Upload start to server settlement | 45.634 s | 43.048 s | 61.001 s | 74.082 s |

- 30 of 30 Runs completed.
- No Run was terminal or unfinished.
- 27 of 30 server Runs completed within 60 seconds.
- Cloud Run recorded zero warning-or-error logs during the benchmark window.
- The complete 30-Shot batch settled in 202.640 seconds.
- Disposable-data cleanup completed and was independently verified.

## What this proves

Shoots can accept a 30-Shot burst and settle every Run through the deployed
event-driven pipeline. The current product is background processing, not instant
critique. The production p50 closely matches the earlier 39.8-second local corpus
mean, while p90 and maximum expose the tail that an average hid.

## Limits

- This measures API upload through completed Run, not Camera capture through Android
  visibility.
- The current Run schema keeps final stage state but not historical attempt counts.
  Zero warning-or-error logs support a clean run, but do not prove that no transport
  redelivery occurred.
- ADK exposes model usage metadata, but Shoots does not persist it yet. This run
  therefore cannot support an exact per-Shot token or cost claim.
- Thirteen unique images were repeated to create the 30-upload load. This is a
  pipeline benchmark, not a new model-quality corpus.

Raw measurements: [upload-pipeline-30-20260829.json](upload-pipeline-30-20260829.json).
