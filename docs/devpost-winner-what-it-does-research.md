# How hackathon winners write "What it does"

Research date: 2026-08-28

## Scope and evidence

This review covers eight recent AI-agent winners. Winner status was checked separately from the teams' own project claims:

- [Google Cloud Rapid Agent Hackathon official winner gallery](https://rapid-agent.devpost.com/project-gallery)
- [Google ADK Hackathon official winner announcement](https://cloud.google.com/blog/products/ai-machine-learning/adk-hackathon-results-winners-and-highlights)
- [Gemini Live Agent Challenge official winner announcement](https://cloud.google.com/blog/topics/developers-practitioners/winners-and-highlights-of-the-gemini-live-agent-challenge)

Each "What it does" section below is entrant-written. It shows how a winning submission presented itself, not independent proof that every claim was true. Winning also does not prove this section caused the win.

The current All Things Agentic rules matter here because judges may rely only on the text, images, and video. Taskmaster judging specifically asks whether the agent completes a multi-step background workflow without human intervention, while production-readiness judging asks for undeniable proof of action. [Official rules](https://allthingsagentichackathon.devpost.com/rules)

## Winner comparison

| Winner | First move | Structure and length | Complexity and trust cues | Lesson for Shoots |
|---|---|---|---|---|
| [AutoSRE, Dynatrace first place](https://devpost.com/software/autosre-the-autonomous-on-call-engineer) | Opens with the complete promise: detect an incident, diagnose it, propose one fix, then stop for approval. Outcome first. | Six ordered steps, then value and differentiation. 279 words. | Live telemetry, a framework-enforced approval gate, action, recovery verification, tenant write-back, an append-only audit, and measured evaluation results. | Best structural model. Put the whole Shoots loop in sentence one, then make the ordered work and proof visible. |
| [Cassandra, Arize first place](https://devpost.com/software/cassandra-jilmgy) | Opens with its integration and continuous monitoring behavior. Mechanism and outcome arrive together. | Eight ordered steps, followed by self-evaluation and MCP access. 221 words. | Fresh traces become diagnosis, a generated evaluation set, a prompt patch, replay of the original failure, and adversarial verification. | Strong model for "learn, act, check." The verification step makes the loop feel complete. |
| [Unravel, Fivetran first place](https://devpost.com/software/unravel-7ak8lf) | Opens by naming the missing active layer between changing genetic evidence and affected families. Outcome first, then mechanism. | Five numbered specialists followed by one operating principle. 206 words. | Named evidence sources, calibrated calculations, withheld low-confidence changes, draft FHIR artifacts, and an ethics boundary. | Expertise becomes credible through exact domain decisions and refusals, not adjectives such as "expert" or "trustworthy." |
| [CrisisRoute, Elastic first place](https://devpost.com/software/crisisroute-multi-agent-emergency-hospital-routing-system) | Opens with the product category, then moves directly into actions. | Nine short capability bullets. 49 words. | Triage, hospital search, capacity checks, scoring, reservation, notification, and a dashboard make the demo easy to picture. It gives little proof or safety detail. | Good scan speed. Weak model for Shoots because a capability list alone does not explain settlement, evidence, or trust. |
| [Epiq, MongoDB first place](https://devpost.com/software/epiq-1ubx5q) | Opens with continuous global outbreak monitoring. Outcome first. | Two dense paragraphs. 125 words. | A 24-hour collection cycle, named sources, database writes, visible activity, projections, vector search, and time-series output. | A few specific clocks, sources, and written artifacts imply more complexity than a long agent roster. |
| [SalesShortcut, ADK grand prize](https://devpost.com/software/salesshortcut) | Opens with the full business outcome, automating sales from lead discovery to deal closure. Outcome first. | Five verb-led capability bullets. 135 words. | The steps cross real systems: Maps discovery, prospect research, proposal generation, calls, email, lead tracking, and calendar scheduling. | Use a concrete verb chain. Avoid its generic words such as "comprehensive" and do not crowd the section with every feature. |
| [drone-copilot, Gemini Live category winner](https://devpost.com/software/drone-copilot) | Opens with the user experience: talk naturally to a drone. Outcome first. | Five example commands, then one result paragraph. 120 words. | The last example expands from one request into an autonomous inspection, captured images, and a report. Physical movement and live telemetry make action undeniable. | One ordinary input followed by a surprisingly complete job creates the fastest "it actually does that" reaction. |
| [Rayan Memory, Gemini Live innovation winner](https://devpost.com/software/rayan-memory) | Opens with a voice-first memory system and two persistent background agents. Mechanism first, but the artifact appears immediately. | Four narrative blocks covering capture, recall, the 3D result, and deduplication. 256 words. | Passive capture, a confidence threshold, structured extraction, embeddings, grounded recall, visible artifacts, and deterministic deduplication. | Closest writing analogue to Shoots. Show the background trigger, the durable personal artifact, and the rule that keeps weak or duplicate material out. Avoid absolute claims such as "cannot hallucinate." |

## What the stronger sections have in common

They do not all use the same format. Length ranges from 49 to 279 words, and some lead with outcome while others lead with mechanism. The repeatable pattern is narrower:

1. The first sentence names a real event or user input and the completed result.
2. The middle exposes an ordered workflow, not a list of generic agent abilities.
3. Complexity appears through concrete sources, decisions, writes, waits, and checks.
4. Trust appears as a boundary the system enforces: approval, abstention, draft-only output, a threshold, audit, replay, or verification.
5. The result is something a judge can point to: a report, database write, blocked merge, updated dashboard, moved drone, generated evaluation set, or visible artifact.

The newer Taskmaster-like winners are especially blunt about the terminal condition. AutoSRE ends with verified recovery. Cassandra ends with replay and red-team checks. Unravel ends with a drafted but deliberately bounded clinical action. This is stronger than saying an agent "analyzes, remembers, chooses, and adapts."

## Direction for Shoots

Shoots should use the AutoSRE shape with Rayan's quiet-background feel and Unravel's evidence discipline:

1. One opening sentence with the normal Camera trigger, the unattended work, and the Shoot Record.
2. A short ordered list using photography-specific actions and artifacts, not generic labels such as Analyze, Remember, or Adapt.
3. One closing sentence with the trust boundary: source Shots, unresolved Evidence, and code-gated eligibility.

The first scan should make this complete job visible:

> After I take images with the normal Android Camera, ShootsAI works in the background across the whole Camera period. It accounts for every Shot, waits until the Shoot has settled, writes one evidence-backed Shoot Record, and chooses one supported response or silence.

Then explain only the parts that make that promise surprising:

- it reads the images the photographer would not have selected for critique;
- it combines measured facts with bounded visual Evidence instead of letting model opinion become fact;
- it finds recurring photographic decisions across Shoots;
- it may offer one optional Experiment and later records Change only when the earlier and later Shots are comparable;
- every claim leads back to its source Shots, and insufficient Evidence remains unresolved.

## Copy and avoid

Copy:

- trigger to work to artifact to boundary in the opening;
- a visible background wait or settlement condition;
- photography-specific nouns and decisions;
- one durable result a judge can recognize in the demo;
- one honest refusal or verification rule.

Avoid:

- opening with "a comprehensive multi-agent platform";
- listing agent names before the judge understands the product;
- using agent count as the main complexity signal;
- generic stage labels that could describe any AI product;
- mixing the full cloud stack into this section;
- claiming trust directly. Show the rule that earns it;
- explaining every feature. The architecture and accomplishments sections can carry the rest.
