# Product decisions

Locked through the nine-stage product interrogation on 2026-08-25 and corrected from real-phone use on 2026-08-26. This file records why the product has its current shape. [Product](product.md) states the result. [Feature list](feature-list.md) tracks what still has to exist.

## 1. Audience first

Shoots is for a self-directed post-beginner hobbyist photographer.

This person:

- has a capable phone or camera and shoots often on walks, weekends, and trips;
- already revisits and selects Shots, but has no recurring mentor;
- understands basic advice, so another rule-of-thirds lesson will not help;
- has enough work for patterns to exist, but cannot tell development from luck;
- wants photography to remain a quiet, enjoyable part of life.

In their own words:

> I want to see like a photographer. I want a few Keepers I am proud of. I want proof that March-me and August-me are different. I want a style that becomes mine. I do not want my walk to become homework.

What they want from the product:

- one useful move today;
- silence until they ask or one unusually valuable opportunity appears;
- praise first, supported by Evidence;
- respect for Intent;
- comparisons against their own earlier work;
- almost no setup, tagging, or review forms.

What they want for themselves is the product outcome: a more deliberate and recognisable way of seeing that no longer depends on the app.

Memory here means photographic memory: Shot Evidence, Technique recurrence, visual comparison, Experiment history, constraints, Intent, and explicit preferences. It is not a chat transcript presented as expertise, a nostalgic gallery, or an invisible personality profile.

They quietly quit when the app nags, grades, assigns generic lessons, mistakes Intent for error, or asks them to maintain the system.

## 2. The problem

The long-term problem is:

> I cannot see how my eye is developing.

The precise question is:

> What patterns keep appearing across my Shots, and can I deliberately reproduce the ones present in my Keepers?

The mechanism is distributed evidence. A Tendency exists across many Shots and months, not inside one frame. The photographer remembers favourites and recent failures, but cannot reliably aggregate placement, distance, light, subject, dwell, Technique use, and change over time. Single-Shot critique forgets the next day. Generic advice never checks whether the photographer already does it, values it, or changes after trying it.

"Why are my Shots boring?" remains a useful entry question, not a diagnosis Shoots can prove. The research found recurring professional advice: decide what the Shot is about, work the Scene, simplify, wait, seek useful light, impose a constraint, and edit alternatives. The advice is already available. The missing part is a memory that finds this photographer's repeated defaults and checks whether an intervention changes them. See [boring Shots advice research](boring-shots-advice-research.md).

## 3. The work accomplished

Shoots turns an accumulating Shot archive into a checked record of photographic behaviour. It detects a Tendency, offers one optional personal Experiment, records only the Shots the photographer explicitly includes, and reports what changed afterward.

A human doing the same work would have to inspect every Shot, maintain comparable measurements, find repeated patterns, select an appropriate exercise, preserve a baseline, inspect the result, and recompute the record. Shoots does that work in the background.

The work leaves three finished artifacts:

1. The Technique Map records what the Evidence has observed and what has recurred.
2. The Experiment Record preserves the question, reason, Baseline, explicit Shot set, type-specific evidence, and post-Experiment Change. Only Reproduce carries Criteria and Verdicts.
3. The Journey Update states what repeats, what became repeatable, and what changed, with a source for every claim.

Advice alone is not work accomplished. A paragraph from a model without these artifacts is decoration.

## 4. The honesty line

| Claim class | What belongs there | What it may say |
|---|---|---|
| Measured by the system | EXIF, Tone, Motion, placement, framing, time, recurrence, corroboration, Criteria checks, profile differences | "Centred placement appeared in 12 of 18 Shots." |
| Model opinion | subject read, mood, narrative, moment, interpretation, artistic suggestion | "The isolation makes the frame feel quieter." |
| Known only from the photographer | Intent, preference, whether a Shot is a Keeper, whether a Change feels like improvement | "You marked three low-angle Shots as Keepers." |

The smallest optional input with the largest honesty gain is the Keeper mark.

A Keeper is positive-only. Marked means valued. Unmarked means unknown, not rejected. The current boolean implementation cannot support this distinction honestly and must change before Keeper correlations become product claims.

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
| Scene | One photographic situation at one place and time | a visual-similarity cluster presented as the same event |
| Evidence | A measured fact or bounded visual claim about a Shot | insight |
| Finding | A checkable issue or observation about one Shot | Fault |
| Technique | A finite photographic method in the taxonomy | skill |
| Technique Map | The longitudinal record of observed and recurring Techniques | skill graph, curriculum |
| Tendency | A neutral repeated pattern across Shots | habit, flaw, default |
| Keeper | A Shot the photographer positively marks as valued | like, model pick, rejected/unrejected binary |
| Experiment | One optional bounded question to try, with type-specific evidence | Quest, challenge, assignment, compulsory camera mode |
| Variation | One optional route inside Explore or Compare | criterion, correct answer |
| Experiment Record | The question, Baseline, explicit Shot set, type-specific evidence, and Change left by one Experiment | advice transcript |
| Inspiration | Optional sourced reference material supporting an Experiment | the Experiment itself, generated filler |
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

## 6. Agent depth

The audience cannot audit an AI critic, so the critic must audit itself.

Expertise belongs in versioned, replayable Technique playbooks and domain code. Prompts interpret visual ambiguity and write language. They do not hide thresholds, promotion rules, excuses, or Reproduce conditions. Explore has no pass condition for a prompt to hide.

The agent system must:

- refuse when Evidence does not support a claim;
- escalate only when a cheap reading leaves a consequential ambiguity;
- plan an Experiment from the longitudinal record;
- remember Shot Evidence, Experiment history, constraints, Intent, and explicit preferences;
- check whether comparable behaviour changed after an explicit Experiment attempt;
- retire or change an approach only after repeated comparable results, not one miss.

Depth already present includes structured agent outputs, deterministic Reproduce mechanics in the legacy Explore path, corroboration, measurement vetoes, abstention, persistent state, and post-Experiment profile comparison. The legacy path proves the machinery but applies it to the wrong question. Gaps include corrected Explore semantics, Reproduce and Compare, structured learner memory, bounded escalation, Live Scene tools, and labelled real-agent evaluation. See [agents](agents.md) and [market comparison](market-agent-comparison.md).

The key causal limit stays explicit: Shoots may say behaviour changed after an Experiment. It may not claim the Experiment caused the Change.

## 7. Pitch

Headline:

> Learn to see like yourself.

One-liner:

> Shoots learns from every Shot, offers one personal Experiment, and tracks what changes.

The product question:

> What patterns keep appearing across my Shots, and can I deliberately reproduce the ones present in my Keepers?

The sentence competitors do not say:

> Shoots can prove what changed. It never pretends the model knows whether your photography got better.

## 8. What Shoots refuses to be

Shoots is not:

- a single-Shot score or critique app;
- an editor, filter, generator, culling utility, or social feed;
- a course, skill tree, streak system, or homework machine;
- a professional manual-camera replacement;
- a chatty viewfinder that corrects every frame;
- an Inspiration feed that competes with social media;
- a location tracker or travel guide;
- a system that captures a real Shot without an explicit shutter or voice command.

Director and generated reference clips are outside the core loop: no automatic topic, subscription, or UI. The optional legacy call remains only as a manual capability. Inspiration may exist as sourced reference material, but it is not the work Shoots sells.

Competitors already claim personal style, progress, critique, and personalised challenges. Shoots cannot differentiate by repeating those promises. It differentiates by separating measurement, model opinion, and photographer signal, then showing the Evidence behind every Change claim. See [market comparison](market-agent-comparison.md).

## 9. The system-camera Companion

Android is the daily Companion around the phone's normal camera, not a replacement camera app.

Boundaries:

- The camera starts free. An offered Experiment is available, not compulsory.
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

The release excludes the earlier Android Ask, custom viewfinder, microphone, Gemini Live, and Scene frames. Those remain later work only if the unattended longitudinal loop first proves useful.

Android and web are two clients of one Shoots identity. Android now uses native Google identity, one build-configured service origin, direct Shot ingress, and optional separate Drive authority. Pairing endpoints remain temporarily for older APKs; the new client has no pairing or server-address UI.

Foreground and background have separate acceptance clocks. A ready Live Scene Session targets first audio at or below 1.5 seconds median and 3 seconds at p90 over at least twenty real-device turns. Deep Analysis stays corroborated and may take longer, but it cannot lock the camera.

The selected visual system is Companion-led Ink + amber. Ink holds the Scene and archive; warm white carries readable content; amber is reserved for an offered or selected Experiment, a Companion suggestion, or a selected action. It never grades quality. Red is reserved for a Finding that needs attention, and generic green success is removed from product surfaces.

## 10. Success test

The idea can compete. The current submission is not ready to win.

Idea risk is medium. Photography may appear less operational than business automation, so the completed background work must be visible. Execution risk remains high because configured physical acceptance, Cloud deployment, and submission artifacts still need proof.

The chief failure mode is building a chatty camera demo. Judges would see a generic multimodal coach and miss the Taskmaster loop.

The 48-hour pass test is one continuous run:

1. Start with a real Shot history.
2. Open the normal Android camera from the signed-in Shoots client and verify one free Shot arrives unattended.
3. Reserve a Reproduce Capture Session, take three Shots, and freeze one immutable ordered manifest.
4. Keep shooting available while the cloud pipeline reads in the background.
5. Open the Evidence behind a Tendency.
6. Show why the Experiment was offered and what its type records.
7. Show every batch member, its Verdict or abstention, the deterministic representative, and one settled summary.
8. Show the resulting Change and Journey Update without claiming causation.
9. Show the Google Cloud execution and architecture.

After watching, a stranger must be able to say: "It remembered the photographer's work, found a recurring pattern, chose what to test, and verified what changed." If they only say "it gives photography advice," the demo failed.

The fallback keeps Android as a thin capture Companion and cuts new context features. The longitudinal loop survives. The official Taskmaster rules and submission requirements remain the external acceptance test: [rules](https://allthingsagentichackathon.devpost.com/rules), [submission page](https://allthingsagentichackathon.devpost.com/), and [FAQ](https://allthingsagentichackathon.devpost.com/details/faqs).

## Open decisions

- The minimum sample and comparability rules for a user-grounded improvement claim.
- Which Live Scene transcript details remain in ActivityEvent after raw audio and frames are discarded.
- Which later Experiment type earns implementation after Reproduce: Explore or Compare.
