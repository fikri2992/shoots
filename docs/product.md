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
5. It freezes the exact ordered Camera members of an explicit Reproduce Capture Session.
6. It judges every member, waits for every Run, and leaves one batch result instead of interrupting after each Shot.
7. It recomputes the record and shows what changed without claiming the Experiment caused it.

The work leaves five checkable artifacts:

- the Run, with one outcome per pipeline stage;
- the Technique Map;
- the Capture Session, with its immutable manifest, member outcomes, representative, and terminal summary;
- the type-specific Experiment Record, including its question, explicit Shot set, evidence, and Change;
- the Journey Update, with a source behind every sentence.

Advice without those artifacts is not the product.

## The outcome

Shoots should help the photographer make more deliberate choices, recognise what they value, and repeat or challenge those choices on purpose. The end state is less dependence on the Companion. Silence grows as the photographer gains confidence.

The first session still needs a win. Shoots should name one corroborated decision in the photographer's own work immediately. A Reproduce Experiment begins only after they mark a Keeper that supports one; silence is better than a generic first assignment.

Every Shot updates the underlying record. A Journey Update appears only when the Evidence supports a meaningful new conclusion, so tracking stays continuous without manufacturing a milestone after every shutter.

## The loop

| Step | Shoots does | Artifact |
|---|---|---|
| Intercept | Android notices an approved new Camera item, skips a known source reference, and uploads in the background. | Shot arrival and transfer ActivityEvents |
| Observe | Ingest reads EXIF and pixels. Analyst adds bounded visual Evidence. | Analysis |
| Remember | Cartographer updates recurring Technique Evidence and the Tendency Profile. | Technique Map |
| Choose | Scout offers one Keeper-backed Reproduce or records why it stayed silent. | Experiment Record with exact Keeper reference |
| Record | Android freezes one ordered Capture Session manifest; Shoots keeps only those members as Reproduce results. | Capture Session and type-specific Experiment evidence |
| Verify | Judge checks declared Criteria only for Reproduce. Measurements may corroborate or veto model claims. | Optional Verdict |
| Learn | Domain code compares compatible earlier and later behaviour. | Change record |
| Reflect | Shoots writes only the longitudinal claims supported by that record. | Journey Update |

The photographer only has to shoot. Keeper and Intent are optional signals that let Shoots say more honestly.

## Three kinds of Experiment

**Explore.** Ask what changes across two to four optional Variations. It records what the photographer tried and noticed. There is no correct result, pass, fail, or Verdict.

**Reproduce.** Deliberately repeat a pattern associated with the photographer's Keepers. Criteria are fixed before the result, and Judge may issue a Verdict about repeatability only.

**Compare.** Change one variable, preserve both alternatives, and let the photographer say which result they value. The model does not choose the winner.

The Taskmaster build implements Reproduce. Scout does not issue the old Criteria-shaped Explore. Corrected Explore and Compare remain later work.

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

Android is the daily client. It shows Now, the Room-backed Shot archive, Shot Evidence, Keeper controls, Capture Session recovery, the Reproduce Record, Change, Technique Map, Tendency Profile, Journey, Drive, and account controls. Cached reads remain visible offline with their sync age. The web remains the deeper ActivityEvent and Run audit desk; both read one Photographer record.

The daily mobile hierarchy is intentionally smaller than the data model:

- **Now** has one focal state: the newest evidence-backed Shot result, an active Capture Session that needs attention, or capture setup before any result exists. The next normal-camera action sits directly beneath that value.
- **Shots** is the visual archive. Shot detail leads with an interactive, evidence-limited annotation before prose.
- **Experiments** owns today's offered Reproduce, on-demand Scout checks, the exact Keeper reference, Capture Session actions, and earlier Experiment Records.
- **Journey** owns Tendency, Technique Map, and Change across time.
- **Settings** is reached from the account control. Its sections are collapsed summaries until the photographer chooses one.

Daily delivery and an on-demand request use the same Scout. Asking now changes timing, not standards: without a supported Keeper-backed direction, Shoots says why it stayed silent. Image marks follow the same rule. A located Finding is drawn where its measurement reaches; a whole-frame or unlocated Finding is labelled honestly rather than given a fictional hotspot.

The Android interaction system uses one optical icon grid, one selected-tab indicator, short directional transitions between destinations, and selectable semantics for tabs and image layers. Motion confirms where state went and remains subordinate to the Shot. Legacy Experiments that predate Keeper-backed Reproduce stay readable but cannot be started under a false current label. Automatic Phone Source timestamps use the known MediaStore instant rather than shifting timezone-less EXIF; other source ambiguity remains explicit follow-up work.

The earlier custom camera, Scene Probe, weather context, and Gemini Live direction are later Companion work. They are excluded from the Taskmaster proof.

## Why agents belong here

The product needs memory, planning, action, refusal, and self-correction across time. A single critique prompt cannot do that work.

Models handle visual ambiguity and language. Versioned domain code owns Technique ids, thresholds, corroboration, vetoes, type-specific Experiment transitions, Reproduce Criteria, and profile comparisons. The agent may recommend. It cannot turn an Explore Variation into a correct answer, rewrite a Reproduce test after seeing the result, or choose a Compare preference.

The current system can:

- refuse an unsupported read;
- choose a Reproduce from corroborated Evidence in a marked Keeper;
- remember relevant Evidence and explicit user signals;
- preserve exact result Shots, abstentions, Criteria, Verdicts, and stage outcomes;
- check whether compatible longitudinal counts changed without claiming causation.

Bounded escalation and automatic advice retirement remain later work.

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

> It remembered the photographer's work, chose one decision from a Keeper, verified an explicit result, and accounted for every stage.

If they only say "it gives photography advice," the product has not been made visible.

The detailed rationale lives in [product decisions](product-decisions.md). Implementation status and acceptance checks live in the [feature list](feature-list.md).
