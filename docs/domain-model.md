# Shoots domain model



The ubiquitous language. If a word is not here, it is not a thing.



## The loop



Shoots is an event-driven control loop, the shape that won 2026 agentic hackathons (see the Visual QA research doc: watch, diagnose, act in the system of record, verify, audit trail, human gate).



```

Drive folder changes                       (watch)

  â†’ Ingest    pulls the file, reads EXIF/ffprobe, draws the grid, tiles video frames

  â†’ Analyst   reads the gridded frame: techniques seen, composition, critique   (diagnose)

  â†’ Cartographer  updates the skill graph                                       (act: system of record)

  â†’ Judge     if the shot answers an open quest: checks criteria, closes it     (verify)

  â†’ Scout     daily, or right after a quest closes: finds the gap, researches,

              writes the next quest, generates a reference clip, emails it      (act)

  every step  â†’ ActivityEvent                                                   (audit trail)

  the user    â†’ may skip a quest; that is the only thing they ever have to do   (human gate)

```



## Nouns



**Shot.** One photo or video file from the user's Drive folder. Identified by Drive file id; a redelivery of the same file id is a no-op. Carries EXIF (photo) or VideoMeta (video), the grid spec the Analyst saw, and blob paths for the original, the gridded frame, the contact sheet and a thumbnail.



**Technique.** One entry in `domain/taxonomy.py`. Has a family (composition, light, exposure, lens, color, video), a level 1-3, a cue (what the Analyst looks for), optional hard EXIF bounds, and prerequisites. The catalogue is finite on purpose. ~65 entries.



**Evidence.** The Analyst's claim that a shot demonstrates a technique, with a confidence 0-1 and the cells where it is visible. Hard evidence is EXIF; soft evidence is vision. Soft evidence below `judge_min_confidence` (0.6) does not count.



**Analysis.** Everything the Analyst said about one shot: evidence list, composition read (subject cells, horizon row, suggested crop, moves), a critique paragraph, a 1-10 score.



**Move.** A composition suggestion: "move *what* from cells X to cells Y because Z". The dashboard draws it as an arrow over the original. Cells, never pixels.



**Skill graph.** One SkillState per (user, technique). Status: unexplored â†’ attempted â†’ practiced â†’ solid, and solid â†’ rusty after `skill_decay_days` without practice. Carries attempts, best score, last score, last practiced, recent shot ids.



**Quest.** A request to shoot one technique, issued by the Scout. Has a title, a brief (how to do it, grounded in real references found by search), *why now* (the gap reasoning), criteria, up to three references with URLs, and a Veo reference clip. Status: open â†’ passed | failed | skipped | expired.



**Criteria.** What counts as done, in two halves. `exif`: an ExifRule with bounds the Judge checks mechanically. `vision`: technique ids the Analyst must have tagged at or above threshold. `text`: the plain-language version the user reads.



**Verdict.** The Judge's result for one submitted shot against one quest: per-check pass/fail, per-tag confidence, feedback text. A quest can hold several verdicts; the first passing one closes it.



**ActivityEvent.** One durable record per agent step. The live feed (SSE) is a view of these; Firestore is the truth.



## Agents



| Agent | Trigger | Reads | Writes | Model |

|---|---|---|---|---|

| Ingest | `media.new` | Drive file | Shot, blobs | none (ffmpeg, Pillow) |

| Analyst | `media.ingested` | gridded frame, clean frame, EXIF | Analysis: voted evidence, rubric elements, computed score, observations, critique | gemini-3.7-flash × 4: a ParallelAgent of three lenses (Technician, Composer, Storyteller) then a Synthesizer, in a SequentialAgent |

| Cartographer | `media.analyzed` | Analysis, SkillStates | SkillStates | none (pure) |

| Judge | `media.analyzed` | Analysis, Quest | Verdict, Quest status, `media.judged` always, `quest.closed` on pass | gemini-3.7-flash (feedback only; pass/fail is pure) |

| Scout | daily tick, `quest.closed` | skill graph, taxonomy, user location | Quest with `deliver_at`, push when due, `quest.issued` | gemini-3.7-flash + Search grounding |

| Director | `quest.issued` | Quest, technique | reference clip blob on the Quest | gemini-3.7-flash (storyboard), veo-3.1-fast |

| Scribe | `media.judged` | annotated frame, Analysis, Verdict | the reviewed copy in the user's Drive (`Shoots/Reviewed/`) | none (Pillow) |

| Coach | a tap on the shot page (WebSocket) | gridded frame, Analysis, Quest, the user's constraints | ActivityEvent with the transcript; the Listener turns what the user said into `User.constraints` | gemini-live-2.5-flash-native-audio; gemini-3.7-flash (Listener) |

| Scheduler | Cloud Scheduler | Users | renews Drive channels, expires quests, triggers Scout | none |



Cartographer and Judge pass/fail are pure code. That is deliberate: the skill graph and quest outcomes must be reproducible from stored data, and a model must not be able to pass its own quest.



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

19. **The Composer's crop must beat the original on the pixels.** `suggested_crop_cells` is an opinion until `agents/crop.py` renders the crop, has a rater score original and crop as finished frames, and keeps it only if composition rose; the rater may propose one alternative, so at most two rounds. A crop that failed is cleared, so neither the overlay nor the Drive review ever draws an untested suggestion. The loop is Python, not an ADK `LoopAgent`: an `LlmAgent` with an `output_schema` cannot take tools, and no agent can inject a rendered image into the conversation mid-invocation.

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
