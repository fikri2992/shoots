# Learning path

> Product learning contract, 2026-08-26. This is not a curriculum or Technique
> ladder. The domain rules remain authoritative in [domain-model.md](domain-model.md),
> and implementation state remains in [feature-list.md](feature-list.md).

## The Photographer's problem

The primary user already knows how to use a phone camera and recognizes some
Techniques. They may take thirty Shots on a walk and post one to Instagram, but they
cannot answer:

> Am I making photographic decisions more deliberately, or am I randomly taking
> enough pictures to get lucky sometimes?

Single-Shot critique does not answer this. It forgets the other twenty-nine Shots,
turns interpretation into long prose, and cannot show whether the same decision
recurred across Scenes or later became repeatable. Community replies such as “good
picture, keep it up” also omit what should be kept up. Asking an expert repeatedly
costs time and social confidence.

The product must therefore do background accounting, not merely provide advice. It
observes ordinary Camera media, closes a natural Shoot, records the photographer's
decisions across its Scenes, and later compares that evidence with the same
photographer's earlier work. The photographer remains free to shoot the same subject,
try something new, ignore an Experiment, or mark a Keeper.

## What each unit can teach

| Unit | Question it can honestly answer | Artifact |
|---|---|---|
| Shot | What is visible or measured in this one frame? | Analysis, Findings, Moves, Technique Evidence, Run |
| Scene | How did I work one photographic situation? | Ordered Shot membership and observable Variations |
| Shoot | What decisions repeated or varied while I was out shooting? | Revisioned Shoot Record and short receipt |
| Experiment | Could I deliberately explore, reproduce, or compare one declared decision? | Type-specific Experiment Record |
| Journey | What changed across comparable evidence over time? | Journey Update with exact evidence references |

A good Shot is not proof of control. A recurring Technique is not proof of quality. A
Reproduce Verdict answers only its declared Criteria. Change is not automatically
improvement. Only the Photographer can supply taste through a Keeper, state Intent,
or say that a Change moved toward what they wanted.

## The learning loop

1. **Shoot freely.** Phone Source observes approved future Camera media without an
   upload ritual. Free Shots stay free; capture time never puts them in an Experiment.
2. **Account for the Shoot.** Capture continuity groups Shots into Scenes and one
   Shoot. Every member Run completes or becomes terminal before the current Shoot
   Record settles.
3. **See the decisions.** The receipt states how many Shots and Scenes were included,
   which measured or model-read decisions repeated, which varied, and what could not
   be read. It contains no quality score or best-Shot verdict.
4. **Choose only justified help.** Scout may explain the receipt, ask one consequential
   Intent question, offer a type-correct Experiment, or stay silent. It records the
   warrant and rejected routes before any model writes copy.
5. **Test deliberateness optionally.** Explore broadens possibilities, Reproduce tests
   declared Criteria against an exact Keeper reference, and Compare preserves
   alternatives for an optional Photographer preference. These types never borrow one
   another's outcome language.
6. **Compare with yourself.** Comparable later evidence may show Change in decision
   distributions or repeatability. The Journey preserves unchanged and insufficient
   evidence as real results.
7. **Adapt the next intervention.** Scout remembers what it offered, whether it was
   entered, what could be observed afterward, and whether the evidence was sufficient.
   Ignoring an offer is not failed advice; one Criteria miss is not a bad Shot.

Explore has two honest entrances. "Use my Tendencies" lets Scout choose from the
Photographer's current record and may freeze a comparable Baseline. "Choose a
Technique" starts from explicit curiosity, including a Technique not seen before. It
has no invented Baseline and cannot claim longitudinal Change against unrelated old
Shots. New to the record means unobserved, not missing or behind.

### How adaptation works now

The immutable Shoot Record keeps the original Scout route and warrant. A separate
Intervention Record is the current projection of what happened next:

| Observed event | Attempt state | Outcome claim |
|---|---|---|
| Explain or evidenced silence | `not_applicable` | No intervention was offered |
| Ask or Experiment delivered | `offered` | No result inferred |
| Photographer answers Ask | `completed` | Intent recorded; Change still separate |
| Capture Session reserved | `entered` | Participation proven, not success |
| Experiment left or expired | `left` | No failure claim |
| Experiment completes without comparable Baseline | `completed` | `not_applicable` |
| Comparable Change exists | `completed` | `changed`, `unchanged`, or `insufficient_evidence` |

One unchanged comparable outcome changes nothing by itself. After two completed,
comparable `unchanged` outcomes for the same Technique, automatic Scout selection may
deprioritize that Technique and records why. This is not a ban: an explicit
Photographer request may choose it again. Criteria not met, unreadable media, and no
attempt never count as unchanged behavior.

## Evidence ladder

Shoots can quantify evidence without pretending to quantify artistic worth:

1. **Measured facts:** EXIF, Tone, Motion, orientation, capture timing, Scene and Shot
   counts. These are replayable code outputs.
2. **Labelled model reads:** subject placement, framing, visual Technique Evidence,
   and observations. These retain model, prompt, and per-Analysis digests.
3. **Photographer-owned signals:** Keeper, Intent, Experiment entry, source role, and
   optional Compare preference. The model may not manufacture these.
4. **Recurrence:** the same corroborated Technique or decision across distinct Shots,
   Scenes, and Shoots. Recurrence says “observed again,” not “mastered.”
5. **Declared reproduction:** an explicit Reproduce result against Criteria frozen
   before capture. This is stronger evidence of control, not a quality grade.
6. **Longitudinal Change:** comparable earlier and later evidence changed, stayed the
   same, or remained insufficient. Improvement requires a direction grounded in the
   Photographer's own signal.

This ladder answers “was I lucky?” gradually. No single rung settles it. Repeated
corroborated observation plus an explicit comparable reproduction is stronger than one
successful frame; neither licenses the sentence “you are a better photographer.”

## One Shot teaching receipt

Shot detail is supporting evidence, but it still has to teach clearly when the
Photographer opens it. Shoots projects the stored Analysis into one short receipt:

| Part | What it says | Authority |
|---|---|---|
| Keep | The strongest corroborated Technique worth noticing again | Labelled model read with multi-lens proof |
| Notice | One measured Finding, or one explicitly labelled observation when no Finding exists | Measured or model read, never blended |
| Try | One next-capture camera or subject Move; a tested crop is secondary | Stored Move with its reason |
| Check | The visible condition that would show whether the Move changed the next Shot | Deterministic wording from the Finding or Move type |

The four parts are one read, not four independent critiques. Copy is bounded to one
useful sentence per field; the complete Analysis remains behind disclosure. The image
opens on exactly one matching layer: a located Finding, a drawable Move, the relevant
guide, or clean. A camera-position Move stays textual because drawing it as an arrow
inside the old frame would be false precision.

`Check` matters because advice without an observable result cannot teach control. “Try
a lower viewpoint” becomes learnable only when the Photographer also knows what to
inspect afterward, such as whether a background beam still crosses the subject. This
does not create a Verdict. Only a declared Reproduce Experiment can do that.

When Evidence supports no Technique, Finding, observation, or Move, the receipt stays
empty and the image stays clean. Shoots does not manufacture a lesson to fill the card.

Composition coordinates stay neutral. A centred horizon, a subject between common
guide lines, or a broad subject region may be deliberate, exploratory, or accidental;
the numbers alone cannot decide. Shoots may show the coordinate under a selected guide
or Experiment, but new Analysis does not turn it into a Finding. Existing historical
records remain inspectable. A slow shutter is likewise reported as camera-shake risk,
not proof that every soft edge came from shake.

The receipt excludes a Move whose only warrant is guide conformity and a Move that
undoes its strongest corroborated Technique. Those alternatives remain visible in
full Analysis and may become Explore Variations. `motion_blur` names the neutral
visible relationship where a stable anchor stays sharp while another region streaks;
it does not claim the Photographer intended the effect or pretend it knows whether
the camera was panned, moved through the Scene, or used another method.

## First Shoot receipt

The deterministic v1 receipt contains:

- exact Shoot revision, Scene ids, Shot ids, and member Run outcomes;
- Scene count and ordered Shots per Scene;
- analyzed and terminally unreadable coverage;
- placement, framing, light, key, palette, and orientation distributions where
  supported;
- Technique sightings and the subset corroborated by multiple Analyst lenses;
- positive Keeper ids;
- short repeated, varied, and blind-spot lines;
- calculation version, Analyst inputs, and relevant Analysis digests.

It deliberately omits an overall score, element scores, a “best” Shot, inferred
Intent, a pass/fail for the Shoot, and any claim of improvement. A bounded Shoot reader
is deferred until real receipts show a useful comparison that arithmetic and stored
Analyses cannot express.

## When the first interpretation is wrong

- **Wrong grouping:** a later Camera item or explicit correction creates a newer Shoot
  revision. Earlier Shoot Records remain inspectable.
- **Unreadable member:** the receipt names the missing coverage; the rest of the Shoot
  still settles. It does not fill the gap with model prose.
- **Analysis changed:** the stored digest changes, preventing the new model read from
  masquerading as Photographer Change.
- **No repeated or varied decision:** the receipt reports coverage and blind spots.
  Scout may choose evidenced silence.
- **The Photographer repeats the same kind of Shot:** Shoots records recurrence. It
  does not punish repetition; an optional Experiment may reproduce it deliberately or
  explore an alternative.
- **The Photographer disagrees:** Keeper and Intent remain theirs. Later correction
  supersedes the scoped signal rather than rewriting what the model originally saw.
- **The receipt becomes too textual:** preserve the same typed figures and reduce the
  visible copy. Do not remove evidence or replace it with a score.

## Alternatives explored

| Alternative | Decision |
|---|---|
| Per-Shot AI critique as the product | Keep only as inspectable evidence; it cannot show a Shoot or learning over time. |
| Quality or Technique scores | Reject. They collapse different authorities and reward optimization toward the model. |
| Skill tree or fixed lessons | Reject. The Photographer wants identity and evidence of control, not a curriculum grind. |
| Constant camera coaching | Defer. It interrupts the quiet practice and does not complete the Taskmaster background work. |
| Replace the normal camera | Reject for the current product. The system camera owns capture. |
| Choose the best Shot automatically | Reject until the Photographer provides a selection signal. “Keeper” is not the model's decision. |
| Add a Shoot-level Gemini reader now | Defer until deterministic receipts expose a measured gap. A second essay is not depth. |
| Vector database for memory | Defer. Structured ids, revisions, evidence axes, and provenance answer the current retrieval problem. |
| Generate a social carousel per Shot | Rejected. Current Deconstruction follows the settled Shoot or Experiment Record, derives every page from stored Evidence, requires a photographer-owned cover, and never auto-posts. |

## Current calibration and tests

The available local archive is weak evidence for the exact Shoot inactivity gap: only
8 of 27 Shots have reliable capture timestamps, 19 are undated, and 15, 30, 45, 60,
and 120-minute gaps all produced the same seven groups among the timed subset. The
default therefore remains configurable at 30 minutes. Physical Camera history must
validate it; the product must not present that threshold as photographic truth.

Acceptance should use ordinary phone behavior, not curated single images:

1. one Shoot with at least two Scenes and mixed decisions;
2. one terminally unreadable member;
3. one Shot shared with a frozen Capture Session;
4. one late Camera item creating a newer Shoot revision;
5. one Shoot with no useful repetition so silence is possible;
6. one repeated decision later attempted through Reproduce;
7. a process restart and offline read of the same current receipt.
8. one Ask answer that writes scoped Intent and one “just shooting” answer that opens
   no Experiment;
9. two comparable unchanged Intervention Records that alter only automatic routing.
10. one Shot Teaching Receipt whose Keep, Notice, Try, Check, and default image layer
    describe the same stored Analysis, plus one abstained Analysis that invents no
    lesson.

The feature is useful only if the Photographer can answer “what did I keep doing,
what did I vary, what could Shoots not know, and what is worth trying next?” without
opening thirty critiques.
