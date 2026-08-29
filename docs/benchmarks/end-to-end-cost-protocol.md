# End-to-end time and cost protocol

## What the clock measures

One number would hide different waits. Report these separately:

1. **Camera media to accepted Shot.** Android discovers approved Camera media,
   WorkManager uploads it, and ingress returns the Shot id.
2. **Accepted Shot to visible visual story.** The Run settles, Android refreshes
   Room, and Shot detail renders the stored teaching receipt and visual layers.
3. **Thirty-Shot batch.** The first upload starts and every Run settles.
4. **Natural Shoot.** The last Camera item arrives, the real 30-minute inactivity
   rule elapses, the five-minute Scheduler closes it, and Android receives the
   terminal Shoot Record, Scout outcome, and Deconstruction attempt.

The API benchmark can prove server readiness. Only an Android run can prove that
the result became visible on the device.

## What cost means

The benchmark records one deduplicated usage receipt for every Gemini response,
including retries. Each receipt contains prompt, cached, tool-result, answer,
reasoning, and total tokens, plus any grounding queries.

For Gemini 3.7 Flash on the global endpoint through 2026-12-31:

- uncached input: $0.75 per million tokens;
- cached input: $0.075 per million tokens;
- answer and reasoning output: $3.75 per million tokens.

The benchmark calculates list-price model cost as:

```text
((prompt - cached + tool) × 0.75
 + cached × 0.075
 + (answer + reasoning) × 3.75) / 1,000,000
```

If grounding occurs, the report keeps its query count separate. It does not call
the total exact until the applicable monthly free allowance is known.

Sources: [Gemini pricing](https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing)
and [usage metadata fields](https://cloud.google.com/vertex-ai/generative-ai/docs/reference/rest/v1/GenerateContentResponse).

## Infrastructure cost limit

Token cost is attributable to this benchmark because each receipt carries the
disposable Photographer id. Cloud Run, Pub/Sub, Firestore, GCS, and Logging share
project-level billing, free tiers, and rounding. The project has no Cloud Billing
BigQuery export configured as of 2026-08-29, so an instant exact infrastructure
invoice delta cannot be recovered for one three-minute batch.

Report these as different figures:

- **measured model list price**, from response usage receipts;
- **observed project invoice delta**, once billing data arrives, if an isolated
  billing export is configured before the run;
- **estimated infrastructure list price**, only when the service metrics and
  operation counts support it.

Do not add an estimate to an exact token cost and label the sum exact.

## Current evidence

The deployed revision `shoots-00006-mzn` completed 30 of 30 per-Shot Runs in
202.640 seconds. That run included the Analyst panel and code-rendered visual
artifacts. It did not measure Android visibility or wait for Shoot settlement,
and the deployed runtime did not retain usage metadata.

The next production run must use a revision containing usage receipts and the
extended benchmark. It must keep Android-shaped source timestamps, wait for the
real inactivity and Scheduler window, and poll the authoritative mobile snapshot
until its Shoot Record contains all 30 Shot ids. No shortened inactivity setting
may be called the real end-to-end number.
