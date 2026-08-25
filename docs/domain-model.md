# Shoots domain model



The ubiquitous language. If a word is not here, it is not a thing.

The product language below was locked on 2026-08-25. Existing code and stored data still contain the legacy identifiers `Quest`, `Fault`, `SkillState`, `quest.*`, and a 1 to 10 score. They are migration debt tracked in [feature list](feature-list.md), not approved names for new APIs, prompts, or UI copy. The numbered history retains some legacy identifiers where it describes the implementation that existed at the time. Decisions 41 through 48 supersede that language wherever they conflict.



## The loop



Shoots is an event-driven control loop, the shape that won 2026 agentic hackathons (see the Visual QA research doc: watch, diagnose, act in the system of record, verify, audit trail, human gate).



```

Drive folder or camera receives a Shot      (watch)

  → Ingest    reads the file, EXIF, Tone, Motion, grid, and video frames

  → Analyst   produces measured and visual Evidence, Findings, and a reading     (diagnose)

  → Cartographer  updates the Technique Map and Tendency Profile                 (remember)

  → Scout     selects one personal Experiment and freezes its baseline           (plan)

  → Companion adapts the active Experiment to the current Scene when useful      (assist)

  → Judge     checks the result against declared Criteria                        (verify)

  → Cartographer recomputes comparable behaviour; Journey records the Change     (learn)

  every step  → ActivityEvent                                                    (audit trail)

  the user    → shoots; Keeper and Intent are optional                           (human signal)

```



## Nouns



**Shot.** One photo or video file from the user's Drive folder. Identified by Drive file id; a redelivery of the same file id is a no-op. Carries EXIF (photo) or VideoMeta (video), the Tone measured off the frame, the Motion measured across a clip, the grid spec the Analyst saw, and blob paths for the original, the gridded frame, the contact sheet and a thumbnail.



**Technique.** One entry in `domain/taxonomy.py`. Has a family (composition, light, exposure, lens, color, video), a level 1-3, a cue (what the Analyst looks for), optional hard EXIF bounds, and prerequisites. The catalogue is finite on purpose. ~65 entries.



**Evidence.** The Analyst's claim that a shot demonstrates a technique, with a confidence 0-1 and the cells where it is visible. Hard evidence is EXIF; soft evidence is vision. Soft evidence below `judge_min_confidence` (0.6) does not count.



**Finding.** One checkable issue or observation about a Shot. A measured Finding carries the figure and rule that produced it. A model Finding stays labelled as opinion. A Finding may be excused by corroborated Technique Evidence or explicit Intent. The legacy implementation calls measured Findings `Fault`.

**Analysis.** Everything recorded about one Shot: Evidence, Findings, composition read, measured facts, model observations, and critique. The legacy schema still carries a 1 to 10 score pending removal. The score is model opinion and may not drive the Technique Map, Journey, Keeper, or any claim of Change.



**Move.** A composition suggestion: "move *what* from cells X to cells Y because Z". The dashboard draws it as an arrow over the original. Cells, never pixels.



**Tone.** What the pixels say about colour and light, measured at ingest in `imaging/tone.py`: colour temperature, cast, saturation, the dominant hues and the angle between them, the warm and cool shares, luminance percentiles and clipping. Exif for everything the camera did not write down — every real file reports auto white balance, so the camera records that it chose and never what it chose. `domain/tone.py` is the arithmetic on top, the way `domain/exposure.py` sits on Exif.

**Motion.** How the camera itself travelled, measured between consecutive frames in `imaging/motion.py` and read in `domain/motion.py`. Signed drift in frame widths, the mean and largest step, direction reversals and the share of steps that did not move.

**Technique Map.** One longitudinal record per photographer and Technique. Its user-facing states are `unobserved`, `observed`, and `recurring`. Corroborated Evidence moves the state. Time alone does not turn a Technique into a flaw, and model scores move nothing. The legacy implementation stores this as `SkillState` with `unexplored`, `attempted`, `practiced`, `solid`, and `rusty` states.



**Experiment.** One bounded thing to try, selected by Scout from the photographer's record. It has a type, reason, frozen baseline, Criteria, optional reference, results, Verdicts, and a post-Experiment Change. Its type is `explore`, `reproduce`, or `compare`. Status is `open`, `completed`, `skipped`, or `expired`. A failed result does not close an Experiment unless its design says one attempt is sufficient. The legacy implementation calls this `Quest` and currently supports only the Explore shape.



**Criteria.** What counts as done, in two halves. `exif`: an ExifRule with bounds the Judge checks mechanically. `vision`: technique ids the Analyst must have tagged at or above threshold. `text`: the plain-language version the user reads.



**Verdict.** The Judge's result for one submitted Shot against one Experiment's declared Criteria. It records each check, relevant confidence, abstention, and feedback. It says whether the Criteria were met, never whether the Shot is good or the photographer improved.



**ActivityEvent.** One durable record per agent step. The live feed (SSE) is a view of these; Firestore is the truth.

**Scene.** One photographic situation at one place and time containing one or more Shots. Scene membership must come from capture continuity or explicit grouping, not visual similarity alone.

**Tendency.** A neutral repeated pattern across Shots. It describes a distribution or low-variance dimension and carries its Shot set, count, blind spots, and calculation version. It does not imply a problem or Intent.

**Keeper.** A Shot the photographer positively marks as valued. Unmarked means unknown, not rejected. A Keeper is the only direct taste signal in v1 and never changes Criteria or Technique Map state.

**Change.** A measured difference between comparable earlier and later behaviour. Change may be `changed`, `unchanged`, or `insufficient evidence`. It is not automatically improvement and does not prove an Experiment caused it.

**Experiment Record.** The durable record of one Experiment's reason, type, frozen baseline, Criteria, results, Verdicts, and Change. It is the checkable artifact left by the Scout and Judge loop.

**Journey Update.** The evidence-backed longitudinal conclusion written when the photographer's record meaningfully changes. Each clause cites measured Evidence, corroboration, or an explicit photographer signal.

**Intent.** The photographer's optional statement of what they are trying to make in a Shot, Scene, or Experiment. Inferred purpose is model opinion. Explicit Intent may excuse a conflicting Finding or local camera warning.

**Companion.** The quiet camera-side agent. It adapts the active Experiment to the Scene, answers when summoned, and may offer a rare high-value interjection. It is not the photographer and does not control the shutter.

**Scene Probe.** A temporary low-resolution capture used to inspect or compare the current Scene. It is discarded unless the photographer explicitly saves it as a Shot. It never enters the Technique Map, Tendency Profile, or Journey by itself.

**Inspiration.** Optional sourced reference material attached to an Experiment. It may help the photographer explore, but it is not an Experiment, an artifact of completed work, or a reason to generate media by default.



## Agents



| Agent | Trigger | Reads | Writes | Model |

|---|---|---|---|---|

| Ingest | `media.new` | Drive file or camera upload | Shot, blobs, Tone, Motion | none (ffmpeg, Pillow, numpy) |

| Analyst | `media.ingested` | gridded frame, clean frame, EXIF | Analysis with voted Evidence, Findings, observations, and critique | gemini-3.7-flash × 4: three parallel lenses then a Synthesizer |

| Cartographer | `media.analyzed` | Analysis, Technique Map, Tendency Profile | Technique Map, Tendency Profile, Change, Journey trigger | none (pure) |

| Judge | Experiment result analysed | Analysis, Experiment | Verdict and Experiment result state | gemini-3.7-flash for feedback only; checks are pure |

| Scout | first profile, scheduled tick, completed Experiment | Technique Map, Tendency Profile, Keeper signals, constraints | one Experiment with reason, baseline, Criteria, and delivery time | gemini-3.7-flash + Search grounding where a reference is useful |

| Director | legacy `quest.issued` | legacy Quest and Technique | optional generated reference clip | gemini-3.7-flash, veo-3.1-fast; outside the core product |

| Scribe | `media.judged` | annotated frame, Analysis, Verdict | reviewed copy in the user's Drive | none (Pillow) |

| Coach | Companion summon | current Scene preview, active Experiment, measurements, explicit memory | one move, one question, or silence; ActivityEvent transcript | gemini-live-2.5-flash-native-audio; gemini-3.7-flash Listener |

| Scheduler | Cloud Scheduler | photographers and open Experiments | renews Drive channels, expires Experiments, triggers Scout | none |



Cartographer and Judge state changes are pure code. The Technique Map, Criteria checks, and Change records must be reproducible from stored data. A model cannot pass its own Experiment or call its suggestion an improvement.



## Decisions



1. **Drive is the only input.** No upload endpoint in v1. The PWA's "Shoot" button uploads to the Drive folder through the Drive API, so phone and desktop use the same path and the watch channel is the only trigger.

2. **Finite taxonomy.** The model tags from a list. Unknown ids are dropped and logged.

3. **Cells, not pixels.** Reused from Visual QA: the grid adapts to aspect ratio (~64 cells), refs are chess-style, `domain/grid.py` does all conversion.

4. **Hard evidence first.** The Judge checks EXIF bounds before looking at vision tags. A quest whose technique has EXIF bounds cannot pass on vision alone when EXIF is present and fails the bounds.

5. **Photo first, video supported.** Videos become a contact sheet (scene-cut frames, up to 12, tiled 4 wide) plus ffprobe metadata. Video techniques are judged on the sheet. No per-frame analysis in v1.

6. **One quest a day, one open at a time.** Anything added to the folder while a quest is open is an attempt at it (or a shot tagged with the quest id by the Shoot button). A failed attempt appends a verdict with feedback and the quest stays open until its TTL; the first passing verdict closes it and the Scout issues the next. Skipping is the human gate and is logged, never deleted.

7. **Pipeline stages are transport-agnostic.** The same stage functions run chained in-process locally and behind Pub/Sub push subscriptions on Cloud Run. Every subscription has a dead-letter topic; every stage is idempotent on shot id.

8. **Secrets stay out of Firestore.** The Drive refresh token lives in Secret Manager (prod) or `.blobs/tokens` (local). Firestore holds the user's Drive folder id and page token only.

9. **Gemini 3.7 via the Vertex global endpoint; Veo and Gemini Live via us-central1.** Verified per model on 2026-08-23; each has its own `*_location` setting. App infrastructure in asia-southeast2.

10. **Voice review is a relay, not a browser-side Live client.** The phone opens one WebSocket to this service per shot; the service opens the Gemini Live session with the gridded frame and the Analyst's read as the first turn, and relays 16 kHz PCM in and 24 kHz PCM out, plus transcripts. The browser never holds a Google credential and the briefing never leaves the server. The session ends as one ActivityEvent with the transcript, so the feed shows what was discussed.

11. **A service account reads the folder; OAuth stays non-sensitive.** The shared consent screen is in production and unverified, and `drive.readonly` is a restricted scope, so the app never asks for it. On Connect, the app creates the user's `Shoots` folder with `drive.file` (non-sensitive) and shares it with `shoots-ingest@…iam.gserviceaccount.com` through the Drive API. The service account watches, lists and downloads whatever lands in that folder, whoever uploaded it. Sync is a folder listing keyed by Drive file id; a `files.watch` channel on the folder (Drive reports child changes on it) calls `/drive/notify`, the Scheduler renews channels before their one-day cap, and `/tasks/sync` polls as the fallback. Local dev has no public URL, so it has no channel and polls; the sync code is the same.

12. **Quest delivery is Web Push to the PWA, not email.** Gmail send is a restricted scope with the same verification problem. Push lands on the phone, which is where the quest is acted on anyway.

13. **The reference clip is a nicety the quest never waits on.** The Scout publishes `quest.issued` and returns; the Director has Gemini write the Veo prompt, Veo renders 6 s vertical with its own ambient sound, and `quest.reference_clip` is set when it lands, about a minute later. Veo failing dead-letters and the quest simply has no clip; a quest closed meanwhile gets no clip. Lyria was tried and cut: a music bed under a reference clip decorated the bonus list, not the photographer.

14. **One stage, one push subscription.** Handlers register under a stage name; `/pubsub/<stage>` delivers to exactly that handler. Cartographer and Judge both read `media.analyzed` but retry and dead-letter independently, and a replay from a DLQ re-runs one stage, not the fan-out.

15. **The review goes back where the photo came from.** After the Judge, the Scribe writes `Shoots/Reviewed/<name> — <score> of 10.jpg` into the user's Drive as the user (`drive.file`): the frame with the composition read drawn on it and the critique, moves and verdict as a caption band and as the file description. It shows up in the Drive and Files apps on the phone and can be shared as-is; the app is optional for reading a review. The Judge therefore always publishes `media.judged`, verdict or not, so the first write already carries the outcome.

16. **The Scout decides when, not just what.** Each technique has a light window (`taxonomy.LIGHT`); the user's location is the GPS of their own newest frame, never asked for. The quest is stored at issue time with `deliver_at` and a reason ("fifty minutes before sunset where you last shot"); the push goes out on the five-minute tick when that moment comes. Solar times are NOAA's equations in `domain/sun.py`, UTC throughout; the phone formats them.

17. **Talking to the Coach is how the user steers the planner.** There is no settings form. After a voice session the Listener extracts standing facts ("no tripod", "shoots at lunch near the office") into `User.constraints`; the Scout's ranking drops techniques whose `taxonomy.NEEDS` gear is missing and its brief is written inside the notes. The Coach is briefed with the same facts so it never asks twice.

18. **A frame is read by a panel, scored by a rubric, decided by code.** The Analyst is an ADK `SequentialAgent`: a `ParallelAgent` runs three lenses that differ in instruction *and* input (Technician: EXIF + gridded frame; Composer: gridded frame only; Storyteller: clean frame only), then a Synthesizer writes the critique from their readings. What the frame shows is a vote in `domain/panel.py`: two lenses, or the owning lens at ≥ 0.75; confidence is the mean over those who agreed, and the agreement count travels with the evidence to the Judge, the feed and the phone. Each lens reads in Feldman's order (describe by cell, analyse, interpret, judge last) and rates only its own elements of a rubric derived from PPA's *12 Elements of a Merit Image* against anchored descriptors; the overall score is the rubric's weighted mean computed in code. A panel below quorum is not a reading; the stage retries. Sources and the reasoning are in `docs/technique-evidence.md`, as are the citations behind every EXIF bound.

19. **The Composer's crop must beat the original on the pixels.** `suggested_crop_cells` is an opinion until `agents/crop.py` renders the crop, has a rater score original and crop as finished frames, and keeps it only if composition rose; the rater may propose one alternative, so at most two rounds. A crop that failed is cleared, so neither the overlay nor the Drive review ever draws an untested suggestion. The loop is Python, not an ADK `LoopAgent`, and that is a choice rather than a constraint: this note used to say an `LlmAgent` with an `output_schema` cannot take tools, which ADK 2.7.1 contradicts outright — tools are exposed during the thought loop and structure is enforced only on the final output. What stands is that injecting a freshly rendered image mid-invocation needs a `before_model_callback` and that path is untested, `LoopAgent` is itself deprecated in 2.7.1, and a bounded two-round Python loop is testable with a number.

20. **Arithmetic before opinion.** `domain/exposure.py` derives EV, the handheld limit, freeze thresholds and the 500-rule ceiling from EXIF and hands them to the Technician and the Judge as facts ("1/40 s is slower than the 1/46 s handheld limit"). The lens is told these are arithmetic, not impressions.

21. **The bar is your own previous best.** The Judge's feedback gets the photographer's highest-scoring earlier shot for the technique (from `SkillState.shot_ids`) as a second image with its observations, and must say in one sentence what improved and what was lost. `Verdict.compared_with` records which shot.

22. **Pre-flight before upload.** For a quest, the Shoot button sends a 640 px preview to a one-call check of the quest's SEEN criteria (`agents/preflight.py`, ~8 s) and shows "shoot again" with a concrete fix before the frame is sent. Camera settings are never guessed from a preview; that stays with the Judge.

23. **Evidence on demand for video.** The Composer may name two timestamps; `agents/scrub.py` pulls those exact frames with ffmpeg, grids them, and votes as a fourth lens on camera-move techniques only. It rates no elements.

24. **The Coach acts.** The Live session carries three function declarations: `issue_quest(technique_id, reason)`, `remember(missing_gear, notes)` and `skill_map()`. Function calls are answered by `services/coach.py` inside the relay and echoed to the phone as "→" lines; a quest issued by voice is an ordinary quest (Scout, Director, timing). The Listener remains as the post-session fallback. Cost: the Scout's research runs inside the tool call, so the photographer waits ~40 s for the answer; a "working on it" spoken filler is the obvious next step.

25. **One screen, one state, one decision.** The app's home is `Now`, and it renders exactly one of connect / seed / reading / quest / idle — never a dashboard of all of them. The skill map and the audit trail moved to `Journey`, the grid to `Frames`; a phone gets three tabs and no floating shutter, because a global shutter would upload outside a quest and so skip pre-flight, which is the only moment a reshoot is still free. Layout follows from that: media full-bleed, one hero line, criteria in plain sentences, the action pinned in the thumb zone, and everything that explains rather than instructs behind a disclosure row. Three type weights (hero, body, meta) and one accent — amber, meaning "the agent decided this" — replace the seven-colour chip vocabulary.

26. **The first quest is not asked for.** A new account connects Drive, hands over three or four photos it already has (multi-select, straight into the same Drive folder — the Drive app is never opened), and the pipeline narrates itself while they are read. When the Cartographer updates the map, `scout.issue_first` fires if the user has never had a quest: within about ninety seconds of signing in, the agent has read the photographer's work and set them a task. After that only the daily tick and `quest.closed` issue quests, so it can never loop.

27. **The Coach is text-first.** The session opens without the microphone: a WebSocket, the frame, and a text box that works from the first second, because a photographer in a gallery, on a street, or on a laptop without a mic still deserves an answer. The mic is one tap away. A question the user clicked ("why did this not pass") is sent as the opening turn, but only after the model's briefing turn completes — a second turn on top of a generating one is what produced the 1006 abnormal closures. One dropped session is picked up again silently, with the last question replayed.

28. **Two grids, two readers.** The cell mesh (`A1`..`G9`) is an addressing system: it exists so a lens can point at the bamboo pole and so code can map that back to pixels. It is not a compositional idea, and it never reaches the photographer at all: not as a mesh on the frame, and not as a coordinate in a sentence. The Synthesizer, the Judge and the Coach are told to place things in words ("the pole across the top"), and anything already written with cells is rewritten on the way to the screen and into the Drive review (`cells.plain`, `Grid.place`). Showing the machinery was itself the mistake: the reader has no grid to check it against. What the photographer sees is a *guide*: thirds, the phi grid, the diagonal method or a centre axis, chosen from the technique the panel agreed the frame is built on (`domain/guides.py`), with the subject's own centre drawn on it so the frame can be seen sitting on the guide or missing it. The readout ("sitting on the thirds point", "19% of the frame off") is withheld unless the read is finer than half a cell, which is why the Composer now also returns `subject_x`/`subject_y` in frame units — kept only when the point falls inside the cells the same lens named.

29. **A crop is not a vector, and a viewpoint is not a direction.** Every change carries a `kind`. `move` is a repositioning inside the frame and is the only thing drawn as an arrow; `crop` names the region that survives and is drawn by dimming what leaves; `camera` ("kneel to her eye level") is written as words and gets no mark at all, because a change of viewpoint has no honest representation on a flat image. A crop asked for as a move is routed into `suggested_crop_cells`, where the crop loop has to prove it on the pixels before anyone sees it. One instruction is drawn at a time, over a quiet guide and thin findings; the overlay used to draw four marks at equal weight and an arrow from a strip of sky to the middle of the frame.

30. **Colour, light and motion are measured, or they are not evidence.** Composition arrived with a grid, a guide, a subject point, a tested crop and four faults; colour and light arrived as adjectives, and they fire nearly as often — measured over the corpus, 0.94 and 1.06 sightings a shot against exposure's 0.94. A lens saying "the palette is cool" is an opinion the reader cannot check. So `imaging/tone.py` measures colour temperature, cast, saturation, hue relationship, key, tonal range and clipping off the pixels at ingest, and `imaging/motion.py` phase-correlates a dense low-resolution strip to measure how far the framing actually travelled. Camera EXIF cannot stand in for either: every real file reports auto white balance, and the contact sheet's tiles are seconds apart, which is why twelve video techniques were firing at 0.11 a shot. Two new faults follow the same rule as the other four — `blown_highlights` and `colour_cast`, each carrying its figure and each excused by the technique the panel agreed on, so a vivid sunset is not accused of a tungsten cast. Colour temperature is withheld when the frame sits too far off the Planckian locus for the number to mean anything: a frame of pure red is a red object, not 2655 K light.

31. **Each lens is told only what it owns; the Synthesizer is told everything.** The measurements are routed by `panel.OWNER_BY_FAMILY` — the Technician gets the exposure arithmetic and where the scale ran out, the Composer the temperature, the key and where the sun was, the Storyteller the palette and the hue relationship — and the three sets are disjoint, asserted by a test. Handing all three lenses the same numbers would buy anchored claims at the cost of the only thing a panel is for, three readings whose errors are not shared. The Synthesizer is the exception, because it writes the one paragraph the photographer is guaranteed to read: it gets every measured fact and must quote the one that carries the point it is already making. A critique that cannot cite the arithmetic is a critique any model could have written from the picture alone, which is what the Synthesizer's old contract — "you do not restate them, you write the words" — guaranteed it would be. Golden hour and blue hour are the two light techniques the sun can settle, so `domain/tone.py` places the frame against NOAA's sunrise and sunset from the EXIF time and GPS and the Composer is told; a claim of golden light three hours from the horizon is now disprovable.

32. **What translation cannot see is never claimed.** `domain/motion.py` settles `static_tripod`, `pan`, `tilt` and `whip_pan`, and says so; `orbit`, `push_in`, `tracking` and `rack_focus` turn on rotation, scale or focus, which phase correlation does not measure, so nothing corroborates or contradicts them and the lenses keep the last word. The measurement is checked against clips whose movement we chose — a window slid across a still at a known rate — and it lands within the (n-1)/n frame-interval factor of the truth. Naming the limit in the prompt is the point: a lens told that the measurement is blind to zoom will not read a push-in as a failed pan.

33. **The map tracks reliability, because reliability is what it can measure.** Promotion used to read `Analysis.score`, which is one number for the whole photograph: a frame demonstrating six techniques handed the same number to all six, so every technique in a good frame was credited with whatever the best one earned. Measured over the corpus that put 32 of 37 skills at a best score of 8 or 9 and 16 of them at solid, from 18 shots — and `diagonals` reached solid on a 9 it had no part in. The rubric cannot separate them either: its five elements correlate at r = 0.89 and the weighted mean tracks `impact` alone at 0.986, so no per-element substitute exists. What *is* about one technique is how the panel saw it, so `domain/skills.py` counts **corroborated** attempts — two lenses agreeing at 0.75 or better, both conditions, because the panel admits a single lens at 0.75 and one lens with a habit is one opinion however often it repeats. Practiced is two attempts with one corroborated; solid is three attempts with three. Rebuilt over the same corpus, solid falls from 16 techniques to 6, and the ones that fall are the ones no second lens ever saw. The score is still recorded on the SkillState for the Judge's comparison and the Coach's briefing; it simply promotes nothing. The map now claims that a technique is *repeatable*, which the arithmetic supports, and stops claiming it was done *well*, which nothing here measures. Sources and the corpus figures are in `docs/research-findings.md`.

34. **Arithmetic outranks the panel, and not only in the prompt.** `domain/motion.py` has always computed what the measured drift *rules out* — a clip that travelled 2.42 frame widths is not a locked-off tripod shot — and `motion.describe()` has always handed that sentence to the Technician and the Composer. Then it stopped: the only occurrence of the word `motion` anywhere in `domain/panel.py` was the string `"slow_motion"` in an owner override. The vote could not read the measurement, so a lens was free to claim `static_tripod` on that clip and the evidence stood, promoted a SkillState and reached the photographer. "Arithmetic, not opinion" was true of the prompts and false of the panel. `panel.aggregate` now takes `settled_for` and `settled_against`, two sets of technique ids that measurement has already decided. Against is a veto: the evidence drops however many lenses saw it and however sure they were, and the sighting travels on as dissent so the feed still shows what was claimed and what beat it. For is a corroborating vote, so a single lens noticing is enough, and the evidence records `measured` alongside the lenses that saw it at a confidence of 1.0 — a proof does not become less certain because a model was half sure, and arithmetic is the one voter in the system that cannot share the panel's blind spots, which is exactly what decision 33's corroboration bar is asking for. A technique the measurement settles *for* that no lens mentioned at all still creates nothing: evidence is a claim a lens made, and a measurement with no reading behind it is a gap in the panel rather than a sighting. The sets arrive as plain ids because the vote does not need to know which measurement settled them; motion supplies them today, and tone and exposure could supply more. Replayed on the corpus clip, `pan` moves from one lens at 0.85 — which decision 33 can never count as corroborated — to two votes at 1.0. Sources and the benchmark evidence behind the change are in `docs/video-findings.md`.

35. **The viewfinder runs the arithmetic, natively.** The phone app becomes a native Android camera (`android/`, Kotlin + CameraX + Compose), because the moment a reshoot is free is *before* the shutter, and a web view cannot read frames at frame rate. Two loops, strictly separated: a fast loop on the device runs the same arithmetic as `imaging/tone.py` — the constant is CLIP_HIGH = 250 in both languages, asserted by mirrored tests — and paints camera zebras over blown highlights plus the thirds guide, live, with no model anywhere in it; a slow loop sends an occasional downscaled frame to the Coach for one spoken or written line. The shutter uploads into the same ingest path the Drive watcher feeds, so the panel, the faults, the skill map and the quests are unchanged. The fast loop never phrases an opinion and the slow loop never draws on the frame: what is painted is measured, what is said is the model's, same as everywhere else in the system.

36. **The Tendency Profile: the photographer is a distribution, and tendencies are its narrow dimensions.** Every shot is a point in decision-space — height (IMU pitch, in-app shots only), distance (subject share of frame), placement (`subject_x`/`subject_y` against the guides), light (capture hour against NOAA sun position), dwell (frames given to a scene, clustered by time gap), subject type, moment versus static (the model's read, marked as such). A tendency is a dimension with low variance: the photographer explores distance but height is a constant — and the word is chosen over "habit" because a tendency is neutral. A repeated centred composition might be laziness or the beginning of a personal style, and Shoots does not decide that alone; the profile describes, and only the photographer's own Keeper marks (decision 40) say which repetitions are valued. `domain/tendency.py` computes the profile from measurements already on disk — pure, no model call, every count re-derivable from the file it came from. Where Keepers exist, the profile correlates *the photographer's own* keeper rate against each dimension, so a challenge is measured taste, underexplored, rather than generic advice; the panel's verdicts may be correlated too, but are always labelled as the model's read and never presented as the photographer's taste. Honesty rules: counts are shown before claims; correlations say nothing at n = 18 and say so; height is absent for Drive-ingested shots and the profile names its blind spots. The Scout reads the profile when choosing (decision 26's machinery unchanged; the profile is one more input, with the citation carried onto the quest card).

37. **The coach grades itself.** Every quest records the tendency-state it was issued against — the counts of the dimension it constrains, frozen at issue time. When later shots are ingested, domain code diffs the profile against that frozen state: the counts moved or they did not, and the diff is written on the quest as arithmetic, not adjudicated by a model. A constraint type that repeatedly fails to move behaviour for this photographer is retired for this photographer — the agent runs experiments on its own advice and drops what does not work, which is the difference between a coach and a critique queue. What this deliberately does not claim: that moved counts mean better photographs. Behaviour change is the measurable claim; quality remains the panel's opinion at compare time, labelled as such (decision 33's discipline, applied to the coach itself).

38. **The panel may abstain.** A verdict requires either a measurement that settles the question or lenses that actually agree; when the reads fully disagree and no arithmetic reaches the claim, `panel.aggregate` returns an abstention instead of averaging three opinions into a fake consensus, and the system says "I cannot call this one" — asking for another frame, or letting the shot stand unjudged. Expertise is knowing the edge of one's competence; a panel that must always produce a number is a scoring app wearing a jury costume. Abstention is honest silence, which is also what the product principle demands of the coach — and like every verdict it leaves an audit trail: the reads, the disagreement, and why nothing settled it.

39. **Four words, kept apart: Tendency, Progress, Journey Update, Verdict.** A **Tendency** is a repeated, evidence-backed pattern across Shots — neutral, never automatically good or bad. **Progress** is change over time in one of the three things the system can honestly measure: exploration (variance widening across decision-space dimensions), reliability (a Technique corroborated again under decision 33), and change itself (the recent distribution against the earlier one). A **Journey Update** is the finished artifact of the whole product: the agent's current conclusion about the photographer, in one paragraph — what they consistently notice, which Techniques have become repeatable, how the recent work differs from the earlier work, and one optional direction to explore — every clause anchored to a count or a corroboration, produced when the profile meaningfully moves, not on a schedule. A **Verdict** stays what it has always been: pass or fail against one Quest's criteria, and nothing else inherits the word. What no vocabulary may claim: artistic improvement. The system can say "you changed" with arithmetic; it can say "you improved against your own taste" only where Keeper marks (decision 40) supply the taste; and it can never say "you improved" on the model's score alone, because decision 33 already established the score measures nothing per-technique and one number cannot carry a person.

40. **The Keeper: one optional tap, and the only source of taste.** The photographer may mark any Shot a Keeper — from the phone gallery or the web grid, one tap, never asked for, never required. It is the single personal-preference signal in the system, and it is what separates "you do this often" (frequency, which the profile measures) from "this is what you value" (taste, which nothing else can supply — the panel's score is the model's taste and is never presented as the photographer's). With Keepers, the Tendency Profile gains its most personal sentences: keeper rate correlated against each dimension, and the divergence between what is done often and what is kept — "you take low angles 7% of the time and keep them at three times your average rate." Without Keepers everything still works and the Journey Update simply says less; sparse marking is expected and the correlations state their n. A Keeper is not a score, feeds no promotion (decision 33's corroboration bar is untouched), and is never second-guessed: a kept photograph of the photographer's dog is taste, not noise.

41. **The audience is the self-directed post-beginner hobbyist.** They have enough Shots for patterns to exist, already understand basic advice, lack a recurring mentor, and cannot tell development from luck. They want Keepers, proof of Change, an emerging identity, and an enjoyable practice. The product must not become school. This supersedes any professional workflow framing.

42. **The product answers a longitudinal question.** The canonical question is: "What patterns keep appearing across my Shots, and can I deliberately reproduce the ones present in my Keepers?" "Why are my Shots boring?" may introduce the problem, but Shoots cannot prove boringness. It can prove recurring behaviour and Change across comparable Shots.

43. **Experiment replaces Quest.** One active Experiment at a time preserves focus, but no daily cadence is mandatory. An Experiment is `explore`, `reproduce`, or `compare`. Explore widens an underused dimension. Reproduce tests whether a Keeper-associated pattern can be made deliberately. Compare changes one variable and asks for an optional photographer preference. Criteria and baseline are fixed before results arrive. The current `Quest` schema is the migration source, not the final domain.

44. **The work leaves an Experiment Record and a Journey Update.** Advice text is insufficient. The Experiment Record preserves its Tendency or Keeper reason, frozen baseline, Criteria, results, Verdicts, and Change. The Journey Update states what repeats, what became repeatable, and what changed, with source Evidence for every clause.

45. **Keeper is positive-only.** `kept` means valued. `unknown` means the photographer supplied no taste signal. Unknown Shots cannot become negative examples or the denominator of a preference claim. A future explicit rejection signal would be a separate domain concept and does not exist. This supersedes decision 40 wherever its rate calculation treats every unmarked Shot as not valued.

46. **Technique Map and Change replace ability language.** The user-facing states are `unobserved`, `observed`, and `recurring`. `solid`, `rusty`, level-up language, and the 1 to 10 score leave product surfaces. `Change` replaces `Progress` unless an explicit photographer goal and preference signal define what progress means. A Verdict answers Criteria only.

47. **The camera is a quiet Companion.** It adapts the active Experiment to the current Scene. Local measurements stay fast and deterministic. Weather, temperature, current light, and place facts appear only when they affect the Experiment or the photographer asks. The Companion speaks on summon and otherwise stays silent except for a rare high-value opportunity. The photographer controls the shutter. A Scene Probe is temporary and excluded from every longitudinal record unless explicitly saved as a Shot. Explicit Intent may mute a conflicting warning. Hidden location history and the internal cell grid never reach the user.

48. **Agent depth follows from the honesty problem.** A hobbyist cannot audit an AI critic, so the critic audits itself. Versioned domain code and Technique playbooks own thresholds, Criteria, corroboration, vetoes, state changes, comparability, and retirement rules. Prompts own visual interpretation and language. The system may refuse, escalate a consequential ambiguity, plan, remember explicit signals, and grade whether comparable behaviour changed after its advice. It never claims causation or artistic improvement from that Change.
