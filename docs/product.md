# Shoots

> Learn to see like yourself.

Shoots learns from every Shot, offers one personal Experiment, and tracks what changes.

## Who it is for

Shoots is for a self-directed phone photographer. They shoot on walks, weekends, and trips, select a few Shots for Instagram, and leave the rest in the Camera archive. They love photography but may not own a dedicated camera or feel entitled to call their phone work real photography. They have no mentor who remembers the whole archive.

They want a few Keepers, proof that their eye is developing, and eventually a way of seeing that feels like their own. They will quit an app that nags, grades, assigns homework, or turns a quiet walk into a lesson.

## The problem

> I cannot see how my eye is developing.

One Shot cannot reveal a Tendency. The Evidence lives across months of work: where the photographer stands, what they notice, how long they work a Scene, which light they choose, which Techniques recur, and which results they keep.

Critique apps inspect one Shot and forget it. Generic advice says "move closer" without knowing whether this photographer already does, whether they value the result, or whether trying it changed anything. Instagram shows audience response, not whether a photographic decision became deliberate. The Camera archive grows without becoming a learning record.

Shoots answers:

> What patterns keep appearing across my Shots, and can I deliberately reproduce the ones present in my Keepers?

## The work

After one source permission, Shoots intercepts new phone Shots and performs the bookkeeping no photographer or occasional mentor will maintain by hand:

1. It identifies and uploads each unseen Camera Shot without an Analyse button.
2. It measures and reads each Shot.
3. It updates a longitudinal Tendency Profile and Technique Map.
4. It offers one personal Experiment and cites why it may be worth trying.
5. It records only Shots explicitly associated with that Experiment.
6. It recomputes the record and shows what changed without claiming the Experiment caused it.

The work leaves three checkable artifacts:

- the Technique Map;
- the type-specific Experiment Record, including its question, explicit Shot set, evidence, and Change;
- the Journey Update, with a source behind every sentence.

Advice without those artifacts is not the product.

## The outcome

Shoots should help the photographer make more deliberate choices, recognise what they value, and repeat or challenge those choices on purpose. The end state is less dependence on the Companion. Silence grows as the photographer gains confidence.

The first session still needs a win. Shoots should find one supported Tendency, name one thing the photographer already does well, and offer one Experiment they can understand immediately.

Every Shot updates the underlying record. A Journey Update appears only when the Evidence supports a meaningful new conclusion, so tracking stays continuous without manufacturing a milestone after every shutter.

## The loop

| Step | Shoots does | Artifact |
|---|---|---|
| Intercept | Android notices an approved new Camera item, skips a known source reference, and uploads in the background. | Shot arrival and transfer ActivityEvents |
| Observe | Ingest reads EXIF and pixels. Analyst adds bounded visual Evidence. | Analysis |
| Remember | Cartographer updates recurring Technique Evidence and the Tendency Profile. | Technique Map |
| Choose | Scout offers one Explore, Reproduce, or Compare Experiment. | Experiment Record with baseline |
| Record | Shoots keeps only Shots explicitly associated with the Experiment. | Type-specific Experiment evidence |
| Verify | Judge checks declared Criteria only for Reproduce. Measurements may corroborate or veto model claims. | Optional Verdict |
| Learn | Domain code compares compatible earlier and later behaviour. | Change record |
| Reflect | Shoots writes only the longitudinal claims supported by that record. | Journey Update |

The photographer only has to shoot. Keeper and Intent are optional signals that let Shoots say more honestly.

## Three kinds of Experiment

**Explore.** Ask what changes across two to four optional Variations. It records what the photographer tried and noticed. There is no correct result, pass, fail, or Verdict.

**Reproduce.** Deliberately repeat a pattern associated with the photographer's Keepers. Criteria are fixed before the result, and Judge may issue a Verdict about repeatability only.

**Compare.** Change one variable, preserve both alternatives, and let the photographer say which result they value. The model does not choose the winner.

An Experiment is optional. The camera starts free, only explicitly selected Shots join, and the photographer may pause or leave without failing anything.

## The honesty line

Quality is an opinion. Behaviour is measurable.

Shoots keeps three claim classes separate:

- Measurements may state what happened and what changed.
- Models may offer interpretations and suggestions, labelled as model reads.
- Only the photographer supplies Intent, Keeper preference, and the signal that a Change was an improvement.

A Keeper is positive-only. Unmarked means unknown, never disliked. Model opinion cannot become the photographer's taste through repetition or storage.

When Evidence is weak, Shoots says less. The panel may abstain. The Companion may stay silent. The Journey Update may state a blind spot instead of inventing a conclusion.

The sentence competitors do not say:

> Shoots can prove what changed. It never pretends the model knows whether your photography got better.

## The phone source

The photographer keeps using Android's normal camera. Shoots asks once for honest media access, filters to approved Camera media, uploads unseen Shots in the background, and reports what was imported, skipped, retrying, or unreadable. Selected-media permission provides manual import only. Full access enables automatic future imports. Shoots never labels one as the other.

The Android client is not where the photography is judged. It shows source permission, background transfer state, the offered Experiment, and a route to the web record. The web remains the audit desk for Evidence, Experiment Records, Change, Journey, and failures.

The earlier custom camera, Scene Probe, weather context, and Gemini Live direction are later Companion work. They are excluded from the Taskmaster proof.

## Why agents belong here

The product needs memory, planning, action, refusal, and self-correction across time. A single critique prompt cannot do that work.

Models handle visual ambiguity and language. Versioned domain code owns Technique ids, thresholds, corroboration, vetoes, type-specific Experiment transitions, Reproduce Criteria, and profile comparisons. The agent may recommend. It cannot turn an Explore Variation into a correct answer, rewrite a Reproduce test after seeing the result, or choose a Compare preference.

The system earns depth when it can:

- refuse an unsupported read;
- escalate a consequential disagreement;
- choose an Experiment from the archive;
- remember relevant Evidence and explicit user signals;
- check whether comparable behaviour changed after an explicitly attempted Experiment;
- stop using an approach that repeatedly fails under comparable conditions.

## What Shoots refuses to become

- a single-Shot score;
- a chatty rules recital;
- a course, streak, or skill tree;
- a social feed, editor, generator, filter, or culling tool;
- a professional manual-camera replacement;
- an Inspiration feed;
- a hidden location tracker;
- an agent that takes the Shot for the photographer.

Generated reference clips and the Director are outside the core. Inspiration may support an Experiment, but it is not the work accomplished.

## Product test

A successful demonstration shows one uninterrupted Shot history to Journey loop. A stranger should be able to say:

> It remembered the photographer's work, found a recurring pattern, chose what to test, and verified what changed.

If they only say "it gives photography advice," the product has not been made visible.

The detailed rationale lives in [product decisions](product-decisions.md). Implementation status and acceptance checks live in the [feature list](feature-list.md).
