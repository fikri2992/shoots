# Feature list

Product backlog derived from the decisions in [product decisions](product-decisions.md). Product rules were corrected from real-phone use and deepened around the Shoot-level learning record on 2026-08-26. State describes the current repository, not a deployment claim.

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
| P0.3 | Technique Map | built | The projection rebuilds from authoritative records and keeps sightings, corroborated Shots, distinct Scenes/Shoots, explicit Reproduce results, Criteria-met results, abstentions, and positive Keeper Shots separate. Experiment history remains visible if current sightings retract. Condition coverage waits for reliable inputs. No totals, locks, levels, prerequisites, or scores make it a curriculum. |
| P0.4 | Explore Experiment | partial | Scout can issue corrected Explore from a supported Tendency Direction or explicit supported Technique. It offers three optional Variations, freezes the chosen Variation on each Capture Session, records ordered results and structured observations, and creates no Criteria or Verdict. Backend, Android, and web reads exist; cross-session Change, physical acceptance, and richer positive Keeper interpretation remain. |
| P0.5 | Experiment Change check | partial | `Change` has three states, exact Baseline Shot ids, and a reason for Comparability. Reproduce and Tendency-backed Explore compare only their Baseline plus explicit result Shots accumulated across Capture Sessions; unrelated free Shots cannot move them. Explicit-request Explore correctly has no invented Baseline. Shoot-level condition transfer and Compare set rules remain unbuilt. No outcome claims causation. |
| P0.6 | Journey Update | built | A meaningful Profile difference creates one update from supplied figures. Live polling reloads Journey and Profile with the event that changed them. The first update does not compare against an empty history. |
| P0.7 | Claim provenance | built | Deterministic claims carry exact Shot ids, sample size, and `CALC_VERSION`. Model-read dimensions also carry Analyst model/prompt digests plus a per-Shot digest of the soft fields used, so re-analysis cannot masquerade as photographer Change. Journey prose records its writer separately. |
| P0.8 | Score removal | built | Overall and element scores are absent from `Analysis`, `TechniqueState`, migration output, API, client state, phone, reviewed file, Journey, Coach tools, Judge, and comparison selection. Legacy stored keys are dropped by `scripts/migrate_vocabulary.py`. |
| P0.9 | Vocabulary migration | partial | Existing Experiment, Variation, Finding, Technique Map, Change, Shot, Scene, Shoot, Shoot Record, Inspiration, corrected Explore, and Deconstruction seams agree. The legacy `skills` Firestore collection key and `TechniqueState` class remain named migration targets. |
| P0.10 | Android Phone Source | partial | Room atomically freezes source assignments with its Camera watermark, WorkManager discovers and streams originals from `ContentResolver` without `readBytes()`, and selected-only access stays explicit. The upgraded release build compiles; current-build Xiaomi recovery and maximum-size acceptance remain. |
| P0.11 | Evidence-first Shot read | partial | Shot detail leads with corroborated Technique Evidence and separates model opinion from measured Findings. Done means one image-led read keeps the supported decision, scoped Finding or labelled observation, one next-capture Move, and one visible condition together; Reproduce Criteria remain separate. Current Android fragments these fields and hides useful Moves. |
| P0.12 | Agent desk | built | Every accepted Shot owns a durable Run with separate Ingest, Analyst, Cartographer, Scout, Judge, and Scribe outcomes. Now reads this stored state rather than inferring completion from event order; Shot detail exposes the same account. Retry, terminal media, abstention, free Shot judgment, and unavailable Drive output remain distinct. |
| P0.13 | Real-agent quality gate | partial | The existing `backend/scripts/check_*.py` runs against a small labelled set with expected claims, allowed abstentions, false-positive counts, and saved results. |
| P0.14 | Cloud deployment | needed | Audit on 2026-08-27 found gcloud authenticated with a configured project but no `shoots` Cloud Run service in `asia-southeast2`. Done means the exact approved candidate runs on Google Cloud, Pub/Sub retries and idempotency are visible, and the deployed revision and health check are recorded. See [release readiness](release-readiness.md). |
| P0.15 | Submission architecture artifact | partial | The Mermaid source in [agents](agents.md) is updated to current vocabulary and exported as a readable diagram for the submission. |
| P0.16 | Four-minute continuous demo | needed | One continuous run shows ordinary Camera media arriving without upload or Analyse controls, several Shots becoming Scenes and one settled Shoot Record, every member Run accounted for, Scout's warranted action or silence, one explicit Experiment result, Change, Journey, Deconstruction attempt, ActivityEvents, and visible Google Cloud proof. |
| P0.17 | Authenticated Phone Source | partial | Credential Manager obtains a nonce-bound Google ID token; the backend verifies signature, issuer, audience, expiry, nonce, and verified email before issuing a revocable 30-day encrypted device session. Pairing endpoints remain only for old APKs. OAuth/Firebase credentials and physical sign-in acceptance remain. |
| P0.18 | Explicit Experiment participation | built | A committed Capture Session manifest is the authority for Reproduce membership and outranks client Experiment input. Free Shots never enter Reproduce. Capture time never implies participation. Legacy single-Shot submissions retain their behavior. |
| P0.19 | Background import lifecycle | partial | Room owns immutable assignments, session recovery, attempts, terminal errors, server Shot ids, cache, and sync age. WorkManager orders discovery, manifest commit, streaming upload, then snapshot refresh. Emulator acceptance proves a real authenticated WorkManager HTTP refresh into Room and offline Shoot receipt recovery after database reopen. Current-build physical process-death, permission-loss, and network-loss acceptance remain. |
| P0.20 | Durable unattended Run | built | One Run is created before the first publish. Independent stages settle their own outcomes idempotently, and an atomic barrier closes the Run only after every required stage settles. A deterministic completion event is replay-safe. Android shows the latest backend Run state. |
| P0.21 | Batch Capture Session | built | Reproduce reserves one session, freezes an ordered manifest, judges every accepted member including abstentions and terminal media, applies `judge all, any met`, chooses a deterministic representative, waits for every Run, then attempts one FCM summary. |
| P0.22 | Native offline read surfaces | partial | Navigation Compose exposes Now, paginated Shots, Shot detail, Journey, and Settings from Room-backed flows. The typed Shoot and Shoot Record now travel inside the existing ETag snapshot and cached resource, so the newest receipt remains readable offline without a second Room truth. Full physical interaction and accessibility acceptance remain. |
| P0.23 | Native account and Drive controls | partial | Drive authority is separate from identity; Android can connect with an offline code, disconnect while preserving user files, revoke its device, or request idempotent account cleanup after fresh Google confirmation. Configured-account acceptance remains. |
| P0.24 | Decision-led mobile IA | partial | Bottom navigation is Now, Shots, Experiments, and Journey; Settings is secondary and progressive. Now prioritizes active Capture Session, processing Shoot, newest current Shoot Record, then Camera; a superseded receipt cannot outrank its pending revision, and per-Shot critique is only a legacy fallback. Emulator tests cover the focal order, cached DTO, and Keeper-backed Experiment action. Physical 390 px and accessibility acceptance remain. |
| P0.25 | Evidence-grounded Shot annotation | partial | Clean, Finding, Try, and Guide layers draw current regions, placement, horizons, tested crops, Moves, and blown-highlight masks. Done means ambiguous proxies are narrowed or removed, camera and subject Moves outrank crop salvage for next-capture teaching, one observable check accompanies the Move, and one layer speaks at a time. |
| P0.26 | Daily and on-demand Experiments | partial | Shoot Scout may offer supported Reproduce or Explore, and Android can request either on demand. Reproduce keeps its Keeper Evidence gate; Explore requires a supported Tendency Direction or explicit Technique. Both preserve the one-open slot, start typed Capture Sessions, and keep previous Experiment Records. Explicit Android Technique selection and configured-device acceptance remain. |
| P0.27 | Purposeful mobile interaction | built | Proportional 24 dp vector icons share one optical grid; bottom and segmented navigation expose selected semantics; route and Journey changes slide and fade directionally; Shot layers crossfade; clickable cards show ripple and press scale; disclosure chevrons rotate; and every transition stays between 90 and 220 ms while respecting the device animation scale. |
| P0.28 | Legacy Experiment safety | built | Android starts Reproduce only with an exact Keeper reference and visible Criteria, and Explore only with current Variations. Older or incomplete records are labelled as legacy, cannot reserve a Capture Session, and may be replaced only through an explicit supported Scout request. Stored `skipped` reads as `left`. Emulator integration coverage proves refusal and the current typed paths. |
| P0.29 | Honest automatic Phone Source time | built | Automatic Phone Source Shots display the MediaStore instant frozen in their source reference instead of shifting a timezone-less EXIF clock. The observed Camera Shot now reads 15:39 rather than 22:39. Selected and Drive timezone ambiguity remains separate work. |
| P0.30 | Persisted Scene and Shoot lifecycle | partial | Backend capture continuity now assigns Android Shots to persisted Scenes and a natural Shoot, preserves capture order under replay and out-of-order arrival, and keeps Capture Session membership orthogonal. Explicit Photographer regrouping, Firestore-emulator concurrency, and client reads remain. |
| P0.31 | Shoot-level terminal workflow | partial | Backend scheduled closure waits for every current-revision Run, accepts completed and terminal outcomes, settles one replay-safe Shoot Record and ActivityEvent, recovers interrupted closing work, and versions late media without rewriting history. Its Scribe attempt records a replay-safe Deconstruction id and outcome without blocking settlement. The current Shoot and newest Record ship in the cached Android snapshot. Cloud/device proof remains. |
| P0.32 | Shoot synthesis and evidence of control | partial | Pure deterministic code records exact Scene and Shot coverage; measured and model-read placement, framing, light, key, palette, and orientation distributions; corroborated Technique figures; Keeper ids; blind spots; and versioned provenance. Android renders the short repeated/varied receipt and expandable Evidence without a score or improvement claim. Focal evidence, bounded unresolved visual comparison if proven necessary, and longitudinal control figures remain. See [learning path](learning-path.md). |
| P0.33 | Mine versus Inspiration authority | partial | Automatic Camera media stays Mine. New Android picker and web archive imports ask Mine or Inspiration; Inspiration has a separate current record, receives no Run or longitudinal writes, appears separately in both clients, and a free manual Shot can move across the boundary with projection rebuild and retained history. Experiment-cited and Camera-source correction, Scene regrouping, and bounded Inspiration study remain deliberately refused or unbuilt. |
| P0.34 | Typed Scout learning choice | built | Each settled Shoot stores one code-gated `explain`, consequential `ask`, supported-Tendency `explore`, Keeper-backed `reproduce`, or `silence` decision with exact warrants, rejected routes, input and projection versions, execution result, attempt state, and a replay-safe ActivityEvent. Ask options come only from corroborated Shoot Techniques; one answer stores Shoot-scoped Intent and may deterministically open Explore. Every route now receives an Intervention Record. |
| P0.35 | Deconstruction draft | partial | Scribe prepares one evidence-bound draft at Shoot settlement, requires an explicit eligible Keeper cover, and deterministically renders four to seven 1080×1350 pages from Shoot or Experiment Evidence. Android caches the authenticated JPEGs and invokes one multi-image share sheet; web audits the same record. It never invents a cover, shows scores or cells, or posts. MediaStore export, caption editing, configured-device sharing, automatic Experiment preparation, and optional Drive output remain. |
| P0.36 | Intervention memory and adaptation | built | One replay-safe Intervention Record projects each immutable Shoot Scout decision through offered, entered, left, and completed states. It keeps explicit results, Criteria-met counts, abstentions, Variations, Comparability, and Change separate. Capture Session reservation and Experiment closure refresh it. Two completed comparable unchanged outcomes may deprioritize the same Technique only for later automatic routing; explicit Photographer requests still win. Android and web show the latest outcome. |

P0 passes only when this sentence is visibly true:

> Shoots turned an ordinary Camera period into a settled learning record, chose the kind of help the Evidence supported, checked what happened next, and accounted for every stage.

## P1: complete the longitudinal coach

| ID | Feature | State | Done when |
|---|---|---|---|
| P1.1 | Reproduce Experiment | partial | Scout selects a corroborated Keeper-associated Technique, freezes one exact Keeper reference and Criteria, stores every explicit result Shot including abstentions, and asks Judge for a Verdict about repeatability. Journey shows the exact reference and latest result. The remaining gate is one current-build end-to-end Reproduce run through the physical Phone Source. |
| P1.2 | Compare Experiment | needed | Shoots names one controlled decision and at least two Variations, records both explicit Shot sets, and asks one optional preference question. It produces no quality Verdict and the model does not choose the winner. |
| P1.3 | Journey comparison hero | built | Journey pairs the exact Keeper frozen by Reproduce with its latest explicit result. It states the declared Criteria outcome or abstention and explicitly refuses to call the result better. |
| P1.4 | Comparable-set rules | partial | Reproduce now owns one fixed Keeper reference and explicit result set. Baseline Change already refuses incompatible samples, but Explore and Compare set rules remain unbuilt. |
| P1.5 | Intent | partial | Intent stays absent by default. Scout asks one short native question only when at least two corroborated Shoot Techniques make its next route ambiguous. One tap writes attributable Shoot-scoped Intent; “I was just shooting” creates no Experiment, while a supported Technique may open corrected Explore. Intent-aware Shot review, Finding excuses, and later Live use remain. |
| P1.6 | Structured learner memory | partial | Shoot/Scene records, independent Technique Map axes, invalidation, Keepers, Experiment and Intervention Records, Mine/Inspiration, scoped Photographer Signals, and native contextual Intent authoring now exist. Signals are idempotent, attributable, correctable, expiry-aware, and returned through bounded role recall; Listener quotes are checked and Live announces exact writes. Remaining: legacy-constraint migration and explicit grouping correction. |
| P1.7 | Bounded escalation | needed | A cheap read settles clear cases. Only consequential disagreement opens the full panel or asks for one more view. The escalation reason is stored. |
| P1.8 | Advice retirement | needed | Shoots retires one Experiment approach only after repeated comparable non-movement, while distinguishing no attempt from an attempted but unchanged result. |
| P1.9 | Scene grouping refinement | later | P0.30 owns the first durable capture-continuity grouping. Later refinement adds explicit regrouping, richer place continuity where the Photographer permits it, and contact-sheet correction without using visual similarity as event truth. |
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
| P2.3 | Inspiration discovery | later | P0.33 owns the Mine/Inspiration authority boundary. Later work may find a relevant sourced reference or local fact for an Experiment; it remains optional and never becomes generated filler or Photographer Evidence. |
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
| Several generic grids over one Shot | replace | Show only one evidence-linked structure at a time; post-hoc grid fitting is not proof of composition. |
| One critique paragraph per Shot | replace | Shot detail remains evidence; a settled Shoot produces the primary learning reflection. |
| Manual reference imported as Photographer Shot | forbid | Inspiration cannot teach the system another photographer's work as the user's Technique, Tendency, Keeper, or Change. |
| Automatic social posting | forbid | Shoots prepares a Deconstruction draft; the photographer chooses the cover, caption, and publication. |
| Hidden location history | forbid | Context does not justify surveillance. |
| Social feed, filters, editing, culling | out of scope | Mature neighbouring products already solve these jobs. |
| Streaks and skill-tree grinding | forbid | Retention should come from seeing personal Change, not obligation. |

## Recommended implementation order

The active dependency order, 48-hour keep decision, fallback, commit sequence, and
post-submission work are maintained in [implementation order](implementation-order.md).

In short: verify a deployed fallback, add Scene/Shoot records and the Shoot barrier,
synthesize one deterministic Shoot Record, store Scout's typed decision, show one
mobile receipt, apply the 48-hour acceptance gate, then deploy the exact accepted SHA
and stop feature work for the submission.
