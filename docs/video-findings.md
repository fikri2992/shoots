# Video: what the panel could watch, and what it must keep refusing

Six questions were researched, 116 findings returned, and the five least-certain load-bearing claims went through an adversarial check — **two came back misstated**. Where a verdict contradicts a finding, the verdict wins and the finding is not repeated here.

Every claim carries a status, on the same rule as [research-findings.md](research-findings.md).

| Status | Meaning |
|---|---|
| **measured** | Arithmetic run against this repo's files or its clips. Method stated inline. |
| **checked** | The primary source was fetched and the figure is what it says. |
| **lead** | Read once, or reasoned but not run. A direction to check, not a fact to build on. |

**Two corrections to the brief this research was given, both mine.**

*Three clips, not one.* The store holds one ingested video, but the tree holds three distinct clips, and [`domain/motion.py:10`](../backend/app/domain/motion.py) already quotes all three: 2.42 / 0.58 / 0.03 frame widths of travel at 5% / 53% / 92% still steps. The constants in the tree were fitted on three. Three is still too few to validate a threshold; it is not one.

*The 0.11 figure is weaker evidence than I made it.* Video techniques fire at 0.11 sightings a shot against composition's 1.94 — but the denominator is 18 Shots of which **17 are photos**, where video techniques should not fire at all. The honest statement is that three clips produced two of twelve possible video techniques (`pan` once, `slow_motion` once; the other ten have never fired). That is a gap worth closing. It is not proof the pipeline is broken.

## The calls

Ordered by value per build-hour. This table is the document.

| # | What | Call | Hours | Why |
|---|---|---|---|---|
| 1 | Give the bare `loudness: -31.4 LUFS` line in [`analyst.py:188`](../backend/app/agents/analyst.py) its reference level, or delete it | **SHIP** | 0.5 | An unreferenced figure sitting in a lens prompt, in a system built to refuse unreferenced figures. |
| 2 | Make `motion.Read.contradicts` **binding at the vote**, not prose in a prompt | **SHIPPED** | 2 | Done — decision 34. `panel.aggregate` takes `settled_for` / `settled_against`. |
| 3 | Two temporal Faults from figures `Motion` already returns | **SHIP** | 3 | Six Faults, none temporal. Zero new compute, zero new dependency. |
| 4 | Send a native video `Part` instead of `tile_sheet()` | **SHIP** | 3–4 | Cheaper than the contact sheet for a short clip, and stops destroying temporal order before the panel looks. |
| 5 | Narrow the shipped video taxonomy from twelve techniques to **three** | **SHIP** | 2 | Twelve techniques firing at 0.11 a shot is not a taxonomy, it is noise with names. |
| 6 | Similarity fit (Lucas–Kanade + `estimateAffinePartial2D`) to settle `push_in` | **SHIP IF TIME** | 6–8 | Measures scale to 0.05% — but adds OpenCV to a CPU-only image and cannot be validated on three clips. |
| 7 | Tracking discriminant on top of #6 | **SHIP IF TIME** | +4 | Separates cleanly in synthesis, never run on a real clip. |
| 8 | `fps=4` windowed re-read around a measured motion event | **SHIP IF TIME** | 4 | The published frame-count ablation is non-monotonic. A hypothesis, not a fix. |
| 9 | A loudness Fault against a −14 LUFS target | **DON'T SHIP** | — | −14 LUFS has no primary source anywhere in Google's documentation. |
| 10 | Let a lens vote `push_in` / `tracking` / `orbit` / `rack_focus` into Evidence | **DON'T SHIP** | — | 43.5% on ShotBench camera movement against ~25% chance. A coin flip with no figure attached. |
| 11 | `orbit` and `rack_focus` by arithmetic | **DON'T SHIP** | — | Orbit needs parallax and depth; rack focus needs a focus measure the 64×36 strip has thrown away. |
| 12 | Music fit, pacing, average shot length | **DON'T SHIP** | — | ASL over a 10–30 s clip with 0–5 detected cuts is not a statistic. |

Rows 1–5 total **eight to nine and a half hours**. That should be the whole of the week's video budget.

---

## 1. The arithmetic already reaches the model. It cannot overrule it.

**measured, and this is the highest-value row in the table.**

[`domain/motion.py`](../backend/app/domain/motion.py) computes `Read.contradicts` — the techniques the measured translation *rules out* — at four separate branches. `motion.describe()` formats it into a sentence ("measured translation rules out: …"), and [`analyst.py:246`](../backend/app/agents/analyst.py) hands that to the Technician and the Composer as `{camera_move}`.

Then it stops. Grepping the tree, the only occurrence of the string `motion` in [`domain/panel.py`](../backend/app/domain/panel.py) is `"slow_motion"` inside `OWNER_OVERRIDES`. **The vote has no knowledge of the measurement.** A lens can vote `static_tripod` on the clip measured at 2.42 frame widths of travel, and that Evidence stands, promotes a SkillState, and reaches the photographer.

"Arithmetic, not opinion" is currently true of the prompts and false of the panel.

**checked, and it is external validation of the whole thesis.** [arXiv 2603.13119](https://arxiv.org/html/2603.13119v1) finds off-the-shelf VideoLLMs near the 25% random-guess rate on camera motion; probing alone reaches 0.450 instance accuracy; **adding geometry-aware external signals reaches 0.738**. Injecting measured geometry is the intervention with published evidence behind it. Shoots already does the injection. It just left out the enforcement.

**Shipped** — [decision 34](domain-model.md). `panel.aggregate` now takes `settled_for` and `settled_against` as plain id sets, so the vote never needs to know which measurement settled them. Against is a veto and the sighting travels on as dissent; for is a corroborating vote recorded as `measured` at confidence 1.0, which is what carries it past decision 33's corroboration bar. A technique settled *for* that no lens mentioned still creates nothing.

**measured.** Replayed on the corpus clip — 2.42 frame widths of travel, 5% still steps, read as `whip_pan` supporting `pan` — the stored `pan` sighting moves from one lens at 0.85, which decision 33 can never count as corroborated, to two votes at 1.0. The veto itself did not fire on this clip because no lens claimed `static_tripod`; it is a guard, and the corroboration path is what the corpus exercises.

## 2. Does the model just watch it?

**Yes, and the contact sheet becomes the fallback.** The cost argument that justified tiling has evaporated.

**checked.** Gemini 3.7 Flash takes video natively, 1M context, and `mp4` is on the supported container list — which is what the ffmpeg pipeline already emits, so there is no transcode step.

**checked, and adversarially confirmed.** Google's own documentation gives **three different numbers** for video token cost:

| Page | Figure | Status |
|---|---|---|
| [video-understanding](https://ai.google.dev/gemini-api/docs/video-understanding) | ~300 tok/s default, 100 tok/s low | stale |
| [tokens](https://ai.google.dev/gemini-api/docs/tokens) | 263 tokens per second | older still |
| [media-resolution](https://ai.google.dev/gemini-api/docs/media-resolution) | **70 tok/frame** for Gemini 3 | current |

The [Vertex mirror](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/video-understanding) settles it: 70 is the Gemini 3 tokenisation and 258/66 belong to "earlier Gemini models". Budget from 70. Note the trap — 70 + 32 audio ≈ 102 tok/s is almost exactly the stale page's "100 tok/s at low", so it is possible to reach the right number for the wrong reason.

Two consequences that are not obvious:

- On Gemini 3, `low` and `medium` media resolution do **not** reduce video cost. All three are 70 tokens. **FPS is the only cost lever**, and it is configurable: `VideoMetadata.fps` defaults to 1.0 with a valid range of (0.0, 24.0], verified in the installed SDK (google-genai 2.19.0). Every summary saying "video is sampled at 1 FPS" describes a default, not a limit.
- Audio arrives with the frames at 32 tok/s whether wanted or not.

**lead on the price** — the Vertex SKU page would not render on any fetch route tried, so $0.75/1M input (introductory through 31 December 2026) is corroborated only from secondary write-ups.

| Input the panel sees | Tokens | $ / 3-lens panel |
|---|---|---|
| 12-tile contact sheet | 1,120 | $0.0025 |
| 10 s clip, native, 1 fps + audio | 1,020 | **$0.0023** |
| 60 s clip, native, 1 fps + audio | 6,120 | $0.0138 |

A 10 s clip watched natively is *cheaper* than the contact sheet of it. Cost does not decide this; the destruction of temporal order does.

## 3. Motion beyond translation

`domain/motion.py` refuses `orbit`, `push_in`, `tracking` and `rack_focus`. **The literature independently confirms the refusal is correct rather than lazy** — [arXiv 2608.10932](https://arxiv.org/html/2608.10932v1) reports estimated pose "cannot identify some movements, such as Zoom and Focus Shift".

But the refusal is a statement about *phase correlation*, not about arithmetic. A translation has 2 degrees of freedom, which is all `shift_between()` can hold. A **4-DOF similarity transform** — scale, rotation, tx, ty — is the minimum that separates a push-in from a pan.

| Technique | What settles it | CPU | Call |
|---|---|---|---|
| `static_tripod`, `pan`, `tilt` | translation, shipped | ~0 | **settled today** |
| `whip_pan` | `step_max` ≥ 0.25 | shipped | settled, **threshold rests on one clip** |
| `push_in` | scale term of a similarity fit | 3.08 ms/pair at 480×270 | SHIP IF TIME |
| `tracking` | *which group moved* | +~1 ms/pair | SHIP IF TIME |
| `orbit` | nothing available — needs depth | — | **keep refusing** |
| `rack_focus` | nothing available at 64×36 | — | **keep refusing** |

**measured** (synthetic warps of a real corpus frame): Lucas–Kanade plus `estimateAffinePartial2D` recovers scale to within **0.05%** and rotation to within **0.02°**. Log-polar / Fourier–Mellin is the wrong tool — it broke outright on rotation (truth 5.0° → 7.7°) and is 4.4× slower.

**measured, and the discriminant is not the obvious one.** A tracking shot and a static camera with a moving subject are *identical* in outlier share (0.116 vs 0.111) and cluster spread (0.080 vs 0.078). They differ only in which group carries the motion. Any tracking detector built on counting outliers measures nothing.

**checked.** [ShotBench](https://arxiv.org/html/2506.21356v2) puts camera movement at 43.5% for Gemini-2.5-flash against ~25% chance; over half the models fall below 40%. The documented failure modes are, to the technique, exactly the four already refused: models "struggle to distinguish between camera position changes (push in/out) and focal length adjustments (zoom in/out)".

And reliability tracks **move intensity**, not model quality — low-intensity moves score 41–52%, high-intensity 100%. Amateur handheld footage is the low-intensity row.

## 4. The first temporal Faults

All six existing Faults are photo-oriented. Two proposals, both computed from numbers `Motion` already returns.

**`unbraced_frame`** — "the framing wobbles without moving". The branch [`motion.py:86`](../backend/app/domain/motion.py) already isolates and currently returns nothing for: `travel < MOVE_DRIFT` **and** `still_share < STILL_SHARE`. That is exactly a fault — the photographer meant to hold still and did not. It **invents no new threshold**, which is why it ships first. Excused by any `SETTLED` technique the vote supports, plus `tracking` and `orbit`.

**`unsteady_pan`** — reversals per second during a pan. Threshold proposed at 1.0/s and **not validated**; it should carry that admission in its docstring the way `BLOWN_SHARE` carries its 19-frame provenance. Critically, `motion.py:14` states that **cuts show up as reversals rather than as drift**, so a cut clip would fire this on the editing rather than the hand. Excusing on `len(scene_times()) > 1` is load-bearing, not decorative.

## 5. Sound

**Ship the honesty fix. Do not ship a loudness Fault.**

**checked, and adversarially confirmed twice.** The −14 LUFS figure a videographer would most want has **no Google primary source**. Four YouTube Help specification pages were fetched directly; every one gives codec, sample rate, bit depth and bitrate, and **none states any figure in LUFS, LKFS or dBTP**. The strongest adversarial find reinforces it: Google's own [Transcoder API docs](https://docs.cloud.google.com/transcoder) attribute −14 to "Spotify, as well as Amazon Echo" — not to YouTube.

**The brief said loudness was measured but unused. That was wrong, and the truth is worse.** [`ingest.py:145`](../backend/app/services/ingest.py) stores it as `VideoMeta.lufs` and [`analyst.py:188`](../backend/app/agents/analyst.py) emits it into the lens fact block as a bare `loudness: -31.4 LUFS`. It is already in front of a model, with no reference level, in a system whose whole principle is that an uncheckable claim is worthless. Either drop the line or give it its standard and direction:

```
loudness: -31.4 LUFS integrated (EBU R128), 8.4 LU below the -23 LUFS broadcast reference
```

Only then is a Fault conceivable, and it must cite **EBU R128 (−23 LUFS)** or **IAB (−24 LKFS**, the figure Google itself publishes for DV360**)**, never −14. One reason not to ship even that: BS.1770 gating is unreliable below roughly ten seconds of audible content, and these clips are 10–30 s.

**Music and pacing stay out — but not for the reason first given.** "No standard exists for pacing" is false: Average Shot Length has been published since [Barry Salt, 1974](https://cinemetrics.uchicago.edu/barry-salt-database). What does not exist is a *prescriptive* threshold, and the real objection is arithmetic — `scene_times()` yields 0–5 cuts on a short clip, and an average over that means nothing. Likewise EBU's LDR quantifies music-to-dialogue with a threshold, but needs a separate dialogue stem, which a single mixed handheld track does not provide.

## 6. The seven-day call

Photos stay the priority. Build rows 1–5 and stop.

**Narrow twelve techniques to three: `static_tripod`, `pan`, `tilt`.** These are the three arithmetic can both prove and disprove from a measurement that already runs on ingest. Keep `whip_pan` as a *modifier of* `pan`, flagged unvalidated — its threshold rests on one clip peaking at 0.634 a step against a pan's 0.063.

The other eight come out of what the panel may vote into Evidence. Two of them, `slow_motion` and `timelapse`, are settleable from `ffprobe` alone and could come back cheaply — [`panel.py:45`](../backend/app/domain/panel.py) already routes both to the Technician via `OWNER_OVERRIDES`, which suggests someone saw this already.

If a lens still wants to say "this looks like a push-in", let it say so as an impression in the Synthesizer's paragraph — **never as Evidence, and never as a Technique that promotes a SkillState.** The Skill graph has already been burned once by promotions built on evidence a second lens never corroborated ([research-findings.md](research-findings.md) §5).

## 7. Open questions

Nothing here is decided.

1. **The token cost, definitively.** Three Google pages give three figures. **One `CountTokens` call on a real clip against `gemini-3.7-flash` on Vertex settles it.** Cheapest, highest-value thing to run first.
2. **The Vertex SKU price.** Could not be read off `cloud.google.com`. Confirm in the billing console; a post-January budget doubles.
3. **Whether Vertex bills the same video part three times** when it fans out to three parallel lenses. Not established. 3× in relative terms.
4. **Whether MM:SS timestamps come back accurately.** Prompt-side is documented; timestamped *output* has no official example and no accuracy figure. Cheap to check — `scene_times()` is ground truth.
5. **No published benchmark evaluates Gemini 3.7 *Flash* on camera movement.** Every 2026 figure cited is Pro. **43–68% is most likely an upper bound.**
6. **Every threshold in this note.** `UNSTEADY_REVERSALS`, `WHIP_STEP`, `MOVE_DRIFT`/`STILL_SHARE` are fitted or proposed against three clips. Any could be wrong by a factor of two and nothing here would reveal it.
7. **The corpus contains no push-in, no orbit and no tracking shot.** Every accuracy figure for those comes from synthetic warps of a single real frame.
8. **Cloud Run timings.** All measured on a Windows laptop. Shared vCPUs run 2–3× slower; budget 1.5–4 s a clip.
9. **Whether native video beats the contact sheet on the panel's actual output**, as opposed to on cost and on principle. That tiling destroys temporal order is true. That it produces better Evidence is reasoning, not measurement.
10. **Rolling shutter.** All three clips are phone video. Skew during a fast pan introduces a shear a 4-DOF similarity model cannot represent.

The single largest constraint is that **three clips cannot validate any of this.** Tone and motion were fitted against real frames and against synthesized pans with known ground truth. Nothing above has that. Five or six deliberate clips — locked off, pan, tilt, push-in, rack focus, handheld walk — is the difference between shipping measurement and shipping numbers someone guessed.
