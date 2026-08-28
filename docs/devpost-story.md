# Devpost draft — project details

> Status: superseded draft retained for comparison. Use `devpost-story-codex.md`.
> It must not define submission scope. The Inspiration section was explicitly rejected on
> 2026-08-27 as polished but soulless. Read
> [the story writing brief](devpost-story-writing-brief.md) before revising it.

Working copy for the Devpost "Project Details" step. Paste sections into the form
after review. Claims below follow the build-claim rule: nothing is stated as done
unless the repository or a recorded run proves it.

## About the project (story field, Markdown)

### Inspiration

"Am I actually getting better at taking pictures?"

I shoot on walks, thirty photos at a time. After a year and thousands of photos
I still could not answer that question. I could not even tell whether my best
photo came from technique or luck.

The options are real, and each is good at something. A community can tell me
when a photo lands, but it cannot remember what I posted in March. A critique
app can name the rule I broke, but it starts from zero on every upload. A
chatbot will read any photo I hand it and explain it well, but hand it three
months of walks and it has never met me. A human mentor would solve all of
this, which is exactly why almost nobody has one. Underneath, every option is
answering the same small question: is this photo good? The question that keeps
a hobbyist shooting is different. Am I becoming someone who takes good photos
on purpose? With nowhere to ask it, I did what everyone does: scrolled my own
camera roll, comparing this month to last by eye. It told me nothing I could
trust. A photo cannot confess whether I meant it.

Then the realization: improvement was never going to be visible in any single
photo. It is a pattern across months. Which decisions keep repeating? Which ones
can I make on purpose? Which ones are changing? The evidence for all three was
already sitting in my archive. The only missing thing was something that reads
all of it, remembers all of it, and never grades my taste. No person will do
that job. No app did either.

So I built ShootsAI for the Taskmaster track: a mentor that watches my normal
camera, reads every photo, remembers the whole archive, and measures my
behaviour instead of scoring my art. Progress I can see is progress I can
trust. The rest of this page is the receipts.

### What it does

ShootsAI watches my phone's normal camera. After one media permission, future
Camera Shots are assigned and uploaded in the background. No replacement camera,
no per-Shot upload screen.

From there the system works alone:

- Each Shot gets a durable Run: measured EXIF, tone, and motion facts, then a
  panel of three model readers with different eyes, then validation that throws
  away anything the taxonomy or the pixel grid cannot vouch for.
- Capture continuity groups Shots into Scenes and Scenes into one natural Shoot.
  When the Shoot goes quiet and every member Run settles, the system freezes one
  immutable Shoot Record: exact members, what repeated, what varied, what it
  could not read.
- Scout then chooses one of five routes: explain the work, ask one consequential
  question, offer an Explore, offer a Keeper-backed Reproduce Experiment, or stay
  silent. Code computes which routes the Evidence permits. The record stores the
  chosen route, its warrant, and every rejected route with its reason.
- Outcomes feed back. Each intervention is stored with what happened next, and a
  technique that produced two comparable unchanged outcomes stops being offered.
  The system evaluates its own advice, and it is not allowed to grade my art.

Perceive, remember, choose, act, observe, adapt. That is the loop, and every step
of it leaves a checkable artifact.

Two design rules matter more to me than any feature. Quality is my opinion,
behaviour is measurable, so ShootsAI stores counts, corroborations, and comparable
attempts, never a score. And silence is a real answer. When the Evidence supports
nothing, Scout says why and offers nothing.

The payoff surfaces are for me, not for the pipeline. A Shot Teaching Receipt
with one thing to keep, one thing to notice, one move to try. A Journey that
compares me to my earlier self, where every claim carries the exact Shot ids and
calculation version it came from. A Deconstruction carousel I can post, built
only from stored Evidence, with the cover always my choice.

### How I built it

Kotlin and Compose on Android, with WorkManager and Room running the background
import so it survives the app dying. FastAPI and Google ADK on the backend, with
Gemini 3.7 Flash for every reader and writer. Firestore, Cloud Storage, Pub/Sub,
and Cloud Scheduler on Cloud Run, one push subscription per stage with dead
letter topics. A Vue 3 web desk for auditing what the agents did.

The architecture principle is strict. Stages are code, agents answer questions
with schemas, and arithmetic outranks opinion. A measured camera motion can veto
a model's claim. Technique Evidence needs corroboration, and dissent is stored
instead of averaged away. Automatic Scout routes are code-gated; model and Coach
tool proposals are revalidated before any state transition.

Durable memory is the store, never a model session. Each Shot and Scout call gets a
bounded slice assembled by code. The record the agents write into is designed so
they cannot silently borrow authority, and re-analysis under a newer model
re-baselines instead of pretending I improved.

### Challenges

Idempotency under Pub/Sub redelivery was the long fight. One Shot owns one Run,
three different barriers (Run, Capture Session, Shoot) settle over the same Run
truth, and a late photo has to version the Shoot Record instead of silently
staling it. Adversarial review under forced interleavings found real settlement
races. Their forced-interleaving tests now define the settlement correction that
must pass before the final continuous proof is recorded.

The other fight was with my own model calls. A malformed GPS tag decoded as NaN
and walked into solar arithmetic. A model kept inventing crop hotspots for
findings that had no location. The answer both times was the same: validate at
the boundary, and let code refuse.

### What I learned

Restraint is a feature. The versions of this product that graded my photos,
assigned homework, or spoke after every shutter all died in the docs before they
shipped. What survived is a system that mostly stays quiet and can prove every
sentence it does say.

### What's next

Broader longitudinal validation on real Camera histories, Compare Experiments,
and richer Deconstruction pages.

## Built with (tags)

kotlin, jetpack-compose, workmanager, room, python, fastapi, google-adk, gemini,
vertex-ai, firestore, cloud-run, pub-sub, cloud-scheduler, cloud-storage,
cloud-build, secret-manager, firebase, fcm, vue, vite, tailwindcss, pillow,
ffmpeg, pydantic

## Try it out links

- https://shoots-718560154436.asia-southeast2.run.app/
- https://github.com/fikri2992/shoots

## Still needed on this form

- Video demo link (required field; comes from the Lane D recording).
- Image gallery, 3:2, up to 15: Shoot receipt, Shot Teaching Receipt with a
  drawn Finding, Scout route with rejected routes, Journey comparison,
  Deconstruction pages, architecture diagram.
