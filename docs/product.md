# Shoots, as one thing

Product note, 2026-08-23. Pulls `lighting.md`, `conditions.md` and the Day 8
interaction rebuild into one object the person experiences. `classroom.md` is kept
as a record of the road not taken.

## The one sentence

**Shoots makes an appointment with the light, gets you there ready, talks you
through the viewfinder, and tells you what actually happened.**

Everything in the product is a phase of that appointment. Nothing is a feature.

## The object: a shoot

Internally it stays `Quest`. To the person it is *a shoot* — "Saturday's shoot" —
which is also the app's name, and drops the game word. One shoot is open at a time.
It has phases, and the **Now** screen renders exactly the current phase:

| phase | when | what Now shows | the one action |
|---|---|---|---|
| **planned** | issued → T−30 min | clip (or diagram indoors), title, *when* line with conditions, the light sentence, the strip; `How to shoot it`, `Before you go`, `Why now` behind disclosures | Skip |
| **moved** | a re-plan happened | same, with the amber line *Moved from Fri 17:10 — 82 % rain* | Skip |
| **soon** | T−30 → window opens | the prep list as a checklist, *leave by 17:15*, the gear items that are time-bound (*take the phone out of the air-con now*) | Open the viewfinder |
| **open** | the light window | the viewfinder: camera, sun ring outdoors / histogram indoors, the Coach speaking; pre-flight on the shutter | Shoot |
| **reading** | frame sent | the three stages ticking, as today | — |
| **verdict** | judged | passed / not yet, the one next thing, the light checks and the sky behind `How it scored`; *not on you* when excused | Ask the Coach · Shoot again |
| **idle** | nothing open | last verdict, best frame, and what the Scout is waiting for (light, sky, or the daily tick) | Ask for one now |

Pushes are the phase changes: issued, moved, soon (T−30), open (window), verdict.
Nothing else is ever pushed.

## What each piece is, in the person's words

| piece | where it lives | the person's sentence |
|---|---|---|
| sun timing (`timing.py`, `sun.py`) | the *when* line, the strip | "it knows when the light is right where I shoot" |
| sky and air (`conditions.md`) | the *when* line numbers, `Before you go`, *Moved* | "it checked the weather and moved it for me" |
| light plan (`lighting.md`) | the light sentence, the diagram indoors | "it told me where to put her and where to stand" |
| prep (`conditions.md`) | `Before you go` | "it told me to bring water and get the phone out of the AC" |
| camera card | a `Before you go` item of kind `camera` | "it gave me the settings for my phone" |
| viewfinder + sun ring + Coach live | phase **open** | "it talked me into position" |
| pre-flight | the shutter in phase **open** | "it stopped me sending a bad one" |
| panel, crop loop, guides | the frame page | "it showed me the frame on the grid it's built on" |
| light facts + read | the frame page light row | "it knows where the sun was when I pressed" |
| light checks + excuse | the verdict | "it was fair — the cloud wasn't my fault" |
| Replanner | *Moved*, the log | "the plan changed when the sky did" |
| skill map + road ahead | Journey | "I can see what's next and why it changed" |
| Drive review | the person's own folder | "the review is in my Drive, I never opened the app" |
| Veo storyboard | the clip on **planned** | "it showed me the move" |
| Lyria reel | `Shoots/Reels/` monthly | "my best frames, with music" (bonus; last day) |

Things that do not appear in this table are cut: the classroom, the embedding
reference, the mentor view, Gemma (kept only if pre-flight moves to it invisibly
on a spare hour).

## Who it is for

One primary person; two at the edges. Written from the VSCO 2026 photographers
survey, the critique-app landscape, and the fact that the author is the primary
person.

### The plateaued phone shooter (primary)

Owns a good phone, maybe a used mirrorless with the kit lens. Shoots on weekends
and trips, has done so for two or three years, and the photos look the same as they
did two years ago.

- **Believes**: that better photos come from better gear or a better place; that
  "composition" is a talent other people have; that they would improve if someone
  told them *what to do next*, because tutorials tell them everything at once.
- **Goal**: to be able to look at a scene and know what to do. To get a frame they
  are proud of once a week, not once a year. Secretly: to be told they are getting
  better, by something that is not a friend being polite.
- **Objections**: "AI will just say generic things about the rule of thirds." "I do
  not want to upload my photos somewhere." "Another app that sends notifications."
  "It will not know what I was trying to do." "I will not keep it up."
- **Workaround today**: YouTube at night, a Reddit post that got two comments, a
  "photo a day" challenge abandoned on day nine, a folder called *good ones*, and
  asking a friend who shoots, who says "nice".
- **What answers each objection, in the product**: the verdict reads EXIF and the
  sun, not vibes — numbers where it acted; frames stay in their own Drive and the
  review lands there; five pushes per shoot, all phase changes; the Coach asks what
  they were going for; the Scout sets the next one by itself, so keeping it up is
  showing up on Saturday.

### The returning enthusiast (edge)

Shot seriously ten years ago, has a real camera in a drawer, knows the words.
Believes they have forgotten less than they have. Goal: a structured way back in
without a course. Objection: "do not explain thirds to me." Workaround: none; the
camera stays in the drawer. The product answers with the skill map (it reads what
they already do and starts from there), the light row and the checks (specifics,
not lessons), and the Coach as a peer.

### The working photographer (edge, mostly not a user)

Believes AI is taking their work and their images — 58 % of UK AoP members have
lost work to it. Objection is moral, not functional: "you trained on us." Goal, if
any: a second pair of eyes that is not a client. Workaround: peers, a paid mentor,
their own taste. The product does not court them; it avoids offending them: it
never generates the photograph, the storyboard is labelled, the review is signed
as a read, not a judgement of art, and the person's frames are not training data,
said in one sentence on connect.

### The belief the product has to change

Not "AI can critique photos" — that is accepted and crowded. The belief to change
is *"improving is a matter of knowledge"*. It is a matter of being in the right
light, ready, with one thing to try, and then being told honestly what happened.
Every phase of the shoot is built to make that the felt experience, which is why
the product is an appointment and not a critique.

## Why AI photo critique works today, and for whom

Read on 2026-08-23: LENSIC, PhotoCritic.ai, PhotoMentor, Vision Mentor, Jenova's
coach, the GPT-store critics, Adobe's Project Indigo critique, and one working
photographer's write-up of using them.

**The job they are hired for** is not "make me better". It is *"tell me if this one
is good, now, without asking anyone."* The moment is after the shoot, photo in hand,
nobody to show it to whose opinion is both honest and safe. Every product is shaped
by that moment: upload, 20 seconds, a number, a paragraph, optionally a share link.

**Why it works (the mechanics, all of them present in every tool):**

1. *A number.* 87/100, 7.5/10, five categories out of 100. The score is the product;
   the paragraph is the justification. People come back to move the number.
2. *No friction at all.* No login (LENSIC, PhotoMentor, PhotoCritic), free first
   uses, web only. The job is impulsive; a sign-up kills it.
3. *The promise of honesty.* "Honest critique. Real growth." "An editor's honest
   critique." "Dispense with the false compliments." The value is explicitly that
   the machine will say what a friend will not.
4. *Safety.* Private, no audience, no comments section. The Reddit critique thread
   is the competitor and its failure mode is public.
5. *Categories from the competition rubric.* Composition, lighting, colour,
   storytelling, technical — the PPA-shaped five. It reads as authoritative because
   it sounds like judging.
6. *Marks on the image.* PhotoMentor draws bounding boxes "where attention leaks";
   Indigo uses deterministic buttons instead of prompts because, in Levoy's words,
   prompts are "tricky". Specific beats conversational.

**Who they target, and the two business models:**

- *Enthusiasts and intermediates, by genre.* Landscape / portrait / street / still
  life selectors; "from beginners to working professionals" in the copy, enthusiasts
  in practice. Free or $5 a month. Volume claims are small (PhotoMentor: 6,000+
  photos; Jenova: 28,000 users of a coach persona). This is a long tail of tiny
  tools, not a category leader.
- *Working photographers, for culling.* PhotoMentor's $15 "Pro Workflow" ranks the
  strongest frames of a shoot and explains the cut; a Chrome extension scores inside
  Google Photos. This is the only segment paying real money, and the job is
  throughput, not learning.
- *Platforms.* Adobe is putting critique inside the camera app, as buttons.
  Once that ships, "upload a photo, get a score" is a feature, not a product.

**Where every one of them stops** (the gap is the same in all):

- The unit is one photo. None keeps a model of the person across frames
  (PhotoMentor has a "progress dashboard" of scores; none has a skill map).
- Nothing happens *before* the photo. No tool tells you when to go, where to stand,
  or what to try; the critique arrives after the only moment it could have helped.
- No hard evidence. None reads EXIF against a bound, none knows where the sun was.
  Scores are impressions, which is why the working photographer's review says they
  "flag deliberate artistic choices as flaws" and give "bland (and often banal)
  critique" without context.
- No intent. The same review's central finding: "the more information the tool has,
  the more useful the feedback" — and none of the tools asks.
- Nothing leaves the tool. The photo goes in, the text stays on their site.

**What Shoots keeps from them, deliberately:** the number (the score and the five
elements stay), the marks on the image (the guide and the one instruction), the
honesty promise (as numbers, not as a tone setting), and privacy (the person's own
Drive). **What it refuses:** the upload box as the front door — the front door is a
push that says *Saturday 17:40*. The critique is the last phase of the shoot, not
the product.

**Consequence for the pitch:** do not say "AI photo critique"; judges and
photographers both file that under solved-and-crowded. Say what happens before the
photo. The critique tools prove the demand for honest feedback; the demand they
cannot serve is for the next Saturday.

## Language, once

- *shoot*, not quest; *the light*, not the lighting plan; *moved*, not rescheduled;
  *not on you*, not excused. The log may use the internal names.
- Every number the agent acted on is shown where it acted: the *when* line, the prep
  reasons, the *Moved* line, the light row. Honesty is the numbers, not a badge.
- One accent, amber, still means "the agent decided this": the *Moved* line, the
  sun ring when you are on it, the light sentence's key phrase.
- No grid cells anywhere a person reads. No degrees in sentences; degrees live in
  the diagram, the ring and the light row.

## Journey gets one new thing

**The road ahead**: the next four shoots the Scout intends, each with its light and
the earliest day the sky allows. After a verdict, a skip, or a re-plan the list
visibly changes, with the reason inline. This is the whole planner made legible,
and it costs a list.

## The day it is demoed

Saturday morning, push: *Rim light on a walker — Sat 17:40, Kota Tua. Clear, 31°,
feels 36.* Open **Now**: clip, strip, "sun low in the west, put it behind him, face
east", `Before you go`: water, forty minutes, phone out of the AC at 17:10.
Friday 17:00 a push: *Moved to Sunday 17:35 — 82 % rain Saturday.* Sunday 17:05:
*Leave by 17:15. Take the phone out of the air-con now.* 17:35: **Open the
viewfinder** — the ring turns amber as you turn, the Coach says "there". Shoot.
Pre-flight says the rim is there. Reading. Verdict: passed; *face went black, a wall
on your left next time*; the review is in Drive. Journey: the road ahead moved
silhouette up a week.

Four minutes. The architecture slide is the same story with stage names.

## Eight days

| day | date | work |
|---|---|---|
| 1 | 08-24 | Stage One: architecture diagram, README walkthrough, the Director bug on voice-issued shoots, deploy prep; deploy on "go deploy" |
| 2 | 08-25 | `sun_position`, `light.py` facts, recipes, `LightPlan` on the Scout, strip + diagram + light row |
| 3 | 08-26 | weather + air client and cache, `derive`/`fit`/`prep`, Scout slots, *when* line, `Before you go` (camera item included) |
| 4 | 08-27 | Replanner on the tick, *Moved*, excused checks in the Judge, the pushes per phase |
| 5 | 08-28 | viewfinder: camera frames into the Live relay, sun ring, histogram, Coach briefed with the tell, pre-flight on the shutter |
| 6 | 08-29 | phases on **Now**, the road ahead on Journey, walk both on the phone, redeploy |
| 7 | 08-30 | video with an unedited live run, blog post + hashtag post, Lyria reel if the morning is clean |
| 8 | 08-31 | submit by noon PDT; the afternoon is slack for the first time |

Cuts, in order, if a day slips: Lyria reel → road ahead → histogram indoors →
Replanner keeps only `shift` (no `swap`).
