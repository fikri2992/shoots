# Feature list

Product backlog derived from the decisions in [product decisions](product-decisions.md). State is a repository snapshot from 2026-08-25, not a deployment claim.

## Status

- `built`: present and exercised locally in the current repository
- `partial`: useful code exists, but it does not meet the locked product rule
- `needed`: required for the promise or hackathon demonstration
- `later`: valid product work after the core loop is proven
- `remove`: conflicts with the product

## P0: prove the product

These features make the one-liner true and make the completed work visible.

| ID | Feature | State | Done when |
|---|---|---|---|
| P0.1 | Tendency Profile | built | Pure code recomputes dimension counts, exploration, dwell, and named blind spots from stored Shot measurements. |
| P0.2 | Positive-only Keeper signal | built | `kept_at` and absence are distinct; unmarking returns a Shot to unknown. Concentration is marks over shots taken, so an unmarked Shot is only ever exposure. Sparse samples stay silent. |
| P0.3 | Technique Map | built | The UI and API use `unobserved`, `observed`, and `recurring`. Corroborated Evidence moves state. Scores do not. |
| P0.4 | Explore Experiment | built | Scout creates one Experiment from a cited Tendency, freezes its Baseline with provenance, records its type, declares Criteria, accepts results, and records a Verdict that answers Criteria only. A Baseline is frozen only where the Tendency actually chose the Technique. The record is readable on the card and on the Journey. No user-facing Quest or grading language remains. |
| P0.5 | Experiment Change check | built | `Change` is `changed`, `unchanged`, or `insufficient evidence`, with a `Comparability` saying why. Minimum shots, minimum scenes, a `CALC_VERSION` bump, an unknown dimension and a missing sample are told apart; only a sample that can still grow is re-checked. Frames taken and frames the dimension could read are counted separately. No outcome sentence claims causation, and a test holds that. |
| P0.6 | Journey Update | built | A meaningful profile difference creates one update from supplied figures. The first update does not compare against an empty history, and the copy avoids unsupported improvement. |
| P0.7 | Claim provenance | built | `Provenance` on every Journey Update: Shot ids, sample size, `CALC_VERSION`, and model plus prompt digest only where a model wrote words. Grading refuses to compare baselines across a version bump. |
| P0.8 | Score removal | built | No score on the phone, web, reviewed filename, caption, Journey, Coach prompt or tools, Judge prompt, activity events, or any user-facing API — the read API names its fields rather than publishing the entity. It no longer chooses the comparison frame either. Stored and read by nothing; `tests/test_surfaces.py` drives the real endpoints to hold it. |
| P0.9 | Vocabulary migration | built | Quest is now Experiment (Pub/Sub topics included), Fault is now Finding, and the skill graph is the Technique Map with three states. Events, schemas, UI, prompts, docs and stored data agree; `scripts/migrate_vocabulary.py` moves an old store and is idempotent. |
| P0.10 | Android Shot to pipeline | built | A paired phone captures a Shot, uploads through the same ingest path, sends pitch, and receives a praise-first pulse. |
| P0.11 | Evidence-first pulse | partial | The pulse leads with the strongest corroborated Technique and its proof, then one Finding. It never says Keeper unless the photographer marked it, and the keeper button now reflects what the server took rather than latching optimistically. |
| P0.12 | Agent desk | partial | One screen shows Shot arrival, measurements, panel reads, abstention or veto, Technique Map update, Experiment selection, Verdict, and Change check in order. |
| P0.13 | Real-agent quality gate | partial | The existing `backend/scripts/check_*.py` runs against a small labelled set with expected claims, allowed abstentions, false-positive counts, and saved results. |
| P0.14 | Cloud deployment | needed | The exact demo build runs on Google Cloud. Pub/Sub retries and idempotency are visible. The deployed revision and health check are recorded. |
| P0.15 | Submission architecture artifact | partial | The Mermaid source in [agents](agents.md) is updated to current vocabulary and exported as a readable diagram for the submission. |
| P0.16 | Four-minute continuous demo | needed | One continuous run shows Shot history, new capture, Evidence, personal Experiment, Verdict, Change, Journey Update, and Cloud proof. A stranger can repeat the work accomplished afterward. |

P0 passes only when this sentence is visibly true:

> Shoots remembered the photographer's work, found a recurring pattern, chose what to test, and verified what changed.

## P1: complete the longitudinal coach

| ID | Feature | State | Done when |
|---|---|---|---|
| P1.1 | Reproduce Experiment | needed | Shoots selects a Keeper-associated pattern, asks the photographer to reproduce it deliberately, and compares the result without treating unmarked Shots as dislike. |
| P1.2 | Compare Experiment | needed | Shoots holds one variable as the focus, records both alternatives, and asks one optional preference question. The model does not choose the winner for the photographer. |
| P1.3 | Journey comparison hero | needed | Journey pairs comparable earlier and recent Shots for one Technique and states only the measured difference plus a labelled model read. |
| P1.4 | Comparable-set rules | needed | Domain code defines which Shots may be compared by Experiment type, Technique, Scene conditions, and minimum sample. Incomparable sets return `insufficient evidence`. |
| P1.5 | Intent | needed | The photographer may state one short Intent without being prompted. It travels into review and may mute a conflicting Finding or camera warning. Absence stays valid. |
| P1.6 | Structured learner memory | needed | Shoots remembers explicit constraints, preferred cadence, repeated Experiment responses, Intent, and Keeper signals with provenance. It never promotes inferred personality to user fact. |
| P1.7 | Bounded escalation | needed | A cheap read settles clear cases. Only consequential disagreement opens the full panel or asks for one more view. The escalation reason is stored. |
| P1.8 | Advice retirement | needed | Shoots retires one Experiment approach only after repeated comparable non-movement, while distinguishing no attempt from an attempted but unchanged result. |
| P1.9 | Scene grouping | needed | Capture continuity or explicit grouping puts related Shots into one Scene. Contact-sheet comparison can describe how the photographer worked it without forcing a score. |
| P1.10 | Graduation | later | When a Technique recurs reliably, the Companion stops teaching it and says so once. It may return only after contrary Evidence or a user request. |

## P1: camera Companion

The Companion helps while a photographic decision is still open. It does not replace the longitudinal product.

| ID | Feature | State | Done when |
|---|---|---|---|
| C1 | Active Experiment in the viewfinder | partial | The current Experiment, reason, and one instruction are visible without covering the Scene. |
| C2 | Fast local measurements | partial | Zebras, guide, and pitch run locally. Scene count, framing variation, and useful light timing are added only as measured readouts. |
| C3 | Summonable Coach | needed | Tap or voice sends the current preview, active Experiment, relevant measurements, and memory. The response gives one move or one question. |
| C4 | Silence policy | needed | Uninvited speech is off by default or hard-capped to rare high-value cases. Repeated low-confidence suggestions produce silence. |
| C5 | Context relevance gate | needed | Weather, temperature, current light, and location facts appear only when they change the active Experiment or the photographer asks. Every fact has a source and capture time. |
| C6 | Scene-aware direction | needed | The Companion can ask the photographer to move or reframe, inspect the next preview, and explain one visible difference. It never claims to see an unobserved angle. |
| C7 | Human guide overlay | partial | The user sees a guide, arrow, crop region, or plain direction. Internal cell references never appear. |
| C8 | Scene Probe | later | The Companion captures a temporary low-resolution preview only after an explicit probe action. It may annotate or compare it, then discards it unless saved as a Shot. |
| C9 | Explicit capture control | built | Only the shutter or an explicit voice command creates a Shot. Suggestions and probes never silently enter the archive. |
| C10 | Explicit place memory | later | The photographer can save a useful place note. Shoots stores the note and its source, not a hidden movement trail. |

If P0 is unstable, C3 through C10 wait. The Companion is the first fallback cut.

## P2: identity without overclaiming

| ID | Feature | State | Done when |
|---|---|---|---|
| P2.1 | Emerging identity view | later | Shoots groups recurring subjects, approaches, and Keeper signals as hypotheses with examples. It never assigns a fixed style label. |
| P2.2 | Personal projects | later | Repeated Intent and Keeper patterns may suggest a project. The photographer accepts it explicitly. |
| P2.3 | Reference Inspiration | later | A relevant real photograph or local fact may support an Experiment. It is optional, sourced, and never generated filler. |
| P2.4 | Long-horizon plan | later | The agent sequences Experiments across a user-chosen goal and revises the plan from Evidence. No streaks or artificial deadlines. |

## Remove or forbid

| Feature | Action | Reason |
|---|---|---|
| User-facing 1 to 10 score | remove | It collapses model opinion into false precision and conflicts with the thesis. |
| Solid, rusty, and level-up language | replace | It turns a neutral Technique record into a curriculum and claims ability beyond Evidence. |
| Quest, challenge, assignment, homework | replace | Experiment better covers exploration, reproduction, and comparison without coercion. Done 2026-08-25. |
| AI-generated reference clip as a core step | remove from core | It adds latency and spectacle but does not improve the longitudinal work. |
| Director as a required pipeline stage | demote or remove | The Experiment must not wait for generated media. |
| Constant viewfinder narration | forbid | It makes photography annoying and makes the agent the photographer. |
| Automatic Shot capture | forbid | The photographer controls the shutter. |
| Internal cell grid in UI | forbid | Cells are model addressing, not a photographic guide. |
| Hidden location history | forbid | Context does not justify surveillance. |
| Social feed, filters, editing, culling | out of scope | Mature neighbouring products already solve these jobs. |
| Streaks and skill-tree grinding | forbid | Retention should come from seeing personal Change, not obligation. |

## Recommended implementation order

1. ~~Fix Keeper semantics and migrate product vocabulary.~~ Done 2026-08-25.
2. ~~Remove user-facing scores and add claim provenance.~~ Done 2026-08-25.
3. ~~Polish the existing Explore Experiment through Experiment Record and Journey Update.~~ Done 2026-08-25.
4. Deploy and record the continuous P0 demo.
5. Add one Companion capability, the summonable one-move Coach.
6. Add Reproduce Experiment.
7. Add Compare Experiment and Intent.
8. Add Scene, structured memory, and bounded escalation.
9. Consider Scene Probe, identity hypotheses, projects, and Inspiration only after repeated user evidence.
