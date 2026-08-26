# Shoots memory contract

> Active memory contract, drafted 2026-08-26. This document governs new memory
> implementation. [The domain model](domain-model.md) remains the product authority.
> [memory.md](memory.md) and [memory-suggested.md](memory-suggested.md) are reference
> material only.

## The job

Shoots memory exists to answer:

> Which photographic decisions am I making repeatedly, which can I now make on
> purpose, and how is that changing across my Shoots?

The answer needs more than an archive or a generated summary. Shoots must preserve
the exact Shots, how they formed Scenes and a Shoot, which Techniques appeared, what
the Photographer explicitly valued or intended, which Experiments they entered, and
what changed across comparable evidence.

Memory is a checked record of photographic behaviour. It is not chat history, a
personality profile, or a score.

## Current truth and target

| Area | Current repository | Contract target |
|---|---|---|
| Shot | Stable source reference, original, measurements, Analysis, model and prompt provenance | Keep |
| Run | Durable stage account for one Shot | Keep as the only per-Shot terminal authority |
| Technique Map | Rebuildable projection with separate sightings, corroborated Shots, Scene/Shoot coverage, Reproduce results, Criteria outcomes, abstentions, and positive Keeper figures | Add supported condition coverage after reliable inputs exist |
| Tendency Profile | Rebuilt from the complete readable archive under `CALC_VERSION` | Rebuild from authoritative evidence; cache only with an input digest |
| Keeper | Positive `kept_at`; unmarked means unknown | Keep |
| Intent | Generic scoped Photographer Signal and API exist; no native creation flow yet | Add the smallest contextual client action before using Intent in selection |
| Experiment | Baseline, explicit results, Reproduce Criteria and Verdicts, Change; new Shoot route stores exact Keeper warrant ids | Complete intervention outcomes for every Scout route |
| Scene | Persisted capture-continuity membership with grouping revisions | Add explicit Photographer correction |
| Shoot | Persisted natural Camera activity, revisioned terminal Shoot Record, deterministic receipt, and typed Scout outcome | Add client delivery, correction, full projections, and Deconstruction outcome |
| Constraints | Scoped attributable Signals, correction, bounded recall, literal Listener quote gate, Live announcement, and legacy read-only fallback | Remove the legacy fallback after stored-data migration |
| Inspiration | Explicit Android/web manual role, separate current record, projection-safe free-Shot correction, and client archive section | Add bounded study and correction for Experiment-cited history without weakening immutable records |
| Android | Room cache and outbox; device token ciphertext uses Android Keystore | Keep Room as a non-authoritative cache; do not claim Room encryption |

## Rules that do not move

1. **The store remembers.** Model sessions start without conversational memory. Code
   builds every agent view from durable records.
2. **Authority stays separate.** Measurements, model reads, and Photographer signals
   retain different sources. Storage never blends them into one certainty.
3. **The Photographer owns meaning.** Keeper, Intent, preference, correction, manual
   Mine versus Inspiration, and whether Change feels like improvement come from the
   Photographer. Approved Camera media defaults to Mine through the source contract.
4. **Derived memory can be rebuilt.** Technique Map, Tendency Profile, Change, and
   current Journey claims point to authoritative inputs and calculation versions.
5. **No absence becomes dislike.** Removing a Keeper returns the Shot to unknown.
6. **No timer erases history.** Recency may affect Scout selection, never whether a
   Technique was previously observed or recurring.
7. **No overall ability score exists.** Sightings, distinct Scenes, deliberate
   attempts, Criteria outcomes, conditions, positive Keepers, and Change remain
   separate evidence.
8. **Similarity is not event truth.** Scene and Shoot membership come from capture
   continuity or explicit correction, never image similarity alone.
9. **Every intervention is accountable.** Scout stores its route, warrant, rejected
   routes, delivery state, attempt state, and supported outcome.
10. **Corrections supersede; they do not rewrite history.** Earlier records and
    ActivityEvents remain inspectable while clients resolve the newest valid revision.

## What is authoritative

| Record | Authority | Mutability |
|---|---|---|
| Shot source and original | Phone Source or explicit import | Immutable except deletion |
| Measured media facts | Ingest | Recomputed only under a new calculation version |
| Analysis | Analyst output plus model and prompt version | New version; old provenance remains traceable |
| Scene and Shoot membership | Capture-continuity code or Photographer correction | New grouping revision |
| Keeper, Intent, manual source role, preference | Photographer | Supersedable, never inferred as fact |
| Capture Session manifest | Explicit Experiment handoff | Immutable after commit |
| Experiment Record | Domain transitions, Judge, Photographer signals | Append or valid state transition |
| Run | Pipeline stages | Idempotent stage transitions to one terminal result |
| ActivityEvent | The stage that acted | Append-only audit |

The Technique Map and Tendency Profile are projections. Journey Update and
Deconstruction are presentations. None may become a second source of truth.

## Memory module seam

Memory should be a deep module. Callers should not know Firestore queries,
invalidation order, provenance assembly, revision rules, or context budgets.

Its conceptual interface has four operations:

```text
observe_shot(shot_id) -> membership change
settle_shoot(shoot_id) -> pending | Shoot Record
recall(role, purpose, scope_id) -> typed bounded view
apply_photographer_signal(signal) -> changed records and invalidations
```

The interface promises:

- idempotency for the same source or signal id;
- user isolation on every operation;
- exact input references in every derived result;
- no agent archive access outside `recall`;
- explicit pending, insufficient, superseded, and terminal outcomes;
- current-read resolution to the newest valid revision.

Store adapters may vary. Memory behaviour must not.

## Scene, Shoot, and Shoot Record

### Scene

A persisted Scene contains:

```text
id, user_id, shoot_id, grouping_revision
ordered_shot_ids
started_at, ended_at
grouping_source: capture_continuity | photographer_correction
grouping_version
```

The first implementation reuses the existing four-minute `SCENE_GAP`. A Shot with no
reliable capture instant starts its own Scene rather than being guessed into another.

### Shoot

A Shoot contains:

```text
id, user_id, device_id
state: open | closing | settled
revision, current_record_revision
ordered_scene_ids, ordered_shot_ids
started_at, last_capture_at, closed_at
grouping_version
```

- `open` accepts capture-continuous Camera membership.
- `closing` accepts no ordinary extension after the configured inactivity gap and
  waits for known member Runs.
- `settled` has a terminal Shoot Record for its current revision.
- A late Camera Shot or Photographer correction increments the revision and returns
  the Shoot to `closing`. It does not mutate an earlier Shoot Record.

The exact Shoot inactivity gap remains configuration to validate on real Camera
history. It must be longer than `SCENE_GAP`.

### Shoot Record

One immutable Shoot Record revision contains:

```text
shoot_id, user_id, revision
scene_ids, shot_ids
member Run outcomes and unreadable coverage
decision distributions and observed Variations
Technique Evidence and positive Keeper signals
Scout route, warrant, rejected routes, input versions
Deconstruction outcome when attempted
Provenance and settled_at
```

`Shoot.current_record_revision` selects the current record. Historical Journey Updates
retain the revision they cited. Current clients never keep showing a superseded record
as the latest truth.

## The three terminal barriers

The barriers share member Run status. They do not duplicate Analysis or wait for each
other.

| Barrier | Member set | Terminal meaning |
|---|---|---|
| Run | One accepted Shot | Every required per-Shot stage completed or became terminal |
| Capture Session | Exact source references frozen at Experiment commit | Every explicit member has an outcome and terminal Run; one batch summary may send |
| Shoot | Camera Shots assigned by capture continuity for one revision | Every member Run settled; one Shoot Record revision may settle |

Interaction rules:

1. Capture Session membership never changes after manifest commit.
2. A committed source reference may upload late. It is not new Capture Session
   membership, but it may create a newer natural Shoot revision.
3. Any late Camera Shot may revise a Shoot, whether free or explicitly associated
   with an Experiment.
4. A Capture Session cannot settle until every committed member has a Shot id, Judge
   or terminal-media outcome, and terminal Run.
5. A Shoot does not wait for an Experiment to close. A Capture Session does not wait
   for unrelated Shoot members.
6. When one Shot belongs to both aggregates, its single Run settlement triggers both
   independent checks.
7. Replaying either check is a no-op after the same revision or session settled.

## Technique Map memory

Keep `unobserved`, `observed`, and `recurring`. Add these independent figures:

```text
sightings
corroborated_shots
distinct_scenes
distinct_shoots
reproduce_attempts
criteria_met_results
abstentions
positive_keeper_shots
supported_condition_coverage
last_observed
projection_version
input_digest
```

The projection stores useful counts and a small recent-reference set. Exact Analyses,
Scene/Shoot membership, Keepers, and Experiment Records remain sufficient to rebuild
it. A Journey or Scout claim freezes the exact ids it used.

Recurrence does not prove control. A declared Reproduce attempt with supported
Criteria Evidence is stronger, but still does not prove artistic quality.

## Photographer memory and Listener migration

A remembered Photographer fact carries:

```text
user_id
scope: photographer | inspiration | shoot | scene | shot | experiment
scope_id
kind: intent | constraint | preference | source_role
value
source: direct_statement | confirmed_suggestion | photographer_action
source_event_id or transcript_digest
created_at, confirmed_at, superseded_at, optional_expires_at
```

Rules:

- A direct Photographer statement may be stored without another form or question.
- The Live `remember` tool tells the Photographer what it stored and writes an
  ActivityEvent.
- Post-session Listener extraction may store only literal standing facts supported by
  a direct statement and transcript provenance.
- A derived implication, inferred Intent, preference, or source role requires
  confirmation.
- Every stored fact has a correction and removal path.
- Scout receives only facts relevant to its current decision.

`services/coach.remember` and the Live tool now write per-fact Signals rather than
mutating `User.constraints`. Listener candidates survive only when their literal quote
appears in a Photographer turn, and the Live tool reports exactly what it stored.
Legacy `User.constraints` remains a read-only fallback until existing records migrate.

## Intervention memory

Each Scout decision stores:

```text
route: explain | ask | explore | reproduce | silence
warrant: exact Evidence references and thresholds
rejected_routes: route plus reason
input ids, projection versions, policy version
model and prompt version when a writer contributed
delivered_at
attempt_state: not_offered | offered | entered | left | completed
observable_outcome: unchanged | changed | insufficient_evidence | not_applicable
```

The record evaluates the intervention:

- offered but never entered is not failed advice;
- entered with unreadable results is not unchanged behaviour;
- Criteria not met is not a bad Shot;
- one unchanged attempt cannot retire an approach;
- repeated comparable outcomes may change a later route without altering the earlier
  Experiment Record.

Domain code decides which routes are available. The model writes only inside the
selected route. An unimplemented route is rejected with a reason or becomes silence.

## Bounded recall

Agents never query the archive directly.

| Role | Receives | Does not receive |
|---|---|---|
| Analyst lens | One Shot and its assigned measured facts | Photographer history or earlier critique |
| Shoot reader | One settled Shoot revision, contact sheet, compact Analyses, unresolved comparisons | Tendency Profile on its first read |
| Cartographer | Authoritative Evidence and affected projection inputs | Artistic prose as fact |
| Scout | Latest Shoot Record, relevant Technique/Tendency evidence, Keepers, recent Experiment outcomes, scoped Intent and constraints, route eligibility | Whole archive or prose biography |
| Journey writer | Precomputed comparable Change, evidence axes, blind spots, prior wording | New facts or unrestricted Shots |
| Companion | Current summoned Scene, selected Experiment, scoped Intent, small relevant memory | Hidden location history or raw archive search |

The Shoot reader works blind to longitudinal identity on its first pass. Code compares
its structured read with earlier memory afterward. This limits confirmation bias.

Every recall result includes its scope, input ids, blind spots, provenance, and a hard
size budget.

## Retrieval and embeddings

The first release uses structured retrieval:

1. filter by Photographer and Mine/Inspiration authority;
2. select exact Shot, Scene, Shoot, Technique, Experiment, Keeper, and time scopes;
3. reject incompatible calculation or Analysis versions;
4. rank by task relevance, then recency;
5. return exact references and blind spots.

Do not add a vector database before structured Shoot memory works. Embeddings may
later retrieve candidate visual analogues or Inspiration. They may not:

- assign Scene or Shoot membership;
- count Technique recurrence;
- infer Intent or preference;
- decide Reproduce Criteria;
- measure Change or improvement.

Similarity helps retrieval. It is not longitudinal truth.

## Correction and invalidation

- **Late Camera Shot.** Increment the Shoot revision, retain the earlier record, wait
  for affected Runs, write a new record, refresh projections, and reconsider Scout's
  current route.
- **Scene correction.** Preserve the prior grouping revision and recompute
  distinct-Scene claims.
- **Mine changed to Inspiration.** Remove the item from Photographer projections and
  rebuild affected current claims. Hiding it in the UI is insufficient.
- **Keeper removed.** Return the Shot to unknown and recompute taste-linked figures.
- **Intent corrected.** Supersede the scoped Intent. Do not rewrite an earlier model
  observation as if it knew the corrected Intent.
- **Analysis rerun.** Keep model and prompt provenance. Re-baseline incompatible
  Journey or Change comparisons.
- **Account deletion.** Idempotently remove authoritative records, projections,
  caches, credentials, and service access. Preserve user-owned Drive files.

For the first release, rebuilding affected projections is safer than incremental
subtraction. Optimise only after measuring archive cost.

## Android memory

Room owns the import outbox, stable assignments, Camera watermark, Capture Session
recovery, upload attempts, server ids, cached read models, and sync age. It is not a
second photographic truth.

Room is not currently encrypted. The device bearer token ciphertext is protected
separately with an Android Keystore key. Backup excludes credentials, import queues,
and cached server data. Revoke or deletion clears Room, image cache, WorkManager jobs,
and token ciphertext as already required by the Android release plan.

## Delivery gates

The detailed active sequence, timeboxes, commit boundaries, and fallback live in
[implementation order](implementation-order.md). This section keeps the memory-specific
gates.

### Gate 0: protect the submission

Before the Shoot slice, deploy the known-good baseline from a clean checkout after
explicit approval. Verify public health, authentication, one complete cloud Run, and
visible Google Cloud execution. Keep that revision available as the fallback.

Build the Shoot slice in a separate branch or worktree. Give it a 48-hour checkpoint.
Do not deploy a dirty checkout.

### Pre-deadline Shoot slice

1. Reuse `SCENE_GAP` to persist deterministic Scenes and add a configurable Shoot
   inactivity gap.
2. Persist Shoot state, revision, exact membership, and the Shoot terminal barrier.
3. Produce a deterministic Shoot Record from existing Runs and Analyses. Do not add a
   Shoot-level model reader yet.
4. Store Scout route, warrant, and rejected routes. At runtime, code exposes only
   implemented routes.
5. Show one useful Shoot receipt in Android or web.
6. Prove idempotency and one late-member revision through an integration test.
7. Deploy the accepted slice and record the continuous workflow.

The 48-hour slice passes only when a user can see the completed learning record. New
database rows without the receipt do not pass.

If the slice misses the checkpoint, keep the deployed per-Shot Reproduce path as the
honest fallback. Do not weaken the Run or Capture Session guarantees to force it in.

### Later target sequence

After submission:

1. Add the full Technique Map evidence axes and projection invalidation.
2. Complete Scene grouping and Experiment-cited source-role correction.
3. Add native Intent authoring and remove the legacy `User.constraints` fallback after migration.
4. Add the blind bounded Shoot reader only if deterministic synthesis leaves useful
   ambiguity.
5. Add Deconstruction from the settled Shoot Record.
6. Consider embeddings only after structured retrieval has measured gaps.

## Acceptance

The pre-deadline slice must prove:

1. Camera Shots across at least two capture-continuous Scenes become one Shoot without
   manual upload or tagging.
2. The Shoot Record contains exact members and every member Run outcome.
3. Repeating settlement produces no duplicate record or ActivityEvent.
4. A delayed committed Capture Session member may revise the Shoot but never changes
   the frozen Capture Session manifest.
5. A late Camera Shot creates exactly one newer Shoot Record revision.
6. Scout stores an eligible route, warrant, rejected routes, and input versions.
7. The client shows the newest Shoot receipt and does not present a superseded one as
   current.
8. The same workflow completes on the deployed Google Cloud revision.

The full contract later adds tests for Photographer correction, Inspiration
isolation, Listener provenance, Analysis-version invalidation, account deletion, and
bounded cross-user recall.

## Configuration still to settle

- Shoot inactivity gap on real Camera history.
- Exact correction UI for Scene membership and Mine/Inspiration.
- Which environmental conditions are reliable enough to count.
- Archive size that justifies cached per-Shoot projection folding.
- Whether embeddings ever earn their privacy, cost, and versioning burden.

These choices do not weaken the authority, barrier, correction, or intervention
rules above.
