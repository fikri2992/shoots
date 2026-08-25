# Light

Technical note, 2026-08-23. How light is planned, shown, coached and verified.
Weather, sky and air — what the sky does with the sun, and what the person needs to
bring — are in `conditions.md`.
Nothing here is built; decisions get numbered in `domain-model.md` when they ship.

## The split

Three layers, and the boundary between them is the whole design:

| Layer | Who | What |
|---|---|---|
| **Facts** | code (`domain/light.py`, `domain/sun.py`) | sun position, camera heading, clipping, colour cast, lit/shadow ratio, shadow-edge width, scene EV, indoor/outdoor guess |
| **Reasoning** | agents (ADK `LlmAgent` with output schemas) | *which situation to set up* given the technique, the person's gear and rooms, the slots the sun allows, the weather, and what they have been shooting in; *what the frame shows* that only a reader can see (pattern, catchlight, sources) |
| **Verification** | code | plan vs facts vs read, with tolerances from the recipe; the Judge's model only writes the words |

The agent never computes where the sun is, and code never decides whether a window
or a lamp is the better key for this person on Saturday. Same rule as
`exposure.py`: arithmetic before opinion, and the opinion is asked *inside* the
envelope the arithmetic allows.

## Data

```python
class LightSource(StrEnum):
    SUN = "sun"; SKY = "sky"; WINDOW = "window"; LAMP = "lamp"; FLASH = "flash"; PRACTICAL = "practical"

class Quality(StrEnum):
    HARD = "hard"; SOFT = "soft"

class Pattern(StrEnum):
    REMBRANDT = "rembrandt"; LOOP = "loop"; SPLIT = "split"; BUTTERFLY = "butterfly"
    BROAD = "broad"; SHORT = "short"; FLAT = "flat"; RIM = "rim"; SILHOUETTE = "silhouette"
    NONE = "none"

class Tolerance(BaseModel):
    key_azimuth_deg: float = 25
    key_elevation_deg: float = 20
    fill_stops: float = 1.0

class LightPlan(BaseModel):
    """What the Scout set up. Agent fields are reasoned; computed fields are filled by code."""
    setting: Literal["outdoor", "indoor"]
    source: LightSource
    pattern: Pattern
    #: Key direction relative to the camera axis, seen from above. 0 = from behind the
    #: camera (front light), 180 = from behind the subject (backlight), positive = camera-left.
    key_azimuth_deg: float
    key_elevation_deg: float
    quality: Quality
    fill_stops: float | None = None          # key minus fill, in stops; None = no fill asked
    modifiers: list[str] = []                # "white card opposite", "lamps off", "1 m from the glass"
    say: str                                 # one sentence for the experiment hero
    # computed
    at: datetime | None = None               # deliver_at
    sun_azimuth_deg: float | None = None
    sun_elevation_deg: float | None = None
    camera_heading_deg: float | None = None  # outdoors: where to point so the key lands as planned
    window_azimuth_deg: float | None = None  # indoors, when known
    soft_until: datetime | None = None       # indoors: direct sun reaches the window after this
    tolerance: Tolerance = Tolerance()

class LightFacts(BaseModel):
    """Per frame, computed. Every field optional: phones and exports drop things."""
    setting_guess: Literal["outdoor", "indoor", "unsure"]
    ev100: float | None
    flash_fired: bool | None
    sun_azimuth_deg: float | None            # from captured_at + GPS
    sun_elevation_deg: float | None
    heading_deg: float | None                # EXIF GPSImgDirection
    sun_relative_deg: float | None           # sun azimuth minus heading, -180..180; 0 = straight ahead
    clipped_high_pct: float                  # luma >= 250 of 255
    clipped_low_pct: float                   # luma <= 5
    cct_left_k: int | None                   # over the subject box halves
    cct_right_k: int | None
    cct_delta_k: int | None
    lit_shadow_stops: float | None           # over the subject box
    edge_width_frac: float | None            # shadow-edge transition / subject box width

class LightRead(BaseModel):
    """What the Technician saw. Structured, so the Judge can diff it."""
    pattern: Pattern
    key_azimuth_deg: float                   # same convention as the plan, from catchlight and shadows
    key_elevation_deg: float
    quality: Quality
    sources: list[LightSource]
    catchlight: str = ""                     # "10 o'clock", "none"
    confidence: float

class LightCheck(BaseModel):
    name: str                                # "key direction", "pattern", "fill", "timing", "mixed light"
    wanted: str
    got: str
    ok: bool
    hard: bool                               # from facts (hard) or from the read (soft)
```

`Experiment.light: LightPlan | None`, `Analysis.light_facts`, `Analysis.light_read`,
`Verdict.light_checks: list[LightCheck]`. `Exif.heading_deg` is new (GPSImgDirection;
the `M`/`T` ref is ignored, magnetic declination is under 1° where this is demoed).

## Facts: the arithmetic

### Sun position — `sun.sun_position(at, latitude, longitude) -> (azimuth, elevation)`

`sun.py` already has NOAA's equation of time and declination. Add the hour angle and
the spherical triangle (all UTC, degrees):

```
tst      = minutes_utc + eqtime + 4 * longitude              # true solar time
ha       = tst / 4 - 180
cos_zen  = sin(lat) sin(decl) + cos(lat) cos(decl) cos(ha)
elev     = 90 - acos(cos_zen)
cos_az   = (sin(decl) - sin(lat) cos_zen) / (cos(lat) sin(zen))
az       = acos(clamp(cos_az))          ;  az = 360 - az  if ha > 0
```

Tested against three NOAA-calculator fixtures (Jakarta noon, Jakarta 17:40 in
August, a northern winter afternoon) to ±0.5°. No refraction term; it matters only
at the horizon and by less than the tolerance.

### Heading and the sun relative to the lens

```
sun_relative = ((sun_az - heading + 540) mod 360) - 180       # -180..180
key_azimuth_from_sun = ((sun_relative + 180 + 180) mod 360) - 180
```

so the sun straight ahead (`sun_relative = 0`) is `key_azimuth = 180`: backlight.
Outdoors the plan's computed `camera_heading_deg` is the inverse: the heading at
which the planned key lands, `heading = sun_az - (key_azimuth - 180)`.

### Window: when is it soft — `light.window_soft_intervals(day, lat, lon, window_az)`

Direct sun enters a window facing `W` when the sun is in front of it and not too high
for the reveal: `|((sun_az - W + 540) mod 360) - 180| < 75` and `3° < elevation < 55°`.
Step the day in five-minute intervals; the complement between dawn and dusk is soft.
The experiment's `soft_until` is the end of the soft interval containing `deliver_at`.
The window's azimuth is a standing fact in `User.constraints` ("big window faces
north-west"), written by the Listener from a Coach session — asked once, never a form.

### Pixel facts — `light.facts(frame, subject_box, exif)`

- **Clipping**: fraction of luma (Rec. 601) `≥ 250` and `≤ 5` over the whole frame.
- **Colour cast per side**: mean linear RGB over the left and right halves of the
  subject box (sRGB → linear, the 2.4 curve) → XYZ → `xy` → McCamy:
  `n = (x − 0.3320) / (0.1858 − y)`, `CCT = 449n³ + 3525n² + 6823.3n + 5520.33`.
  This is the *residual* cast after the camera's white balance — which is exactly what
  the viewer sees. `cct_delta_k > 800` is mixed light.
- **Lit/shadow ratio**: Otsu threshold on luma inside the subject box; mean of the
  lit class over mean of the shadow class; `log2` of it is the ratio in stops. Fill
  ratio 1:2 ≈ 1 stop, 1:4 ≈ 2 stops, 1:8 ≈ 3 stops.
- **Shadow-edge width**: along the boundary between the two Otsu classes, sample
  perpendicular luma profiles and measure the 20 %–80 % transition width; median,
  divided by the box width. `< 0.015` is hard, `> 0.04` is soft, between is "mixed"
  and the Technician's read decides. This is an estimate and is labelled as one in
  the prompt ("edge 14 px, reads soft"); the model's `quality` is recorded beside it
  and a disagreement is logged, not hidden.
- **EV** from `exposure.ev100`; the `light_band` label already exists.
- **Setting guess**: `outdoor` when GPS is present, the sun is above the horizon at
  `captured_at`, and `EV ≥ 11`; `indoor` when the flash fired, or `EV ≤ 8`, or there is
  no GPS and `EV ≤ 10`; otherwise `unsure`, and the Storyteller's read breaks the tie.

No subject box (no Composer read yet) → the cast and ratio are computed over the
centre third of the frame and flagged `approx`.

## Reasoning: the agents

### The Lighting Designer — inside the Scout

`SequentialAgent[lighting_designer → (code: complete + validate) → brief_writer]`.
The code step between two `LlmAgent`s is a Python step, as in the crop loop; the
designer is an `LlmAgent` with `output_schema=LightPlanOut` (the agent fields only)
and no tools.

Input, all assembled by code:

- the technique and its **recipe envelope** (below): allowed patterns, key azimuth
  and elevation ranges, quality, fill range, the "tell";
- `User.constraints`: gear (reflector, flash, tripod), known rooms and windows, notes;
- candidate **slots** from `timing.py`, each with the sun's azimuth/elevation and the
  cloud cover at that time (Google Maps Platform Weather API; overcast ⇒ `SKY`, soft);
- the last five `LightFacts`/`LightRead`s: what they have been shooting in
  (a week of EV 6 frames with a 3100 K cast says "their evenings are lamp-lit");
- whether a location is known at all.

The designer reasons and returns: setting, source, pattern, key azimuth and
elevation, quality, fill, modifiers, `say`. It is told the envelope is a wall, not a
hint. Code then **completes** (sun position at the slot, camera heading, soft-until
for a known window, the recipe's tolerance) and **validates** (inside the envelope;
an outdoor plan has a slot; a window plan has a window or says "any window with no
direct sun"; `say` names no angle in degrees). A violation re-runs the designer once
with the violation quoted, like the panel's quorum retry; a second violation falls
back to the recipe's default plan with a logged event, never a silent one.

The brief writer gets the completed plan and writes the experiment in sentences.

### The Technician — the read

Gets `LightFacts` as lines ("EV 6 · lamp side 3100 K, window side 5600 K, 2500 K apart
· lit over shadow 2.3 stops · edge 14 px of 310, reads soft · sun 2° up at 279°, 35°
left of the lens") and returns `LightRead`. The prompt teaches the two reverse-
engineering tells every portrait teacher uses: the **catchlight** (clock position in
the eye → key direction and height: 10 o'clock ≈ 45° camera-left, 30° up) and the
**nose shadow** (touching the cheek shadow with a closed triangle of light = Rembrandt;
a loop beside the nose = loop; half the face dark = split; a butterfly under the
nose = butterfly). Where facts exist they override: with `sun_relative_deg` present,
the read's `key_azimuth_deg` is set by code and the model is told so.

### The Judge — the diff

`light.check(plan, facts, read) -> list[LightCheck]`, pure:

| check | wanted | got from | hard? |
|---|---|---|---|
| timing | `plan.at ± window` | `captured_at` | yes |
| key direction | `plan.key_azimuth ± tol` | `facts.sun_relative` (outdoor) else `read.key_azimuth` | yes / no |
| key height | `plan.key_elevation ± tol` | `facts.sun_elevation` else `read` | yes / no |
| pattern | `plan.pattern` | `read.pattern` | no |
| quality | `plan.quality` | `facts.edge_width` then `read.quality` | yes / no |
| fill | `plan.fill_stops ± tol` | `facts.lit_shadow_stops` | yes |
| mixed light | `cct_delta < 800` | `facts.cct_delta_k` | yes |
| clipping | technique-specific (`high_key` allows highlights; `silhouette` allows blacks) | `facts.clipped_*` | yes |

A hard check beats a soft one on the same name. Light checks gate the verdict only
when the technique is in `Family.LIGHT` or the experiment's criteria text mentions light;
otherwise they are advice in the feedback. The feedback model receives the list
verbatim and turns it into the one next thing ("face went black: a white wall on
your left next time"), never a new judgement.

### The Coach — live

Outdoors the phone does the arithmetic: a JavaScript port of `sun_position`
(~40 lines, tested against the Python on shared fixtures) plus
`deviceorientationabsolute` for heading gives the sun's bearing relative to the lens
at 60 fps, with no round trip. The ring turns amber when `|sun_relative −
(plan.key_azimuth − 180)| < tol`. Indoors there is no compass; the viewfinder draws a
live histogram from the camera stream on a canvas (clipping in JS) and the Live
session is briefed with the plan and the tell ("target Rembrandt; say when the nose
shadow meets the cheek shadow"), so the Coach reads the frames it is sent and speaks
the adjustment. Pre-flight gets the same `light.check` on the facts a preview can
give (clipping, cast, ratio; no EXIF).

## Recipes — `taxonomy.RECIPES`

Per pattern: key azimuth range, elevation range, quality, fill range, the tell.

| pattern | key az | key el | quality | fill (stops) | tell |
|---|---|---|---|---|---|
| rembrandt | 35–55 (either side) | 30–60 | any | 1.5–3 | closed triangle of light on the shadow cheek |
| loop | 25–45 | 20–45 | any | 1–2 | nose shadow beside the nose, not touching the cheek |
| split | 80–100 | 0–30 | hard | ≥ 3 | half the face dark |
| butterfly | 0–15 | 40–60 | any | 1–2 | shadow under the nose, under the chin |
| broad / short | 30–60 | 20–45 | any | 1–2.5 | lit side toward / away from camera |
| flat | 0–20 | 0–30 | soft | ≤ 0.5 | no modelling shadow |
| rim | 150–180 | 0–15 | hard | ≥ 3 | bright line on hair and shoulders |
| silhouette | 170–180 | 0–10 | any | ≥ 4 | subject black, clipping low allowed |

Technique → allowed patterns: `rim_light → rim`; `golden_hour → any, sun el 0–10,
source SUN`; `window_light → loop | rembrandt | broad | short, soft, source WINDOW`;
`silhouette → silhouette`; `high_key → flat, soft, fill ≤ 0.5, highlights may clip`;
`low_key → split | rembrandt, hard, fill ≥ 3, blacks may clip`; `backlight → rim |
silhouette`. Techniques outside `Family.LIGHT` get no recipe and no plan; the
designer is not run for them.

## What the phone receives

- `experiment.light`: the completed plan, plus the day's `SunTimes` for the strip. The
  hero shows the strip outdoors (blue–golden–day–golden–blue from the real times,
  the slot marked, "now" marked) or the **diagram** indoors — an SVG drawn from
  `key_azimuth_deg`, `key_elevation_deg` and `modifiers` (subject at the centre,
  camera at the bottom, key at the angle, fill opposite when asked). One sentence
  under either. No legend.
- `analysis.light_facts` + `analysis.light_read`: the **light row** on the frame
  page — key direction and height, quality with the edge number, cast in kelvin per
  side when mixed, EV and the band, and outdoors "sun 2° up, 35° left of the lens".
- `verdict.light_checks`: rendered as the check list behind "How it scored", and the
  feedback sentence in the open.
- Viewfinder: `plan.key_azimuth_deg` and tolerance for the ring, the tell for the
  Coach's briefing.

Nothing about the sun is shown for a frame without GPS; it gets the pixel facts only.

## Tests

- `sun_position` against three NOAA fixtures, ±0.5°; the JS port equal to the
  Python on the same fixtures.
- `window_soft_intervals` for a west window in Jakarta in August: soft from dawn to
  ~14:40, direct until sunset.
- McCamy on synthetic frames: D65 grey → 6500 ± 150 K; a 2850 K tungsten patch
  → 2850 ± 200 K; a half-and-half frame → `cct_delta` > 2000.
- Clipping and ratio on synthetic gradients; edge width: a 2 px step reads hard, a
  40 px ramp reads soft.
- `light.check`: a rim plan with `sun_relative = 12` passes direction, `= 60` fails
  it; an indoor Rembrandt with a `loop` read fails pattern softly and a 2.3-stop
  ratio passes fill.
- Designer validation: an out-of-envelope plan is retried once and then replaced by
  the recipe default with an event.

## Cost

`sun_position` + window intervals 0.3 d · pixel facts 0.5 d · recipes and envelope
0.3 d · designer + complete/validate + brief input 0.5 d · Technician read + Judge
diff + feedback input 0.5 d · strip, diagram, light row 0.5 d · sun ring + histogram
(on the viewfinder day) 0.4 d ≈ **3 days**, of which about one is shared with the
"Scout picks the spot" and viewfinder items already planned.
