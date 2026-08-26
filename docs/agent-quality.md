# Real-agent quality gate

> The executable gate is
> [`backend/scripts/check_learning_quality.py`](../backend/scripts/check_learning_quality.py).
> The manifest shape is shown in
> [`eval/learning-quality.example.json`](../eval/learning-quality.example.json).
> [`backend/scripts/check_journey_quality.py`](../backend/scripts/check_journey_quality.py)
> separately checks the real Journey writer against recurrence and causation traps.

## Why this exists

A passing integration suite proves that Shoots stores, retries, settles, and projects
model output correctly. It does not prove that the Analyst saw the Shot well or that
the teaching receipt is useful.

The quality gate runs the real Ingest and Analyst stages on labelled media. It records
the exact model, provider, prompt version, manifest and input digests, measured Shot
evidence, Analysis, Shot Teaching Receipt, latency, and rendered artifacts. A prompt
or model change can therefore be compared against the same source bytes instead of
judged from memory.

## What code may grade

The harness can check facts declared in the manifest:

- whether at least one Technique from a labelled set appeared;
- whether a known false-positive Technique or Finding appeared;
- whether abstention was permitted for that Shot;
- whether Try and Check exist when the case requires an action;
- whether the Move kind, forbidden contradiction phrases, and default image layer are
  appropriate;
- whether the subject cells overlap a human-labelled normalized box;
- whether visible copy leaks internal cells or exceeds its copy budget;
- whether authority labels and taxonomy ids remain valid.

These checks are narrow. A missing expected Technique is a failed label, not proof that
the Shot is bad. A forbidden Finding is a false positive only because a human declared
that exact exception for that exact case.

## What still needs a person

The harness records `review` items for questions code cannot settle:

- Does Keep name the decision that makes the Shot worth returning to?
- Do Notice, Try, and Check form one coherent lesson?
- Does the annotation point to the claimed subject or distraction precisely enough?
- Does the response respect deliberate style and stated Intent?
- Is silence more useful than the advice produced?
- Would a hobbyist know what to inspect on the next capture?

A review item is never counted as pass. The reviewer records the answer beside the
saved report or promotes a repeatable failure into a new manifest label.

## Corpus composition

The deadline corpus should include at least:

1. ordinary phone Shots with no curated technique;
2. strong Shots where praise or silence is appropriate;
3. technically weak Shots with one clear next-capture action;
4. deliberate silhouette, centre placement, high key, low key, and motion blur;
5. sparse EXIF, unreadable media, and ambiguous subjects;
6. several Shots from one Shoot;
7. explicit Explore and Reproduce results.

Do not fill the set with famous or unusually dramatic images. The product claim is
about daily phone photography.

## Run it

Copy the example to an ignored local manifest and point each case at media you may use:

```powershell
Copy-Item eval/learning-quality.example.json eval/learning-quality.local.json
cd backend
uv run python scripts/check_learning_quality.py ../eval/learning-quality.local.json
```

The script writes JSON under `eval/output/` and rendered Analyst artifacts beside it.
Those paths are ignored because the media and reports may be private. A report exits
non-zero when any declared check fails, but still runs the remaining cases.

Use `--limit 1` while validating credentials. Use `--case ladybug_umbrella` to rerun
one named case, and repeat `--case` for a small failure class. Use `--output` to give
two prompt or model runs stable filenames for comparison.

When only deterministic receipt or annotation code changed, reuse one saved
real-model report without paying for or disguising another model run:

```powershell
uv run python scripts/check_learning_quality.py `
  ../eval/learning-quality.local.json `
  --reproject-report ../eval/output/learning-quality-accepted-current.json `
  --output ../eval/output/learning-quality-accepted-final.json
```

The reprojected report preserves the original model-run timestamp and adds the
source-report digest plus a separate projection timestamp.

## Reading failures

Classify a failure before changing anything:

| Failure | First place to inspect |
|---|---|
| Unknown Technique or cell | validation boundary; the model output should have been dropped |
| Repeated false Technique | owning lens prompt, panel agreement, and corpus label |
| Measured Finding conflicts with deliberate Technique | detector scope and `EXCUSED_BY` rules |
| Try is generic or unrelated | Composer Move schema, selection order, and stored reason |
| Annotation misses the claimed object | subject cells, Finding cells, and rendered layer |
| Long or contradictory receipt | deterministic receipt projection before changing the Analyst |
| One isolated odd answer | record it; do not tune the system yet |

Change a prompt, threshold, detector, or projection only after the same failure class
appears across multiple defensible labels. Save the before and after reports. A nicer
single example is not evidence of a better agent.

## Accepted still-Shot run

The local acceptance run on 2026-08-27 used 11 real cases: six ordinary phone
Shots, including four from one Shoot, plus deliberate silhouette, low-key portrait,
motion blur, long exposure, and freeze action. The model was
`gemini-3.7-flash` through Vertex AI. Every case used prompt digest
`1c738851cdfb`.

The final report recorded 180 automatic passes, zero failures, 12 human-review
questions, and no errored cases. The mean end-to-end Ingest plus Analyst time was
39.8 seconds; the maximum was 53.6 seconds. Shoots therefore treats Analysis as
background work. The current implementation does not support an "instant critique"
claim.

Developer review against the locked hobbyist perspective produced these outcomes:

| Case | Review outcome |
|---|---|
| Farm Shot 1 | Backlight is noticed; the overhead beam leads to one camera-height Move. |
| Farm Shot 2 | Clipped sky is measured; the next capture has one visible highlight check. |
| Farm Shot 3 | Deliberate centre is preserved while the overhead structure is challenged. |
| Farm landscape | The foreground obstruction gets one camera Move without a composition-rule Finding. |
| Umbrella | High angle leads; removing the cyclist does not prescribe eye level. |
| Skyline | Wide-angle cloud and city relationship leads; no forced repair appears. |
| Silhouette | Silhouette leads; no exposure correction or thirds homework appears. |
| Low-key portrait | Chiaroscuro leads; no mandatory repair appears. |
| Motion blur | Motion blur leads; a corroborated stable-anchor and streak relationship suppresses shake risk without claiming Intent. |
| Long exposure | Long exposure leads; the blurred water is not treated as a technical failure. |
| Freeze action | Freeze action leads; the captured instant appears before optional refinement. |

The run found and corrected six repeated failure classes:

- neutral coordinates promoted into composition-rule Findings;
- advice that contradicted the strongest supported Technique;
- guide conformity used as corrective warrant;
- every annotation layer stacked into one unreadable image;
- grid references translated into broken visible sentences;
- no neutral Technique for a sharp stable anchor against a motion-streaked region.

The accepted report remains ignored because it contains private local media paths.
Its SHA-256 is
`5c161d5c760345e900a3b4b8307e4b90ca771c6958d794d1adc81c2b8bb1f4e3`.
The committed example manifest preserves the reproducible contract without
publishing the corpus.

## Accepted Journey-writer run

The local acceptance run on 2026-08-27 used two evidence-only cases against
`gemini-3.7-flash` through Vertex AI under Journey prompt version `ddabb4791f14`:

- a newly recurring Technique with no Reproduce session and unknown taste;
- a measured distribution Change beside an earlier offer, without causal Evidence.

Both returned usable paragraphs under 90 words. Neither converted recurrence into
reliability, repeatability, mastery, improvement, or control; neither invented taste
or said the offer caused the later Change. Code also discards a Journey paragraph if
the writer emits one of those unsupported control or improvement phrases. The stored
figures remain visible when prose is discarded.

## Completion rule

P0.13 is complete only when a versioned corpus report from real Gemini calls has no
unresolved critical false positive, every automatic failure is classified, and the
human review shows the receipt is specific enough to guide the next capture. The
harness existing is necessary, but it is not the result.
