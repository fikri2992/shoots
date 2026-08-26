# Product decisions

Locked through the nine-stage product interrogation on 2026-08-25, corrected from real-phone use, and deepened from the photographer's own learning problem on 2026-08-26. This file records why the product has its current shape. [Product](product.md) states the result. [Feature list](feature-list.md) tracks what still has to exist.

## 1. Audience first

Shoots is for a self-directed beginner or post-beginner hobbyist photographer who already knows how to shoot and recognises some Techniques.

This person:

- has a capable phone or camera and shoots often on walks, weekends, and trips;
- already revisits and selects Shots, but has no recurring mentor;
- understands basic advice, so another rule-of-thirds lesson will not help;
- has enough work for patterns to exist, but cannot tell development from luck;
- may take thirty Shots in one session and has no desire to inspect or upload them one by one;
- receives vague encouragement from communities but cannot tell which decision to keep repeating;
- may avoid asking an experienced photographer because it takes time or their work feels too embarrassing to show;
- wants photography to remain a quiet, enjoyable part of life.

In their own words:

> I know some Techniques and I know how to shoot, but I do not know whether I am improving or randomly taking pictures. I want to know whether a result came from a decision I can repeat or whether I was lucky. I want proof that March-me and August-me are different without turning my walk into homework.

What they want from the product:

- automatic learning from the Camera archive without manual uploads;
- one useful Move with a visible condition to look for, not an essay;
- silence until they ask or one unusually valuable opportunity appears;
- praise first, supported by Evidence;
- respect for Intent;
- comparisons against their own earlier work;
- a visual Deconstruction they can keep or share as an Instagram carousel;
- almost no setup, tagging, or review forms.

What they want for themselves is the product outcome: a more deliberate and recognisable way of seeing that no longer depends on the app.

Memory here means photographic memory: Shot Evidence, Technique recurrence, visual comparison, Experiment history, constraints, Intent, and explicit preferences. It is not a chat transcript presented as expertise, a nostalgic gallery, or an invisible personality profile.

They quietly quit when the app nags, grades, assigns generic lessons, mistakes Intent for error, or asks them to maintain the system.

## 2. The problem

The long-term problem is:

> I cannot see how my eye is developing.

The precise question is:

> Which photographic decisions am I making repeatedly, which can I now make on purpose, and how is that changing across my Shoots?

The mechanism is distributed evidence. A Tendency exists across many Shots and months, not inside one frame. Deliberate control needs stronger Evidence than recurrence: an explicit attempt, a declared decision, and a supported result across more than one Scene. The photographer remembers favourites and recent failures, but cannot reliably reconstruct sessions, aggregate placement, distance, light, subject, dwell, Technique use, and Change over time. Single-Shot critique forgets the next day. Generic advice never checks whether the photographer already does it, values it, or changes after trying it.

The product objections are part of the problem definition:

- AI critique produces long single-Shot text without longitudinal memory.
- Uploading a thirty-Shot session to a general model is manual work and still does not create a Technique or Change record.
- Direct instruction can make the camera feel owned by the app. The photographer wants free shooting, optional Experiments, and later proof.

"Why are my Shots boring?" remains a useful entry question, not a diagnosis Shoots can prove. The research found recurring professional advice: decide what the Shot is about, work the Scene, simplify, wait, seek useful light, impose a constraint, and edit alternatives. The advice is already available. The missing part is a memory that finds this photographer's repeated defaults and checks whether an intervention changes them. See [boring Shots advice research](boring-shots-advice-research.md).

## 3. The work accomplished

Shoots turns ordinary Camera activity into a checked record of photographic behaviour. It intercepts Shots, assembles Scenes and a natural Shoot, waits for every member Run, records what repeated and varied, chooses one justified learning action or silence, and reports what changed afterward.

A human doing the same work would inspect every Shot, reconstruct Scenes and sessions, maintain comparable measurements, find repeated patterns, distinguish recurrence from deliberate reproduction, select an appropriate Experiment, preserve a Baseline, inspect the result, recompute the record, and lay out a shareable explanation. Shoots does that work in the background.

The work leaves six finished artifacts:

1. The Run accounts for every required stage of one accepted Shot.
2. The Shoot Record preserves exact Shot and Scene membership, terminal coverage, observed Variations, and the stored Scout outcome.
3. The Technique Map records sightings and recurrence while separate figures preserve deliberate attempts, distinct Scene coverage, Criteria outcomes, and positive Keeper counts.
4. The Experiment Record preserves the question, reason, Baseline, explicit Shot set, type-specific Evidence, and post-Experiment Change. Only Reproduce carries Criteria and Verdicts.
5. The Journey Update states what repeats, what became deliberately reproducible, and what changed, with a source for every claim.
6. The optional Deconstruction turns that Evidence into an image-led draft the photographer can keep or share.

Advice alone is not work accomplished. A paragraph from a model without these artifacts is decoration.

## 4. The honesty line

| Claim class | What belongs there | What it may say |
|---|---|---|
| Measured by the system | EXIF, Tone, Motion, placement, framing, time, recurrence, corroboration, Criteria checks, profile differences | "Centred placement appeared in 12 of 18 Shots." |
| Model opinion | subject read, mood, narrative, moment, interpretation, artistic suggestion | "The isolation makes the frame feel quieter." |
| Known only from the photographer | Intent, preference, whether a Shot is a Keeper, whether a Change feels like improvement | "You marked three low-angle Shots as Keepers." |

The smallest optional inputs with the largest honesty gain are the Keeper mark, Mine versus Inspiration on a manual import, and Intent only when its answer would materially change the Move.

A Keeper is positive-only. Marked means valued. Unmarked means unknown, not rejected. The current `kept_at` representation supports that distinction; a model-selected cover or unmarked denominator does not.

Rules:

- Model opinion never becomes fact because it was stored.
- Change is measurable. Improvement requires the photographer's signal.
- A model score never represents the photographer's taste.
- Sparse or incomparable Evidence produces a limit statement or abstention, not a confident story.
- Every longitudinal claim carries its Shot set, count, calculation version, and model or prompt version where a model contributed.

## 5. Vocabulary

| Term | One meaning | Avoid |
|---|---|---|
| Shot | One captured photo or video | photo, image, frame when referring to the domain object |
| Scene | One photographic situation at one place and time inside a Shoot | a visual-similarity cluster presented as the same event |
| Shoot | One natural period of Camera activity containing one or more Scenes | Capture Session, album, arbitrary date bucket |
| Shoot Record | Exact settled membership, coverage, Variations, Evidence, and Scout outcome for one Shoot | session critique, scorecard |
| Evidence | A measured fact or bounded visual claim about a Shot | insight |
| Finding | A checkable issue or observation about one Shot | Fault |
| Technique | A finite photographic method in the taxonomy | skill |
| Technique Map | The longitudinal record of observed and recurring Techniques | skill graph, curriculum |
| Tendency | A neutral repeated pattern across Shots | habit, flaw, default |
| Keeper | A Shot the photographer positively marks as valued | like, model pick, rejected/unrejected binary |
| Experiment | One optional bounded question to try, with type-specific evidence | Quest, challenge, assignment, compulsory camera mode |
| Variation | One optional route inside Explore or Compare | criterion, correct answer |
| Experiment Record | The question, Baseline, explicit Shot set, type-specific evidence, and Change left by one Experiment | advice transcript |
| Inspiration | Sourced reference material explicitly studied outside the Photographer's longitudinal record | Shot, Keeper, Photographer Evidence, generated filler |
| Deconstruction | A shareable, image-led draft rendered from stored Evidence and labelled reads | scorecard, automatic social post |
| Criteria | The checks declared before a Reproduce result | Explore instruction, rubric score |
| Verdict | The Judge's result against Reproduce Criteria | Explore result, quality judgment, progress verdict |
| Change | A measured difference between comparable earlier and later behaviour | Progress without a user-grounded goal |
| Journey Update | The evidence-backed longitudinal conclusion shown when the record meaningfully changes | report card |
| Intent | The photographer's optional statement of what they are trying to make | inferred purpose presented as fact |
| Companion | The quiet camera-side partner that sees and hears the current Scene when summoned | generic camera, narrator, Experiment enforcer |
| Live Scene Session | An explicit temporary audio-and-camera conversation before the shutter | always-on recording, post-Shot review |
| Scene Probe | A temporary low-resolution fallback used to inspect the current Scene without audio | Shot, Keeper, training history |

"Eye" belongs in the promise, such as "Learn to see like yourself." It is not a metric. "Style" is an emerging interpretation supported by repeated Tendency and Keeper signals, never a label the model declares.

An Experiment may do one of three jobs:

1. Explore asks what happens across two to four optional Variations. It has no pass, fail, or Verdict.
2. Reproduce tests a Keeper-associated pattern deliberately. It may use fixed Criteria and a Verdict.
3. Compare preserves two alternatives of one changed variable and asks which result the photographer values.

One Experiment may remain open as an offer, but the camera starts free. Only explicitly selected Shots join it. Pausing or leaving is not failure.

A Shot may belong to one Scene and Shoot through capture continuity and separately belong to one Capture Session through explicit Experiment participation. Those memberships are orthogonal. Inspiration is not a Shot and belongs to neither.

## 6. Agent depth

The audience cannot audit an AI critic, so the critic must audit itself.

Expertise belongs in versioned, replayable Technique playbooks and domain code. Prompts interpret visual ambiguity and write language. They do not hide thresholds, promotion rules, excuses, or Reproduce conditions. Explore has no pass condition for a prompt to hide.

The agent system must:

- refuse when Evidence does not support a claim;
- escalate only when a cheap reading leaves a consequential ambiguity;
- plan an Experiment from the longitudinal record;
- remember Shot Evidence, Experiment history, constraints, Intent, and explicit preferences;
- check whether comparable behaviour changed after an explicit Experiment attempt;
- synthesize a settled Shoot instead of repeating one critique for every member Shot;
- choose whether to explain, ask one consequential Intent question, offer Explore, offer Reproduce, or stay silent before generating prose;
- leave a Shoot Record and optional Deconstruction after the chosen workflow;
- retire or change an approach only after repeated comparable results, not one miss.

Depth already present includes structured agent outputs, per-Shot Runs, persisted Scene and Shoot membership, a Shoot barrier and deterministic synthesis, typed Scout choice including consequential Ask, scoped Photographer memory, Mine/Inspiration authority, corrected Explore, deterministic Reproduce mechanics, measurement vetoes, abstention, Capture Session barriers, Deconstruction, and post-Experiment comparison. Gaps include advice adaptation across repeated outcomes, broader Intent consumers, and labelled real-agent evaluation. See [agents](agents.md) and [market comparison](market-agent-comparison.md).

The key causal limit stays explicit: Shoots may say behaviour changed after an Experiment. It may not claim the Experiment caused the Change.

## 7. Pitch

Headline:

> Learn to see like yourself.

One-liner:

> Shoot freely. Shoots turns each Shoot into evidence of what you are learning.

The product question:

> Which photographic decisions am I making repeatedly, which can I now make on purpose, and how is that changing across my Shoots?

The sentence competitors do not say:

> Shoots does not score your photographs; it shows which photographic decisions are becoming yours.

## 8. What Shoots refuses to be

Shoots is not:

- a single-Shot score or critique app;
- an editor, filter, generator, culling utility, or social feed;
- a course, skill tree, streak system, or homework machine;
- a professional manual-camera replacement;
- a chatty viewfinder that corrects every frame;
- an Inspiration feed that competes with social media or mistakes another photographer's work for the user's Evidence;
- a location tracker or travel guide;
- a system that captures a real Shot without the photographer pressing the shutter.

Director and generated reference clips are outside the core loop: no automatic topic, subscription, or UI. The optional legacy call remains only as a manual capability. Inspiration may be studied and may seed an Explore, but it is never counted as the Photographer's work.

Competitors already claim personal style, progress, critique, and personalised challenges. Shoots cannot differentiate by repeating those promises. It differentiates by separating measurement, model opinion, and photographer signal, then showing the Evidence behind every Change claim. See [market comparison](market-agent-comparison.md).

## 9. The system-camera Companion

Android is the daily Companion around the phone's normal camera, not a replacement camera app.

Boundaries:

- The camera starts free. An offered Experiment is available, not compulsory.
- Capture-continuous Shots are assembled into Scenes and a Shoot in the background; the photographer does not maintain that grouping.
- The primary reflection is a settled Shoot receipt, not one interruption per Shot.
- Explicit Intent comes first. An Experiment may support it, offer a Variation, or stay out of the way.
- Only Shots explicitly selected for an Experiment enter its Record.
- Current light, weather, temperature, environment, and location facts appear only when photographically relevant or requested.
- A place fact may spark one useful question or adaptation. Trivia by itself is not coaching.
- Silence is the default. A Live Scene Session begins only when summoned and may be interrupted at any time.
- It asks a good question when Intent would resolve ambiguity.
- It may remember explicit location notes and preferences. It does not build hidden movement history.
- It may ask the photographer to move, inspect later Scene frames, and compare what is visible. It cannot claim to choose or inspect an angle the phone has not seen.
- Live Scene frames and a Scene Probe never enter the Technique Map or Journey. The photographer must use the shutter to create a Shot.
- The internal cell grid never reaches the photographer. The Companion shows a human guide, arrow, crop region, or plain direction.
- Intent may mute a conflicting local warning, such as zebras for a declared silhouette.

The release excludes the earlier free-form Android Ask, custom viewfinder, microphone, Gemini Live, and Scene frames. The current one-tap Scout Question is a bounded authority action inside the unattended longitudinal loop, not a live camera coach.

Android and web are two clients of one Shoots identity. Android now uses native Google identity, one build-configured service origin, direct Shot ingress, and optional separate Drive authority. Pairing endpoints remain temporarily for older APKs; the new client has no pairing or server-address UI.

Foreground and background have separate acceptance clocks. A ready Live Scene Session targets first audio at or below 1.5 seconds median and 3 seconds at p90 over at least twenty real-device turns. Deep Analysis stays corroborated and may take longer, but it cannot lock the camera.

The selected visual system is Companion-led Ink + amber. Ink holds the Scene and archive; warm white carries readable content; amber is reserved for an offered or selected Experiment, a Companion suggestion, or a selected action. It never grades quality. Red is reserved for a Finding that needs attention, and generic green success is removed from product surfaces.

## 10. Success test

The idea can compete. The current submission is not ready to win.

Idea risk is medium. Photography may appear less operational than business automation, so the completed background work must be visible. Execution risk remains high because configured physical acceptance, Cloud deployment, and submission artifacts still need proof.

The chief failure mode is building a chatty camera demo. Judges would see a generic multimodal coach and miss the Taskmaster loop.

The next pass test is one continuous Shoot-level run:

1. Start with a real Shot history and open the normal Android camera.
2. Make several free Shots across at least two capture-continuous Scenes without uploading, tagging, or pressing Analyse.
3. Wait for every member Run and show one settled Shoot Record with exact membership and terminal coverage.
4. Show what repeated, what varied, and which statements are measured, model-read, or photographer-owned.
5. Show Scout's stored choice to explain, ask, offer an implemented Experiment, or stay silent, including its warrant.
6. Start one explicit Capture Session, freeze its immutable ordered manifest, and let every member settle.
7. Show type-specific Experiment Evidence, comparable Change, and Journey without claiming causation or overall quality.
8. Generate a small Deconstruction draft and show that no Inspiration entered Photographer memory.
9. Show the Google Cloud execution, barriers, and architecture.

After watching, a stranger must be able to say: "It turned an ordinary Camera session into a learning record, chose the kind of help the Evidence supported, and checked what happened next." If they only say "it gives photography advice," the demo failed.

The fallback keeps Android as a thin capture Companion and cuts new context features. The longitudinal loop survives. The official Taskmaster rules and submission requirements remain the external acceptance test: [rules](https://allthingsagentichackathon.devpost.com/rules), [submission page](https://allthingsagentichackathon.devpost.com/), and [FAQ](https://allthingsagentichackathon.devpost.com/details/faqs).

## 11. Shoot-level learning record

The photographer's own description settled the primary unit and the desired outcome:

> I take many Shots in one session. I do not want to upload or inspect each one. I want to shoot freely, know whether a good result came from a Technique I can repeat, compare myself with my earlier work, and share a visual deconstruction of how I made it.

The resulting decisions are:

1. Shot remains the atomic media and Evidence record. It is not the completed learning work.
2. Capture continuity groups Shots into Scenes and Scenes into one natural Shoot. Visual similarity cannot invent event membership.
3. A Shoot settles only after all member Runs are complete or terminal, then leaves one Shoot Record.
4. Recurrence, deliberate Reproduce Evidence, condition coverage, Keeper counts, and Change remain separate quantities rather than one score.
5. Scout chooses a bounded kind of help before any prose: explain, ask, Explore, Reproduce, or evidenced silence.
6. Corrected Explore is the next Experiment type after the Shoot Record. It records Variations and observed differences without a Verdict.
7. Manual imports declare Mine or Inspiration. Inspiration may be studied but cannot enter the Photographer's longitudinal record.
8. Scribe may prepare a Deconstruction carousel from stored Evidence. The photographer chooses any Keeper cover and controls posting.
9. The system evaluates whether its intervention produced the declared observable difference; it does not evaluate artistic worth.
10. Image-led learning keeps what, why, one Move, and one visible condition together. More prose or generic grids do not deepen the advice.

Architecturally, the existing per-Shot pipeline remains. A new aggregate layer assembles and settles Shoots, synthesizes Scene Variations, updates multi-scale memory, asks Scout for a typed choice, and asks Scribe for an optional artifact. This is a deeper workflow, not a larger critic swarm.

## Open decisions

- The minimum sample and comparability rules for a user-grounded improvement claim.
- The exact capture-continuity thresholds that separate Scenes and Shoots, including late Camera discovery.
- The minimum deterministic Variation set needed before one bounded Shoot-level model read adds value.
- Which carousel pages can be drafted without a Keeper and how the photographer selects a cover.
- Which Live Scene transcript details remain in ActivityEvent after raw audio and frames are discarded.
