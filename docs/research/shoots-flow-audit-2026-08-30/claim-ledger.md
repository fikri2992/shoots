# Claim-to-source ledger

Audience: Shoots product and submission work  
Date: 2026-08-30  
Status: internal research trace

This ledger separates official requirements, external expert evidence, observed local behavior, implementation facts, production evidence, and product decisions.

| ID | Claim | Evidence | Strength | Important limit | Product consequence |
|---|---|---|---|---|---|
| C1 | Taskmaster rewards a multi-step background workflow completed without human intervention. | [Official rules](https://allthingsagentichackathon.devpost.com/rules) | Direct, binding brief | Does not define Shoots’ creative boundary. | Keep the human-free terminal at settled Shoot Record. |
| C2 | The official score prioritizes operational utility, then architecture and demo proof. | [Official overview](https://allthingsagentichackathon.devpost.com/) | Direct, official | Judges retain discretion. | Lead with removed friction and visible completion, not agent names. |
| C3 | Post-capture review, download, organization, editing, sorting, and filing are real photography work. | [Understanding Photowork](https://www.microsoft.com/en-us/research/wp-content/uploads/2006/04/paper_chi06_photowork.pdf) | Direct photography field research | Published in 2006; tooling has changed. | Frame Shoots as an autonomous post-capture worker. |
| C4 | A mismatched AI mental model can cause frustration and abandonment; the product should explain user benefit and limits first. | [Google PAIR: Mental Models](https://pair.withgoogle.com/guidebook-v2/chapter/mental-models/) | Strong design guidance | Not a Shoots outcome study. | Show the completed benefit before optional learning features. |
| C5 | User feedback should have a clear scope and time to impact. | [Google PAIR: Feedback and Control](https://pair.withgoogle.com/guidebook-v2/chapter/feedback-controls/) | Strong design guidance | Does not prescribe a cooldown duration. | Make “Not today” and calibration visibly change later behavior. |
| C6 | Long work needs completed and remaining progress, background continuation, and a salient completion summary. | [NN/g: Long Waits and Interruptions](https://www.nngroup.com/articles/designing-for-waits-and-interruptions/) | Strong expert UX guidance | Complex enterprise examples are adjacent, not photography-specific. | Show found, read, waiting, retrying, elapsed, completion time, and record link. |
| C7 | A session gap and a result-emission trigger are separate concepts; late data can revise an earlier result. | [Google Cloud Dataflow](https://docs.cloud.google.com/dataflow/docs/concepts/streaming-pipelines) | Direct streaming-system guidance | Dataflow is an architectural analogy, not a Shoots mandate. | Keep capture-time grouping but emit an earlier Shoot Record and revise on late Shots. |
| C8 | A 30-minute inactivity threshold is conventional but may be arbitrary and domain-inappropriate. | [Microsoft session-boundary research](https://www.microsoft.com/en-us/research/publication/identifying-user-sessions-interactions-intelligent-assistants/) | Peer-reviewed adjacent evidence | The study’s roughly two-minute result is for assistant interactions, not photography. | Test a photography-specific trigger. Do not inherit 30 minutes as user wait. |
| C9 | Less-experienced photographers can be overwhelmed by dense composition guidance; adaptive, limited guidance can help. | [Stanford HCI](https://hci.stanford.edu/publications/paper.php?id=380) | Direct photography interaction evidence | Narrow capture-time study; no longitudinal learning proof. | Keep one image-led idea, easy to dismiss, with deeper Evidence below. |
| C10 | Agent evaluation must examine both trajectory and final output. | [Google ADK evaluation](https://github.com/google/adk-docs/blob/main/docs/evaluate/index.md) | Direct framework guidance | Does not define Shoots-specific metrics. | Verify the stage path and the final Shoot Record separately. |
| C11 | The current Now page prioritizes a Scout Recommendation over a completed Shoot Record. | [NowPage](../../../frontend/src/pages/NowPage.vue); [screen evidence](../../evidence/shoots-flow-deep-research-2026-08-30/01-now-recommendation-first.png) | Direct implementation plus observation | Local working tree, not confirmed current production. | Reverse the order. |
| C12 | The current default uses the same 30-minute value for Shoot grouping and closure; Run settlement cannot close an open Shoot. | [Config](../../../backend/app/config.py); [Shoot service](../../../backend/app/services/shoots.py); [scheduler](../../../infra/scheduler.sh) | Direct implementation | Deployment overrides were not reverified in this pass. | Separate membership from emission and show the deployed value honestly. |
| C13 | The 75-Shot gate is a workflow stress corpus, not 75 independently captured originals. | [Production audit](../../taskmaster-production-e2e-audit-2026-08-30.md) | Direct local audit | It still validly tests throughput and recovery. | Label it and use an intact Camera account for the personal story. |
| C14 | The domain already supports a newer revision when a late Shot arrives. | [Domain model](../../domain-model.md) | Direct product contract | A free-shooting source manifest is not yet a named domain concept. | Reuse revision semantics; update the domain before adding batch behavior. |
| C15 | The current production test proves substantial autonomous completion and repair, but not the Photographer-benefit loop. | [Production audit](../../taskmaster-production-e2e-audit-2026-08-30.md) | Direct local production evidence | Controlled account and corpus; no real Experiment, Verdict, or Change. | Preserve the operational claim and avoid a learning claim. |
| C16 | The proposed flow and estimated judge score are evidence-informed product judgments. | C1 through C15 | Reasoned synthesis | No judge or target user was observed in this pass. | Validate with first-glance, field, and judge-rehearsal tests. |

## Evidence labels used in the report

- **Verified implementation:** current source behavior inspected directly.
- **Observed local UX:** visible in the signed-in local web app during this pass.
- **Production evidence:** recorded in the existing production audit.
- **Official requirement:** stated by Devpost or Google contest rules.
- **Expert guidance:** relevant research or practitioner guidance outside Shoots.
- **Product decision:** a proposed behavior that still needs implementation and validation.

