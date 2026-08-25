# Research findings: what holds, what does not

Seven questions were researched. This note records the answer to each, the status of every load-bearing figure, and a ship / don't-ship call.

Every claim carries a status, because the first pass through this research was not checked against its sources and produced six errors in twelve claims — three of which would have changed a decision. The status is the point of the document.

| Status | Meaning |
|---|---|
| **measured** | Arithmetic on this repo's corpus (18 Shots, 18 Analyses, 37 SkillStates). Reproducible; the method is stated inline. |
| **checked** | The primary source or the raw dataset was read, and the figure below is what it says. |
| **lead** | Read once, not verified against the primary. A direction to check, not a fact to build on. |

## The calls

| # | Question | Call |
|---|---|---|
| 1 | Is the 1-10 score meaningful? | **Ship a fix.** The score is one number wearing five hats, and it is inflated past anything the reference distribution contains. |
| 2 | Should scoring become ranking? | **Ship.** Strongest result in the batch, and decision 21 already has the machinery. |
| 3 | Do five text levels beat the integer 1-10? | **Don't ship.** The method needs token log-probabilities we cannot get. |
| 4 | Is the three-lens panel independent? | **Ship a fix.** It is not, and the rubric is where it shows. |
| 5 | Can the Skill graph track progress deterministically? | **Shipped.** BKT and Elo are unfittable for one photographer. Panel corroboration is already computed and is genuinely per-Technique. |
| 6 | Should colour harmony be scored against templates? | **Don't ship.** Still degenerate after the obvious repair. |
| 7 | Should a no-reference quality model or saliency be added? | **Don't ship.** Both measured here; both too weak to carry a Fault. |

---

## 1. The score is inflated, and it is one number

**measured.** The five rubric elements do not measure five things.

| | impact | composition | lighting | technical | story |
|---|---|---|---|---|---|
| **impact** | — | 0.97 | 0.88 | 0.94 | 0.90 |
| **composition** | 0.97 | — | 0.91 | 0.94 | 0.86 |
| **lighting** | 0.88 | 0.91 | — | 0.89 | 0.74 |
| **technical** | 0.94 | 0.94 | 0.89 | — | 0.86 |
| **story** | 0.90 | 0.86 | 0.74 | 0.86 | — |

Mean off-diagonal r = **0.888**, lowest pair 0.74. Three consequences, all on the same 18 Analyses:

- The weighted mean correlates **0.986 with `impact` alone**. Four of the five elements are decoration.
- **Reversing the PPA weights end for end** — 10/15/20/25/30 instead of 30/25/20/15/10 — moves the overall score by a mean of **0.12 points**, r = 0.995. The weights in `domain/rubric.py` are inert.
- A plain unweighted mean correlates **0.999** with the weighted one.

**checked.** The score is also inflated, by more than it looks. AVA is the standard aesthetic reference set: 255,530 photographs, each rated by around 200 people. Computed directly from the released `AVA.txt`, not quoted from a summary:

| Quantity | Value |
|---|---|
| Grand mean of per-image mean scores | **5.383** |
| SD **across** images | **0.731** |
| SD **within** one image (voter spread) | 1.429 |
| Images with mean ≥ 8 | **48 of 255,530** — 1 in 5,324, z = 3.58 |
| Images with mean ≥ 9 | **0** |

The Analyst's stored scores over 18 Shots: median **8**, mean 7.28, and **four Shots scored 9**. No photograph in AVA reaches a mean of 9. The Analyst hands 22% of one photographer's camera roll a grade that a quarter of a million photographs never earn.

The 1.429 is why this was missed on the first pass: 1.4 is the spread *among voters looking at one photo*, not the spread among photos. Using it puts a score of 8 at roughly 1 in 25 and makes the inflation look like rounding.

**Ship.** Two changes, both cheap:

1. Give the anchored descriptors in the lens prompts an explicit reference population, and put 8 and 9 where AVA puts them. A 9 has to mean "I have not seen this before".
2. Stop presenting five elements as five judgements. Either give the lenses genuinely disjoint criteria (§4) or collapse the readout to one number and stop implying a breakdown the arithmetic does not support.

Source: [AVA: A Large-Scale Database for Aesthetic Visual Analysis (Murray, Marchesotti & Perronnin, CVPR 2012)](https://ieeexplore.ieee.org/document/6247954). Figures computed from `AVA.txt`.

## 2. Ranking beats scoring, and by a lot

**checked.** In the Visual Aesthetic Benchmark human study, eight expert annotators labelled 226 tasks under both protocols, a majority needing five of eight. Measured as whether independent experts reproduce the same "best image" label:

| Task type | Scoring | Ranking | Δ |
|---|---|---|---|
| Matched content (N = 119) | 52.9% | **95.0%** | +42.0 |
| Mixed content (N = 107) | 65.4% | **94.4%** | +29.0 |
| Matched content, best *and* worst | 39.5% | **90.8%** | +51.3 |

All p < 0.001, McNemar. Asking an expert to *score* matched content is close to a coin flip. Asking the same expert to *rank* it is near-perfect.

Note what the split is not: homogeneous versus heterogeneous **content**, not photographs versus other media. The separate VAB model benchmark is 400 tasks and 1,195 images across fine art, photography and illustration.

**Ship.** Decision 21 already hands the Judge the photographer's highest-scoring earlier Shot for the Technique. That is a ranking operation currently reported as a comparison of two scores. Make it a ranking outright — better than / worse than / cannot separate, against a named Shot the photographer can pull up. It is more reproducible than the number and it is the thing a photographer can act on.

Source: [Visual Aesthetic Benchmark: Can Frontier Models Judge Beauty?, arXiv:2605.12684](https://arxiv.org/abs/2605.12684)

## 3. Text levels instead of numbers — do not do this

**checked.** Q-Align replaces the numeric target with five words (excellent / good / fair / poor / bad) and reaches SRCC 0.822 on image aesthetic assessment. Two facts kill it here:

- It is **supervised fine-tuning** of mPLUG-Owl2 on 236K AVA images. The zero-shot base model scores 0.552. It is not a prompting change.
- The score is a probability-weighted sum over the five level tokens. The paper extracts "the close-set probabilities of rating levels" and "the log probabilities on different rating levels". Without those logits the method collapses to argmax over five buckets — **coarser than the integer 1-10 the Analyst already returns**.

Gemini through ADK structured output does not expose level-token logprobs. Adopting the five words without the probabilities would lose resolution, not gain it.

**Don't ship.** The transferable idea is §1's: anchor descriptors to a real population. That works on a numeric scale.

Source: [Q-Align, ICML 2024, arXiv:2312.17090](https://arxiv.org/abs/2312.17090)

## 4. The panel is not independent

**measured.** Decision 18 differentiates the three lenses by instruction *and* by input, on the theory that a panel is only worth its cost when the errors are not shared. Test it on the two lenses that share the least. The Technician sees EXIF plus the gridded frame; the Storyteller sees the clean frame and nothing else; they rate different elements against different criteria.

`technical` ↔ `story` correlate at **0.86**.

Different instructions, different pixels, different criteria, and the outputs still move together. Input diversity did not decorrelate the lenses. Whatever the panel measures, it is one thing, and it is most likely the frame's overall appeal leaking into every element.

**lead.** Published work on LLM juries reports the same failure — panels of correlated judges delivering roughly two effective votes out of nine. That figure is one benchmark row and others in the same paper are higher, so treat it as direction, not magnitude. The measurement above is this repo's own and needs no citation.

**Ship a fix.** The vote in `domain/panel.py` is fine: Evidence is a claim about whether a Technique is present, and lenses can genuinely disagree there. The rubric is the problem. Either give each lens criteria that cannot be satisfied by "this is a good photo", or stop averaging element scores across lenses and let each element belong to exactly one lens — the way decision 31 already routes the measurements.

Source: [Nine Judges, Two Effective Votes](https://arxiv.org/html/2605.29800), with the scope caveat above.

## 5. Deterministic skill progress

**measured.** The Skill graph inflates, and the mechanism is the score, not the threshold.

| Quantity | Value |
|---|---|
| Techniques that reached `solid` | **16 of 37**, from 18 Shots |
| Attempts taken to reach `solid` | median 5, min 3, max 8 |
| Of those 16, `best_score` = 9 | **12** |
| All 37 SkillStates with `best_score` 8 or 9 | **32** |

The promotion rule was not obviously wrong — nothing reached `solid` on fewer than three attempts. The input was, and worse than "the score is inflated".

**The score is a property of the frame, and it was being spent per Technique.** `apply_analysis` set `state.best_score = max(state.best_score, analysis.score)` for every Technique the panel found. One photograph demonstrating six Techniques handed the same number to all six, so each was credited with whatever the best one in the frame earned. `diagonals` reached `solid` carrying a `best_score` of 9 and **zero** corroborated sightings — promoted on a number it had no part in.

No per-element substitute exists either: §1 and §4 show the rubric's five elements correlate at 0.888 and the weighted mean tracks `impact` alone at 0.986. There is no per-Technique quality signal anywhere in an Analysis.

What *is* about one Technique is how the panel saw it. Over the 105 stored evidence rows:

| Evidence quality | Rows |
|---|---|
| One lens only | **52** |
| Two lenses | 35 |
| Three lenses | 18 |

Half the map was built on single-lens sightings — §4's finding, arriving in the Skill graph. The panel admits a lone lens at confidence ≥ 0.75, and one lens with a habit is one opinion however often it repeats.

**Shipped** (decision 33, `domain/skills.py`). Promotion now counts **corroborated** attempts — `agreement >= 2` **and** `confidence >= 0.75`, both conditions. `practiced` is two attempts with one corroborated; `solid` is three with three. The score stays on the SkillState for the Judge's comparison and the Coach's briefing, and promotes nothing. Rebuilt over the same 18 Shots:

| | before | after |
|---|---|---|
| Techniques that reached `solid` | 16 of 37 | **6 of 37** |

The ten that fall are the ones no second lens ever saw. The map now claims a Technique is *repeatable* — which the arithmetic supports — and stops claiming it was done *well*, which nothing here measures.

**checked.** Bayesian Knowledge Tracing cannot be fitted here at all. Slater and Baker simulated BKT parameter recovery across sample sizes and found estimates converge to their seed parameters at **25 or more students per model**; at 5 and 10 students they do not converge, and the authors decline to report those conditions in the rest of the paper. BKT is fitted per skill *across a population*. Shoots has one photographer. There is no population to fit against, at any number of Shots. The same objection sinks Elo and IRT.

**lead.** Half-life regression was the other candidate and it points the opposite way from how it was first reported here. The form is `h = 2^(k−f)` over a handful of features. Duolingo's own follow-up work removed the per-item lexeme features and the thinner model beat the full one; an independent replication puts the full model near chance. A rich per-Technique learned half-life is therefore the documented failure mode, not the fix, and the fixed `skill_decay_days` interval is defensible as it stands. This paragraph was not verified against the primary — check it before acting on it.

**Next, if there is time.** The corroboration fix gives the map a successes-over-attempts pair for the first time, which is exactly what a **Beta-Binomial posterior with shrinkage** needs: shrink `corroborated / attempts` toward the photographer's own overall rate and report an interval rather than a status word. About fifteen lines of arithmetic in `domain/`, reproducible from stored data the way decision 14 requires, and it would refuse to call three sightings mastery because the interval is still wide. Keep the four status words on screen; compute them from the interval's lower bound. Not required — the corroboration count already fixes the false promotions; this only makes the confidence honest at small n.

Sources: [Slater & Baker, *Degree of Error in Bayesian Knowledge Tracing Estimates From Differences in Sample Sizes*](https://link.springer.com/article/10.1007/s41237-018-0072-x); [Settles & Meeder, *A Trainable Spaced Repetition Model for Language Learning*, ACL 2016](https://aclanthology.org/P16-1174/) — the half-life paragraph is a lead, not checked.

## 6. Colour harmony templates stay out

**measured.** Template fitting — Cohen-Or's seven hue templates, each rotated to its best fit — is degenerate in its plain form: the widest template wins on any input. The obvious repair is to require *balance* as well as coverage, so a template only scores when all of its sectors are occupied. Scored as coverage × balance over synthetic hue distributions with a known right answer:

| Input | Should win | Won | Score |
|---|---|---|---|
| Complementary, 30°/210° | X | X | 1.00 |
| Triadic, 0/120/240° | T | T | 0.67 |
| Single hue | i or V | V | 1.00 |
| Analogous, broad | i or V | **T** | 1.00 |
| **Uniform random hue (null)** | nothing | **T** | **0.51** |

The balance term fixes the worst cases and leaves the one that matters. Random hue still scores 0.51 as triadic, and broad analogous is misread as triadic outright. A fit score that gives noise half marks cannot support a Fault or Evidence.

**Don't ship.** `domain/tone.py` already reports the honest version: the two dominant hues and the angle between them, `opposed` above 120° and `neighbouring` below 60°. That is a measurement. A harmony *score* is not available at this quality.

**measured — and a correction.** A related claim reported earlier, that ranking hues by chroma rather than by pixel count flips the dominant hue on almost every frame, does not hold. Re-run over all 16 photographs in the corpus, weighting each hue sector by S×V instead of by pixel count changes the top hue on **3 of 16**. Real, but small. The `np.bincount` ranking in `imaging/tone.py` stays; revisit only if a Fault ever depends on it.

Source: [Cohen-Or et al., *Color Harmonization*, SIGGRAPH 2006](https://dl.acm.org/doi/10.1145/1179352.1141933)

## 7. No-reference quality and saliency

**measured.** Classical saliency is fast and cannot localise. Both OpenCV detectors, over this repo's own frames at a 768 px long edge:

| Detector | Time | Fraction of pixels holding 50% of the saliency mass |
|---|---|---|
| Spectral residual | 2.1 ms | 0.174 (range 0.093–0.254) |
| Fine-grained | 41.5 ms | 0.182 (range 0.118–0.240) |

A tight subject would concentrate that mass into roughly 5% of the frame. At 17–18%, spread over a fifth of the picture, the map cannot say where the subject is — which is the only thing we would want it for. The Composer's `subject_x` / `subject_y` is better evidence than this, and decision 28 already gates it on the cells the same lens named.

**lead.** NIQE and the other no-reference metrics correlate with human aesthetic judgement somewhere around 0.23–0.38 on in-the-wild photographs: weak, positive, and not enough to carry a Fault. An earlier report that NIQE *inverts* was wrong — the negative correlation in question was against ground-truth PSNR on a low-light-enhancement benchmark, not against perceived quality. The conclusion is unchanged; the reason given for it was not.

One licensing note worth recording. `pyiqa`, the usual route to these metrics, redistributes several models under **PolyForm Non-Commercial**. MANIQA is Apache-2.0 at its own source and inherits the non-commercial terms only through pyiqa's redistribution, so taking it upstream is a legitimate route if it is ever wanted.

**Don't ship.** Neither is arithmetic in the sense decision 20 means. Both are a second model's opinion with a number printed on it.

## Accent detection, as a side finding

**measured.** A `single_accent` detector built from area, connected-component compactness and chroma contrast separates the cases it should — one vivid blob scores 0.75, the same vivid area scattered scores 0.002, half a vivid frame scores 0.0 — but a vivid blob **jammed into the corner also scores 0.75**. Compactness and contrast cannot tell a subject from a distraction. Centrality is computed and left unused, and wiring it in would be inventing a compositional rule rather than measuring one.

Worth knowing before anyone builds it. Not ready.

---

## Corrections to the earlier reports

Recorded because each was stated as settled during the work, and two of them are mine rather than a source's.

| Claim as first reported | What it is |
|---|---|
| Calibration beats rubric-writing about 3×, −0.463 against −0.156 | **Refuted.** Those figures come from v1 of arXiv:2601.08654, which was replaced. In v2 the calibration ablation costs 0.0508 QWK on the essay benchmark against 0.0311 for rubric locking — 1.6×, not 3× — and the bootstrap SE on that row is ±0.0601, larger than the effect itself. The paper also retitled, dropping "Locked Rubrics". Separately, "rubric locking" freezes an already-written rubric against runtime drift; it never varied rubric *quality*, so reading it as "time spent writing the rubric" was a category error on top of a stale version. |
| AVA mean 5.5, SD 1.4, so a score of 8 is about 1 in 25 | **Wrong, and it understated the problem by two orders of magnitude.** 1.4 is the within-image voter SD. Across images the SD is 0.731 and a mean of 8 is 1 in 5,324. |
| Q-Align's five level words are a prompting change worth adopting | **Wrong.** It is supervised fine-tuning, and the scoring step needs level-token logprobs we do not have. |
| Fixed decay intervals fail, so learn a half-life per Technique | **Backwards.** The failure documented at Duolingo is of rich per-item learned features, and their fix was to delete them. |
| NIQE inverts and would downgrade the best frames | **Wrong reason, right conclusion.** The negative correlation was against PSNR on a low-light benchmark. |
| Ranking beats scoring "on photographs specifically" | **Fabricated precision.** The split is homogeneous versus heterogeneous content. The result itself holds, at +29 to +42 points. |
| The rule of thirds has no aesthetic effect | **Overstated.** Amirshahi et al. found thirds-conforming photographs *were* rated more aesthetic — 0.59 against 0.54, p < 0.01 — but at Cohen's d = 0.36. Weak, not absent. Keep the guide; soften what `off_guide_subject` claims. |
| 16 Techniques reach `solid` on a median of 2 observations | **My own error.** 2 is the median across all 37 SkillStates. The 16 that reached `solid` took a median of 5 attempts, minimum 3. The threshold is not the bug; the score feeding it is. |
| Weighting hues by chroma flips the top hue on 11 of 12 frames | **My own error.** Re-run over all 16 photographs: 3 of 16. |

Two of the eight are mine and were reported as measurements. Both were arithmetic run over the wrong subset, and neither would have survived being re-run. That is the argument for stating the method inline beside every figure above.

Source for the rule-of-thirds correction: [Amirshahi, Hayn-Leichsenring, Denzler & Redies, *Evaluating the Rule of Thirds in Photographs and Paintings*, Art & Perception 2 (2014) 163–182](https://doi.org/10.1163/22134913-00002024)

## What was not researched

Two directions were opened and never checked against sources: **product cadence** (feedback timing, streaks, the Scout's daily rhythm) and the **colour emotion** literature behind the warm and cool axis in `imaging/tone.py`. Nothing in this document rests on either. Anything drawn from them should be treated as `lead` until read.
