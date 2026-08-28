# Devpost Inspiration — Claude proposal

> Proposal file per the writing contract in
> [devpost-story-writing-brief.md](devpost-story-writing-brief.md). Does not
> overwrite `devpost-story.md`. Compare and pick.

**Intention:** a judge with no photography knowledge understands the
lucky-vs-improving problem in three seconds, and every sentence either sets up
that problem or leads to the solution.

## Rules this version follows

- Hook question is line one.
- No capitalized product vocabulary until "Shoots" appears at the end.
- No personal backstory unrelated to the solution. Every detail that stays
  (walks, thirty photos, growing archive) is load-bearing for the problem.
- Each alternative gets one sentence with its own shape, no "can X, cannot Y"
  symmetry.
- One closing line.

## Proposed Inspiration

"Am I actually getting better at taking pictures?"

I shoot on walks, about thirty photos at a time. After a year that is
thousands of photos, and I still can't answer the question. When one comes out
good, I can't tell whether I made it good or got lucky.

I've tried what exists. A community tells me when a photo lands, but nobody
there remembers what I posted in March. A critique app names the rule I broke
in one frame, then meets me as a stranger on the next upload. A chatbot
analyzes any photo I paste in, but pasting in three months of walks is a job,
and the answer evaporates with the chat. A mentor would fix all of this, and
almost no hobbyist has one.

Every one of those answers the same question: is this photo good? Mine is
different. Am I becoming someone who takes good photos on purpose? The closest
I could get was scrolling my camera roll, comparing this month to last by eye.
It told me nothing I could trust, because a photo can't confess whether I
meant it.

That was the realization. Improvement doesn't live in any single photo. It
lives in the pattern across months: which choices keep showing up, which ones
I can repeat when I try, which ones are changing. The evidence for all three
was already sitting in my camera roll. Nothing was reading it.

So I built Shoots for the Taskmaster track, a mentor for the archive instead
of the photo. It watches my normal camera, reads every shot, remembers the
whole history, and measures what I do instead of scoring what I made. When
the evidence supports nothing, it says nothing. My taste stays mine, and
every claim points back to the photos that earned it.

## Proposed pipeline paragraph (What it does)

ShootsAI performs that missing work. It runs one loop, start to finish,
without me:

- **Analyze.** Each photo is read as it arrives and grouped with the rest of
  the same outing.
- **Settle.** When every photo is accounted for, the results become one
  record: what I repeated, what I changed, and what it could not read.
  Repeated might mean the horizon sitting dead center for the third walk in a
  row.
- **Memorize.** Each settled record updates a durable memory of me: which
  choices keep recurring, which photos I kept, what it has already told me.
  Every outing after the first is read by something that already knows my
  history.
- **Choose.** It weighs the new record against that memory and makes exactly
  one move: explain what I did, ask one useful question, or propose an
  Experiment, a deliberate retry to prove a choice wasn't luck.
- **Adapt.** It watches what happens next. Advice that changes nothing twice
  in a row stops being offered.

## Claim check

- "Watches my normal camera / background upload" — claimed in
  `devpost-story.md` What-it-does; verify against `docs/release-readiness.md`
  before submission.
- "Says nothing without evidence" — matches the Scout silence route.
- "Never scores taste / measures behaviour" — matches the two design rules in
  the current draft.
- No user counts, no improvement claims, no invented events or feelings.
