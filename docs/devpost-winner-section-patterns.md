# How agentic winners use each Devpost section

Research date: 2026-08-28

## Scope

This review covers seven verified winners whose Devpost stories expose most or all sections from "What it does" onward. Winner status was checked separately from the teams' own claims:

- The [Google Cloud Rapid Agent official winner gallery](https://rapid-agent.devpost.com/project-gallery) identifies AutoSRE, Cassandra, Unravel, CrisisRoute, and Epiq as partner-track winners.
- The [Google ADK official winner announcement](https://cloud.google.com/blog/products/ai-machine-learning/adk-hackathon-results-winners-and-highlights) identifies SalesShortcut as the grand-prize winner.
- The [Gemini Live official winner announcement](https://cloud.google.com/blog/topics/developers-practitioners/winners-and-highlights-of-the-gemini-live-agent-challenge) identifies drone-copilot as the Live Agent winner.

Their Devpost text is entrant-written. It is evidence of how winners presented their work, not independent proof of every implementation claim. Winning also does not prove that the copy caused the win.

The comparison is interpreted against the [All Things Agentic judging rules](https://allthingsagentichackathon.devpost.com/rules). Shoots needs to make three things easy to score: personal autonomous utility at 40%, architectural discipline at 30%, and undeniable live execution plus documentation at 30%.

## Winner sample

| Winner | Strongest section move | Weakness worth avoiding |
|---|---|---|
| [AutoSRE](https://devpost.com/software/autosre-the-autonomous-on-call-engineer) | Carries one claim through the whole story: detect, diagnose, propose, pause, act, verify. Architecture, challenges, tests, and future work all deepen that loop. | Some proof is repeated between "What it does" and accomplishments. |
| [Cassandra](https://devpost.com/software/cassandra-jilmgy) | Makes autonomous repair concrete through replay and adversarial verification, then names the recursion and observability failures encountered while building it. | The voice is memorable but sometimes oversells self-trust. |
| [Unravel](https://devpost.com/software/unravel-7ak8lf) | Establishes expertise through exact domain decisions, published methods, calibrated withholding, evaluation limits, and a dedicated honesty section. | Very long. A rushed judge may not reach its best validation material. |
| [CrisisRoute](https://devpost.com/software/crisisroute-multi-agent-emergency-hospital-routing-system) | Nine short actions make the end-to-end hospital-routing job visible in seconds. | How, challenges, and accomplishments are mostly unverified lists. The story says little about failure handling or proof. |
| [Epiq](https://devpost.com/software/epiq-1ubx5q) | Uses concrete clocks, named sources, database writes, projections, and visible activity to imply a working background system without a long agent roster. | It omits distinct challenges, accomplishments, and future-work sections, leaving less room for validation and judgment. |
| [SalesShortcut](https://devpost.com/software/salesshortcut) | Crosses real systems and completes a legible business workflow from discovery through outreach and scheduling. | Agent counts, stack inventory, generic achievement claims, sponsor praise, and a sprawling roadmap overwhelm evidence. |
| [drone-copilot](https://devpost.com/software/drone-copilot) | One ordinary spoken command expands into physical movement, image capture, and a report. Its challenges and accomplishment describe the same real loop. | "What's next" expands into a platform before proving broader demand. |

## The section contract

The strongest stories give each section one job.

| Section | What a judge should know after reading it | Evidence that belongs here |
|---|---|---|
| What it does | What starts the work, what the agent completes, what durable result appears, and where it refuses or stops. | User or event trigger, ordered actions, external writes, terminal condition, safety boundary. |
| How I built it | Why the architecture can deliver that result reliably. | Responsibility boundaries, state ownership, model versus code split, event path, retries, deployment. |
| Challenges | Which hard failure changed the design. | Concrete failure, its cause, the invariant or mechanism introduced, and how it was checked. |
| Accomplishments or validation | What actually ran and what evidence supports the claims. | Live run, exact counts, before and after, audits, real inputs, deployment, stated proof limits. |
| What I learned | What product or engineering belief changed because of the build. | One earlier assumption, observed contradiction, and current principle. |
| What's next | What the demonstrated system naturally enables or still needs to validate. | One near continuation and one larger direction, both grounded in current limits. |

This division matters. Repeating the feature list in every section makes the story longer without increasing confidence.

## What it does

### What worked for winners

AutoSRE and Cassandra state the whole loop before naming components. drone-copilot uses examples a judge can picture. Epiq names its 24-hour trigger, sources, database write, visible map, and forecast. Unravel shows expertise through decisions such as withholding a low-confidence change and producing draft-only clinical artifacts.

The shared move is trigger to work to artifact to boundary. Agent names matter only after the job is understood.

### Weak patterns

- Generic verbs such as analyze, remember, and adapt without domain objects.
- A list of capabilities with no settlement or completion condition.
- Agent count used as proof of complexity.
- Claims that the system is trustworthy instead of showing the rule that constrains it.
- Architecture and stack details before the judge understands the result.

### Recommendation for Shoots

Open with the surprising completed job: normal Camera use becomes an evidence-backed Shoot Record in the background. Then expose only the hard parts that make this more than image critique: all Shots are accounted for, the Shoot waits to settle, measurements bound model readings, the record affects one next response, and weak Evidence can produce silence.

The section should end with what the judge can see in the demo. Do not introduce the full cloud stack here.

## How I built it

### What worked for winners

AutoSRE maps each component to a responsibility and a safety boundary. Its remediation tools have framework approval plus server-side allow-lists. Unravel explains where agent judgment belongs and where deterministic code owns detection, probability, ranking, and output envelopes. Epiq explains why it has separate agent and deterministic data paths. drone-copilot identifies the persistent session as the design decision that makes the interaction possible.

This is stronger than a stack list because it answers why the architecture has its shape.

### Weak patterns

- Inventory such as frontend, backend, AI, cloud, with no relationship between them.
- Agent taxonomy and counts presented as architecture.
- Calling a system production-ready without state, retry, security, or deployment evidence.
- Describing prompts as the only safety mechanism.

### Recommendation for Shoots

Organize the section around three enforced responsibilities:

1. Domain code owns measurements, vocabulary, admissible claims, comparability, and state transitions.
2. Gemini agents perform bounded visual interpretation and writing into typed schemas.
3. Infrastructure stores the record and moves replayable work through Cloud Run, Pub/Sub, Firestore, and Cloud Storage.

Then show the event path once and explain why Run, Capture Session, and Shoot barriers share one Run truth. Name idempotency and late-Shot revision handling here. Put the technology beside the job it performs, not in a detached paragraph.

## Challenges

### What worked for winners

The strongest challenge sections are miniature engineering stories. AutoSRE explains how a human pause broke a live stream, how refusal events were initially misclassified, and how quotas became visible backoff. Cassandra explains why its own test traces caused recursive supervision. Unravel admits an evaluation that initially graded its own plumbing, then explains the harder replacement. drone-copilot names a physical limit that no simulator exposed.

Each problem earns a design decision. That makes architecture claims believable.

### Weak patterns

- "Orchestration was difficult" with no failure or resolution.
- Listing normal implementation work as challenges.
- Turning the section into adversity theatre.
- Mentioning a bug without stating what changed in the system.

### Recommendation for Shoots

Keep settlement as the main challenge. Explain one forced ordering that could have closed a Shoot incorrectly, then state the invariant that now prevents it and the integration case that proves it. Use model-boundary failures as the second challenge, but connect each example to one lasting rule: invalid numbers stop before arithmetic, and model locations never become pixel claims without validated coordinates.

The current draft has the right raw material. It needs one more sentence showing how each failure was verified after the fix.

## Accomplishments and validation

### What worked for winners

AutoSRE reports the complete live loop, 25 graded runs, zero false actions, five refusal traps, latency, committed transcripts, and a test count. Cassandra leads with an under-one-minute live loop and the visible before-and-after replay. Unravel separates a real variant set, synthetic patients, a small live-agent sample, deterministic validation, and clinical limits. drone-copilot points to one physical end-to-end mission.

The best entries state what ran, the input, the finished artifact, and the proof limit. Numbers help only when their denominator and meaning are clear.

### Weak patterns

- "Successfully built" or "production-ready" with no run evidence.
- Test totals that do not say what important behavior they cover.
- Mixing deterministic checks, model-quality review, and real-device proof into one success number.
- Future capability written as an accomplishment.

### Recommendation for Shoots

Add a short dedicated validation section. Separate three evidence types:

- one uninterrupted physical Camera-to-Shoot-Record run with exact Shot count and visible background completion;
- real-agent quality results with the exact case and check counts plus the twelve human-review questions;
- integration evidence for retries, duplicate delivery, late Shots, and offline readback.

Do not call emulator coverage proof of the physical Camera path. Do not hide the real-device result inside "What it does" or "What's next" once it exists.

## What I learned

### What worked for winners

AutoSRE says the approval pause became the product. Cassandra says supervision works through traces rather than invasive integration and that one patch cannot settle reliability. Unravel says tight scope and disclosed limits produced the credible differentiators. drone-copilot contrasts simulated assumptions with wind, latency, and interruption in physical use.

These are changed beliefs, not summaries of libraries learned.

### Weak patterns

- Praising sponsor technology.
- Repeating the architecture section.
- Saying the team learned a framework with no product consequence.
- Generic lessons about teamwork, persistence, or AI potential.

### Recommendation for Shoots

Keep the shift from per-Shot grading to a Shoot-level Companion. Make the before and after concrete. Earlier versions spoke after every Shot and treated advice as a lesson. The current system waits for the Shoot and separates recurrence from deliberate repeatability. That is both a product lesson and an architecture consequence.

## What's next

### What worked for winners

Unravel names the next validation step, a larger held-out evaluation and a clinician pilot, before wider integrations. AutoSRE extends known constraints such as concurrency, approval channels, and regression gating. drone-copilot ties future work to hardware limits observed during the demo.

The next step feels credible when it repairs a known limit or extends the proven loop.

### Weak patterns

- A feature buffet across industries, marketplaces, languages, enterprise tiers, and no-code builders.
- Describing required submission proof as future work.
- Introducing a different product rather than deepening the demonstrated one.
- Claiming future automation that removes an intentional human boundary.

### Recommendation for Shoots

Remove the physical Xiaomi proof from "What's next." It is required evidence for this submission and must be completed before final copy. The public roadmap should begin with broader longitudinal validation on real Camera histories, then name one product extension such as Compare. Do not add Gemini Live, Live Scene Sessions, Scene Probes, the post-Shot Coach, a custom viewfinder, or video Analysis; those directions are parked.

## Working structure for Shoots

Use this sequence from "What it does" onward:

1. **What it does.** One compact promise, one concrete background loop, one visible result, one refusal boundary.
2. **How I built it.** Responsibility split, event path, shared Run truth, failure handling, and deployed Google services.
3. **Challenges.** Settlement race and model-boundary failure, each ending in a verified design rule.
4. **Validation.** Physical live run, real-agent quality result, and integration evidence kept distinct.
5. **What I learned.** Why the product moved from instant grading to quiet Shoot-level reflection.
6. **What's next.** Validation scale and one grounded extension, not missing submission work.

The strongest model is not one winner's prose. It is AutoSRE's complete loop, Unravel's evidence discipline, Cassandra's verification step, Epiq's concrete background clock, and drone-copilot's undeniable physical result. Shoots already has the underlying material. The rewrite should make each section prove a different part of the same Camera-to-Shoot-Record story.
