# Conditions

Technical note, 2026-08-23. Weather, sky and air as inputs to the plan, the person's
preparation, and the verdict. Companion to `lighting.md`; the same split applies:
code measures and derives, agents decide between trade-offs, code verifies.

## Why it belongs in the loop

A experiment is an appointment with the sky. The sun's position is certain; what the sky
does with it is not: 85 % cloud cancels golden hour, haze kills backlight and makes
the sunset redder, rain makes reflections and ruins the phone. And the person is out
in it: 34 °C that feels like 39 °C is a 40-minute shoot, not a 2-hour one; a phone
carried out of air-conditioning into a 25 °C dew point fogs for ten minutes. An agent
that sends someone out at the wrong hour, unprepared, and then fails them for a light
the sky never provided is neither autonomous nor considerate. Conditions make the
plan *live*: issued with a forecast, re-checked as it nears, re-planned when the sky
changes, and judged against what the sky actually did.

## Sources

- **Google Maps Platform Weather API** — hourly forecast to 240 h and current
  conditions: temperature, feels-like, humidity, dew point, precipitation
  probability and amount, cloud cover %, condition type, UV index, wind, visibility.
- **Google Maps Platform Air Quality API** — universal AQI and dominant pollutant.
- Fallback: Open-Meteo (no key) with the same fields, so local dev runs without a
  billing account.

Fetched by `infra/weather.py`, cached per rounded coordinate (0.05°) and hour in the
store, so one experiment costs a handful of calls across its life. The location is the one
the Scout already uses: the GPS of the person's newest frame.

## Data

```python
class Conditions(BaseModel):
    """One hour at one place, as forecast or as observed."""
    at: datetime
    source: Literal["forecast", "observed"]
    temp_c: float | None
    feels_like_c: float | None
    humidity_pct: float | None
    dew_point_c: float | None
    precip_prob_pct: float | None
    precip_mm: float | None
    cloud_cover_pct: float | None
    condition: str = ""            # API's type: CLEAR, PARTLY_CLOUDY, RAIN, THUNDERSTORM, ...
    uv_index: float | None
    wind_kmh: float | None
    visibility_km: float | None
    aqi: int | None

class Sky(StrEnum):
    CLEAR = "clear"                # 0–20 % cloud: hard light, clean golden hour
    BROKEN = "broken"              # 20–60 %: variable, dramatic skies, light comes and goes
    OVERCAST = "overcast"          # 60–90 %: soft, colour muted, no rim
    FLAT = "flat"                  # > 90 %: shadowless, golden hour cancelled

class Comfort(StrEnum):
    COOL = "cool"; FINE = "fine"; WARM = "warm"; HOT = "hot"; DANGEROUS = "dangerous"

class Derived(BaseModel):
    """Pure functions of Conditions; every field carries the number it came from."""
    sky: Sky
    comfort: Comfort               # feels-like < 18 / < 30 / < 34 / < 40 / ≥ 40
    max_minutes: int               # 120 / 120 / 90 / 45 / 0
    rain: Literal["dry", "possible", "likely", "raining"]   # prob < 25 / < 60 / ≥ 60 / mm > 0 now
    fog_risk: bool                 # temp − dew point ≤ 2
    lens_fog_risk: bool            # dew point ≥ 24 (an air-conditioned phone meets it)
    haze: Literal["none", "some", "heavy"]                  # AQI < 100 / < 150 / ≥ 150, or visibility < 5 km
    wind: Literal["calm", "breezy", "strong"]               # < 15 / < 30 / ≥ 30 km/h
    golden_hour_usable: bool       # sky in {clear, broken}
    rim_possible: bool             # sky is clear and haze is not heavy

class PrepItem(BaseModel):
    what: str                      # "Carry water; shade between frames"
    why: str                       # "34 °C, feels like 39 °C at 17:40"
    kind: Literal["body", "gear", "light", "timing"]

class Fit(BaseModel):
    """How well a slot's conditions suit a technique, 0..1, with the reasons."""
    score: float
    reasons: list[str]
```

`Experiment.conditions_at_issue: Conditions`, `Experiment.conditions_latest: Conditions`,
`Experiment.prep: list[PrepItem]`, `Experiment.replans: list[Replan]`,
`Verdict.conditions: Conditions | None` (observed at `captured_at`).

## Derivation: the arithmetic — `domain/weather.py`

- `derive(conditions) -> Derived` with the thresholds above. Comfort uses the API's
  feels-like (a heat index with humidity) rather than dry-bulb temperature; the
  bands follow the usual public heat-advisory scale, and `DANGEROUS` means the slot
  is not offered at all — the Scout does not get to reason about it.
- `sky_light(sky) -> (source, quality)`: `CLEAR → (SUN, HARD)`, `BROKEN → (SUN,
  HARD, variable)`, `OVERCAST → (SKY, SOFT)`, `FLAT → (SKY, SOFT)`. This is the
  bridge into `lighting.md`: the designer's envelope is narrowed by the sky before it
  reasons — under overcast, `rim` and `silhouette` are not in it.
- `fit(technique, derived) -> Fit`, a table, not a model:

  | technique wants | scores high when | scores low when |
  |---|---|---|
  | golden hour, rim, backlight, long shadows | clear or broken, haze none | overcast, flat, heavy haze |
  | soft portrait, window light (outdoors: open shade) | overcast, flat | clear midday |
  | dramatic sky, silhouette | broken | flat |
  | reflections, rain streets | raining, wet after rain | dry |
  | long exposure, panning | calm or breezy | strong wind (tripod), raining (phone) |
  | any | comfort fine or warm | hot (score × 0.6), dangerous (0) |

  Every deduction is a reason string with its number, and the reasons travel with
  the plan into the log ("moved from Friday: 82 % rain at 17:00").
- `prep(technique, derived, constraints) -> list[PrepItem]`: templates with numbers.
  Examples of the whole vocabulary — there are about fifteen:
  - body: *Carry water, shade between frames* — feels like 39 °C; *Forty minutes,
    then stop* — hot; *Sunscreen, a hat* — UV ≥ 8 and a daytime slot.
  - gear: *Take the phone out of the air-con ten minutes early* — dew point 25 °C;
    *A plastic bag or a cover* — rain likely; *Weight the tripod* — wind 28 km/h and
    the technique needs one; *Lens cloth* — raining or fog risk.
  - light: *Haze will flatten contrast; expect a redder sunset* — AQI 140; *Light
    comes and goes; wait for a gap* — broken sky; *No rim today; shoot the soft
    version* — overcast.
  - timing: *Rain clears by 16:00; go after* — hourly precipitation.

  No item without a number. No general advice ("dress appropriately").

## Reasoning: where the agent decides

Three decisions need judgment, and only these run a model.

1. **Which slot, which technique** — the Scout already ranks techniques by skill gap;
   now each candidate slot carries `Derived` and `Fit`, and the Lighting Designer's
   envelope is already narrowed by the sky. The designer reasons over the trade-off
   the table cannot: Saturday is clear but hot (fit 0.6), Sunday is broken and fine
   (0.85) but the person wrote "weekday lunches only"; it chooses and says why.
2. **Re-planning** — the five-minute tick (`/tasks/tick`) already delivers experiments.
   Add: at T−24 h, T−6 h and T−90 min, refetch; code computes the delta
   (`sky` changed band, `rain` crossed "likely", `comfort` crossed "hot", fit fell by
   more than 0.3). Below threshold, nothing runs. Above it, the **Replanner** — an
   `LlmAgent` with `output_schema=ReplanOut` — is given the experiment, the old and new
   `Derived`, the next three alternative slots with fits, and the person's
   constraints, and returns one of `keep | shift(slot) | swap(technique, slot) |
   hold`, with a one-sentence reason. Code applies it: `shift` rewrites `deliver_at`
   and re-completes the light plan; `swap` re-runs the designer for the new
   technique; `hold` keeps the experiment open without a delivery and tries again next
   tick. The person gets one push with the reason, and `experiment.replanned` lands in the
   log. The Replanner cannot invent a slot that code did not offer.
3. **The verdict under the sky that was** — the Judge gets `Verdict.conditions` as
   observed at `captured_at` (fetched at judge time; current conditions when the
   frame is fresh, the cached hour otherwise). `light.check` is run against the
   plan *as the sky allowed it*: if `rim_possible` was false at capture, the rim
   check is marked `excused`, and the feedback model is told that the light, not the
   person, failed. An excused experiment is not closed and not failed: the Replanner is
   invoked with `reason="sky"` and the experiment moves. That is the considerate part, and
   it is a rule, not a mood.

Everything else — thresholds, fits, prep, deltas — is code, tested, and logged with
numbers. The multi-agent design is justified by the fan-in, not by agent count: sun
(code), sky and air (two APIs), the person's constraints (Coach memory), the skill
gap (Cartographer), the venue (Places, later) all meet in one planner that has to
choose, and one watchdog that has to change its mind.

## What the phone shows

- **Experiment hero, the `when` line**: `Sat 17:40 · 31°, feels 36 · 20 % cloud · rain 10 %`.
  Nothing else; the numbers are the honesty.
- **Before you go** — a disclosure row with the prep items, each with its reason in
  meta type. The `gear` items that are time-bound ("take the phone out of the
  air-con") are also pushed at T−30 min.
- **Moved** — an amber line above the `when` line when the experiment was re-planned:
  *Moved from Fri 17:10 — 82 % rain*. Tapping opens the log entry.
- **Frame page, light row**: adds `sky: overcast 85 %` and `haze: AQI 140` when
  observed conditions exist.
- **Verdict**: an excused check reads *"No rim possible under 85 % cloud — not on
  you. Moved to Sunday 17:35."*
- **Journey log**: `Scout · replanned · 82 % rain at 17:00 → Sun 17:35`.

## Tests

- `derive` at the band edges (feels-like 29.9 / 30.0 / 34.0 / 40.0; cloud 20 / 60 /
  90; dew-point spread 2.0).
- `fit` table: rim under flat sky → 0 with "overcast" in reasons; reflections while
  raining → high; any technique at `DANGEROUS` → 0 and the slot absent from the
  Scout's candidates.
- `prep`: every item has a number in `why`; a dry, fine, clear slot yields nothing
  but the sunscreen item at UV 9.
- Delta thresholds: a 15 % cloud change does not invoke the Replanner; a band change
  does; the Replanner's `shift` can only name an offered slot (schema `Literal`
  over the offered ids, built per call).
- Judge: rim plan, `rim_possible=False` at capture → check excused, experiment not
  closed, `experiment.replanned` published once.
- Weather client against recorded responses; the cache keyed by rounded coordinate
  and hour; Open-Meteo fallback selected when no Maps key is configured.

## Cost

Client + cache 0.3 d · `derive`/`fit`/`prep` 0.5 d · Scout slot input 0.3 d ·
Replanner + tick hooks + push 0.5 d · Judge conditions + excuse 0.3 d · hero line,
Before-you-go, Moved, light row 0.4 d ≈ **2.3 days**. Comes out of the same eight as
`lighting.md`; together they are the "Scout picks the spot and the sky" day plus
about two more. The trade I would make: drop the month reel and the camera card,
keep the Replanner — a plan that visibly changes its mind is worth more in four
minutes of video than either.
