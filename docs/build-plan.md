# Build diary

Historical implementation notes below preserve what was tried, including features
later removed. They are not current behavior. As of 2026-08-26, decisions 52–81 in
[the domain model](domain-model.md) supersede score storage, Keeper-rate arithmetic,
curriculum selection, capped longitudinal corpora, and automatic Director/Veo work.
Current status is in [the feature list](feature-list.md).

## Day 12 notes (2026-08-26), Taskmaster thin slice

- Cut the custom camera and Gemini Live from P0. Android is now a permission-aware Phone Source: it watches approved Camera media with WorkManager, uploads unseen originals by stable source id, survives restart, and leaves the system camera in control of the shutter. Pairing remains the four-day authentication cut.
- Direct ingress is independent of Drive and idempotent on `(user, source, source_id)`. A selected Experiment id is validated at ingress; an untagged Shot remains a free Shot and cannot become a submission merely because it was made while an Experiment was open.
- The real connected Xiaomi completed the unattended path on a synthetic screen-capture fixture placed in Camera media: Phone Source found and uploaded it, Ingest measured it, the real Analyst found `single_accent` and `low_key`, Cartographer updated both Technique records, Scribe wrote the reviewed Shot to Drive, and `pipeline.run_completed` recorded the terminal receipt. The fixture was removed from the phone after acceptance.
- Physical testing found and fixed a real Evidence-boundary defect: malformed GPS decoded as `NaN`, reached solar arithmetic, and stopped the pipeline. EXIF parsing and domain records now reject non-finite and out-of-range coordinates while preserving valid 0° latitude/longitude.
- The first receipt was event-derived and could close when Scribe finished before Cartographer and Scout. It is replaced by one durable Run per accepted Shot. Ingest, Analyst, Cartographer, Judge, Scribe, and Scout settle independently; the last required outcome closes the Run atomically. Retry and terminal media remain different states, and the completion ActivityEvent has a deterministic id.
- The hackathon Experiment is now Reproduce or silence. Scout freezes one exact marked Keeper and Criteria before any result. The Experiment Record keeps every explicit result Shot, including abstentions. Journey shows the exact Keeper beside the latest result and refuses to call it better. The old Criteria-shaped Explore is no longer issued.
- Android shows the latest backend Run and will not associate Camera media with a legacy non-Reproduce Experiment. Web onboarding now says direct ingress works without Drive; Drive is optional import and reviewed output.
- A phone-width browser pass covered seed, idle Run receipt, Shot Run detail, and the Reproduce Journey pair. It exposed and fixed Windows local blob paths for `dev:` identities plus the stale claim that Phone Source records camera pitch.
- Current local gates: backend ruff plus the full 543-check suite pass; frontend 31 checks and production build pass; Android debug assemble and lint pass. The latest APK has not yet been installed on the Xiaomi. No Cloud deployment was attempted.


## Day 2 notes (2026-08-22)



- Real-Google check passed: OAuth (`drive.file`, offline) → `/drive/connect` created the `Shoots` folder and shared it with `shoots-ingest@…` → uploads as the user → reader (service account impersonated via ADC) listed + downloaded → 4 shots ingested incl. a 27 MB 120 fps video.

- The consent screen is branded "Visual QA Agent" (shared Google Auth Platform branding on the project). Left alone; changing it would rebrand Visual QA. Judges watch a video, they do not sign in.

- authlib: `access_type`/`prompt` belong in `authorize_params`, not `client_kwargs`, or no refresh token comes back.

- uvicorn `--reload` did not restart on edits here; run without it and restart by hand.

- Sync is a plain folder listing keyed by Drive file id. `changes.list` with a page token is a day-7 optimisation if listing cost shows up; with one folder per user it will not.



## Day 3 notes (2026-08-22)



- Real chain timing: `/drive/sync` → 4 shots ingested (incl. 27 MB video) → 4 analysed in 35 s wall clock, in-process bus, Vertex global endpoint.

- Analyst quality on first run: `light_trails` 0.98 justified by the 10 s shutter; `slow_motion` 0.95 from 120 fps; declined to tag `panning` on a first-person bike shot (correct). Scores 3-7, critiques specific to the frame. Cells always valid after `validate()`.

- Composition read renders well: crop dim, horizon, subject box, move arrows (`imaging/overlay.py`).

- Local dev: `FileStore` (JSON) keeps users/shots across restarts. Stop the server via the task that started it; `taskkill` on the PID does not reach it.



## Day 4 notes (2026-08-22)



- `/api/techniques/rebuild` re-derived 11 Techniques from four stored Analyses; the historical Scout run then issued a grounded Experiment. Current Scout requires a cited Experiment Direction and otherwise stays silent.

- Grounding chunk titles are bare domains (adobe.com, slrlounge.com) and URLs are `vertexaisearch.cloud.google.com/grounding-api-redirect/...` redirects. Acceptable; the dashboard shows the domain as the label.

- Scout research uses google-genai directly with the Search tool because ADK disables tools when `output_schema` is set; the write step is an ADK agent. Worth one sentence in the architecture doc.

- Day 5 next: Judge (pure EXIF checks + vision threshold, model feedback only), daily tick, backfill job.

## Day 5 notes (2026-08-23)

- Full autonomous loop verified: `POST /tasks/daily` → sync found the submission → ingest → Analyst (`golden_hour` 0.92) → Cartographer + Judge (passed; feedback named the fence and suggested f/2.8-4) → `experiment.closed` → Scout issued `monochrome` ("Strip away all color"). 17:14:42 to 17:16:04, no human step.
- Decision 6 refined: a failed attempt keeps the experiment open with a verdict; `ExperimentStatus.FAILED` removed.
- Docs had mixed cp1252/UTF-8 bytes from earlier Windows-default writes; normalised to UTF-8. Always pass `encoding="utf-8"` in patch scripts.
- Remaining for the Taskmaster story: Drive push channel + renewal (day 7), Pub/Sub + DLQ (day 7), PWA + Web Push (day 6), Veo clip per experiment (day 7).

## Day 6 notes (2026-08-23)

- PWA served from `backend/static` (same as the Cloud Run image): experiment card, skill map, shots grid, shot page with SVG overlay in cell units (`viewBox = cols rows`, no pixel math in the browser), activity feed, bottom tab bar with floating Shoot. Checked at 412 px and 1280 px in Chrome.
- Shoot button → `POST /drive/shoot` → user's Drive folder via their `drive.file` token → shot tagged with `experiment_id` → pipeline starts without waiting for sync.
- Web Push: pywebpush + VAPID; `/api/push/key|subscribe|test`; Scout and Judge push. Verified to the browser permission prompt; delivery is checked on a device with the `/api/push/test` that runs on subscribe.
- Dashboard polls `/api/events` every 5 s while visible and refetches the rest when the newest event changes. SSE was available from Visual QA but polling is one less thing to break across Cloud Run instances.
- `FRONTEND_ORIGIN` is `http://localhost:8000` locally now: the backend serves the built app, so sign-in lands on the app.

## Day 7 notes (2026-08-23), features first, deploy after

- Veo 3.1 fast on Vertex us-central1: 4-6 s 9:16 720p clip in 32-60 s, bytes returned inline (no GCS hop). Lyria 3 clip preview is served from the `global` endpoint only and needs `response_modalities=["AUDIO","TEXT"]` (the us-central1 publisher entry 404s on every method); 30 s mp3 in 16 s. Gemini Live native audio: us-central1 only, first audio in ~6 s.
- Historical Director trial: storyboard → Veo produced a reference clip in about 80 s. This automatic stage, topic, subscription, and UI were removed from the core loop; the retained manual legacy call conditionally attaches only while the Experiment remains open.
- Coach: WebSocket relay to Gemini Live, briefed with the gridded frame and the Analyst's read. Typed-question check through the real app wiring (`check_live_ws.py`): opening line names the strongest thing in the frame, answer references cells ("hitting the child's face in D2 and E2"), event recorded with the transcript. Mic path is the same socket plus PCM frames; checked on the phone after deploy.
- Pub/Sub push: handlers register by stage name, `/pubsub/<stage>` verifies the OIDC token (service-account email + audience) and delivers to that one handler. Drive push: `files.watch` per folder on Connect and from the daily tick, `/tasks/renew-channels` twice a day, `/drive/notify` checks token and channel id. Both can only be exercised with a public HTTPS URL; that is day 7b.
- FileStore caveat: two processes on one `store.json` lose writes to each other (a check script ran while the dev server was up and the server's next flush dropped the clip path). Stop the server before running a `check_*` script that writes, or accept a manual fix. Firestore has no such problem.
- Day 7b (deploy): Cloud Run asia-southeast2 with identity shoots-ingest, Firestore + GCS + Secret Manager via `cloud_state`/`gcs_bucket`, `infra/topics.sh` with the service URL, Scheduler jobs for `/tasks/daily`, `/tasks/sync`, `/tasks/renew-channels`, VAPID + OAuth redirect on the real origin, push delivery and the Coach on the phone.

## Day 7c notes (2026-08-23), the step back

- Re-centred on "redefining interaction": the agent lives in the user's Drive and notifications, the app is the audit trail. Four moves, all shipped and checked on the real stack:
  - **Scribe**: after Judge, the review is written into `Shoots/Reviewed/`: overlay, critique, Moves, Findings, and Verdict. The filename describes what was found and carries no score.
  - **Timing**: techniques carry a light window (`taxonomy.LIGHT`), the user's location is the GPS of their newest frame (`Exif.latitude/longitude`, `User.last_*`), `domain/sun.py` + `domain/timing.py` pick `deliver_at` and a reason; the push waits for the five-minute tick (`/tasks/tick`). Location picked up from a Xiaomi phone frame on the first sync.
  - **Coach memory**: the Listener extracts `missing_gear` and notes from the transcript; Scout ranking and brief respect them; Coach is briefed with them. Real-model check: "only have my phone" → no tripod/telephoto/macro/flash.
  - **Today**: the home tab is the experiment with why-now and why-then; verdicts link to "Ask the Coach why".
- Cut Lyria: Veo 3.1 generates its own ambient audio (`generate_audio=True`); the mux step and the music model are gone.
- Judge now publishes `media.judged` on every shot so the Scribe runs after it; stage order is deterministic, no fan-out race for the verdict.
- `scripts/call_as_user.py` calls the running dev server with a minted session cookie, for demos and checks that must not touch `store.json` while the server is up.

## Day 7d notes (2026-08-23), expert grounding

- Researched before changing anything: PPA's 12 Elements (judging standard, 100-point bands), Feldman's critique order, published setting guidance per technique, PoLL/LLM-judge panel literature (diverse panels beat one judge; same-model panels share errors), ADK workflow agents. Written up in `docs/technique-evidence.md`.
- Analyst is a panel: ADK `SequentialAgent[ParallelAgent[technician, composer, storyteller] → synthesizer]`, about 20 s wall clock. Evidence moves by vote. Lens rubrics structure transient reads; overall and element scores are not stored.
- Two Gemini structured-output gotchas: a `dict[str, int]` field is never filled (no additionalProperties in the response schema), and optional fields get skipped; element scores are required ints per lens.
- Bounds corrected from sources: freeze 1/500, panning 1/125–1/8, long exposure 0.5 s.
- Frontend shows the five element bars and ●●○ agreement per technique; the feed says "(2 of 3)"; the Scribe's caption carries the element line.

## Day 7e notes (2026-08-23), six ADK-shaped experiments, all checked on the real stack

- Crop loop: the phone frame's suggested crop (A3-G9) was rendered and rated 5 -> 7 ("removes the bamboo pole"), kept; the overlay and Drive review now draw a tested crop.
- Exposure arithmetic: EV, handheld limit, freeze thresholds and the 500 rule are facts in the Technician's and Judge's prompts. Caught my own error: 1/40 s at 23 mm is *slower* than the 1/46 s limit, which the test now asserts.
- Judge vs an earlier frame: feedback prompt gets one of the photographer's own earlier frames of the technique as Image 2 plus its observations, chosen by Keeper then corroboration then recency, never by score; `compared_with` on the verdict.
- Pre-flight: ~8-11 s on a 640 px preview. Front-lit child+dog against the backlight experiment -> "shoot again: move so the sun is behind them"; the backlit frame passes light direction, fails rim light with a fix.
- Scrub lens: `pan` on the camper-van clip went from composer-only 0.55 to x3 at 0.87 with the scrub confirming on exact frames; `static_tripod` x4 on the locked-off clip. Contact-sheet lenses take 20-30 s each on video; the scrub adds ~16 s.
- Coach tools over Gemini Live function calling: "only my phone, no tripod, something else to shoot here" -> `remember` then `issue_quest` -> "Fill the entire frame" issued by voice, no tripod needed. Turn takes ~46 s because the Scout runs inside the tool call.
- Gemini Live closed one session abnormally (1006) mid-tool-response on Windows (semaphore timeout); the retry ran clean. Worth a reconnect-with-resume later.

## Day 8 (2026-08-23), the interaction rebuild

Walked every screen in Chrome at phone and desktop width as a first-time user. Findings that drove the rebuild: the floating shutter skipped pre-flight and still got judged; "Reference clip rendering…" never resolved; the experiment card put its Shoot button two screens down; Today repeated the whole skill map and a 60-row feed; "Ask the Coach why" jumped to an anchor and started nothing; the Coach refused to open without a microphone; three lenses' observations were shown three times each.

Rebuilt around one decision per screen:

- **Now** — connect / seed / reading / Experiment / idle, one at a time. `ExperimentHero` leads with Criteria and the cited Baseline; Shoot + Skip stay reachable.
- **Shots** — one grid, newest ingest first, Keeper and processing state only, with `Add Shots` for archive imports.
- **Frame** — sticky media with `read` / `grid` toggles, verdict and moves in the open, observations deduped across lenses and cell refs stripped from prose, evidence and camera behind disclosures, Drive link in the footer.
- **Journey** — six skill bars that open into chips, past experiments, and the agent log condensed (identical consecutive lines fold into `×N`).
- **Coach** — a sheet over the frame, text-first, mic opt-in, opened with the question the user clicked.

Backend: `scout.issue_first` after the Cartographer, so the first experiment needs no click (`tests/test_first_quest.py`). Frontend: design tokens and three type weights in `style.css`; `steps.spec.js` covers the states a returning account never sees. 200 backend tests, 11 frontend tests, ruff clean.

### Day 8b: the overlay, rebuilt around the reader

The overlay drew "crop below the bamboo pole" as a red arrow from the pole to the child's ear, because a crop and a move were the same object. Split them: `Move.kind` is `move` | `crop` | `camera`, required in the Composer's schema, and the prompt says what each is drawn as. On the first real run the model used it exactly as intended — "Trim top bamboo bar" came back as a `crop` (tested by the crop loop, composition 5 → 7, kept) and "Lower camera position" as a `camera` note with no cells and no mark.

The human guide is now chosen from the agreed technique (`domain/guides.py`: thirds / centre / diagonals / fill / phi, thirds as the dimmed fallback), drawn thin and unlabelled with the subject's centre on it, and switchable under the frame. The cell mesh moved into "What the agent saw". The same three layers render in PIL for the Drive review (`imaging/overlay.py`), checked on pixels in `tests/test_overlay.py` — a `camera` change must leave the frame byte-identical.

`subject_x`/`subject_y` in frame units give the guide something finer than a seventh of the width to measure against; a point that contradicts the lens's own cells is dropped, and no fit is claimed below half a cell.

The first pass of this took the split too literally and put the agent's gridded frame on the frame page as "What the agent saw". It came out again: an addressing system is not a feature. The same rule then applied to prose — the critique still said "the umbrella across B3-F6" to a reader with no grid — so the prompts now ask for plain positions, and `cells.plain` / `Grid.place` rewrite anything older on the way to the screen, the caption and the Drive description (whose cell legend is gone with it).

## Day 8c notes (2026-08-23), the design day

No code. Four notes, each a decision with its reasons, all in `docs/`:

- `classroom.md` — the teacher pivot, explored and dropped. Taskmaster's own criterion asks for a workflow completed *without human intervention* on a *unique, personal* problem; an approval queue for a persona neither of us is fails both. Kept as the record, with the market check and the generated-media rule that survived it.
- `lighting.md` — light as plan / show / coach / verify. Code computes the sun, the heading, the cast, the ratio, the edge; agents reason inside a recipe envelope (which window, which pattern, for this person on Saturday) and read what only a reader can (catchlight, nose shadow); code diffs plan against facts with tolerances. Indoors the window is the sun and the diagram is the strip.
- `conditions.md` — sky and air: Weather + Air Quality APIs, derive/fit/prep with a number on every item, the Replanner on the tick (keep / shift / swap / hold, only over slots code offered), and excused checks in the Judge so the cloud is never the person's fault.
- `product.md` — the whole thing as one object: a *shoot* is an appointment with the light, and Now renders its phase (planned, moved, soon, open, reading, verdict, idle). Who it is for, why the critique tools work and where they stop, the drivers under them and which we keep, the language, the demo day, and the eight days from 08-24 with Stage One first.

Rubric facts found on the way: Veo, Lyria and Gemma are +0.2 each, blog and social +0.2 each, on a 1–6 scale; the video is four minutes with an unedited live run and visible Cloud Run proof; the architecture diagram is mandatory. None of the three Stage One artefacts exists yet; that is day 1.

## Day 9 notes (2026-08-25), the product day and the camera pivot

No pipeline code. One scaffold, three docs, and the product argued to a standstill.

- **Architecture research delivered** (`architecture-findings.md`): 72 findings, all three adversarial checks came back misstated. The load-bearing corrections: decision 18's input-separation was never implemented (every lens sees both images — the experiment research-findings §4 relied on never ran), and r = 0.888 is halo within one rater, not inter-rater correlation (each element has exactly one rater, so rows 9-11 attack a correlation that does not exist). Ship rows 1-5 (~3 h): ADK pin `>=2.7,<3` (SequentialAgent/ParallelAgent are @deprecated against an unbounded pin), per-lens images via `before_model_callback`, an ANALYSING status guard (idempotent on write, not on cost — a redelivery re-pays 4-6 model calls), two false words off FramePage, decision 19's first clause corrected.
- **The camera pivot**: native Android, Kotlin + CameraX + Compose (`android/`, decision 35). PWA rejected because per-frame pixel access is the point; RN rejected in favour of true native by explicit choice. No Android Studio: SDK 36 + JDK 17 + hand-placed gradle wrapper, builds CLI (`gradlew assembleDebug`, 10.3 MB APK, first build clean). `Tone.kt` mirrors `tone.py` — CLIP_HIGH = 250 in both languages; the viewfinder paints camera zebras over blown blocks, thirds grid, live clipped-% readout. All arithmetic, no model, at analysis frame rate.
- **The product argued through** (`product.md` rewritten, then user-edited, then extended): boring shots come from passive decisions (12-source synthesis, `boring-shots-advice-research.md`); the thesis is *quality is an opinion, behaviour is measurable*; the loop is detect → assign → study → shoot → verify → compare; surfaces split by tempo (camera = fast half, web = async half + agent's desk). The persona pass added the principles (silence is a feature, praise with proof first, intent respected). The agents pass added the five proofs of depth and the five missing verbs — refuse, escalate, plan, remember, self-grade — of which self-grading (decision 37) and abstention (decision 38) are product-defining; the Tendency Profile is decision 36.
- **Demo angles tried and dropped**, recorded so they stay dropped: the process sentence ("read my photos, assigned a constraint, the count moved") — process as star, statistic as payoff, a judge feels nothing; the before/after pair — every AI demo since 2023, and it quietly asks the audience to judge quality, which the thesis forbids; "one photo, eighteen times" — rejected on taste. What stands: the work-accomplished table in `product.md` and the agent's desk showing a veto fire live.
- **Honest odds, said out loud**: the idea is good enough to win and ideas don't win. Chief risk is execution — native pivot in a new language, upload path and desk feed not yet built, nothing committed. The 48-hour test: tendency profile computing on the corpus, phone shutter reaching ingest, one ugly full loop. Failing that, the camera cuts to capture-only and the loop demos through the Drive door — the agentic depth survives that cut; a stuttering demo survives nothing.
- Next, in order: commit checkpoint → architecture rows 1-5 → `tendency.py` + tests → shutter → ingest → Scout reads the profile → verdict pulse → desk feed.

## Day 10 (2026-08-25, same day, second half): the loop, built

Everything in the day 9 "next, in order" list, plus the two agent-depth verbs. Nine commits; the tree was clean at every one of them. 449 tests pass, ruff clean, both apps build.

**Hygiene first** (architecture rows 1-5). `google-adk` pinned `>=2.7,<3`. Decision 18's input half finally implemented: a `before_model_callback` leaves each reader only its own frame, so the Storyteller stops being asked how a picture feels while looking at a mesh drawn over it, and the Synthesizer — documented as never seeing the image — stops seeing two. About a fifth of the panel's input tokens go with it. The Analyst became idempotent on *cost*, not only on write: the shot is claimed as `ANALYSING` before the first model call, with a dated lease so a dead attempt cannot strand it, closing the worst case of five full panels for one shot. Decision 19's first clause corrected in both the doc and the docstring. `remeasure.py` run over the corpus: 18 shots, 0 skipped, so tone is no longer `{}` and the two tone faults can fire.

**The spine** (`domain/tendency.py`, pure, 34 tests). Seven dimensions, entropy as exploration, counts before claims, blind spots named rather than dropped. Two design bugs the tests caught before the corpus did: a corpus shot entirely in landscape puts orientation at zero exploration on day one, so a naive tie-break would tell every photographer to turn the phone sideways forever — ties now go to more evidence, then to catalogue order; and `-0.0` exploration from a single full bucket.

**What the real corpus said, which partly falsified the pitch.** Placement is explored 0.84 and framing 0.99 — this body of work is *not* one tight cluster, so "one photo, eighteen times" would have been a lie on the data, and it is good that we computed it before pitching it. The one genuine tendency is dwell: **18 shots across 16 scenes, 1.12 frames before moving on** — which is professional advice #2 (6 of 12 sources) measurably absent. Also real: warm in 13 of 17, zero high key, zero square, light unreadable on 16 of 18 (no GPS), height unreadable on all 18 (needs the camera).

**The Keeper** (decision 40) fixed an honesty violation that decision 36 shipped with: the profile correlated "the photographer's own keeper rate" against panel verdicts, which is the model's taste wearing the user's clothes. Taste now has exactly one source, one optional tap, and the panel's score is admitted nowhere near it.

**The Journey Update** (decision 39) works end to end on the real corpus. Two bugs found only by running it: the first update diffed against an empty profile and so announced that the photographer had just discovered shooting warm, cool, close and wide all at once; and the evidence line "two lenses agreeing" came back out of the writer as "repeatable across your lenses" — a photographer must never read the word *lens* about their own photograph. Both fixed, both regression-tested. What it now writes, unedited:

> "You naturally reach for warmth and horizontal frames, with thirteen of seventeen shots leaning warm and thirteen held in landscape. A low camera angle has now become reliably yours, confirmed across three separate occasions. With all eighteen frames sitting in low or mid-key light, you might explore what a high-key exposure feels like on your next walk."

Leaning, then what became theirs, then one direction offered. Every clause anchored to a count. No score, no "improved".

**The camera reached the pipeline.** Device pairing gives the phone a scoped token. The shutter posts into `/drive/shoot` with `pitch_deg`. The pulse requires corroborated Evidence at confidence 0.75, shows its proof, then one Finding with its reason. Keeper remains one optional stored mark.

**The two verbs.** *Refuse*: unresolved visual Criteria or missing required EXIF produces no Verdict. *Self-check*: every Experiment freezes the exact Baseline Shot set; later comparable Shots are checked by code without claiming causation.

**Voice.** The review used to open with the defect, which was right for a critic and wrong for a hobbyist. Praise leads now, and has to clear the same bar as everything else: only a corroborated sighting names the file.

Left undone, deliberately: the agent's-desk polish, the before/after Journey hero, escalation, the learner model, Scene-as-unit, intent, graduation, the study step, and the summonable in-viewfinder coach.

## Day 11 notes (2026-08-25), the product interrogation locked

No feature code. The product went through nine adversarial questions: audience, mechanism, work accomplished, honesty, vocabulary, agent depth, pitch, refusals, and win risk.

The result:

- Audience: the self-directed post-beginner hobbyist, not a professional and not a beginner following a course.
- Problem: "I cannot see how my eye is developing." The Evidence is distributed across many Shots, so one-Shot critique and generic advice cannot answer it.
- Product question: "What patterns keep appearing across my Shots, and can I deliberately reproduce the ones present in my Keepers?"
- Work: detect a Tendency, offer one personal Experiment, then leave an Experiment Record and Journey Update showing what changed.
- Honesty: measurements, model opinion, and photographer signals stay separate. Keeper is positive-only. Unmarked means unknown.
- Vocabulary: Experiment replaces Quest, Finding replaces Fault, Technique Map replaces skill graph, and Change replaces unsupported Progress. Eye remains pitch language, not a metric.
- Experiment types: Explore, Reproduce, and Compare.
- Agent depth: versioned domain code owns thresholds, Criteria, corroboration, vetoes, comparability, and Change. Models interpret and write. The system must refuse, remember, plan, escalate selectively, and grade its own advice.
- Pitch: "Learn to see like yourself." One-liner: "Shoots learns from every Shot, offers one personal Experiment, and tracks what changes."
- Camera: a quiet Companion for the active Experiment. Context must be photographically relevant. The user controls the shutter. Scene Probes are temporary and never enter the Journey unless saved.
- Refusals: no score, skill tree, constant narration, social feed, editor, generated-Inspiration dependency, hidden location history, or generic camera replacement.
- Win risk: idea risk medium, execution risk high. The chief failure would be centring a chatty camera demo and hiding the longitudinal Taskmaster loop.

Documentation changed:

- `product.md` is the current brief.
- `product-decisions.md` preserves the reasoning and open decisions.
- `feature-list.md` separates P0 proof, the longitudinal coach, the Companion, later identity work, and forbidden features.
- `domain-model.md` decisions 41 through 48 supersede the old product language while naming the current code migration honestly.

Recommended next proof, not implementation authorization: deploy one stable continuous run from Shot history through personal Experiment, Verdict, Change, and Journey Update before adding new Companion intelligence.

## Day 12 notes (2026-08-26), the real-phone correction

No feature code in this pass. The Android build was installed on a physical Xiaomi device, camera permission granted, the viewfinder opened, pairing survived a force-stop, and the active Experiment, clipping, pitch, grid, Ask, and temporary Scene Probe were exercised. That use changed the product plan.

**Setup was not a product flow.** The camera asked for a server address and a six-character code created in the signed-in web app. Local testing also needed `adb reverse`. Native Android can authenticate as the same Photographer as web, so pairing is the wrong target abstraction. The release app should carry one stable service origin, use native Google sign-in, receive a revocable Shoots device session, and send camera Shots directly to Shoots storage. Drive remains an optional import and export adapter.

**Ask was slow and narrower than the promise.** Four real Scene Probes took 5.8 to 8.2 seconds. A synthetic request using low thinking took 4.1 seconds versus 5.8 seconds at the default, which helps but does not make a conversation. The current Gemini Live relay works only for a fixed reviewed Shot in the web client. Android has no microphone, audio playback, WebSocket client, or live frame stream. The target is a server-relayed Live Scene Session with interruptible audio, low-rate Scene frames, optional Intent and Experiment context, and cell-ref guide tools. A one-frame Scene Probe stays as the no-audio fallback.

**The current Explore is a gate.** All six stored Experiments are Explore, but the implementation gives them Reproduce mechanics. Eight of ten recorded Verdicts say Criteria were not met. More importantly, every untagged Shot captured after issuance becomes an attempt, and a miss leaves the same Experiment open. The result is exactly what the audience said they would quit: the app insists on its composition instead of helping the photographer try possibilities.

Decisions 69 through 74 correct the model:

- Explore asks one question and offers two to four Variations. It has no Criteria, Verdict, pass, fail, ready, or shoot-again state.
- Reproduce alone uses fixed Criteria and a Verdict about deliberate repeatability.
- Compare preserves alternatives and asks for an optional photographer preference.
- One open Experiment is an offer, not an active camera mode. Only explicit Shot association enters its Record.
- Android and web share one identity. Camera ingress no longer depends on Drive.
- Gemini Live becomes the summoned Scene Companion. The model has no shutter tool.
- Foreground Live and capture use a fast clock. Deep corroborated Analysis stays in the background and never locks the viewfinder.

Next implementation order: corrected Explore and explicit participation, unified identity and direct ingress, Android Live Scene relay and latency check, non-blocking capture, Intent, then the physical-phone Android-to-Journey proof. Deployment follows the exact verified build rather than preceding it.
