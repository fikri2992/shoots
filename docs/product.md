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
