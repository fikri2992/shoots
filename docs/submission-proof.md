# Four-minute submission proof

The executable rehearsal, proof limits, deployment placeholders, paper edit, and
fallback take list are in [Demo rehearsal](demo-rehearsal.md). This document remains
the final claim ledger and capture checklist.

## What the judge should repeat

> Shoots takes one explicit archive selection, performs the per-Shot background work,
> recovers failures, and returns settled Shoot Records with inspectable Evidence.

Primary category: Taskmaster. The accepted production proof starts with **75 selected
Drive Shots** in three batches of 25. It finishes a multi-stage background job without
asking the Photographer to tag, prompt, or supervise every Shot. It produced 75
completed Runs and three Shoot Records; five unique failed Shots completed through six
repair replays. The physical Camera-to-Shoot workflow remains unaccepted.

The Collaborative Partner qualities are supporting evidence, not the category pitch.
The Analyst synthesizes unstructured images, EXIF, Tone, Motion, panel reads, and
Photographer signals. The accepted Taskmaster claim is the completed Shoot Record.
Photographer benefit, Experiment follow-through, and cost remain separate unaccepted
gates.

## Four-minute sequence

| Time | Picture | Narration and proof |
|---|---|---|
| 0:00–0:20 | Open with ordinary source Shots and one settled Shoot Record | "I can take thousands of Shots and still not know which choices I repeat or whether they are deliberate." |
| 0:20–0:45 | Open Drive Picker and select the disclosed batch | "For this accepted proof, one archive selection starts the job. Shoots handles each selected Shot after that." Show the selection count and returned ids. |
| 0:45–1:20 | Split view: web processing state and Cloud logs or Firestore Run | Show the Shot id moving through Ingest and Analyst. Name EXIF as hard Evidence and the panel read as model opinion. Do not wait on a spinner in silence; explain the architecture while the real call runs. |
| 1:20–1:50 | Show the Run and Shoot barriers, including repair | "One Run accounts for one Shot. The Shoot closes only when every current member finishes or ends terminally." Show exact member ids and one replay-safe Shoot Record. |
| 1:50–2:15 | Web Now opens on the Shoot receipt | Read only the repeated, varied, and blind-spot lines. Do not open thirty critiques. Show the newest revision and exact membership. |
| 2:15–2:45 | Open one Shot Teaching Receipt | Keep first. Then Notice, one Try, and one Check over one matching image layer. Expand Full Analysis briefly to prove dissent, model version, measured Findings, and cells still exist behind the simple surface. |
| 2:45–3:10 | Show Scout decision and rejected routes | "Code decides which help is eligible. The model cannot invent a Technique, Criteria, or improvement." Show one supported route and why the others were rejected. |
| 3:10–3:35 | Show Experiment eligibility and its real status | Explain that the Experiment is optional. Do not imply an outcome unless one real Photographer completed it. |
| 3:35–3:50 | Journey and Deconstruction | Show the source Shots and what the current record can establish. State that Photographer usefulness is not yet accepted. |
| 3:50–4:00 | Architecture SVG beside Cloud Run revision | "Shoots learns from every Shot, offers one personal Experiment, and tracks what changes. It never turns the model's taste into mine." |

## Unedited proof-of-action segment

Use one continuous screen recording from Drive Picker confirmation through the first
durable Cloud stage transition. Keep these visible at the same time where possible:

- Picker result and processing state;
- Cloud Run logs with generic ids;
- Firestore or an audit endpoint showing the same Run id;
- the final Shot Teaching Receipt or Shoot receipt.

The segment fails if a database row is repaired by hand, an id changes between views,
or a cut hides the transition. In the accepted 75-Shot run, durable Run latency was
48.72 seconds at p50 and 2,306.161 seconds at maximum; Picker import requests averaged
104.353 seconds. Use the actual wait to explain the barriers. Do not claim instant
feedback.

## Claim-to-proof ledger

| Claim | Visible proof | Stored proof |
|---|---|---|
| One explicit archive selection | Drive Picker confirmation and returned count | stable Drive source ids and import assignments |
| Every Shot accounted for | processing count reaches terminal coverage | Run outcomes and exact Shoot Record member ids |
| Personal memory | Journey separates “keeps recurring” from settled Reproduce Evidence | Technique Map axes, session-level attempt/evaluable/Criteria-met counts, Tendency Profile, scoped Signals, input digests |
| Agent chooses justified work | one focal route, not a menu of generated suggestions | Scout route, warrant, rejected routes, policy and input versions |
| Advice evaluation | Not accepted; omit from the current proof | Requires a real Photographer, frozen Experiment Record, and later comparable Evidence |
| Photographer retains authority | Keeper, Intent, source role, and cover controls | attributable Photographer Signals and supersession history |
| Failure tolerance | replay or network recovery creates no duplicate terminal result | ActivityEvents plus Run, Capture Session, and Shoot barriers |
| Google Cloud execution | live service and stage logs from the candidate run | exact candidate revision, Pub/Sub subscriptions, Scheduler jobs |

The 75-file set came from 67 visually reviewed real hobbyist Shots plus disclosed
deterministic variations. It proves workflow and recovery at this scale, not 75
independent captures. The first full-scale attempt failed settlement; the fix passed
the 75-Shot gate, and the complete 300-file run was not repeated. Cost was not
measured, so no cost figure is accepted.

## Memory-to-action proof gate

The strongest optional 35 to 45 second segment is one causal chain:

```text
checked records
-> saved role- and purpose-specific Scout recall
-> selected and rejected routes
-> exact Experiment result
-> changed later automatic selection
```

Do not film this as implemented until the Scout decision stores the recall id, digest,
exact Signal and Intervention ids, exclusions, blind spots, size, and policy version.
Once that gate passes, show:

1. **What Shoots knows.** Exact Technique Evidence, one scoped Intent, one Keeper,
   earlier comparable outcomes, and one known gap.
2. **What Scout used and excluded.** The fixed Shoot Record and relevant references,
   beside unrelated Shoots, expired Signals, old generated prose, and unnecessary
   location data left out.
3. **How memory changed the action.** One selected route, one rejected repeat, and the
   exact earlier outcome that changed automatic eligibility.
4. **Photographer control.** Correct or remove one typed fact and show its later policy
   effect without rewriting the historical decision.

The climax is not retrieval. It is an earlier checked outcome changing a later action.
The full extracted rationale is in
[ChatGPT repository and memory review](chatgpt-analysis-2026-08-29.md).

## Words to refuse

Do not say:

- "AI photo critic";
- "skill score" or "photo score";
- "Shoots knows your style";
- "this Shot passed" outside explicit Reproduce Criteria;
- "you improved" without the Photographer's own signal;
- "real-time" or "instant" Analysis;
- "multi-agent" as the reason the product matters.

Say instead:

- Shot, Shoot, Technique, Finding, Experiment, Verdict, Change;
- measured, model read, or Photographer-owned;
- complete, terminal, abstained, or insufficient Evidence;
- the available Evidence did not support a recommendation.

## Capture checklist

- [ ] Exact candidate SHA and Cloud Run revision recorded.
- [ ] Public health and App Links endpoints visible.
- [ ] Disposable account and non-sensitive Drive media prepared.
- [ ] Android notifications cleared before filming.
- [ ] Personal email, tokens, OAuth codes, file paths, and Firestore contents outside
      the disposable record hidden.
- [ ] One failure-recovery path recorded separately as backup footage.
- [ ] Architecture SVG readable at 1080p.
- [ ] Repository setup starts from the public README and succeeds.
- [ ] Signed internal APK SHA-256 recorded.
- [ ] Video duration at or below four minutes.
- [ ] Devpost title, description, category, repository, demo URL, video, team, and
      Google Cloud proof links checked after publishing.

## Required placeholders before recording

```text
candidate_sha=
cloud_run_revision=
service_url=
disposable_photographer_id=
shoot_id=
shoot_record_revision=
experiment_id=
intervention_id=
apk_sha256=
physical_device_model=
android_version=
```

Never pre-fill these from an earlier local run. Record them from the accepted Cloud
and Xiaomi execution.
