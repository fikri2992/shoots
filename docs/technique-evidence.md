# Technique evidence: where the numbers come from

The Judge's hard criteria are EXIF bounds in `backend/app/domain/taxonomy.py`. Each one below is either sourced from published guidance or marked as a house rule. The Analyst's rubric and the panel design are sourced at the end.

Bounds are deliberately generous: they are the range within which the technique is *possible*, not the ideal. The panel's vision check decides whether it was *achieved*. A bound exists to make a quest un-fakeable, not to grade it.

| Technique | Bound | Why | Source |
|---|---|---|---|
| `freeze_action` | shutter ≤ 1/500 s | 1/250 freezes everyday motion, 1/500 people in motion, 1/1000+ sport; 1/500 is the floor for "stopped dead". | [Canon Europe, shutter speed guide](https://www.canon-europe.com/get-inspired/tips-and-techniques/how-to-use-shutter-speed/) |
| `panning` | 1/125 s ≥ shutter ≥ 1/8 s | Panning is taught at 1/15–1/60 s for cars and bikes, up to 1/125 s for fast subjects; slower than 1/8 s the subject smears too. | [Canon Europe](https://www.canon-europe.com/get-inspired/tips-and-techniques/how-to-use-shutter-speed/), [Amateur Photographer guide](https://amateurphotographerguide.com/panning-photography-beginners-guide/) |
| `long_exposure` | shutter ≥ 0.5 s | Moving water turns silky between ½ s and 1 s; "milky" needs several seconds. | [Digital Photography School](https://digital-photography-school.com/how-create-silky-smooth-water-effects/), [Tamron](https://tamron-americas.com/blog/silky-water-photography-slow-shutter-guide/) |
| `light_trails` | shutter ≥ 2 s | Street light trails are shot at 2–4 s on a phone, longer on a camera at a quiet junction. | [John Greengo](https://www.johngreengo.com/blog/2026/07/my-favorite-shutter-speeds/) |
| `light_painting` | shutter ≥ 2 s | Same physics as light trails; the light is moved by hand. | house rule, follows `light_trails` |
| `astro` | shutter ≥ 8 s, ISO ≥ 1600 | The 500 rule (500 ÷ focal length) gives 10–25 s at wide angles; NPF shortens it on dense sensors, rarely below 8 s. High ISO is the norm. | [PhotographyLife, 500 vs NPF](https://photographylife.com/500-rule-vs-npf-rule), [AstroBackyard](https://astrobackyard.com/the-500-rule/) |
| `shallow_dof` | aperture ≤ f/2.8 | Shallow depth of field is taught at f/1.4–f/2.8 for portraits; phones sit at f/1.7 so the vision check carries the weight. | [Adobe](https://www.adobe.com/creativecloud/photography/discover/shallow-depth-of-field.html), [DPS](https://digital-photography-school.com/how-to-get-shallow-depth-of-field-in-your-digital-photos/) |
| `bokeh_balls` | aperture ≤ f/2.8 | Point lights render as discs only with a wide aperture. | follows `shallow_dof` |
| `deep_dof` | aperture ≥ f/8 | Landscapes are shot at f/8–f/16 for front-to-back sharpness. | [Canon UK](https://www.canon.co.uk/pro/infobank/depth-of-field/), [DPS](https://digital-photography-school.com/understanding-aperture-landscape-photography-f16-not-only-choice/) |
| `high_iso_night` | ISO ≥ 3200 | House rule: the point of the technique is accepting grain; 3200 is where phones and entry cameras visibly do. | house rule |
| `icm`, `zoom_burst` | shutter ≥ 1/8 s | The camera or zoom ring must move during the exposure; under 1/8 s there is no time to. | house rule |
| `wide_angle` | focal ≤ 24 mm (35 mm eq.) | 24 mm and wider is the conventional wide-angle range. | house rule, conventional |
| `telephoto_compression` | focal ≥ 135 mm (35 mm eq.) | Compression is visible from 85 mm and obvious from 135 mm; the bound asks for the obvious case. | house rule, conventional |
| `normal_portrait` | 45–90 mm (35 mm eq.) | The classic portrait range, 50–85 mm, with a margin either side. | house rule, conventional |
| `fill_flash` | flash fired | Definitional. | — |

Techniques without a bound (every composition, light and colour technique) are judged on the frame alone by the panel, which is what they are: ways of seeing, not settings.

## Exposure arithmetic (`domain/exposure.py`)

| Quantity | Formula | Source |
|---|---|---|
| EV at ISO 100 | `log2(N² / t) − log2(ISO / 100)`; sunny-16 ≈ EV 15 | [Exposure value, Wikipedia](https://en.wikipedia.org/wiki/Exposure_value) |
| Handheld limit | `1 / (2 × focal length)` (35 mm eq.) — the reciprocal rule with a stop of margin | [John Greengo](https://www.johngreengo.com/blog/2026/07/my-favorite-shutter-speeds/) |
| Freeze thresholds | ≥ 1/500 s people in motion, ≥ 1/1000 s sport | [Canon Europe](https://www.canon-europe.com/get-inspired/tips-and-techniques/how-to-use-shutter-speed/) |
| Star-trail ceiling | 500 rule, `500 / focal length` | [PhotographyLife](https://photographylife.com/500-rule-vs-npf-rule) |

## The rubric

Five elements, 1–10 each, weighted 30/25/20/15/10 (impact, composition, lighting, technical, story), the overall a weighted mean computed in code (`domain/rubric.py`). Derived from the Professional Photographers of America's *12 Elements of a Merit Image*, the judging standard for PPA print competitions, scored on 100 points with published bands (95–100 exceptional, 80–84 merit, 70–74 average, below 70 not exhibition standard). Presentation, Style and Technique are left out as they concern finished competition prints; Center of Interest is folded into Composition, Subject Matter and Creativity into Story, Color Balance into Technical. Our anchors map the bands onto 1–10.

- [PPA: 12 Elements of a Merit Image](https://www.ppa.com/ppmag/articles/12-elements-of-a-merit-image)
- [PPA Massachusetts: the 12 elements and the scoring scale](https://www.ppam.com/12-elements-and-scoring)

## The critique order

Each lens reads in Feldman's order: describe (neutral, by cell), analyse, interpret, judge; judgement is withheld until last. The `observations` field is the description step and is stored, so the Coach and the Scribe can point at what was seen before what was thought.

- [Feldman model of criticism](https://us.humankinetics.com/blogs/excerpt/feldman-model-of-criticism)
- [Feldman's critical analysis model in education (ERIC)](https://files.eric.ed.gov/fulltext/EJ1086252.pdf)

## The panel

Three lenses with different instructions and different inputs (Technician: EXIF + gridded frame; Composer: gridded frame only; Storyteller: clean frame), run concurrently by an ADK `ParallelAgent`, then a Synthesizer in a `SequentialAgent`. Evidence is by vote: two lenses, or the owning lens at ≥ 0.75. Element scores are averaged over the lenses that rate them. The reasoning: panels of graders beat a single grader when their errors are not shared, and anchored score descriptors reduce grader variance; same-model panels that see the same thing share errors, which is why the inputs differ.

- [Verga et al. 2024, Replacing Judges with Juries (PoLL)](https://arxiv.org/abs/2404.18796)
- [LLMs-as-Judges: a comprehensive survey (2024)](https://arxiv.org/html/2412.05579v2)
- [Nine Judges, Two Effective Votes: correlated errors undermine LLM panels](https://arxiv.org/html/2605.29800)
- [ADK workflow agents: ParallelAgent, SequentialAgent](https://adk.dev/agents/workflow-agents/parallel-agents/)

## The guides

The overlay draws one compositional guide, chosen by the technique the panel agreed on. Only these four have geometry a photographer would recognise; everything else draws none.

| Guide | Geometry | Source |
|---|---|---|
| Thirds | lines at 1/3 and 2/3, four power points | [Rule of thirds](https://en.wikipedia.org/wiki/Rule_of_thirds) |
| Phi grid | 1 : 0.618 : 1, so the lines sit at 0.382 and 0.618 | [Golden ratio in composition](https://en.wikipedia.org/wiki/Golden_ratio#Art) |
| Diagonal method | both diagonals plus a 45° bisector from each corner, at 45° on the print, which is why the renderer needs the aspect ratio | [Edwin Westhoff, the diagonal method](https://www.diagonalmethod.info/) |
| Centre | the two mid-lines | conventional, for `centre_composition`, `symmetry`, `reflections` |

The fit readout is quantisation-aware: cells are a seventh of the frame wide, so nothing is claimed unless the Composer gave a sub-cell subject point and the distance exceeds half a cell.
