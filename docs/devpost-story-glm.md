# Devpost draft — GLM proposal

> Status: superseded proposal for comparison. Use `devpost-story-codex.md`; do not
> use this file to define submission scope or paste it into the form.
>
> Earlier status: proposal for comparison, not approved copy. Do not paste into the form
> until Fikri selects a version. v4 applies the Deceptive Promise formula
> inverted: the Hook is the plain question "Am I actually getting better at
> taking pictures?", the Commitment is definitive but true, the Runaround is
> replaced by proof up front (the real 18-photo-corpus Journey paragraph), and
> the Escape/Pivot is replaced by an explicit limit stated as the credibility
> anchor. First-person anecdote is gone; concrete stories are real system
> outputs.

## About the project (story field, Markdown)

### Inspiration

**Am I actually getting better at taking pictures?**

Every hobbyist photographer asks it. No tool answers it. Friends say "nice
shot." A critique app resets to zero with every upload. A chatbot has never seen
yesterday, let alone last spring. The question survives everywhere, because
answering it honestly takes work no human will do: read every Shot, remember
every session, compare decisions across months, and write it all down with
proof.

**Shoots answers that question.** Not a score. Not "great composition!".
Evidence: which of your photographic decisions keep recurring, which you can now
make on purpose, and what measurably changed since.

A typical pitch would now promise you transformation and hide the proof until
after you have paid attention. The reverse: here is what the system wrote, on
its own, from a real archive of eighteen photos — before you have seen a single
screenshot:

> "You naturally reach for warmth and horizontal frames, with thirteen of
> seventeen shots leaning warm and thirteen held in landscape. A low camera
> angle has now become reliably yours, confirmed across three separate
> occasions. With all eighteen frames sitting in low or mid-key light, you might
> explore what a high-key exposure feels like on your next walk."

Every clause carries the count it came from. And the limit is as explicit as the
promise: Shoots cannot tell you whether a photo is good. Quality is your
opinion; behaviour is measurable. No score exists anywhere in the system — the
only verdict on your taste that matters is yours.

That is why Shoots was built for the Taskmaster track: an agent that does the
remembering, the comparing, and the checking on its own, so the only job left
for the photographer is to keep shooting.

### What it does

Shoots turns an ordinary camera session into a settled learning record, with no
upload step, no tagging, no Analyse button, and no human in the loop. The
photographer keeps using the normal Android camera. Everything below happens by
itself.

- **Perceive.** Phone Source watches approved Camera media and uploads unseen
  Shots in the background, surviving app death and reboots. Each Shot gets a
  durable Run: measured EXIF, tone, and motion facts, then a panel of three
  Gemini readers with different inputs, then validation that discards anything
  the taxonomy or pixel grid cannot vouch for.
- **Assemble.** Capture continuity groups Shots into Scenes and one natural
  Shoot. When the Shoot goes quiet and every member Run settles, the system
  freezes one immutable Shoot Record: exact members, what repeated, what varied,
  what it could not read.
- **Decide.** Scout chooses one of five routes — explain the work, ask one
  consequential question, offer an Explore, offer a Keeper-backed Reproduce
  Experiment, or stay silent. Code computes which routes the Evidence permits;
  the record stores the chosen route, its warrant, and every rejected route with
  its reason.
- **Verify.** A Reproduce Experiment freezes Criteria before any result exists;
  the Judge records a Verdict about those Criteria only, or an explicit
  abstention. Explore records Variations with no pass or fail. The system never
  claims its advice made anything better — Change has three answers, and
  "insufficient evidence" is one of them.
- **Adapt.** Each intervention is stored with what happened next. A technique
  that produced two comparable unchanged outcomes stops being offered
  automatically. The agent grades its own advice, never the photographer's art.

Every step leaves a checkable artifact, and the web desk shows the full audit
trail. Two rules matter more than any feature: silence is a real answer — when
Evidence supports nothing, Scout says why and offers nothing — and no score
exists anywhere, because quality is the photographer's opinion while behaviour
is measurable.

The payoff surfaces: a Shot Teaching Receipt (one thing to keep, one to notice,
one move to try), a Journey where every claim carries the exact Shot ids and
calculation version it came from, and a shareable Deconstruction carousel built
only from stored Evidence — with the cover always the photographer's choice.

### How we built it

Kotlin and Compose on Android (WorkManager + Room for the background import),
FastAPI and Google ADK on the backend, Gemini 3.7 Flash for every reader and
writer, Firestore / Cloud Storage / Pub/Sub / Cloud Scheduler on Cloud Run
(live: https://shoots-718560154436.asia-southeast2.run.app/), and a Vue 3 web
desk for auditing what the agents did.

The architecture principle is strict, and it is what makes the loop trustworthy:

- **Stages are code; agents answer questions with schemas.** Every model output
  is validated twice — against the schema, then against the domain (taxonomy
  ids, cells inside the grid, bounds inside the envelope).
- **Arithmetic outranks opinion.** A measured camera motion can veto a model's
  claim. Technique Evidence needs corroboration; dissent is stored instead of
  averaged away.
- **The store is the memory, never a session.** Each agent gets a bounded slice
  assembled by code, so no agent borrows authority it wasn't given.
- **Every stage is idempotent on its id.** Pub/Sub delivers at least once; a
  redelivery is a no-op. Three independent barriers (Run, Capture Session,
  Shoot) settle from one shared Run truth.

Proof of work: 565 backend checks, 31 frontend checks, and an agent quality
gate that runs the real Ingest and Analyst stages against a versioned manifest —
an 11-case run produced 180 automatic passes and zero failures, with model and
prompt versions recorded.

### Challenges

Idempotency under Pub/Sub redelivery was the long fight. One Shot owns one Run,
three barriers settle over the same Run truth, and a late photo has to version
the Shoot Record instead of silently staling it. Adversarial review under forced
interleavings found real settlement races.

The other fight was with our own model calls. A malformed GPS tag decoded as NaN
and walked into solar arithmetic. A model kept inventing crop hotspots for
findings that had no location. The answer both times was the same: validate at
the boundary, and let code refuse.

### What we learned

Restraint is a feature. The versions of this product that graded photos,
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
