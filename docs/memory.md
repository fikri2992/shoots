# Memory

> Reference only. This is the current-state audit used during the memory design
> comparison. New memory work follows the active
> [Shoots memory contract](final-memory.md).

Architecture note, 2026-08-26. What the system remembers, where, and what keeps
the record honest. Current storage is separated from the unbuilt Shoot-level
target; gaps are named at the end. Vocabulary as in the
[domain model](domain-model.md).

## The design rule

**Memory is the store, not the session.** Every model call starts amnesiac: a
fresh runner and session per attempt (`agents/runtime.py`), no conversational
memory between stages, no vector store, no embeddings. Continuity lives
entirely in Firestore (or `FileStore` locally), and code decides what any
agent gets to remember by handing it state. A retry never inherits half-written
state (principle 5 in [agents](agents.md)).

The inversion is deliberate: agents do not accumulate a memory of their own.
The system keeps a record the agents cannot corrupt, and the agents are shown
bounded slices of it.

## The layers, by trust

| Layer | What | Character |
|---|---|---|
| Raw archive | Shots and Analyses, no recency cap | Source of truth. Every layer below is re-derivable from it. |
| Recomputed on read | Tendency Profile (`services/profile.py`, `domain/tendency.py`) | Never stored as accumulating state: rebuilt from the complete readable archive on every build, stamped with `CALC_VERSION`. |
| Accumulated | `TechniqueState` — attempts, corroborations, Shot ids, `last_observed` | Written incrementally by the Cartographer; rebuildable from stored Analyses. Still lives under the legacy `skills` collection key (named migration target). |
| Episodic log | ActivityEvents and Runs | Append-only audit. The feed is a view of the store, not a second truth. |
| Human-authored | Keeper marks (positive only) and Intent | The only memory the photographer writes. Unmarked means *unknown*, never disliked; an unmarked Shot never enters a preference denominator (decision 45). |
| Model-written | `User.constraints` — missing gear and standing notes, extracted by the Listener from Coach transcripts | The only place a model writes to memory. |
| Frozen snapshots | Baseline, Capture Session manifest, Experiment Record, Journey Update provenance | Memory pinned at decision time so a later claim can be checked against exactly what was known. |

## Provenance-guarded comparison

The mechanism that makes "am I improving?" answerable without lying lives in
`services/journey.py`. Before diffing the current Profile against the one the
last Journey Update was written from, it requires:

- the same `CALC_VERSION` of the arithmetic;
- the previous Shot set to be a subset of the current one;
- every previously used per-Shot analysis digest to be unchanged;
- the same Analyst model and prompt versions.

If any condition fails, the update refuses to diff and re-baselines instead.
A re-analysis under a newer model, or a moved bucket edge, therefore cannot
masquerade as photographer Change. Every longitudinal claim carries
`Provenance`: exact Shot ids, sample size, calculation version, and the model
and prompt digests behind every model-read input (`entities.Provenance`,
`services/profile.provenance`).

The same discipline appears at smaller scales:

- `MIN_SHOTS_FOR_TENDENCY` and `MIN_KEEPERS_FOR_TASTE` keep sparse samples
  silent rather than confident.
- A Dimension names its own blind spot (`Dimension.blind`) instead of implying
  completeness, and labels model-read buckets as such.
- Reproduce Change is computed over an explicit frozen Shot set
  (`profile.build_for_shots`), so unrelated free Shots cannot move it.

## What each agent is allowed to remember

Agents never read the archive. Code assembles their slice:

- **Analyst lenses**: one Shot, disjoint measured facts per lens, no history.
- **Scout writer**: the chosen Technique, up to five recent critiques, the
  Technique state list, Constraints, grounded research notes.
- **Coach**: one Shot's briefing, its Analysis, the open Experiment, and
  Constraints ("do not ask again"); the `technique_map` tool answers from the
  store on demand.
- **Journey writer**: only the figures the diff already established.
- **Listener**: one transcript, output written back to Constraints.

## Target Shoot-level memory

This layer is documented but not implemented.

- Persisted `Scene` and `Shoot` membership lets the system remember how several
  situations were worked, not only what appeared in isolated Shots. Capture Session
  membership remains a separate explicit Experiment relation.
- A terminal `ShootRecord` freezes exact members, unreadable coverage, decision
  distributions, Variations, Technique Evidence, Keeper signals, provenance, and
  Scout's action or evidenced silence.
- Cartographer keeps Technique recurrence, distinct Scene coverage, explicit
  Reproduce attempts, Criteria outcomes, condition coverage, and positive Keeper
  counts as separate evidence axes. They never become one ability score.
- The bounded Shoot reader sees code-derived figures, member thumbnails, and only
  unresolved visual comparisons. It does not receive free access to the archive or
  infer Intent.
- Scout receives a bounded multi-scale slice plus domain-selected route eligibility.
  The Shoot Record stores the chosen route, warrant, rejected routes, input ids,
  policy version, and model/prompt provenance so later outcomes can revise advice.
- Manual reference imports are labelled Mine or Inspiration before longitudinal
  writes. Inspiration has separate records and may seed an Experiment, but cannot
  update the Photographer's Technique Map, Tendency Profile, Change, or Journey.
- A Deconstruction is derived from frozen Evidence. It is a shareable read model,
  not another source of truth or taste signal.

## Client-side memory

Android holds a Room database: immutable source assignments with the Camera
watermark, Capture Session recovery state, upload attempts and terminal
errors, server Shot ids, cached read models for offline Now/Shots/Journey, and
sync age. It is a cache and an outbox, never an authority; the backend record
wins.

## Known gaps

1. **No persisted Scene or Shoot layer.** Current memory jumps from one Shot to the
   whole archive. It cannot yet close a natural Camera period into a Shoot Record or
   show how the photographer worked several Scenes.
2. **O(archive) reads.** `profile.build` bulk-loads every Shot and Analysis on
   each build, and the tick triggers it. Acceptable now; linear cost with the
   archive, and no incremental path exists.
3. **No outcome memory in selection.** Scout skips the techniques of the last
   six Experiments but does not read Experiment Records when choosing — no
   memory of which offers led to Criteria met, abstention, or abandonment.
4. **Constraints is narrow and unmanaged.** Gear and free notes only; no
   expiry, no confidence, no correction path beyond the Listener writing again.
5. **Provenance is stored but not surfaced.** No screen shows the Shot ids and
   versions behind a Journey claim, so the integrity work is invisible.
6. **No source-role boundary for manual imports.** The current path can still treat a
   reference as the Photographer's Shot; Mine versus Inspiration is not persisted.
7. **Legacy naming.** `TechniqueState` under the `skills` collection key
   remains the last vocabulary migration target
   ([feature list](feature-list.md), P0.9).
