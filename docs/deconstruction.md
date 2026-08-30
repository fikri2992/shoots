# Deconstruction

> Release contract and current first slice, updated 2026-08-27. Decisions 97 and 105 in the
> [domain model](domain-model.md) is normative; the
> [feature list](feature-list.md) tracks delivery.

A Deconstruction is a shareable, image-led draft made from stored Evidence. Its
first useful form explains one meaningful Shoot or Experiment through one visual
claim per page. It helps the photographer share not only a Keeper, but how they
worked toward it, what they varied, and which decision they could reproduce.

`Deconstruction` remains the internal domain and API name. The client and rendered
artifact call it a **visual story**. Cover prompts say "marked Shot" and "opening
Shot" instead of exposing the internal Keeper term.

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

## Story grammar

The first target is portrait 1080×1350 (4:5), four to seven pages. The visible arc is
an opening, setting or idea, turn or attempts, recurring thread or result, and an
ending. Those chapter labels replace report headings such as "The record", "Declared
check", and raw counts. The stored page kinds and Evidence references stay exact.

Pages are chosen from the eligible set below; only the one-claim rule is fixed.

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
2. Current Scribe code selects, orders, and captions four to seven eligible pages.
   A later bounded writer may rewrite only inside that candidate set; it cannot invent
   a page type, measurement, Intent, Keeper, or claim.
3. Imaging code renders every mark and page deterministically. A scoped mark is
   drawn only where its Evidence reaches; a whole-frame or unlocated observation
   cannot receive a fictional hotspot.
4. The photographer chooses the cover and invokes Android's share sheet. Caption
   editing and persistent export remain later work. Shoots never posts automatically.

The agentic decision is the supported story this body of work can tell. The
photographer retains taste and publication authority.

## Lifecycle and failure

Scribe may prepare one Deconstruction after a meaningful Shoot or Experiment settles.
It does not render one automatically for every Shot. The durable record stores
`needs_cover`, `drafted`, or `failed`, exact input ids, Evidence references, input
digest, and rendering version. A Shoot or Experiment remains settled if drafting
fails.

The photographer may request a later render from stored Evidence without rerunning
perception. Android caches the chosen pages for the system share sheet. A later export
may save them to MediaStore or, when Drive is connected, write them to
`Shoots/Deconstructions/`.

Current implementation prepares a replay-safe `needs_cover` record while a Shoot
settles and after a Reproduce or Explore Experiment becomes terminal with explicit
results. It renders four to seven exact 1080×1350 JPEG pages only after the
Photographer chooses an eligible Keeper. Android and web route the newest draft to its
actual Shoot or Experiment source; Android caches authenticated pages and opens the
system multi-image share sheet. Export to MediaStore, caption editing, and optional
Drive output remain later work. Composition and Technique pages reuse stored Evidence;
they do not replace visible structure with another paragraph.

## Explicitly out

- no overall or element score;
- no model-selected Keeper or best Shot;
- no invented Intent;
- no automatic Instagram integration or posting;
- no generic composition-grid gallery;
- no raw cell references or pipeline prose;
- no claim that an Experiment caused later Change.

## First-release decisions

- Draft pages carry a small "A Shoots story" attribution.
- Pages and one separate suggested post caption are exported; in-app caption editing
  is later work.
- Without an explicitly selected eligible Keeper, the draft stays `needs_cover` and
  does not render a carousel.
- Still-Shot covers and pages only. Video contact-sheet covers remain later work.
- Android shares the rendered page files through the system share sheet. It never
  calls a social-network posting API.
