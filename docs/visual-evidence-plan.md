# Visual Evidence plan

Target contract for making every still-Technique explanation inspectable on
Android. This document describes planned work unless a row is explicitly marked
as current.

## Current implementation — 2026-08-28

Built now:

- all 57 still Techniques resolve through the versioned strategy table;
- `Visual Path`, grouped `Visual Region`, and `Visual Evidence Artifact` survive
  Analyst validation, owner-accountable panel consensus, API serialization, and
  Android parsing;
- deterministic hue, saturation, luminance, sharpness, flat-area noise, edge,
  bokeh-disc, directional-structure, and radial-convergence renderers;
- bounded path-to-edge verification and seeded foreground contours;
- the official MIT-licensed YuNet detector for face and five landmarks, with
  measured side-to-side face luminance;
- Android paths, pairs, instances, planes, scalar-map blobs, EXIF receipts,
  clean/visual switching, and access to every corroborated Technique layer;
- an idempotent backfill that adds current artifacts without rerunning Gemini;
- real Store, BlobStore, authenticated API, emulator interaction, corpus, and
  full backend integration gates.

Still incomplete:

- generic monocular depth refinement;
- pixel contours for every arbitrary semantic object;
- one bounded verifier for every artifact family (paths and contours are bounded
  today; other maps expose their measurement and fallback but do not run a
  second visual judge);
- a real-Gemini corpus rerun after the grouped-region prompt change;
- physical Xiaomi and production deployment acceptance for these artifacts.

## Product rule

> If the story names something visible, the image must point to it.

That does not mean drawing a line for every Technique. The visual must match the
claim:

- a visible path gets one or more ordered paths;
- an object or area gets a region or contour;
- a relationship gets a pair, axis, enclosure, or ordered set;
- a tonal property gets a pixel map and measured legend;
- a camera setting gets an EXIF receipt beside the pixels it helps explain;
- a whole-frame quality gets a whole-frame map or histogram;
- a claim that cannot be located or measured stays labelled **model read** and
  may not borrow precise geometry.

The clean Shot always remains available. Visuals explain stored Evidence; they
do not rewrite the Shot, grade taste, or prove Intent.

## Evidence levels

| Level | Meaning | Examples |
| --- | --- | --- |
| Measured | Deterministic arithmetic from pixels or EXIF | luminance mask, hue mask, clipping, shutter receipt |
| Located model read | Analyst supplies bounded cells; code refines within them | subject contour, frame enclosure, repeated objects |
| Relational model read | Several located items and their relationship | reflection pair, depth planes, juxtaposed subjects |
| Unresolved | Available inputs cannot honestly prove or locate the claim | camera height without a reliable perspective cue |

Measured does not mean the Technique itself is proved. A sharpness map is an
exact map of local contrast, but calling it shallow depth of field still needs
a subject/background relationship. Every artifact preserves both statements.

## Reusable visual grammar

The renderer needs these primitives instead of Technique-specific UI widgets:

1. **Point** — eye, accent, vanishing point, star, pattern exception.
2. **Region or contour** — subject, shadow, hue group, negative space.
3. **Ordered path set** — leading edges, trails, diagonals, blur direction.
4. **Enclosure** — a frame around a subject.
5. **Axis** — symmetry, reflection, face split, horizon.
6. **Pair** — subject/reflection, warm/cool, old/new, sharp/blurred.
7. **Instances** — repetition, rule of odds, stars, bokeh discs.
8. **Ordered planes** — foreground, midground, background.
9. **Scalar map** — luminance, saturation, hue, sharpness, noise, edge strength.
10. **Whole-frame receipt** — EXIF, histogram, frame-wide measurement, or an
    honest unresolved state.
11. **Guide** — thirds, centre, diagonals, phi grid, or golden spiral. A guide
    is a comparison lens, never Evidence by itself.

`Visual Path` is already present. The remaining primitives need typed domain
records, API serialization, and Android renderers.

## Still-Technique map

### Composition — 20

| Technique | Primary visual | What is needed |
| --- | --- | --- |
| Rule of thirds | guide + subject point/contour | current subject location; show distance to the nearest thirds line |
| Deliberate centre | centre axes + subject point/contour | current subject location; symmetry remains separate Evidence |
| Horizon placement | horizon axis + high/centre/low band | edge/Hough candidate constrained by Analyst cells; level confidence |
| Leading lines | separate ordered paths ending toward subject | current `Visual Path`; add edge snapping and path verification |
| Fill the frame | subject contour + occupancy percentage | subject mask seeded by Analyst cells |
| Negative space | subject contour + quiet-space region | subject mask plus texture/edge-density map |
| Frame within a frame | enclosure contour + enclosed subject | nested edge/contour search seeded by Analyst cells |
| Symmetry | symmetry axis + mirrored-difference heatmap | best-axis search and confidence |
| Reflections | source/reflection pair + reflection axis | paired regions and local feature correspondence |
| Foreground, midground, background | three ordered translucent planes | Analyst plane cells; optional monocular-depth refinement |
| Patterns and repetition | repeated instance markers | contour/keypoint clustering inside located region |
| Break the pattern | instances + one contrasting marker | repetition detector plus exception score |
| Diagonals | one or more ordered diagonal paths | current `Visual Path`; add edge snapping and verification |
| Low angle | convergence paths + low viewpoint receipt | perspective cues; otherwise broad region labelled model read |
| High angle / top-down | plane/subject contours + viewpoint receipt | perspective cues; otherwise broad region labelled model read |
| Silhouette | dark subject contour against bright region | subject mask and luminance contrast |
| Minimalism | subject contour + quiet-space share | segmentation, edge density, and element count; never claim Intent |
| Juxtaposition | two labelled regions joined as a pair | two Analyst-located subjects; relationship remains model read |
| Rule of odds | instance markers + count + anchor | instance detection and Analyst anchor |
| Eye-level portrait | face/eye landmarks + eye sharpness + thirds guide | face landmarks and local sharpness |

### Light — 15

| Technique | Primary visual | What is needed |
| --- | --- | --- |
| Golden hour | warm-hue mask + light-direction gradient + time receipt | HSV/luminance maps; capture time/GPS only when available |
| Blue hour | blue ambient mask + time receipt | HSV/luminance maps; optional twilight lookup |
| Backlight | subject contour + front/background luminance comparison | subject mask and boundary luminance samples |
| Rim light | bright boundary band on the subject | subject contour and edge-band luminance |
| Window light | luminance falloff across subject/face | face or subject mask and gradient vector; do not invent a window |
| Rembrandt lighting | face landmarks + cheek-light triangle | face landmarks and local luminance segmentation |
| Split lighting | face midline + left/right luminance comparison | face landmarks and two-side measurement |
| Hard light and shadow | shadow region + crisp boundary | luminance segmentation and boundary-width measurement |
| Soft overcast light | broad gradient map + low edge-transition receipt | luminance gradient and shadow-edge softness |
| High key | bright-tone mask + histogram | deterministic luminance map and distribution |
| Low key | dark-tone mask + isolated lit region + histogram | deterministic luminance map and connected regions |
| Chiaroscuro | light/dark masks + modelling gradient | luminance segmentation plus subject relation |
| Dappled light | repeated bright patches over the subject | connected luma regions intersected with subject mask |
| Fill flash | EXIF flash receipt + lifted-shadow/catchlight region | EXIF is causal proof; face/catchlight localization is supporting Evidence |
| Light painting | bright trail paths + long-shutter receipt | bright-path extraction and EXIF |

### Exposure — 11

| Technique | Primary visual | What is needed |
| --- | --- | --- |
| Shallow depth of field | sharpness map + sharp-subject/blurred-background pair | local sharpness plus subject/background regions |
| Deep depth of field | sharpness map across ordered depth planes | local sharpness plus plane regions |
| Freeze action | shutter receipt + subject edge/sharpness map | EXIF and located moving subject; one frame cannot prove prior motion alone |
| Motion blur | directional blur field + stable anchor region | blur-kernel/orientation estimation and located anchor |
| Panning | sharp subject paired with horizontal background blur | subject mask, local sharpness, and blur orientation |
| Long exposure | shutter receipt + moving/static region comparison | EXIF, semantic regions, and blur map |
| Light trails | separate bright ordered paths + shutter receipt | bright-path extraction and current `Visual Path` fallback |
| Handheld night | ISO/shutter receipt + noise map + highlight mask | EXIF, denoise residual, and luminance map |
| Night sky | star instances + sky/foreground regions + EXIF receipt | point-source detection and broad sky segmentation |
| Intentional camera movement | whole-frame directional field | global blur orientation; Intent remains unknown unless stated |
| Zoom burst | radial paths + centre of expansion | radial blur estimation |

### Lens — 5

| Technique | Primary visual | What is needed |
| --- | --- | --- |
| Wide-angle drama | focal receipt + convergence paths + near/far pair | EXIF and perspective lines; visual drama remains model read |
| Telephoto compression | focal receipt + stacked depth planes | EXIF and Analyst-located planes; compression is not recoverable exactly from one frame |
| Portrait focal length | focal receipt + face geometry | EXIF is the main proof; optional face landmarks support distortion discussion |
| Macro detail | subject contour + frame occupancy + texture-detail map | subject mask and local sharpness; true magnification needs metadata unavailable on many phones |
| Bokeh highlights | detected soft discs + sharpness map | circle/blob detection filtered by low edge sharpness and background location |

### Colour — 6

| Technique | Primary visual | What is needed |
| --- | --- | --- |
| Black and white | saturation map + channel receipt | deterministic HSV measurement |
| Complementary colours | two hue masks + swatches + hue-angle receipt | deterministic HSV clustering; keep only spatially meaningful groups |
| Single accent colour | accent mask + frame-share receipt | deterministic saturation/hue outlier map |
| Warm against cool | warm/cool masks + boundary or paired regions | deterministic hue masks plus spatial components |
| Muted palette | saturation map + distribution | deterministic HSV measurement |
| Colour blocking | large hue regions + clean shared boundaries | connected hue components and edge agreement |

## Code needed

### 1. Typed artifact contract

Add one `Visual Evidence Artifact` referenced by a `Visual Mark`:

- Technique id and story-step id;
- artifact kind and renderer version;
- authority: measured, located model read, relational model read, or unresolved;
- source cells and any `Visual Path` inputs;
- typed geometry or scalar-map blob path;
- metric, unit, threshold, and legend when measured;
- verification state and fallback reason;
- original Shot digest so stale artifacts cannot survive re-analysis.

The Analyst may choose semantic cells and relationships. It still never emits
pixels. Code refines pixels only inside the supplied cells and records when it
could not.

### 2. Deterministic imaging modules

- luminance masks, histograms, gradients, and clipped regions;
- HSV hue and saturation masks with connected components;
- local sharpness and noise maps;
- Canny/Hough edges and cell-constrained path snapping;
- symmetry and mirrored-difference maps;
- blur orientation and radial-flow estimation;
- circle/blob detection for bokeh and stars;
- contour, repetition, and exception helpers;
- seeded subject extraction, with a coarse-cell fallback;
- face and eye landmarks for portrait-lighting Techniques;
- optional ordinal depth refinement for plane-based Techniques.

OpenCV is suitable for the measured maps and geometry. Face landmarks need a
small dedicated detector. Generic semantic segmentation and depth are the least
reliable parts and must retain broad-cell fallbacks.

### 3. Bounded verification

After rendering the selected story artifact:

1. verify that every named visible element has a corresponding mark;
2. verify paths overlap strong edges or bright trails where that is the claim;
3. verify points and contours remain inside their source cells;
4. permit one refinement attempt;
5. otherwise downgrade to a broad region, whole-frame map, EXIF receipt, or
   explicit unresolved state.

The verifier may reject precision. It may not manufacture replacement Evidence.

### 4. Android presentation

- show one story step and its matching visual at a time;
- allow clean/visual comparison without losing scroll position;
- support paths, contours, axes, pairs, instances, planes, scalar-map legends,
  and EXIF receipts;
- state **Measured** or **Model read** beside the explanation;
- make each visible noun tappable from the sentence to its highlight;
- keep Guide comparison separate from Evidence;
- never show an empty or irrelevant overlay.

## Delivery order

1. Ship deterministic colour and luminance maps first. They provide reusable
   support across the Light and Colour families.
2. Add sharpness, noise, bokeh/star blobs, and blur direction for Exposure and
   Lens Techniques.
3. Add edge snapping, axes, pairs, instances, enclosure, and plane renderers for
   Composition.
4. Add face landmarks for eye-level portraits, Rembrandt, split light, window
   light, and fill-flash support.
5. Add optional subject segmentation/depth refinement last; keep cells as the
   honest fallback.
6. Run the labelled corpus, require every displayed sentence to have a matching
   mark, then test the Android interaction on emulator and Xiaomi.

## Acceptance

- All 57 still Techniques resolve to an allowed visual strategy.
- No unordered cells are converted into a precise line.
- No model output crosses the cell-reference boundary as pixel geometry.
- A Technique-specific detector failure is visible and falls back honestly.
- A measured artifact includes its metric and legend.
- An EXIF-dependent claim never presents a pixel map as causal proof.
- The selected story visual appears quickly; expensive secondary comparisons
  may finish later and update the cache.
- The same stored Analysis and renderer version reproduce the same artifact.
