# Devpost story, Codex proposal

> Status: proposal for comparison. Do not paste it into Devpost or replace
> `devpost-story.md` until Fikri selects it.

## Intention

Make a judge understand the personal problem in three seconds, then show that
ShootsAI finishes a real background job that a single-Shot critique cannot do.

## Why the GLM draft misses

- It removes Fikri from the story and makes an eighteen-Shot system quote carry
  the emotion.
- "Every hobbyist" and "no tool answers it" claim more than the evidence allows.
- The paragraph about what a typical pitch would do talks about copywriting when
  the reader should be inside the problem.
- Its repeated bold stages turn the product into an architecture presentation.
- It describes the continuous physical Android workflow as complete. The emulator
  and backend path passed, but the full Xiaomi acceptance run remains undone.
- Several test counts are stale. This proposal uses only current recorded proof.

## Opening formula

Use the anatomy of a deceptive promise without copying its dishonesty:

1. Hook with the exact pain.
2. Commit only to the work ShootsAI performs.
3. Put the receipt beside the commitment.
4. State the limit before the judge has to find it.

The first four paragraphs must work as a complete pitch. A judge can understand
them in one scan. The longer story exists only for a judge who chooses to continue.

## About the project

### Inspiration

As a hobbyist photographer, I can come home from a walk with about thirty images.
I may know which one I love, but I cannot tell what made it work, how much of that
came from me, or whether I could do it again.

So one question remains: **am I improving, or am I just getting lucky?**

I can post one image for feedback or upload it to an image-critique AI for a
detailed analysis. Both may teach me something about that image, but neither
compares it with the hundreds of images I have taken over time.

The closest answer I can imagine is a mentor who has followed my work over time. But that relationship still begins with a selection I make. I bring the images I already value, so the mentor sees a curated slice of my work, not how I actually shoot.

The missing piece was a record of how I actually shoot over time, including the
images I normally leave out. That record could show which choices kept returning
and give me a way to test whether a choice I valued was deliberate. I built
ShootsAI to create that record quietly in the background, without turning
photography into another task.

### What it does

ShootsAI is a still-image photography Companion with Android and web clients. In the
accepted production proof, I selected 75 Drive Shots in three batches. ShootsAI
created one Run per Shot, measured and read each file, recovered five unique failed
Shots through six repair replays, settled three Shoots, and returned three immutable
Shoot Records. Each record shows what recurred, what varied, and what the available
Evidence could not establish.

That is the accepted Taskmaster job. The physical Camera-to-Shoot workflow remains
unaccepted. So does the Photographer-benefit loop: the current proof does not show
that a real Photographer found the record useful, completed its Experiment, or made
a later Change. Cost has not been measured.

That record becomes part of my history. ShootsAI compares it with earlier Shoots
and chooses exactly one supported response: explain what happened, ask one useful
question, or offer an optional Explore or Reproduce Experiment. If I enter an
Experiment, ShootsAI freezes the question and the exact result Shots. It
compares earlier and later work only when they are comparable; otherwise it records
insufficient Evidence. Explore has Variations and no Verdict. A Reproduce Verdict
answers declared Criteria only.

For each Shot, ShootsAI combines EXIF and pixel measurements with three bounded
Gemini readers and a Synthesizer. Measurements, model interpretation, and my Keeper
or Experiment choices stay separate. Only Techniques from the fixed catalogue enter
the record. When the available Evidence cannot support a conclusion, ShootsAI keeps
the uncertainty instead of promoting it to a claim.

The finished work appears as a compact Shoot receipt, a longitudinal Journey with
links to its source Shots, and an evidence-bound Deconstruction draft. I choose the
Keeper cover and whether to share it. This hackathon build handles still images only.
The accepted proof uses explicit Google Drive import. Camera discovery is implemented
but is not part of the accepted end-to-end claim.

### How I built it

ShootsAI is an event-driven control loop. The Android client uses Kotlin, Compose,
WorkManager, and Room to discover new Camera images, keep a replayable outbox, and
continue after the interface leaves the screen. Room is a cache, while Firestore
remains the source of truth. The web audit desk uses Vue 3, Vite, and Tailwind to
show the same Photographer record and its ActivityEvents.

The Python and FastAPI service runs on Cloud Run. Cloud Storage holds media,
Firestore holds durable state, Pub/Sub moves stage events with retries and
dead-letter routes, Cloud Scheduler closes inactive Shoots, and Secret Manager holds
service credentials. Local development runs the same stage services in process, so
the transport changes without changing the behaviour.

The architecture enforces three responsibilities:

1. Pure domain code owns measurements, the finite Technique catalogue, Criteria,
   comparability, admissible claims, and state transitions.
2. Google ADK agents use Gemini 3.7 Flash for bounded visual interpretation and
   writing. Every agent result must pass a Pydantic schema before it enters the
   record.
3. Infrastructure adapters store records and move replayable work. They do not make
   photography decisions.

The Analyst is an ADK `SequentialAgent`. A `ParallelAgent` runs the Technician,
Composer, and Storyteller with different instructions and image inputs, then a
Synthesizer reads their structured results. Models emit cell references rather than
pixel coordinates; domain and imaging code decide what can be drawn.

Models hold no durable memory. Code assembles the bounded history for every call.
Each accepted Shot owns one Run, while Capture Session and Shoot barriers read that
same Run truth for different memberships. Duplicate delivery is a no-op. A late
Shot creates a new Shoot revision instead of rewriting the earlier record. The
[architecture diagram](architecture.svg) maps the complete path.

### Challenges

#### Knowing when the background work is finished

One Shot owns one Run, but Run, Capture Session, and Shoot barriers may all react to
it. Pub/Sub may deliver an event again, and a late Shot may arrive after the Shoot
started closing. Forced interleavings exposed races that sequential tests had hidden.
The fix was one shared Run truth, explicit terminal barriers, and immutable Shoot
Record revisions. Integration cases now interleave arrival, settlement, duplicate
delivery, and repair before accepting one terminal record.

#### Keeping model opinion inside its Evidence

One malformed GPS value became `NaN` and reached solar arithmetic. One model
invented crop locations for a Finding that had no position. A real-agent case praised
a deliberate high angle, then prescribed eye level. Those failures became permanent
rules: numbers must be finite before arithmetic, a visual mark needs validated cells,
unknown Techniques are dropped, and advice cannot contradict the strongest supported
Technique. The corrected cases were rerun in the real-agent corpus.

### Validation

#### Real Gemini quality

A historical still-image report used eleven real Shot cases with Gemini 3.7 Flash.
Its 180 automatic checks passed and twelve judgement questions remained for human
review. That report used Analyst prompt digest `1c738851cdfb`. The current prompt
digest is `a3c0dd488f26` and has not completed the real-agent acceptance gate, so the
historical result is regression context, not current model-quality proof.

#### Integration and Cloud evidence

The accepted production run took 75 selected Drive Shots through 75 completed Runs
and three settled Shoot Records. Five unique failed Shots recovered through six
repair replays. Durable Run latency was 48.72 seconds at p50 and 2,306.161 seconds at
maximum; the three Picker requests averaged 104.353 seconds. The files came from 67
visually reviewed real hobbyist Shots plus disclosed deterministic variations, so
this is workflow and recovery proof, not 75 independent captures.

The first full-scale attempt created 350 Shot records and no Shoot Record. The
settlement defect was fixed and the 75-Shot gate passed; the complete 300-file run was
not repeated. These results prove the Drive import path, individual Runs, recovery,
and settlement at the accepted scale. They do not prove physical Camera discovery,
current-prompt visual quality, or Photographer benefit.

> Working note, remove before submission: record one uninterrupted Xiaomi run from
> normal Camera capture through background ingestion, every terminal Run, one Shoot
> Record, one supported Scout response, and offline reopen. Replace this note with
> the exact Shot count, record revision, Cloud Run revision, and result.

### What I learned

Real calls changed the interaction design. The accepted production stress run had a
48.72-second median durable Run and a 38-minute-26-second maximum after recovery.
That work belongs in the background, with visible progress and failure state.

The first versions graded every Shot and treated every Experiment like homework.
Using the product on a phone made the mistake obvious. Explore now offers Variations
without a Verdict, Reproduce alone checks declared Criteria, and unrelated Shots do
not become attempts. The photographer can ignore an Experiment and keep shooting.

The first corpus also contradicted my pitch. Placement and framing were varied, while
the clearest measurable Tendency was dwell: eighteen Shots across sixteen Scenes,
with only 1.12 Shots before moving on. ShootsAI now computes the record before it
speaks. The current Companion is less intrusive than the first design and more
honest about what it cannot know.

### What's next

The next product test is longitudinal: run ShootsAI over months of real Camera histories
and measure whether its single offered Experiment remains useful, varied, and
evidence-backed rather than becoming repetitive.

The next product extension is Compare, where two deliberate alternatives are
preserved and the photographer may state a preference.

## Why this version

- The hook uses Fikri's real question and reaches the mechanism through an ordinary
  walk, not a fabricated breakthrough Shot.
- The first scan of What it does exposes the completed Taskmaster work we can prove:
  one archive selection, background accounting, recovery, and settled Shoot Records.
  It names Camera and longitudinal Photographer benefit as remaining gates.
- How I built it explains responsibility, state, retries, and boundaries instead of
  using framework names or agent counts as proof of architecture.
- Challenges, Validation, and What I learned do different jobs. Concrete failures
  explain design changes, while real-model, integration, Cloud, and device evidence
  retain their separate proof limits.
- Required physical-device proof stays in Validation and the submission checklist.
  It is not disguised as future product work.
- The structure follows the strongest recurring moves from the verified winner
  comparison in `devpost-winner-section-patterns.md` without copying a winner's
  voice or unsupported claims.

## Still needed from Fikri

This version can become more personal if Fikri supplies one real Keeper moment and
one real feedback disappointment. Replace the general walk only with details he
confirms. Do not invent them.

Before this becomes final Devpost copy:

- run the current Analyst prompt through the real-agent acceptance gate;
- record one uninterrupted physical Shoot and replace the Validation working note
  with its exact result;
- have a real hobbyist Photographer inspect a Shoot Record, choose or reject the
  offered Experiment, return with comparable Shots, and report whether it helped;
- choose one public product name, Shoots or ShootsAI, and use it everywhere;
- add the hosted project, public repository, architecture diagram, testing
  instructions, and public four-minute demo links;
- disclose any pre-existing work incorporated into the entry, or state that none was
  used;
- publish one qualifying build article and one social post with
  `#AllThingsAgenticHackathon` for the two 0.2 bonuses;
- add no bonus model unless it performs necessary product work visible in the demo.
