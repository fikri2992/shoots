# Feature list

Product backlog derived from the decisions in [product decisions](product-decisions.md). Product rules were corrected from real-phone use on 2026-08-26. State describes the current repository, not a deployment claim.

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
| P0.1 | Tendency Profile | built | Pure code recomputes dimension counts, exploration, dwell, and blind spots from the complete readable archive: every Shot with an Analysis, no recency cap. Placement and framing are labelled model reads; other dimensions name their limits. |
| P0.2 | Positive-only Keeper signal | built | `kept_at` and absence are distinct. Keeper summaries are counts and shares among readable marked Keepers only; an unmarked Shot never enters a preference denominator. Sparse samples stay silent. |
| P0.3 | Technique Map | built | The domain retains `unobserved`, `observed`, and `recurring`; the read side lists only Techniques with actual Evidence, including sightings and corroborations. No empty catalogue slots, totals, locks, levels, prerequisites, or scores make it a curriculum. |
| P0.4 | Explore Experiment | partial | Scout may offer one cited Explore and atomically retain its open slot, but the target asks one question with two to four optional Variations. It records only explicitly associated Shots, Evidence, and Keeper signals. Explore has no Criteria, Verdict, pass, fail, ready, or shoot-again state. The photographer may pause or leave without failure. |
| P0.5 | Experiment Change check | partial | `Change` has three states, exact Baseline Shot ids, and a reason for Comparability. It honestly reports missing samples and version mismatch today. Done means each Experiment type selects its comparable explicit Shot set correctly instead of treating every later Shot as the Experiment result. No outcome claims causation. |
| P0.6 | Journey Update | built | A meaningful Profile difference creates one update from supplied figures. Live polling reloads Journey and Profile with the event that changed them. The first update does not compare against an empty history. |
| P0.7 | Claim provenance | built | Deterministic claims carry exact Shot ids, sample size, and `CALC_VERSION`. Model-read dimensions also carry Analyst model/prompt digests plus a per-Shot digest of the soft fields used, so re-analysis cannot masquerade as photographer Change. Journey prose records its writer separately. |
| P0.8 | Score removal | built | Overall and element scores are absent from `Analysis`, `TechniqueState`, migration output, API, client state, phone, reviewed file, Journey, Coach tools, Judge, and comparison selection. Legacy stored keys are dropped by `scripts/migrate_vocabulary.py`. |
| P0.9 | Vocabulary migration | built | Experiment, Finding, Technique Map, Change, Shot routes, Android names, prompts, events, schemas, and UI agree. Only the legacy `skills` Firestore collection key and `TechniqueState` class remain named migration targets. |
| P0.10 | Android Phone Source | built | After one honest permission choice, Android detects unseen items in the approved Camera media, uploads their original bytes and stable source references directly to Shoots storage, and schedules persistent work without opening a custom camera. Selected-media access remains manual. Full access enables automatic future imports. Exercised on the connected Xiaomi on 2026-08-26. |
| P0.11 | Evidence-first pulse | built | The pulse requires agreement of at least two and confidence at least 0.75, includes the Technique's proof, then one Finding with its reason. Keeper state reflects only the photographer's stored mark. |
| P0.12 | Agent desk | partial | One screen shows Shot arrival, measurements, panel reads, abstention or veto, Technique Map update, Experiment offer, type-specific result, and Change check in order. A missing Verdict is normal for Explore and Compare. |
| P0.13 | Real-agent quality gate | partial | The existing `backend/scripts/check_*.py` runs against a small labelled set with expected claims, allowed abstentions, false-positive counts, and saved results. |
| P0.14 | Cloud deployment | needed | The exact demo build runs on Google Cloud. Pub/Sub retries and idempotency are visible. The deployed revision and health check are recorded. |
| P0.15 | Submission architecture artifact | partial | The Mermaid source in [agents](agents.md) is updated to current vocabulary and exported as a readable diagram for the submission. |
| P0.16 | Four-minute continuous demo | needed | One continuous run shows a normal phone-camera Shot arriving without an upload button, idempotent background routing, Evidence, one supported Experiment, an explicit result Shot, a type-appropriate result, Change, Journey Update, external write-back, ActivityEvents, and Cloud proof. |
| P0.17 | Authenticated Phone Source | built | The existing revocable pairing token authenticates the four-day demo. The client has one configured service origin and survives restart. Native Google sign-in and removal of pairing remain release work. |
| P0.18 | Explicit Experiment participation | built | Only a Shot carrying the selected Experiment id enters its Record. Untagged Camera Shots still update the archive and are never judged by capture time. The direct-ingress integration check covers the boundary. |
| P0.19 | Background import lifecycle | built | Android shows permission mode, scanning/retrying state, last scan, last meaningful import, discovered, uploaded, known, and failed counts. One serialized WorkManager queue resumes after UI exit, uses exponential backoff and network constraints, and never deletes or edits local media. |

P0 passes only when this sentence is visibly true:

> Shoots remembered the photographer's work, found a recurring pattern, chose what to test, and verified what changed.

## P1: complete the longitudinal coach

| ID | Feature | State | Done when |
|---|---|---|---|
| P1.1 | Reproduce Experiment | partial | Scout selects a corroborated Keeper-associated Technique, fixes Criteria before any result, accepts only explicit submissions, and asks Judge for a Verdict about repeatability. Unmarked Shots remain unknown rather than negative examples. The remaining gate is one current-build end-to-end Reproduce run through the Phone Source. |
| P1.2 | Compare Experiment | needed | Shoots names one controlled decision and at least two Variations, records both explicit Shot sets, and asks one optional preference question. It produces no quality Verdict and the model does not choose the winner. |
| P1.3 | Journey comparison hero | needed | Journey pairs comparable earlier and recent Shots for one Technique and states only the measured difference plus a labelled model read. |
| P1.4 | Comparable-set rules | needed | Domain code defines which Shots may be compared by Experiment type, Technique, Scene conditions, and minimum sample. Incomparable sets return `insufficient evidence`. |
| P1.5 | Intent | needed | The photographer may state one short Intent without being prompted. It travels through the Live Scene Session and review, outranks a conflicting offered Experiment, and may mute a conflicting Finding or camera warning. Absence stays valid. |
| P1.6 | Structured learner memory | needed | Shoots remembers explicit constraints, preferred cadence, repeated Experiment responses, Intent, and Keeper signals with provenance. It never promotes inferred personality to user fact. |
| P1.7 | Bounded escalation | needed | A cheap read settles clear cases. Only consequential disagreement opens the full panel or asks for one more view. The escalation reason is stored. |
| P1.8 | Advice retirement | needed | Shoots retires one Experiment approach only after repeated comparable non-movement, while distinguishing no attempt from an attempted but unchanged result. |
| P1.9 | Scene grouping | needed | Capture continuity or explicit grouping puts related Shots into one Scene. Contact-sheet comparison can describe how the photographer worked it without forcing a score. |
| P1.10 | Graduation | later | When a Technique recurs reliably, the Companion stops teaching it and says so once. It may return only after contrary Evidence or a user request. |

## Later: camera Companion

The custom camera and Gemini Live work are removed from the four-day Taskmaster scope. CameraX and the unreachable viewfinder implementation are not shipped in the Android module; the historical decisions remain below as later product options.

| ID | Feature | State | Done when |
|---|---|---|---|
| C1 | Free camera with offered Experiment | later | The viewfinder opens free. One offered Experiment is available as a quiet chip or sheet with its reason. It affects nothing until the photographer explicitly enters it and never covers the Scene. |
| C2 | Fast local measurements | later | Zebras, guide, and pitch run locally. Scene count, framing variation, and useful light timing are added only as measured readouts. |
| C3 | Summonable Live Scene Session | partial | A server-side Gemini Live relay exists for fixed post-Shot web review. Done means Android sends 16 kHz microphone audio and low-rate Scene frames after an explicit summon, receives interruptible audio and transcripts, and carries Intent, the optional Experiment, measured facts, and relevant memory. |
| C4 | Silence policy | partial | No Scene media leaves the phone before explicit summon. The Companion does not speak first, stops when dismissed, and only the corroborated post-Analysis pulse may appear without a question. Rare opportunity interjections remain unbuilt. |
| C5 | Context relevance gate | needed | Weather, temperature, current light, and location facts appear only when they change the declared Intent, a selected Experiment, or the photographer's question. Every fact has a source and capture time. |
| C6 | Intent-first Scene direction | needed | The Companion asks what caught the photographer's eye when Intent would settle ambiguity, then offers one question, Variation, move, or refusal. It may inspect later frames and name one visible difference. It never claims to see an unobserved angle or treats the offered Experiment as authority. |
| C7 | Live guide tool | later | A Live tool call returns cell refs and a guide kind, domain code validates them, and Android renders one human guide, arrow, crop region, or plain direction. Internal cell references never appear. |
| C8 | Scene Probe fallback | partial | A no-audio fallback sends one temporary preview plus optional Intent and Experiment context, returns one question, Variation, move, or refusal, and stores no image or Shot. It no longer reports ready or checks Explore as pass or fail. |
| C9 | Explicit capture control | built | Only the photographer pressing the shutter creates a Shot. The Live model has no shutter tool, and suggestions, Live frames, and Scene Probes never enter the archive. |
| C10 | Explicit place memory | later | The photographer can save a useful place note. Shoots stores the note and its source, not a hidden movement trail. |
| C11 | Live media lifecycle | needed | Android exposes microphone permission and a clear listening state, sends audio and frames only during a summoned session, handles interruption and reconnect, and discards raw audio and Scene frames when the session ends. Durable transcript and memory remain provenance-labelled. |
| C12 | Real-device response budget | needed | On the acceptance phone, a ready Live Scene Session reaches first audio at or below 1.5 s median and 3 s p90 across at least 20 turns. The test separately reports cold connection, time to listening, capture to ready camera, upload acceptance, and capture to pulse. |

No C-row is required for the Taskmaster proof. Revisit this section only after the unattended phone-Shot to Journey loop is deployed and recorded.

## P2: photographic identity without overclaiming

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
| Director as a required pipeline stage | removed from core | No topic, subscription, automatic publish, or core UI remains. The optional legacy call conditionally attaches a clip only while the Experiment is open. |
| Constant viewfinder narration | forbid | It makes photography annoying and makes the agent the photographer. |
| Automatic Shot capture | forbid | The photographer controls the shutter. |
| Compulsory Experiment mode | remove | An offered Experiment is optional and never owns the free camera. |
| Implicit Experiment submission by capture time | remove | Only an explicit Experiment id associates a Shot. |
| Explore pass, fail, ready, or shoot-again language | remove | Explore asks what happens across Variations; it has no correct answer. |
| Pairing code or server-address setup in release | remove | Android and web are two clients of one Shoots identity and service origin. |
| Foreground wait for deep Analysis | remove | The panel works in the background while the camera remains usable. |
| Internal cell grid in UI | forbid | Cells are model addressing, not a photographic guide. |
| Hidden location history | forbid | Context does not justify surveillance. |
| Social feed, filters, editing, culling | out of scope | Mature neighbouring products already solve these jobs. |
| Streaks and skill-tree grinding | forbid | Retention should come from seeing personal Change, not obligation. |

## Recommended implementation order

1. Make Shot source identity independent of Drive and add idempotent direct ingress.
2. Replace the Android camera entry screen with the permission-aware Phone Source and persistent upload work.
3. Remove implicit Experiment submission and complete one honest type-specific result path.
4. Make the unattended run, terminal state, ActivityEvents, Change, Journey, and external write visible on the web.
5. Exercise the exact workflow on the physical phone, then deploy and record the Cloud proof.
6. Add native Google sign-in, Compare, structured memory, Scene grouping, and Live Companion work only after submission.
