# Deconstruction

> Target design, 2026-08-26. This is not implemented. Decision 97 in the
> [domain model](domain-model.md) is normative; the
> [feature list](feature-list.md) tracks delivery.

A Deconstruction is a shareable, image-led draft made from stored Evidence. Its
first useful form explains one meaningful Shoot or Experiment through one visual
claim per page. It helps the photographer share not only a Keeper, but how they
worked toward it, what they varied, and which decision they could reproduce.

It is not a critique report, an image score, or an automatic social post.

## Why it exists

The photographer wants something more satisfying than a long private Analysis:
an Instagram-ready explanation of composition, light, colour, Scene Variations,
and decision-making. The same artifact makes Shoots' background work visible to a
hackathon judge without turning ActivityEvents into the product experience.

The Deconstruction quantifies evidence of control, never artistic quality. It may
show sightings, distinct Scene coverage, an explicit Reproduce attempt, Criteria
outcomes, Keeper signals, or comparable Change. It does not combine them into a
grade.

## Page grammar

The first target is portrait 1080×1350 (4:5), at most ten pages. Pages are chosen
from the eligible set below; only the one-claim rule is fixed.

| Candidate page | Evidence source | Rule |
|---|---|---|
| Keeper cover | photographer-marked Keeper | Never let the model invent or choose the cover. Without a Keeper, prepare evidence pages and ask for one. |
| How I worked the Shoot | ordered Scene contact sheet and Shoot Record | Show framing, distance, viewpoint, or timing Variations; do not rank every member Shot. |
| Composition | stored subject, horizon, line, crop, or Technique geometry | Render one relevant structure. Internal cell labels and generic grid stacks never appear. |
| Light or colour | EXIF, tone measurements, corroborated Technique Evidence, labelled model read | Keep measurements and interpretation visibly distinct. |
| One Move | supported Shot read | Keep what, why, action, and the visible next-attempt check together. Prefer camera or subject movement to crop salvage. |
| Explore result | explicit Variations and observed differences | No pass, fail, winner, or Verdict. |
| Reproduce result | frozen Keeper reference, Criteria, result members, Verdict or abstention | Say what met the declared Criteria, not whether the Shot is good. |
| Change | exact comparable earlier and later sets | Report the measured difference and sample; never call it improvement without the photographer's signal. |
| The record | Technique sightings, distinct Scenes, condition coverage, attempts, outcomes, positive Keeper count | Display separate figures, not one mastery score. |

Cell references remain model addressing. Captions use plain spatial language after
`domain/grid.py` converts the stored geometry.

## Who decides

1. Domain code creates the candidate set from the Shoot Record, Experiment Record,
   Analyses, Technique Map, Keeper signals, and provenance. Unsupported or
   contradictory material never reaches the writer.
2. A bounded Scribe writer selects and orders four to seven eligible pages and
   writes one concise caption per page. It cannot invent a page type, measurement,
   Intent, Keeper, or claim outside the candidate set.
3. Imaging code renders every mark and page deterministically. A scoped mark is
   drawn only where its Evidence reaches; a whole-frame or unlocated observation
   cannot receive a fictional hotspot.
4. The photographer chooses the cover, edits or removes captions, exports, and
   invokes Android's share sheet. Shoots never posts automatically.

The agentic decision is the supported story this body of work can tell. The
photographer retains taste and publication authority.

## Lifecycle and failure

Scribe attempts one Deconstruction after a meaningful Shoot or Experiment settles.
It does not render one automatically for every Shot. The Shoot Record stores one of
`not_applicable`, `drafted`, or `failed`, including the input ids and rendering
version, so a failed export cannot make the learning workflow disappear.

The photographer may request a later render from stored Evidence without rerunning
perception. Android saves the chosen pages to MediaStore and opens the system share
sheet. If Drive is connected, a later adapter may also write them to
`Shoots/Deconstructions/`.

## Explicitly out

- no overall or element score;
- no model-selected Keeper or best Shot;
- no invented Intent;
- no automatic Instagram integration or posting;
- no generic composition-grid gallery;
- no raw cell references or pipeline prose;
- no claim that an Experiment caused later Change.

## Open decisions

- Default attribution line: “Deconstructed with Shoots,” optional or always on?
- Let the photographer edit the caption before export, or export pages plus a
  separate suggested caption?
- For a Shoot without a Keeper, should the draft stop before rendering image pages
  or render evidence pages and wait for a cover selection?
- Are video contact-sheet covers in the first release or still-Shot only?
