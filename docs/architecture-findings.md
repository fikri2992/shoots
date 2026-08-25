# The panel is one judge, and two of its claims are not implemented

Four questions were researched against the architecture rather than the domain: decorrelating the panel, measuring anything at all, what ADK 2.7 offers, and cost against failure. 72 findings; the three least-certain load-bearing claims went through an adversarial check and **all three came back misstated**.

Status vocabulary is the same as [research-findings.md](research-findings.md) and [video-findings.md](video-findings.md): **measured** (run here), **checked** (source or installed package read), **lead** (reasoned, not run).

**This note corrects two things I published in [research-findings.md](research-findings.md) §4.** Both were wrong about *what was being measured*, not about the number.

## The calls

Six days left, solo, photographs still the product.

| # | What | Call | Hours | Why |
|---|---|---|---|---|
| 1 | Pin `google-adk>=2.7,<3` in [`pyproject.toml:7`](../backend/pyproject.toml) | **SHIP** | 0.1 | `SequentialAgent` and `ParallelAgent` are `@deprecated` "will be removed", and the pin is unbounded. A `uv sync` can delete the Analyst's skeleton. |
| 2 | Actually give each lens its own image, via one `before_model_callback` | **SHIP** | 1.5 | Decision 18 says the lenses differ in input. They do not. This makes the claim true and drops ~18% of Analyst input tokens. |
| 3 | Guard the panel with an `ANALYSING` status before the model calls run | **SHIP** | 1 | Idempotent on write, not on cost. A redelivery today re-pays four to six model calls. |
| 4 | Delete two false words from [`FramePage.vue:281`](../frontend/src/pages/FramePage.vue) | **SHIP** | 0.2 | The page tells the photographer the elements are "weighted" (inert) "and averaged" (one rater each). |
| 5 | Correct decision 19 and the [`crop.py`](../backend/app/agents/crop.py) docstring | **SHIP** | 0.25 | Its first clause is false in ADK 2.7.1. Keep the loop; stop justifying it with a stale constraint. |
| 6 | `domain/panel_stats.py` — the additive model, as a test | **SHIP IF TIME** | 2–3 | Makes exactly one thing falsifiable, from data already on disk. |
| 7 | Token accounting via `after_model_callback` | **SHIP IF TIME** | 1 | Same mechanism as #2; turns an estimated cost into a measured one. |
| 8 | Stop drawing five bars — one score plus the Faults | **SHIP IF TIME** | 2–4 | 95.6% of stored cells sit within ±1 of a fixed offset. Four of the bars carry no information. |
| 9 | A different model per lens | **DON'T SHIP** | 4–8 saved | Measured null: one-model-per-family made effective independence *fall*, 2.18 → 1.93. |
| 10 | Raise temperature, or sample each lens N times | **DON'T SHIP** | 1–2 saved | Jury accuracy 0.463 → 0.482 for K=1→5, with error correlation 0.944–0.972. Triples latency against a 180 s timeout. |
| 11 | A devil's-advocate or debate lens | **DON'T SHIP** | 6–10 saved | Debate buys agreement with human labels. There are no human labels here, and debate makes judges converge. |
| 12 | Migrate the Analyst onto ADK's `Workflow` API | **DON'T SHIP** | 8–16 saved | Real deprecation, wrong week. `Workflow` cannot yet be an `LlmAgent` sub-agent. |

Rows 1–5 total **about three hours**.

---

## 1. Two corrections to what I published

**The input-separation experiment has never been run.** [`analyst.py:266`](../backend/app/agents/analyst.py) passes `images=[bytes_part(gridded_png), bytes_part(clean_jpeg)]` **once** into `run_workflow`. Every lens in the `ParallelAgent` shares that user turn, so **every lens sees both images**. Decision 18 states the lenses "differ in instruction *and* input (Technician: EXIF + gridded frame; Composer: gridded frame only; Storyteller: clean frame only)". The instruction half is real; the input half exists only as prose inside each prompt telling the lens what to look at.

So research-findings §4's conclusion — "input diversity did **not** decorrelate the lenses" — is not supported. Input diversity was never applied. I called a fix a dead end on the strength of an experiment that never ran.

**r = 0.888 is not inter-rater correlation.** `LENS_ELEMENTS` in [`panel.py`](../backend/app/domain/panel.py) is disjoint: technician rates `technical`, composer rates `composition` and `lighting`, storyteller rates `impact` and `story`. **Each element has exactly one rater.** The averaging loop in `aggregate` always averages a single number. What 0.888 measures is the correlation between five *elements*, not the agreement between three *judges* — halo within a rater, not a failure of panel independence.

The number stands. What I said it meant does not.

## 2. The five elements are one number and a fixed offset

**measured**, over the 90 stored element scores. Fit `score[shot, element] = grand + shot_effect + element_offset`:

| Component | Share of variance | SD |
|---|---|---|
| Shot effect | **88.5%** | 1.592 |
| Element offset | 2.9% | 0.286 |
| Everything else | 8.6% | 0.497 |

Grand mean 7.322. Offsets: `technical` **+0.456**, `lighting` +0.067, `impact` +0.011, `composition` −0.100, `story` **−0.433**. Mean absolute residual **0.383** on a ten-point scale, and **95.6%** of cells fall within ±1 of the additive prediction. PC1 of the correlation matrix explains **91.2%**.

The offsets are what the five bars actually display. `technical` is the weakest element on **0 of 18** Shots — not because the photographs are technically strong, but because its offset is +0.46. Remove each Shot's own mean and the residual correlations are indistinguishable from noise (mean residual r = −0.227 against an analytic null of −0.250).

There is no per-element structure left to decorrelate. That is the honest terminal answer, and it is why rows 9–11 are all **DON'T SHIP**: they attack a correlation between raters that does not exist, because there is one rater per element.

## 3. ADK 2.7

**checked, and this is the cheapest insurance in the note.** Installed `google-adk` **2.7.1** against a `>=1.0.0` pin with no upper bound. `SequentialAgent`, `ParallelAgent` and `LoopAgent` all carry `@deprecated` in 2.7.1 — verbatim, *"deprecated in favor of Workflow and will be removed in a future version"*. The Analyst's entire skeleton is both of the first two. Pin `>=2.7,<3` today.

| Not used | Buys | Call |
|---|---|---|
| `before_model_callback` | Per-lens control of what actually reaches the model — this is row 2's fix | **Take it** |
| `after_model_callback` | `llm_response.usage_metadata`: real per-lens token counts into the existing ActivityEvent | **Take it** |
| `plugins/` | One home for retry and logging across all eight modules that call models | Not this week |
| `workflow/` | Nothing the Analyst needs — `Workflow` cannot yet be an `LlmAgent` sub-agent | **Leave** |
| `evaluation/`, `memory/`, `artifacts/` | Evaluation tooling wants ground truth, which does not exist here | Leave |

**Decision 19's first clause is false.** [`llm_agent.py:402`](../backend/.venv/Lib/site-packages/google/adk/agents/llm_agent.py) says verbatim: *"The ADK supports using `output_schema` and `tools` together. It works by exposing tools during the thought loop and enforcing structure only on the final output."* The second clause — no agent can inject a rendered image mid-invocation — now looks reachable through `before_model_callback`, but **that has not been executed** and stays `checked`, not `measured`.

Keep the hand-written crop loop. It is bounded at two rounds and it works, and rewriting it onto a deprecated `LoopAgent` plus an untested callback path with six days left is the wrong risk. Correct the docstring so the loop is recorded as a choice rather than a constraint.

## 4. Cost is not a problem. The retry bill is.

**measured** for tokens, **checked** for prices. Every image costs **1120 tokens** — [`runtime.py:43`](../backend/app/agents/runtime.py) passes no `media_resolution`, so all of them take the default.

| Stage | Calls | Images | Input tok | Output tok |
|---|---|---|---|---|
| Analyst panel + Synthesizer | 4 | 8 | ~20,400 | ~2,000 |
| Crop loop, ≤2 rounds | ≤2 | ≤4 | ~5,400 | ~200 |
| Judge | 1 | 1 | ~1,700 | ~250 |
| **Per photo** | **5–7** | **9–13** | **~27,500** | **~2,450** |

**About 3.0 cents a Shot.** The whole 18-Shot corpus is **$0.54**. Images are 53% of input tokens; the technique catalogue is another 22%. Cost is not a constraint on this project and should stop being treated as one.

**What is a problem: the stages are idempotent on write and not on cost.** The `ANALYZED` guard sits before any model call, so a redelivery *after* success is free. But a failure **after** `agent.analyse()` returns — the overlay render, the blob write, the repository write — leaves the Shot at `INGESTED`, and the redelivery re-pays for all four to six model calls. `infra/topics.sh` sets `MAX_ATTEMPTS=5`, so the worst case for one Shot is five full panels: twenty lens calls, about $0.15, and **four minutes of demo time** before it dead-letters.

The mid-flight duplicate is well guarded — `ACK_DEADLINE=540` against `panel_timeout_seconds=180` and a Cloud Run timeout of 600. That headroom is doing real work and should not be trimmed.

The fix is one enum value and one guard: move the Shot to `ANALYSING` before the panel runs, so a redelivery mid-flight skips instead of re-paying.

## 5. What the eval track could not settle

All three adversarial checks on the eval track came back **MISSTATED**. The statistic proposed for test-retest (ICC) was cited with its form inverted, the published LLM-judge reliability figures dropped the worst benchmark, and the sample-size formula was missing a term that flips its conclusion. None of it is safe to build on as written.

What survives is the shape rather than the numbers: with no labels, **test-retest is the only reliability question this corpus can answer**, and it costs about $1.20 for three repeat runs. The statistic and the threshold need re-deriving before that is worth doing.

The additive model in §2 is the exception — it is arithmetic on data already on disk, it needs no model call, and it makes exactly one claim falsifiable: if a prompt change does not move the 88.5% shot-effect share or the 0.383 residual, it changed nothing.

## 6. Open questions

1. **Whether separating the images actually moves anything.** Row 2 makes decision 18 true. It does not follow that it reduces the correlation, and §2 argues there may be nothing left to reduce.
2. **Whether `before_model_callback` can inject a rendered image.** Reasoned from the source, never executed.
3. **Vertex pricing.** The $0.75/1M figure is from `ai.google.dev`. Vertex may price differently and was not checked.
4. **The eval statistic.** Needs re-deriving from primary sources after three misstatements.
5. **One agent claim I checked and rejected**: the research reported that `run_workflow` has no retry. It does — `with_retry` at [`runtime.py:95`](../backend/app/agents/runtime.py). The recommendation built on it is dropped.
