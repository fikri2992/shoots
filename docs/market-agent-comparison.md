# Shoots agent system against the current market

Research note, 2026-08-25.

This is a market and implementation snapshot using the current product vocabulary.
Competitor language such as challenge, score, and progression is retained only when
describing those products. Use [feature list](feature-list.md) for build status.

## Verdict

Shoots is not the first AI photography coach, the first live camera coach, the
first product with personalized practice, or the first product to compare a
retake with an earlier Shot. Those positions are already occupied.

Its defensible difference is architectural:

> No product in this sample publicly documents the same full chain: an
> automatic Shot trigger, separately bounded expert readers, measured Evidence
> that can overrule model opinion, a persistent Technique Map and Tendency Profile, a
> fixed-criteria Judge, an artifact written back to the photographer's Drive,
> and a personal Experiment that is withheld when the archive supports no Direction.

That difference is real, but it is mostly invisible until the demo shows a
disagreement, a deterministic decision, an external action, and the next state
transition. Saying "eight agents" will not establish it. [Kiratiq already
markets a 10-agent critique panel](https://www.kiratiq.com/), and several
simpler products already deliver the consumer outcome Shoots describes.

The closest direct competitors for deliberate practice are PickEpic,
ShutterCoach, and PhotoCritique.ai. The strongest benchmarks for work completed
are HauShot and Aftershoot. Google Pixel Camera Coach and GudoCam are ahead at
the exact camera moment.

## Method and limits

- Product behavior comes only from official product pages, support docs, and
  first-party app listings retrieved on 2026-08-25.
- Vendor claims were not independently tested. "Available" means an official
  page or store listing was live, not that quality or adoption was verified.
- Most vendors do not publish their internal routing, prompts, models, scoring
  contracts, or state machines. Those fields remain **not disclosed**. Product
  copy is not evidence of a multi-agent architecture.
- Shoots was read from the local working tree on 2026-08-25. Current build claims
  below are limited to behavior present in that tree. Explicit Intent and the
  scene-aware Android Companion remain unbuilt.

## What Shoots actually implements

| Dimension | Current behavior | Evidence in this repo |
|---|---|---|
| Trigger | A Drive or Android Shot starts the same event-driven pipeline. The first complete archive read, a Criteria-met Experiment, or the daily tick may ask Scout to issue; no supported Direction means silence. | `backend/app/api/deps.py`; `backend/app/services/scout.py`; `backend/app/api/tasks.py` |
| Perception | Ingest measures EXIF, Tone, and Motion. Analyst runs Technician, Composer, and Storyteller concurrently with different instructions and inputs, then a Synthesizer writes the critique. | `backend/app/agents/analyst.py:152-165`; `docs/domain-model.md`, decision 18 |
| Evidence control | The panel requires agreement. Measured motion can corroborate or veto a claimed Technique after the model calls. Unknown Technique ids and invalid cells are rejected at validation boundaries. | `backend/app/agents/analyst.py:326-346`; `backend/app/domain/panel.py:120-180` |
| Planning | Pure code derives an Experiment Direction from the complete readable archive. Scout may choose only a supported Technique, then applies recency and gear constraints; there are no levels, locks, prerequisites, or coverage quotas. Gemini Search grounds the brief and references. Solar arithmetic chooses delivery time. | `backend/app/domain/tendency.py`; `backend/app/domain/scout.py`; `backend/app/services/scout.py` |
| Persistent memory | The Technique Map stores attempts, corroboration, state, and Shot ids. The Tendency Profile spans the readable archive and distinguishes deterministic dimensions from model-read dimensions. Keepers, constraints, Baselines, Verdicts, Changes, and ActivityEvents persist without quality scores. | `backend/app/services/profile.py`; `backend/app/domain/entities.py`; `backend/app/domain/tendency.py` |
| Verification | Pure code checks frozen EXIF bounds and required vision Evidence. Unknown required Evidence makes Judge abstain and leaves the Experiment open; a known hard miss can still settle Criteria as not met. Gemini writes feedback but cannot change the result. Only Judge records a Verdict. | `backend/app/domain/judge.py`; `backend/app/services/judge.py` |
| External action | Android captures and uploads into the pipeline. Scribe uploads or updates an annotated review in `Shoots/Reviewed/`; Scout sends a push; Coach can issue an Experiment, remember constraints, and read the Technique Map. Director/Veo is not in the product loop. | `android/app/src/main/java/com/shoots/app/Api.kt`; `backend/app/services/scribe.py`; `backend/app/services/coach.py` |
| Adaptation | A Criteria-met Verdict closes the Experiment transactionally and may trigger another Direction check. A Criteria-not-met Verdict leaves it open. After closure, Scout compares the frozen Baseline with later comparable Shots and records a Change without claiming causation or improvement. | `backend/app/infra/repository.py`; `backend/app/services/judge.py`; `backend/app/services/scout.py` |
| Concurrency refusal | One atomic open slot prevents duplicate Experiments. Verdict, Skip, Expire, delivery, and optional legacy writes cannot overwrite a competing terminal transition. | `backend/app/infra/store.py`; `backend/app/infra/repository.py` |

The strongest design decision is authority separation. Models interpret and
write. Code owns taxonomy, measurement, comparability, and Experiment transitions.
The model that helps write an Experiment cannot record its Verdict.

## Closest systems

### 1. Google Pixel Camera Coach

The user turns Camera Coach on, chooses what they want in the frame or asks for
inspiration, and cloud-based Gemini models scan the current scene. The camera
then presents a sequence of framing, lighting, angle, and camera-mode steps. The
user advances each step and presses the shutter.

- Trigger and perception: explicit user request, one current scene.
- Planning: a short scene-specific instruction sequence.
- Action: the photographer moves the camera and presses the shutter.
- Memory, result verification, and cross-Shot adaptation: not publicly
  described.
- Loop type: one-shot pre-capture guidance.

Sources: [Pixel Camera Help](https://support.google.com/pixelcamera/answer/17367411?hl=en),
[Google product explanation](https://blog.google/products-and-platforms/devices/pixel/how-to-use-camera-coach/).

Pixel makes scene-aware viewfinder coaching non-unique. Shoots does not compete at
that immediate camera moment in the Taskmaster build. Android observes approved
Camera media, uploads unseen originals, carries an explicitly selected Reproduce id,
and shows the backend Run state. Shoots differentiates through longitudinal memory,
fixed Keeper references, and checkable result records.

The locked target corrects two problems found on a physical phone. The camera opens
free, and an Experiment affects only Shots the photographer explicitly includes.
A summoned Live Scene Session receives audio and low-rate camera frames, may offer a
question or Variation, and can call a cell-ref guide tool. Scene conversation becomes
load-bearing; longitudinal Evidence and type-specific Experiment Records remain the
difference Pixel does not publicly describe.

### 2. GudoCam

GudoCam is a more technically explicit live-camera competitor. A local Core ML
model detects a main subject and one of 14 composition types at about 250 ms,
then draws the relevant guide and alignment feedback in the viewfinder. An
opt-in external LLM reads the current frame for one-line advice on composition,
light, position, zoom, and exposure. After capture, the user may request scores
and critique across five dimensions. Its App Store listing also advertises a
portfolio and Weekly Challenge.

- Trigger and perception: continuous on-device composition detection; optional
  user-triggered LLM advice.
- Planning: one of 14 guide choices plus immediate corrections.
- Action: haptic alignment and camera guidance; the photographer shoots.
- Memory: portfolio and challenges are advertised, but no cross-Shot decision
  model is documented.
- Verification: guide alignment and a post-shot AI score. No fixed practice
  Criteria or independent verifier is disclosed.
- Loop type: live composition control plus optional critique.

Sources: [GudoCam product and architecture FAQ](https://gudocam.com/en/),
[GudoCam App Store listing](https://apps.apple.com/us/app/gudocam-ai-photography-guide/id6759212077).

GudoCam already tells the clean "fast arithmetic or vision loop plus slow LLM
advice" story. Shoots must demonstrate why its three-reader Evidence and
longitudinal Experiment loop matter after the shutter.

### 3. ShutterCoach

ShutterCoach analyzes an uploaded Shot across composition, lighting, exposure,
color, focus, and storytelling. Photo DNA updates from critique history and
tracks strengths, growth areas, genres, and style. AI-generated Daily Challenges
use skill level and Photo DNA, and the user completes a challenge by submitting
a Shot that meets its criteria. The product also advertises EXIF-aware critique,
reshoot comparison, batch Shoot reports, weekly insights, and follow-up chat.

- Trigger and perception: manual Shot or batch import; six-skill and EXIF-aware
  cloud analysis.
- Planning: personalized Daily Challenges based on Photo DNA.
- Action: challenge prompt, critique, chat, culling, and reshoot comparison.
- Memory: persistent critique history, Photo DNA, achievements, and progress.
- Verification: the submitted Shot is checked against challenge criteria, but
  the scoring contract and whether any checks are deterministic are not
  disclosed.
- Loop type: a real, user-driven longitudinal deliberate-practice loop.

Sources: [ShutterCoach support](https://shuttercoach.app/support),
[ShutterCoach product page](https://shuttercoach.app/),
[official press kit](https://shuttercoach.app/press/).

This invalidates claims that Shoots alone learns strengths, detects recurring
weaknesses, personalizes challenges, leads with praise, or proves progress with
a reshoot. Shoots' stronger claim is how Evidence and Verdict authority are
bounded and audited.

### 4. PhotoCritique.ai

The photographer manually uploads a Shot and chooses experience level, feedback
style, focus, category, and any intentional technique. The service provides a
critique, then offers Challenge Paths, Next Best Shot, weekly nudges, Edit and
Re-shoot Loops, follow-up Q&A, a Progress Coach over the full critique history,
a Style Fingerprint, a 30-Day Growth Sprint, and portfolio reports. Some insight
jobs run in the background after the user presses Refresh. The changelog says
some Growth features use GPT-5.4, but does not document agent roles or the
verifier.

- Trigger and perception: manual upload with explicit intent and critique
  configuration.
- Planning: challenge paths, Next Best Shot, and history-derived action plans.
- Action: dashboard reports plus print, email, and PDF outputs on paid plans.
- Memory: permanent critiques, full-history Progress Coach, Style Fingerprint,
  sprint and report history.
- Verification: challenge rubric scores and before-versus-after score
  comparisons. The score source and decision contract are not disclosed.
- Loop type: a real, user-driven longitudinal critique and practice loop.

Sources: [How PhotoCritique works](https://photocritique.ai/how-it-works),
[official changelog](https://photocritique.ai/changelog),
[current plan matrix](https://photocritique.ai/pricing).

PhotoCritique is already shipping much of `docs/product.md` as product behavior.
Shoots' Tendency Profile, Intent, and Journey concepts should not be pitched as
market novelty until they exist and use more defensible measurements than a
whole-Shot score.

### 5. ShotLogic

ShotLogic keeps a profile of the photographer's camera bodies, lenses, and
accessories. The user photographs a scene, types, or speaks a question. Its AI
reads light, subject, and environment, cross-references the gear profile and a
Shot Card library, then returns aperture, shutter, ISO, lens, and technique
guidance. It can also generate social captions and gear recommendations.

- Trigger and perception: explicit Snap & Ask, text, or voice request.
- Planning: scene-specific settings constrained by owned gear and reference
  cards.
- Action: advice, matched cards, captions, and retailer links. The photographer
  applies every camera setting.
- Memory: gear inventory, favorites, and pinned prompts. No skill progression is
  advertised.
- Verification and adaptation: no result check, retake comparison, or
  cross-Shot learning is publicly described.
- Loop type: contextual field assistant.

Source: [ShotLogic official product page](https://www.shotlogic.app/).

ShotLogic's planner is narrower than Scout, but the value is easier to explain:
settings for this scene with this gear. Shoots should retain the same clarity
when it explains why Scout selected a Technique.

### 6. PickEpic

PickEpic ships the clearest curriculum competitor. It has 30 structured
challenges across five tiers, daily challenges, five tracked skills, XP,
milestones, and unlocks as skills improve. Users submit Shots for instant AI
feedback on the target Technique. It also scores Shots in several evaluation
modes, ranks up to ten alternatives, extracts and ranks video frames, provides
a live reference overlay, and keeps analysis history. The listing distinguishes
on-device image scoring from cloud AI critique and challenges, but does not
publish its models, evaluator contract, or planning logic.

- Trigger and perception: user opens a challenge or analysis and submits a Shot;
  some library scoring runs on device.
- Planning: structured tier progression and daily assignments.
- Action: feedback, XP, unlocks, rankings, Shot selection, overlay capture,
  and video-frame export.
- Memory: skill XP, level, milestones, streak, and critique history.
- Verification: AI evaluates challenge submissions and awards progress. No
  independent or deterministic criteria layer is disclosed.
- Loop type: a closed, game-like deliberate-practice curriculum.

Source: [PickEpic App Store listing](https://apps.apple.com/ca/app/pickepic/id6748054107).

Shoots cannot use "Experiment, Judge, Technique Map" as proof of novelty by themselves.
The market already has challenges, submission judgments, progression, and
unlocking. Shoots' distinction is a cited Experiment Direction based on the
photographer's own Tendency rather than a fixed tier map, plus a Judge whose
authority is separate from the model that writes the Experiment.

### 7. HauShot

HauShot narrows the job to real-estate photography and completes more of it. A
room-specific voice coach guides height, angle, light, and level. AutoShot fires
the camera when the phone reaches the target level. The workflow then bulk
corrects the property set, applies color, brightness and perspective edits,
offers staging, twilight conversion and item removal, lets the user refine or
revert, and produces listing-ready downloads and captions. The product says
Gemini performs image corrections. The voice coach's model, room planner,
verification rules, and persistent adaptation are not disclosed.

- Trigger and perception: user starts a property Shoot; live room and level
  guidance follows.
- Planning: room-specific capture recipe.
- Action: automatic shutter, batch edit, staging, copy, and delivery.
- Memory: projects, property allowance, and team pool. No learning profile is
  advertised.
- Verification: target level triggers capture; the user reviews generated
  outputs and can rerun or revert. No quality gate is documented.
- Loop type: a narrow capture-to-deliver production workflow.

Sources: [HauShot official product page](https://www.haushot.com/),
[Google Play listing](https://play.google.com/store/apps/details?id=com.cnkyoun.hauskore).

HauShot is the strongest answer to "what work was accomplished?" in this set.
It does not teach a photographer's eye, but it turns a property visit into
listing-ready assets. Shoots needs an equally concrete terminal state, such as
"reviewed Shot written back, Experiment verified, next Experiment scheduled."

### 8. Aftershoot and Narrative Select

These are adjacent post-shoot incumbents, not photography coaches.

Aftershoot can run an automated first-pass cull using user preferences, Shoot
genre, and previous culls. It groups duplicates, chooses candidates, learns from
final selections, applies a trained editing profile, retouches albums, and can
deliver branded galleries. The photographer imports a Shoot and reviews the
result, but the product completes substantial production work. Its models and
internal routing are not public.

Narrative Select stays deliberately assistive. It groups scenes, ranks frames,
checks faces, eye states, focus, expressions, and key elements, then exports the
photographer's selections to Lightroom, Photoshop, or Capture One. Its public
position is that AI should speed creative judgment rather than replace it.

- Trigger and perception: user imports a Shoot; both analyze batches and scene
  groups rather than isolated Shots.
- Planning: Aftershoot adapts selections and edits to learned preferences.
  Narrative prioritizes likely candidates and defects for human review.
- Action: Aftershoot culls, edits, retouches, and delivers. Narrative groups,
  ranks, filters, and exports.
- Memory: Aftershoot learns culling and editing style across Shoots. Narrative's
  public pages do not describe a cross-Shoot preference model.
- Verification: both expose assessments or selections for human review. Neither
  is a deliberate-practice Judge.
- Loop type: production automation or decision support, not coaching.

Sources: [Aftershoot product page](https://aftershoot.com/),
[Aftershoot automated versus assisted culling](https://support.aftershoot.com/en/articles/9190187-the-difference-between-ai-assisted-culling-ai-automated-culling),
[Narrative Select](https://narrative.so/select),
[Narrative face assessments](https://narrative.so/select/face-assessments).

Aftershoot is the best benchmark for adaptation to style. It learns from the
photographer's actual keep and edit decisions, not just model scores. Shoots'
current Technique Map tracks repeatable Technique Evidence. It does not yet learn
the photographer's selection preferences or an emerging style.

## Capability snapshot

| Capability | Shoots now | Strongest sampled benchmark | Honest result |
|---|---|---|---|
| Live viewfinder help | Not in the Taskmaster build; Phone Source leaves the normal camera untouched | Pixel, GudoCam, HauShot | Shoots does not compete at immediate scene coaching |
| Specialized perception | Three differently briefed readers plus measured EXIF, Tone, and Motion | GudoCam discloses local composition model; other internals unknown | Shoots has the most inspectable decomposition |
| Longitudinal learning | Whole-readable-archive Tendency Profile, Technique Map, exact Baselines, and provenance-scoped Change | ShutterCoach Photo DNA; PhotoCritique Progress Coach; Aftershoot learned style | Shoots is differentiated in evidence discipline, not existence of memory |
| Personal Experiment | Scout selects a corroborated Technique from a marked Keeper, freezes the exact reference and Criteria, then applies recency, gear, location, and light constraints; no supported Keeper means silence | ShutterCoach personalized challenges; PickEpic tier unlocks; PhotoCritique Next Best Shot | Shoots differentiates on evidence and refusal, not curriculum depth |
| Fixed verification | Pure EXIF checks plus bounded vision Evidence; model cannot change Verdict | Competitors advertise AI scores and challenge checks but do not publish authority boundaries | Shoots' clearest technical advantage |
| Work in another system | Reviewed Shot written to Drive; push delivery | Aftershoot gallery delivery and creative-app workflow | Shoots has credible external action, but Aftershoot's finished work is easier to value |
| Automatic background trigger | Drive Shot, scheduled tick, Criteria-met Experiment | None in this sample publicly describes an equivalent coaching trigger | Strong Shoots distinction |
| Failure replan | Not implemented | Not publicly documented by the sampled coaches | Open opportunity, and the missing proof of adaptive agency |
| Style and identity | Keeper-linked distributions exist; explicit style interpretation does not | Aftershoot culling and editing profiles; Photo DNA and Style Fingerprint | Shoots has an honest taste signal but not yet the identity layer |
| Intent handling | Inferred Technique and current Experiment; proposed explicit Intent is not implemented | PhotoCritique lets the photographer declare special techniques and critique focus | Shoots can currently misread intentional rule-breaking |

## What this means for the hackathon story

Do not lead with the number or names of agents. Lead with the separation of
authority and show it in motion:

1. A Shot arrives without a prompt.
2. Three expert readers disagree on a Technique.
3. Measured Evidence vetoes or corroborates the claim.
4. Cartographer updates only supported Technique Evidence.
5. Scout offers an Experiment only when the archive supports a Direction.
6. Judge applies Criteria that the feedback model cannot move.
7. Scribe writes the reviewed Shot into Drive; later comparable Shots leave a Change.
8. Criteria met closes atomically and asks Scout again; unsupported advice is silence.

The demo should expose the ActivityEvents and the exact Evidence behind the
transition. That is what makes the system look intentional rather than like
several prompts connected in sequence.

The next architectural improvement should be bounded failure adaptation, not
another agent persona. A failed Experiment should produce a classified reason, then
allow Scout to change timing, instruction, or required setup while preserving
the original Criteria. The next Shot must still face the same Judge. That would
demonstrate replanning without moving the goalposts.

## Safe and unsafe market claims

Safe:

> Shoots is an event-driven photography practice system. It separates visual
> interpretation, measured Evidence, planning, verification, and external
> action so no model can write an Experiment and declare its own success.

> In the products reviewed here, none publicly documents Shoots' combination of
> automatic Shot intake, multi-reader Evidence, fixed-criteria Verdicts, Drive
> writeback, and automatic next-Experiment planning.

Unsafe:

- "The first AI photography coach."
- "The only coach that learns your photography."
- "The only product with personalized challenges or progress tracking."
- "The only product that verifies improvement with a retake."
- "Multi-agent analysis is our innovation."
- "Shoots learns your style" before Keeper or Intent signals exist in the
  domain and implementation.

## Confidence

- **High:** feature and workflow descriptions quoted from official pages and
  store listings; Shoots authority boundaries read directly from source.
- **Medium:** comparisons of user-visible autonomy. They follow documented
  triggers and outputs, but the products were not run side by side.
- **Low or unknown:** competitor model topology, prompts, training data,
  deterministic checks, internal memory representation, failure recovery, and
  orchestration. Vendors generally do not publish them, so this note does not
  infer them.
