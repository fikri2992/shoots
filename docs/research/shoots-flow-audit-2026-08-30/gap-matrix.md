# Shoots flow gap matrix

Date: 2026-08-30  
Scope: current local journey, verified source behavior, existing production proof, and Taskmaster fit

| Boundary | Current state | User risk | Judge risk | Priority | Recommended change | Required proof |
|---|---|---|---|---|---|---|
| First arrival | Product can explain the system, but the full value requires data and a settled Shoot. | User expects coaching or setup before receiving value. | Core chore is unclear. | P1 | One-sentence promise: keep using the Camera; Shoots handles review and leaves a record. | Five-second comprehension test. |
| Source setup | Phone Source is the intended automatic path; Drive remains optional import. | Setup may feel like the product’s main job. | Direct testing may fall back to curated Drive import. | P0 | Keep one source action, then show exactly what will happen automatically. | Normal Camera item reaches the server without manual tagging. |
| Import progress | 25-Shot Drive imports took roughly 97 to 119 seconds with “Opening Drive…” only. | Looks frozen; user cannot decide whether to leave. | Weak production readiness. | P0 | Show found, accepted, read, waiting, retrying, current stage, and background continuation. | Timed 25-Shot import with captured status transitions. |
| Shoot grouping | Thirty-minute capture gap decides membership. | Usually invisible and understandable if accurate. | Needs a stated rationale and real Camera evidence. | P1 | Keep as a testable membership policy, not a UX promise. | Compare actual outings against expected Shoot boundaries. |
| Result emission | Same 30-minute gap blocks closing; scheduler may add five minutes. | Value arrives long after known work is done. | Agent appears slow and arbitrarily gated. | P0 | Emit when a bounded source manifest settles; revise if a late Shot arrives. | Last upload to record latency and late-revision acceptance. |
| Processing state | Run detail exists, but user-facing progress is stage-heavy and incomplete. | User sees system terms rather than outcome progress. | Heavy lifting is not undeniable. | P0 | High-level outcome tracker with expandable technical trace. | UI and ActivityEvents agree on all counts. |
| Now hierarchy | Recommendation wins before completed Shoot Record. | Feels like new homework. | Looks like a recommender instead of Taskmaster. | P0 | Lead with “Your Shoot is ready”; recommendation follows. | Four of five users identify the finished chore in five seconds. |
| Shoot Record | Coverage, Scene, counts, and receipt are strong. | Main takeaway can still be buried below process framing. | Best proof exists but requires navigation. | P0 | Surface its compact receipt on Now, then link to full audit. | Judge finds terminal artifact without coaching. |
| Recommendation | Image-led, one idea, optional controls. | Appears compulsory because it occupies the hero. | Optional coaching distracts from autonomous completion. | P0 | Preserve card; place after result. | User can stop before accepting and still state received value. |
| “Not today” | Records a left Intervention but does not currently affect later ranking as a cooldown. | Control may feel fake. | Human-AI feedback loop is incomplete. | P1 | State and implement exact scope, duration, and reappearance rule. | Next eligible recommendation respects the recorded choice. |
| “Show another idea” | Rotates local stored options without a write. | User may assume preference was remembered. | Behavior and mental model can diverge. | P1 | Label as temporary or persist explicit preference. | Refresh and later Shoot behavior match copy. |
| Journey hierarchy | Mixes 75 archive Shots, 25 latest Shoot Shots, Keepers, Techniques, Scenes, and next action. | User reconstructs the story manually. | Memory effect is hard to see. | P1 | Separate Archive, Latest Shoot, Photographer Choice, Result, and Next. | User locates each layer without help. |
| Shot detail | Companion receipt precedes the image; mask is visually dominant. | The Photographer’s work feels secondary to the system. | Multimodal UX feels technical. | P1 | Image and one relationship first; process and provenance below. | User can explain the Finding from the visual alone. |
| Stress corpus | 75 displayed Shots come from 67 source Shots plus deterministic variations; UI does not disclose this. | Personal history can feel fabricated. | Trust and demo integrity risk. | P0 | Visible stress-corpus badge and separate real Camera account. | Every demo claim identifies which account and evidence type it uses. |
| Failure recovery | Production evidence shows five unique failed Shots recovered through six replays. | Success is mostly hidden. | Strong architecture is undersold. | P0 | Show recovered, still retrying, and terminal counts in completion receipt. | Force one retryable failure in a live rehearsal and recover it. |
| Stable proof chain | Evidence exists across separate runs and surfaces. | User does not need IDs, but needs confidence nothing was lost. | Official proof of action remains partial. | P0 | One inspectable source ID → Shot → Run → Shoot revision → Shoot Record → Drive output chain. | Unedited live execution with UI plus Cloud trace. |
| Optional Experiment | Correctly begins only after explicit acceptance. | Good authority boundary. | Can be mistaken for unfinished Taskmaster work. | P0 | Keep secondary to the settled record. | Demonstrate that no Experiment is needed for terminal completion. |
| Photographer benefit | No current real multi-session Experiment, Verdict, and later Change. | Improvement claim would be premature. | Judges may reject broad coaching claims. | P2 | Run a genuine field loop and use cautious Evidence language. | Real user, explicit Capture Session, honest result, later comparable Shoot. |

## Release gate for the corrected flow

Do not call the journey corrected until all are true:

1. Now leads with the completed Shoot Record.
2. A 25-Shot wait exposes truthful progress and permits leaving.
3. The first record does not wait for the full membership gap when a bounded source batch is settled.
4. A late Shot creates a visible newer revision without data loss.
5. “Not today” has an exact, tested downstream effect.
6. The stress account is visibly labelled.
7. One intact normal-Camera account reaches a settled record in one trace.
8. A fresh evaluator can explain the chore and proof without repository context.

