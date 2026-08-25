# Shoots for a class

Design note for the pivot from one photographer to a teacher running a class.
Written 2026-08-23, eight days before the deadline (2026-08-31 17:00 PDT).
Nothing here is built yet; decisions get numbered in `domain-model.md` when they ship.

## Why

- Taskmaster is about an agent managing work on someone's behalf. One photographer,
  one frame at a time, is a thin queue. Fifteen students handing in an assignment is a
  real one, and the pipeline was already built as per-shot fan-out over events.
- Operational utility becomes countable: hours of review per week, frames per minute.
- Human-in-the-loop becomes the feature. The agent reads every frame, reads the class,
  drafts the next brief and the feedback; the teacher only signs.

### What already exists (checked 2026-08-23)

- AI photo critique, single user, upload → scores + paragraph: LENSIC, PhotoCritique.ai,
  PhotoCritic.ai, PhotoMentor, Vision Mentor, a dozen GPTs. None track a learner,
  set the next task, draw on the frame, or have a class.
- AI grading with a teacher approval queue, for text: CoGrader, GradeWithAI,
  TimelyGrader, GPTZero Reviewer, MagicSchool, OpenEduCat. The approve-before-send
  pattern is validated, not novel; it is not the pitch.
- Nobody joins the two for visual work, and nobody plans the next lesson from the
  aggregate.

Pitch: *one agent runs a photography class — reads every frame, reads the class,
drafts the next brief; the teacher only signs.*

Known objection (EdSurge, a student thanked a teacher for words they never wrote):
feedback the teacher did not touch must still be visibly theirs to approve, and the
Drive review carries the teacher's name, not "Reviewed by Shoots".

## People

**Teacher.** Runs one or more classes. Today: sets the week's assignment, collects
submissions from a mess of channels, reviews each one (the slow part), keeps a mental
or spreadsheet record of who is progressing, and plans the next lesson from the
class's common failure.

**Student.** In one class. Shoots the assignment, hands it in, wants to know what to
fix. The app they get is today's app: Now / Frames / Journey / Coach.

No admin. No role picker. Creating a class makes an account a teacher; opening a
join link makes it a student.

## The workflow, with the agent in it

| Step | Teacher today | With Shoots |
|---|---|---|
| Set the assignment | writes a brief | Scout drafts title, brief, criteria, clip from the class's skill data; teacher edits, approves, it is issued to every student |
| Collect | Drive / Classroom / chat | student shoots in-app (pre-flight) or drops into their own Drive folder |
| Review | one by one, by hand | Analyst + Judge produce a **draft** verdict per frame; queue in the app; approve, edit, or approve all |
| Track | spreadsheet | Cartographer per student; roster shows trend and an attention flag |
| Plan | gut feel | **Class Read**: "6 of 12 in. 4 missed shutter speed. Aisha and Ben ready for harder. Dev stuck twice." |
| Celebrate | slideshow by hand | **Showcase**: best approved frame per student, a reel with a Lyria bed, in the teacher's Drive |

Autonomy stays in exactly two places: Class Read runs on its own and names who needs
attention; Showcase cuts itself when an assignment closes. Everything outward —
feedback to a student, a new assignment, the reel, the storyboard — needs a teacher
tap, one tap for the batch. (Scout-drafted next assignment from Class Read: stretch.) The Scout no longer issues experiments to anyone by itself (`issue_first` off
for members of a class).

## Roles and access

- `User.role`: `teacher` | `student`. Set on first class created / first join.
- `Cohort` {id, teacher_id, name, join_code, created_at}.
- `Membership` {user_id, cohort_id, joined_at}. One class per student, many per teacher.
- `Shot.cohort_id`, `Experiment.cohort_id`, `Experiment.assignment_id`.
- `/auth/me` returns role and cohort ids; the router lands teachers on Class, students on Now.

Authorisation is object-level, not route-level: a teacher can read anything that
belongs to a student of their cohorts; a student reads only their own. Every read of
shots, analyses, skill maps, experiments, events and the Coach socket goes through
`owner_or_teacher_of(user_id)`; class, assignment and approve endpoints need
`require_role("teacher")`. Today every endpoint compares `user_id` with the session;
this is the RBAC work, about ten endpoints.

## Uploading and syncing

Kept: a student's own Drive folder, the watcher, the in-app Shoot button
(`/drive/shoot`), the Scribe writing the review back into `Reviewed/`.

New: Drive is optional for students. Upload → blob → ingest with no Drive target,
Scribe skipped. Sending fifteen teenagers through a Drive consent screen is not an
onboarding flow.

Rejected: a folder tree in the teacher's Drive with one subfolder per student. It
would need a folder→student map in the watcher and the teacher's token in the Scribe,
and the student app already exists; fewer moving parts to keep per-student Drive.

## Teacher forms

- **Create class**: name → join link and six-character code.
- **Assignment**: title, brief, technique (taxonomy pick), criteria (EXIF bounds,
  seen, said — `Criteria` exists), a reference frame picked from the class (a
  student's or the teacher's own), and the Veo storyboard: rendered on save, previewed
  by the teacher, attached or dropped. *Draft it for me* prefills from the Scout with
  the class's skill data.
- **Verdict review**: feedback editable in place, pass/fail toggle, Approve,
  Approve all. Approval is the only way a verdict reaches a student.
- **Class setting**: gate verdicts (default) or auto-send.
- Cut for v1: roster edits, due dates, regenerating codes.

## Generated media, and where it is allowed

The artist's objection to AI is about generation standing in for the work. So the rule:
**the agent never makes the photograph that gets graded.** It illustrates the brief,
reads the work, and scores the celebration.

- **Veo** renders the assignment's storyboard: the *move* ("pan with the rider at
  1/30"), six seconds of motion, never a still presented as the target. For video
  techniques it is the only honest reference. The teacher previews it and decides
  whether the students see it — the human gate covers generated media too. In the
  student's view it is captioned *generated storyboard of the brief — not a photograph*
  and sits beside the real reference frame.
- **Lyria** comes back under real frames, not under Veo (the Day 7c cut stands for
  that). **Showcase**: when an assignment closes, the agent takes each student's best
  approved frame, cuts a 30 s reel (ffmpeg, slow push per frame, name and technique as
  caption) with a Lyria bed prompted from the assignment's mood, and writes
  `Showcase — <assignment>.mp4` into the teacher's Drive. Sharing it is one tap, the
  teacher's. A music bed under students' photographs is the one arrangement nobody
  objects to, and teachers make these by hand today.
- The crop loop renders the student's own pixels; that is a crop, not a generation.

## Standing in the room

What the 2026 climate says (sources in the session of 2026-08-23): 99 % of artists
dislike AI, 58 % of UK AoP members have lost work to it, photographers' top worry is
loss of creative control, art educators worry about AI skipping "the messy middle", and
a student has already thanked a teacher for feedback the teacher never wrote. The
hostility is almost entirely about generation; analytic tools are being adopted, and
Adobe shipped AI critique in its camera app in July 2026.

Built-in answers, not slide answers:

- **The teacher is the author.** Drafts are pre-crit notes for the teacher. The student
  sees feedback *from the teacher*; the Drive file says "Reviewed by <teacher> · read by
  Shoots". Each verdict records whether it was edited before approval, and the class log
  shows the edit rate — the audit trail keeps "Approve all" honest.
- **Intent on submission.** One line, "what were you going for?", read by the Judge next
  to the teacher's criteria. Answers the strongest pedagogical objection: a critic that
  scores what it sees, not what was attempted.
- **Technique, not taste.** The verdict is against the criteria the teacher wrote and the
  EXIF arithmetic; PPA element scores stay in the teacher's view as evidence and never
  reach the student's verdict. No leaderboards: trend and attention flags are
  teacher-only, students never see each other's scores.
- **Data sentence on join.** Frames are read by Google's model under Vertex terms, not
  used to train it, and stay in the student's Drive.
- **Reference is real.** The assignment's reference is a frame from the class; the Veo
  clip is a storyboard, labelled as such, attached by the teacher.

## Screens

Teacher, three tabs:

- **Class** — Class Read at the top (one paragraph, written by the agent, dated),
  roster below: last frame, score trend, attention / on track / quiet, unreviewed count.
  Tapping a student opens their Journey / Frames / Frame — the existing pages
  parametrised by `userId` instead of the session.
- **Assignments** — current and past; detail is the brief, criteria, clip, and the
  submissions grid with draft verdicts and the approve controls. The review queue lives
  here (a separate Queue tab is cut).
- **Student** drill-in as above; the Coach opens on any student frame for the teacher.

Student: today's app. Now shows the current assignment in place of a Scout experiment and
the verdict once approved (before that: "handed in, being reviewed"); Frames, Journey
and the Coach unchanged. One new onboarding step: join a class.

## Pipeline changes

- `Assignment` (cohort-level: title, brief, technique, criteria, clip, author
  `teacher` | `scout`, state `draft` | `issued` | `closed`) fans into one `Experiment` per
  student on issue. Judge and Cartographer untouched.
- `Verdict.state`: `draft` → `approved`; `approved_by`, `approved_at`; `feedback` is
  editable. The Judge writes drafts. `verdict.approved` is a new event; the Scribe and
  the student push move from `media.judged` to it. With auto-send on, the Judge
  approves its own draft and publishes both.
- **Class Read** (new stage, `cohort.read`): on the daily tick and when an assignment's
  submissions change, reads every member's skill map and the assignment's verdicts and
  writes the paragraph. Stored on the cohort; the Class tab shows the latest. The
  drafted next assignment is the stretch, displaced by Showcase.
- Scout becomes a drafter: same research and brief writing, `author=scout`, lands as a
  draft assignment, never issued by itself. Reached from *Draft it for me* on the form.
- **Showcase** (new stage on `assignment.closed`): best approved frame per student →
  reel → Lyria bed → teacher's Drive. Director unchanged for the storyboard.
- `Verdict.edited: bool` and `Shot.intent: str`.
- Push: teacher on each new submission (folded: "3 new in Panning"), student on approval.

## Frontend state

- `class` store (Options syntax): roster, assignments, queue, per-student cache keyed
  by user id. `shoots` stays "mine" for the student app and is reused for drill-in by
  passing the user id through actions.
- Router `meta.role`; `TABS` by role; landing redirect by role.
- Components: `ClassRead`, `Roster`, `AssignmentForm`, `AssignmentDetail`, `VerdictReview`.

## Demo

Seed script: a class of eight, frames from a folder, two assignments (one closed,
one half in), a queue of six drafts. Demo beat: Class Read says what the class missed,
teacher approves six verdicts in one tap, opens the drafted next assignment, issues it,
the clip lands a minute later on a student phone.

## Plan

| Day | Work |
|---|---|
| 1 | entities, cohort + membership repo, `owner_or_teacher_of`, `require_role`, `/auth/me`, join flow, tests |
| 2 | Assignment → Experiment fan-out, Verdict states, `verdict.approved`, Scribe/push rewired, Drive-optional ingest |
| 3 | Class Read paragraph, Scout as drafter behind the form, Showcase (Lyria back, reel cut), teacher push |
| 4 | teacher UI: Class tab, roster, drill-in parametrisation |
| 5 | teacher UI: Assignments tab, form, verdict review, approve all |
| 6 | student side: join step, assignment on Now, pending verdict state; seed script |
| 7 | walk both roles in the browser at phone width, fix; deploy on request |
| 8 | video, README, submission |

No slack. If day 3 slips, Showcase ships without the Lyria bed (Veo's own audio is
not a substitute; the reel goes out silent) and the Scout draft is cut.

## Decided

- Students have their own accounts and their own (optional) Drive.
- Every verdict is gated on teacher approval by default; auto-send is a class setting.
- Veo and Lyria stay, pointed at the brief and the celebration, never at the graded
  photograph. The teacher attaches generated media; it is never shown to a student
  unasked.
- Replace, do not add: the single-photographer mode is not maintained alongside.
  The working personal flow stays on `main` as the fallback demo; the pivot is built
  on a branch until day 7.
