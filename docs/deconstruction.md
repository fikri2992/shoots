# Deconstruction

> Social carousel contract, updated 2026-08-31. Decisions 138 through 140 in
> [the domain model](domain-model.md) are normative.

A Deconstruction is an image-led draft that helps someone look more closely at
the Shot the photographer chose. The interface calls it a **visual story**.
It is not a Shoot activity report, an aesthetic score, or an automatic social post.

## The carousel

1. The chosen Shot with a short title and opening caption.
2. One to five story pages. Each explains a different visible detail or relationship.
   When an existing Visual Evidence Artifact helps, the page pairs it with the full
   Shot and a short legend. Otherwise it uses the full Shot or a labelled detail crop.
   Page count follows the supported material.
3. The same Shot, clean: no text, page number, border, branding, overlays, or crop.

Opening and story pages are portrait 1080x1350 JPEGs. Full-image views contain the
whole Shot rather than silently changing its framing. The final JPEG preserves the
original oriented dimensions and aspect ratio. It is not a camera RAW file or a
byte-identical download of the original. Metadata is omitted from the share files.
Social platforms may apply their own carousel framing; the clean image can also be
posted separately. A suggested post caption is provided alongside the images.

## Who writes and who decides

- On the web Shot detail page, **Build visual story** selects that exact still
  Shot. It needs a usable stored Analysis, not a Keeper mark or settled Shoot.
  Building never bookmarks the Shot. Returning to the page reopens its saved draft.
- Journey also retains its settled Shoot and terminal Experiment stories, with
  their existing marked-cover selection. Settlement only creates a `needs_cover` record.
- Domain code collects that Shot's stored observations and supported Technique
  notes with exact Evidence ids. Shoot counts and invented first-person Intent
  are not story material.
- One bounded Gemini writer inside Scribe sees the clean Shot and this Evidence
  packet. It chooses a supported thread, writes the opening and story beats, and
  cites the supplied ids. It also sees labelled previews of the exact artifacts
  and detail crops it can select. It may reject an observation or artifact
  contradicted by the image, but cannot add uncited facts. It abstains if the material is thin.
- Code checks references, duplicate beats, copy length, and visual eligibility.
  The writer's output schema permits only the supplied Evidence and visual ids.
  These checks establish provenance and structure, not whether every sentence is
  a correct interpretation. The UI labels the output as a model-written draft.
- Pillow renders the pages. A detail selection points to existing cell-addressed
  Evidence; grid math calculates its crop, adding surrounding context when a
  region would otherwise be a thin strip. No part of the located region is cut
  away to fill the page. No invented boxes, arrows, or lines.
- An artifact selection must cite its own Technique Evidence. The file must belong
  to this Shot and Photographer, match the original's digest and current renderer,
  and have rendered status with measured or bounded verification. Missing files,
  unresolved results, fallbacks, manual fixtures, and image-less camera receipts
  are not offered. Code records the exact artifact bytes used. The writer may still
  omit an eligible artifact when it does not explain the claim clearly.
- Subject contours need stored subject cells. If their measured area exceeds those
  cells' context bounds, export withholds them. This catches a broad background
  region mistaken for a small subject; it does not prove other contours correct.
- Artifact pages preserve both images' framing. A short legend explains the marks
  and distinguishes measured maps from located visual reads. A map's measurement
  is not proof of the Technique interpretation. Cover and clean ending stay unmarked.
- The photographer reviews, downloads, shares, and posts. Nothing posts itself.

There is no Analyst rerun, original-image edit, new Verdict, or longitudinal write.
Explore and Compare are never assigned a Verdict by the story writer.

## Reliability and old drafts

The durable record keeps the source and cover, Evidence references, model and
prompt provenance, validated writing checkpoint, input digest, and render version.
Same-input requests reuse a completed draft. Available artifacts and their byte
digests are writer inputs too. A render retry reuses its validated
writing without another model call. A bounded lease prevents overlapping writers;
expired work can be retried. Failures are visible and do not undo a settled source
or replace a previous usable draft with template prose.

Previously rendered template drafts remain readable. Explicitly rebuilding one
uses the new writer; an old draft is never relabelled as model-written.

Shot detail drafts use `source_type=shot`, the exact Shot id, and source revision
`1`. `GET /api/deconstructions?shot_id=...` only retrieves the saved draft;
`POST /api/deconstructions` with that same `cover_shot_id` explicitly builds it.
The mobile snapshot retains the newest Shoot or Experiment draft for Journey.
Deploy the `deconstructions` index on `user_id`, `source_type`, and descending
`updated_at` from `infra/firestore.indexes.json` before deploying this API change.

## Download and sharing

On web, **Download all images** requests one numbered JPEG per page. Each preview
also has a download link if the browser blocks multiple downloads. The interface
reports download requests, not unobservable confirmation of disk writes. The
older ZIP API remains for compatibility but is not used by the web interface.

Android uses the same JPEG pages, the system multi-image share sheet, and
MediaStore save. The clean ending is previewed without a forced crop on both
clients. The suggested caption remains visible to copy. In-app caption editing
and direct social-network posting are outside this change.
