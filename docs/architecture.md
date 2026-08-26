# Submission architecture

![Shoots continuous architecture](architecture.svg)

The diagram separates the three aggregates that share one Shot Run without sharing
membership:

- the Run barrier accounts for every stage on one Shot;
- the Shoot barrier waits for every current natural Camera member before producing a
  revisioned Shoot Record;
- the Capture Session batch barrier waits for the exact Experiment members frozen by
  the Photographer.

Blue means deterministic code or durable state. Amber means a bounded model read or
terminal learning artifact, never quality. Green means Photographer-owned authority.
Grey means an external adapter. The system camera remains outside Shoots and the
Photographer owns the shutter.

This SVG is the submission export. The more detailed agent and sequence diagrams live
in [agents](agents.md); domain guarantees live in the [domain model](domain-model.md).
