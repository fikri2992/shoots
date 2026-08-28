# ADK multi-agent diagram inspiration

## What Google usually shows

Google does not use one universal multi-agent diagram. Its clearest material splits the subject into separate views: agent hierarchy, execution pattern, communication mechanism, and deployment. That is the main lesson for Shoots. The current diagram tries to carry all four at once.

## Official examples

### 1. ADK workflow overview

[ADK workflow overview](https://adk.dev/workflows/) compares graph-based, dynamic, collaborative, and template workflows in one compact figure. Each pattern gets its own bounded panel. The page explicitly distinguishes AI agents from deterministic executable nodes.

- Good for Shoots: use a container for each workflow and show deterministic code beside model-backed agents.
- Weak for Shoots: it is a taxonomy, not a product flow. It does not show Photographer authority, durable records, or deployment.

### 2. Agent hierarchy

[Google Cloud's ADK multi-agent guide](https://cloud.google.com/blog/topics/developers-practitioners/building-collaborative-ai-a-developers-guide-to-multi-agent-systems-with-adk#the_foundational_concept_agent_hierarchy) draws a root agent above its sub-agents as a small tree. The diagram answers one question only: who can delegate to whom.

- Good for Shoots: a hierarchy is instantly readable when a real coordinator owns sub-agents.
- Weak for Shoots: Shoots is primarily event-driven. Drawing every named role under a fictional root agent would misstate the implementation.

### 3. Sequential, parallel, and loop workflows

The same first-party guide gives separate figures for [SequentialAgent, ParallelAgent, and LoopAgent](https://cloud.google.com/blog/topics/developers-practitioners/building-collaborative-ai-a-developers-guide-to-multi-agent-systems-with-adk#orchestrating_tasks_with_workflow_agents). It uses left-to-right input and output, a tinted container around the workflow, fan-out for parallel work, and a visible return edge plus exit condition for loops. The sequential figure also says that its arrows mean execution, not state sharing.

- Good for Shoots: this is the strongest grammar for the Shot path. Put the Analyst lenses inside a parallel container and conditional Reproduce work behind a labelled branch. Show settlement conditions at the edge, not in prose inside nodes.
- Weak for Shoots: the legacy template names should not appear unless Shoots actually instantiates those ADK classes. Current ADK docs point Python and Go users toward graph-based workflows for new work.

### 4. Shared state, transfer, and AgentTool

Google's [communication mechanism figures](https://cloud.google.com/blog/topics/developers-practitioners/building-collaborative-ai-a-developers-guide-to-multi-agent-systems-with-adk#how_do_agents_communicate) separate shared session state, LLM-driven transfer, and explicit AgentTool invocation. This prevents a generic arrow from meaning execution, delegation, data access, and tool use at the same time.

- Good for Shoots: give each edge one meaning. Tools should be small attached nodes, Photographer Signals and durable records should be shared stores, and conditional model choice should use a distinct line style.
- Weak for Shoots: ADK session state is not Shoots' durable source of truth. Firestore records, Run settlement, and immutable Shoot or Experiment Records need their own notation.

### 5. ADK Developer UI graph

The official [ADK Python graph builder](https://github.com/google/adk-python/blob/main/src/google/adk/cli/agent_graph.py) reveals the visualizer's grammar. It renders left to right, uses ellipses for agents, boxes for function tools, cylinders for retrieval tools, clusters for sequential, parallel, loop, and graph workflows, and highlights the active agent-to-agent edge. It also connects every `LlmAgent` to its canonical tools. ADK documentation describes the Developer UI as a development and debugging surface for visualizing agent definitions and inspecting events, state changes, function calls, and traces in [`adk web`](https://adk.dev/get-started/testing/).

- Good for Shoots: use this as an implementation audit. A generated graph can confirm the real agent and tool inventory and expose accidental hierarchy.
- Weak for Shoots: it is a developer graph, not a submission diagram. It omits product authority, event sources, durable artifacts, barriers, and cloud boundaries.

### 6. Google Cloud multi-agent reference architecture

The [Cloud Architecture Center multi-agent system](https://docs.cloud.google.com/architecture/multiagent-ai-system) puts the agentic flow inside a larger runtime diagram. A coordinator branches into sequential and iterative flows, tools sit behind MCP, human intervention is explicit, and Cloud Run, GKE, Agent Runtime, model runtime, and security controls occupy separate infrastructure regions.

- Good for Shoots: keep product flow inside a clear Shoots service boundary, place Android and Drive outside it, and put Cloud Run, Pub/Sub, Firestore, Cloud Storage, Gemini, and Search in a separate deployment view.
- Weak for Shoots: it is an enterprise reference architecture. Copying its coordinator, A2A, MCP, or security components would add systems Shoots does not use.

## Recommendation for Shoots

Replace the current all-in-one graphic with two diagrams.

### Diagram A: how the Companion finishes learning work

This should be the submission hero. Keep it to one left-to-right story:

```text
Camera Shot
  -> deterministic Shot workflow
       -> Ingest
       -> Analyst lenses in parallel
       -> Cartographer
       -> Judge only for explicit Reproduce
       -> Scribe
  -> Run settled
  -> Shoot closes when every current member settles
  -> Shoot Record
  -> Scout chooses explain, ask, Explore, Reproduce, or silence
  -> Photographer receives one optional next action
```

Show the Capture Session as a separate explicit Experiment membership gate below the main line. Show Coach as a separate live, Photographer-summoned path, not another stage in the Shot pipeline. Keep Inspiration outside the Photographer record boundary.

Use this legend:

- rounded container: deterministic workflow or boundary;
- circle or compact agent card: model-backed agent;
- small square: callable tool;
- document shape: durable artifact;
- solid arrow: code-controlled execution;
- dashed arrow: model-selected call or conditional route;
- green input edge: Photographer authority;
- amber never means quality.

### Diagram B: where it runs and what persists

Use a plain deployment view:

```text
Android / Web / Drive
        -> Cloud Run API and workers
        -> Pub/Sub delivery
        -> Firestore records + Cloud Storage media
        -> Gemini / Google Search
```

Include Run, ActivityEvent, Shoot Record, Experiment Record, Photographer Signal, Technique Map, and Journey as grouped durable records. Do not draw every record-to-screen read. One labelled read-model arrow to Android and web is enough.

## Concrete design verdict

The next hero diagram should look like an ADK workflow diagram, not a database schema or a cloud topology. Its central visual should be the real Shot and Shoot execution graph. Tools attach to the agents that can call them. Durable records form a quiet evidence rail underneath. Photographer authority appears only at the shutter, explicit Experiment participation, Keeper, Intent, source role, correction, and preference boundaries. Deployment gets its own second diagram.

Before drawing, generate or inspect the ADK Developer UI graph and compare it with the current code. That prevents the polished diagram from inventing a root coordinator, transfers, AgentTools, or workflow classes that Shoots does not actually use.
