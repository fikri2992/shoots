# Devpost story writing brief

Read this before revising `docs/devpost-story.md` or drafting the hackathon video
story. This file preserves the August 27 writing debate and the reasons the
current Inspiration section was rejected.

## Current status

The Devpost form contains a working draft. It is not approved copy.

The submission-facing product name is **ShootsAI**. Code, repository, APIs, and
domain records retain **Shoots**. In submission copy, `ShootsAI` names the product;
`Shot`, `Shoot`, and plural `Shoots` retain their domain meanings.

The last explicit judgement on the Inspiration section was:

> The writing feels soulless, shallow, and like a nothing burger. Analyze first.

The current draft is useful as source material, but its polished structure is
part of the problem. Do not treat text in the form as a locked answer.

## Source

The original Claude Desktop conversation is stored locally at:

`C:\Users\fikuri\.claude\projects\C--Users-fikuri-Documents-shoots\8332ef19-e3aa-45bc-b1d7-2e5d9e2b8ca4.jsonl`

- Session: `Android app documentation review`
- Session id: `8332ef19-e3aa-45bc-b1d7-2e5d9e2b8ca4`
- Relevant period: 2026-08-27 15:00 to 15:19 local time
- The conversation ends with Claude asking Fikri for three concrete memories.
  Fikri had not answered them in that session.

## The personal truth

Fikri is a beginner phone photographer with some Technique knowledge. He shoots
freely on walks and trips, often taking about thirty Shots in one outing. He
loves photography but cannot afford a DSLR or mirrorless camera. That sometimes
makes phone photography feel less legitimate to him.

The painful uncertainty is not simply whether one Shot is good. It is whether a
Keeper came from a decision he can repeat or from luck. His archive keeps growing,
but he cannot see whether his eye is developing. He does not know what he does not
know. Asking a stronger photographer takes time, and he is shy because he fears
his work is not good enough to show.

Existing options answer useful but smaller questions:

- A community can show whether one posted Shot lands with people. It does not
  remember months of unposted work or explain what "keep it up" refers to.
- A critique app can inspect one Shot and name possible issues. It usually starts
  from zero on the next upload.
- A general chatbot can explain a supplied Shot. Uploading a whole Shoot is work,
  and its answer does not automatically become a durable Photographer record.
- A human mentor could understand the Photographer over time. Most hobbyists do
  not have continuous access to one.

The product question is locked elsewhere in the domain model:

> What patterns keep appearing across my Shots, and can I deliberately reproduce
> the ones present in my Keepers?

The related human question is simpler:

> Am I actually getting better at taking pictures?

The story must connect those questions without pretending ShootsAI can measure
artistic quality or prove general improvement.

## What the product finishes

ShootsAI turns ordinary Camera activity into a settled learning record. It observes
approved Shots, runs analysis, groups natural Camera activity into a Shoot,
waits for every member Run, records what repeated or varied, updates bounded
Photographer memory, then selects one supported explanation, Experiment, question,
or silence. It preserves the reasons for the selected and rejected routes.

The finished artifacts matter more than the pipeline vocabulary:

- a Shot Teaching Receipt with Evidence and one usable move;
- a settled Shoot Record with exact membership and provenance;
- an Experiment Record that separates recurrence from deliberate Reproduce
  evidence;
- a Journey that compares the Photographer with earlier comparable work;
- a Deconstruction draft that the Photographer may turn into a shareable carousel.

The Photographer owns taste, Intent, Keeper choice, and whether a Change was an
improvement. ShootsAI owns the background accounting work.

Before making a build claim, check `docs/feature-list.md`,
`docs/release-readiness.md`, and `docs/cloud-proof.md`. Describe incomplete proof
as incomplete.

## How the draft changed

### First draft

The first draft opened with a broad beginner statement, listed weak community and
AI feedback, then introduced the remembered archive.

Fikri's objection: the problem was buried. A judge could not see why ShootsAI needed
to exist.

### Skill or luck opener

Claude tried variants such as:

> My best Shot this year might be skill. It might be luck.

Fikri's objection: bluntness did not create clarity. The section still moved
between too many ideas and lacked nuance.

### Three-second question

The next version opened with:

> Am I actually getting better at this?

This was the first opening Fikri liked. Claude then made the section follow one
line of reasoning: tools inspect individual Shots, while development appears
across time.

### Advertising structure

Fikri proposed an invisible structure:

1. State the large problem.
2. Show what current solutions offer and where each stops.
3. Reveal the realization or current workaround.
4. Introduce the true product answer.

Claude copied the word "promise" into the prose. Fikri rejected that. The
structure is useful; its labels should never appear in the copy.

### Competitor comparison

Claude gave each alternative credit before naming its limitation. This removed
the strawman, but the result used repeated "can do X, cannot do Y" sentences.

Fikri's objection: tasteful logic was still not human writing. It sounded like a
market comparison wearing first person.

### Final diagnosis

Claude stopped rewriting and identified the actual failures:

- The section contains no concrete lived image.
- Symmetrical competitor sentences sound manufactured.
- One insight is restated several times without developing.
- Tightening removed Fikri's most vulnerable truths.
- Several paragraphs end with polished punchlines, so the writer becomes more
  visible than the person.
- Rhetorical questions imitate depth instead of earning it.

This diagnosis is accepted. No later story version superseded it.

## Missing human material

A final Inspiration section needs three details that an agent may not invent:

1. One real Shot Fikri loved. What was in it, where was he, what did he feel, and
   what exact doubt followed?
2. One real feedback disappointment. Which community, person, or app responded,
   what did it say, and what did Fikri do next?
3. The reason he did not ask a stronger photographer, in his own unpolished words.

Agents may mark these as `[NEEDS FIKRI]`. They must not fabricate a substitute.

## Writing contract for agents

When asked to help, follow this order:

1. Read this brief, `docs/devpost-story.md`, `docs/product.md`, and the current
   release evidence named above.
2. State the single intention of the proposed version in one sentence.
3. Diagnose which part of the existing copy blocks that intention.
4. Write one bounded proposal. Keep the first three seconds understandable to a
   judge with no photography knowledge.
5. Explain the important choices in no more than five bullets.
6. Check every product claim against current evidence.
7. Return the proposal in chat or a uniquely named proposal file. Do not overwrite
   `docs/devpost-story.md` until Fikri selects a version.

Prefer one lived moment and one earned insight over a complete market survey.
Keep useful competitors credible. Let vulnerability remain a little uneven.
Use one memorable closing line at most.

## Acceptance check

A proposal is ready for Fikri to compare only if:

- the problem is clear within the first three seconds;
- it sounds like Fikri, not a product marketer;
- one concrete moment carries the emotion;
- current alternatives receive fair, precise treatment;
- the longitudinal mechanism appears once and clearly;
- ShootsAI arrives as the consequence of the realization;
- no sentence invents Intent, feelings, events, users, or build proof;
- the copy distinguishes measurable Change from artistic improvement;
- removing any polished line would damage meaning, not merely style.
