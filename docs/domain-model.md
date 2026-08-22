# Shoots domain model

The ubiquitous language. If a word is not here, it is not a thing.

## The loop

Shoots is an event-driven control loop, the shape that won 2026 agentic hackathons (see the Visual QA research doc: watch, diagnose, act in the system of record, verify, audit trail, human gate).

```
Drive folder changes                       (watch)
  → Ingest    pulls the file, reads EXIF/ffprobe, draws the grid, tiles video frames
  → Analyst   reads the gridded frame: techniques seen, composition, critique   (diagnose)
  → Cartographer  updates the skill graph                                       (act: system of record)
  → Judge     if the shot answers an open quest: checks criteria, closes it     (verify)
  → Scout     daily, or right after a quest closes: finds the gap, researches,
              writes the next quest, generates a reference clip, emails it      (act)
  every step  → ActivityEvent                                                   (audit trail)
  the user    → may skip a quest; that is the only thing they ever have to do   (human gate)
```

## Nouns

**Shot.** One photo or video file from the user's Drive folder. Identified by Drive file id; a redelivery of the same file id is a no-op. Carries EXIF (photo) or VideoMeta (video), the grid spec the Analyst saw, and blob paths for the original, the gridded frame, the contact sheet and a thumbnail.

**Technique.** One entry in `domain/taxonomy.py`. Has a family (composition, light, exposure, lens, color, video), a level 1-3, a cue (what the Analyst looks for), optional hard EXIF bounds, and prerequisites. The catalogue is finite on purpose. ~65 entries.

**Evidence.** The Analyst's claim that a shot demonstrates a technique, with a confidence 0-1 and the cells where it is visible. Hard evidence is EXIF; soft evidence is vision. Soft evidence below `judge_min_confidence` (0.6) does not count.

**Analysis.** Everything the Analyst said about one shot: evidence list, composition read (subject cells, horizon row, suggested crop, moves), a critique paragraph, a 1-10 score.

**Move.** A composition suggestion: "move *what* from cells X to cells Y because Z". The dashboard draws it as an arrow over the original. Cells, never pixels.

**Skill graph.** One SkillState per (user, technique). Status: unexplored → attempted → practiced → solid, and solid → rusty after `skill_decay_days` without practice. Carries attempts, best score, last score, last practiced, recent shot ids.

**Quest.** A request to shoot one technique, issued by the Scout. Has a title, a brief (how to do it, grounded in real references found by search), *why now* (the gap reasoning), criteria, up to three references with URLs, and a Veo reference clip. Status: open → passed | failed | skipped | expired.

**Criteria.** What counts as done, in two halves. `exif`: an ExifRule with bounds the Judge checks mechanically. `vision`: technique ids the Analyst must have tagged at or above threshold. `text`: the plain-language version the user reads.

**Verdict.** The Judge's result for one submitted shot against one quest: per-check pass/fail, per-tag confidence, feedback text. A quest can hold several verdicts; the first passing one closes it.

**ActivityEvent.** One durable record per agent step. The live feed (SSE) is a view of these; Firestore is the truth.

## Agents

| Agent | Trigger | Reads | Writes | Model |
|---|---|---|---|---|
| Ingest | `media.new` | Drive file | Shot, blobs | none (ffmpeg, Pillow) |
| Analyst | `media.ingested` | gridded frame or contact sheet, EXIF | Analysis | gemini-3.7-flash |
| Cartographer | `media.analyzed` | Analysis, SkillStates | SkillStates | none (pure) |
| Judge | `media.analyzed` when shot.quest_id set | Analysis, Quest | Verdict, Quest status, `quest.closed` | gemini-3.7-flash (feedback only; pass/fail is pure) |
| Scout | daily tick, `quest.closed` | skill graph, taxonomy | Quest, Veo clip, email | gemini-3.7-flash + Search grounding, veo-3.1-fast |
| Scheduler | Cloud Scheduler | Users | renews Drive channels, expires quests, triggers Scout | none |

Cartographer and Judge pass/fail are pure code. That is deliberate: the skill graph and quest outcomes must be reproducible from stored data, and a model must not be able to pass its own quest.

## Decisions

1. **Drive is the only input.** No upload endpoint in v1. The PWA's "Shoot" button uploads to the Drive folder through the Drive API, so phone and desktop use the same path and the watch channel is the only trigger.
2. **Finite taxonomy.** The model tags from a list. Unknown ids are dropped and logged.
3. **Cells, not pixels.** Reused from Visual QA: the grid adapts to aspect ratio (~64 cells), refs are chess-style, `domain/grid.py` does all conversion.
4. **Hard evidence first.** The Judge checks EXIF bounds before looking at vision tags. A quest whose technique has EXIF bounds cannot pass on vision alone when EXIF is present and fails the bounds.
5. **Photo first, video supported.** Videos become a contact sheet (scene-cut frames, up to 12, tiled 4 wide) plus ffprobe metadata. Video techniques are judged on the sheet. No per-frame analysis in v1.
6. **One quest a day, one open at a time.** Failing a quest re-issues it with the Judge's feedback folded into the brief. Skipping is the human gate and is logged, never deleted.
7. **Pipeline stages are transport-agnostic.** The same stage functions run chained in-process locally and behind Pub/Sub push subscriptions on Cloud Run. Every subscription has a dead-letter topic; every stage is idempotent on shot id.
8. **Secrets stay out of Firestore.** The Drive refresh token lives in Secret Manager (prod) or `.blobs/tokens` (local). Firestore holds the user's Drive folder id and page token only.
9. **Gemini via Vertex global endpoint; Veo and Lyria via us-central1.** App infrastructure in asia-southeast2.
10. **Voice review is a stretch.** Gemini Live over a shot, from the phone, targeting the Multimodal UX prize. It reuses the constrained-token pattern from Visual QA and never holds API credentials in the browser.
