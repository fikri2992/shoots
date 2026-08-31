"""Scribe stage: ``media.judged`` → the review written back into the user's Drive.

The photographer's workflow ends in a folder, so the agent's answer lands
in that folder too: ``Shoots/Reviewed/<name> — <finding>.jpg`` is the frame
with the composition read drawn on it, any finding marked on the pixels it was
measured from, and the critique as a caption band, plus the verdict if the
shot was an experiment attempt. It shows up in the Drive and Files apps on the phone
without opening this app, and it can be shared as-is. The file is written *as
the user* (``drive.file`` token), the only thing that token is used for
besides creating the folder.

The file is named after what was *found*, never what it scored. A folder of
``bike — panning.jpg`` is a list a photographer can scroll and act on; a folder
of ``bike — 7 of 10.jpg`` is a report card, and no score reaches the
photographer anywhere in this product (decision 46). What names the file is a
Technique a second lens corroborated, then a Finding with its figure.

Runs after the Judge on the same shot, so the first write already carries
the verdict. A redelivery updates name and caption instead of uploading twice.
"""

import logging
from pathlib import Path
from typing import Protocol

from app.config import settings
from app.domain import findings, taxonomy
from app.domain.entities import Analysis, Experiment, MoveKind, Shot, ShotStatus, Verdict
from app.domain.grid import Grid
from app.imaging import canvas
from app.imaging.caption import add_caption
from app.imaging.findingmark import mark as mark_findings
from app.infra import repository as repo
from app.infra.drive import UserDrive, user_credentials
from app.infra.storage import ANNOTATED
from app.services.context import Context

logger = logging.getLogger(__name__)

AGENT = "scribe"
REVIEW_FOLDER = "Reviewed"


class ReviewPublisher(Protocol):
    async def ensure_folder(self, parent_id: str, name: str, existing: str) -> str: ...

    async def upload(
        self, folder_id: str, name: str, data: bytes, mime_type: str, description: str
    ) -> str: ...

    async def update(self, file_id: str, name: str, description: str) -> None: ...

    def url(self, file_id: str) -> str: ...


# --- pure: what the file is called and says ----------------------------------


def _seen(analysis: Analysis) -> list[str]:
    return [
        taxonomy.BY_ID[t.technique_id].name
        for t in analysis.techniques
        if t.technique_id in taxonomy.BY_ID
    ]


def _corroborated(analysis: Analysis) -> list[str]:
    """What more than one reader actually saw. A single lens with a habit is
    one opinion however often it repeats (decision 33), and praise that turns
    out to be one model's enthusiasm is worse than no praise."""
    return [
        taxonomy.BY_ID[t.technique_id].name
        for t in analysis.techniques
        if t.agreement >= 2 and t.technique_id in taxonomy.BY_ID
    ]


def review_finding(analysis: Analysis) -> str:
    """What the folder listing says about this frame.

    What the frame *did* comes first, and only what a second reader
    corroborated. The photographer this is for is a hobbyist who will stop
    opening an app that greets them with a defect every time, and the thing
    they came for is what they are getting right.

    The finding is next, and it is never dropped — it carries the figure it was
    computed from, which is the one line here anybody can check. There is no
    third option involving a number: the score used to name the file, and one
    number for a whole photograph whose five elements correlate at r = 0.89
    (docs/research-findings.md, §1) is the least informative thing available.
    A frame with nothing corroborated and nothing wrong says exactly that.
    """
    if analysis.abstained:
        return "could not read"
    strong = _corroborated(analysis)
    if strong:
        return ", ".join(strong[:2]).lower()
    if analysis.findings:
        return findings.FINDINGS.get(analysis.findings[0].finding_id, "worth another look").lower()
    seen = _seen(analysis)
    return ", ".join(seen[:2]).lower() if seen else "nothing clear enough to call"


def review_name(shot: Shot, analysis: Analysis, verdict: Verdict | None) -> str:
    stem = Path(shot.filename).stem or shot.id
    mark = "" if verdict is None else ("✔ " if verdict.criteria_met else "✘ ")
    return f"{mark}{stem} — {review_finding(analysis)}.jpg"


def review_title(analysis: Analysis, experiment: Experiment | None, verdict: Verdict | None) -> str:
    """The bold line on the caption band: what the frame does, then what to fix.

    That order is the product's, not a stylistic preference: praise first and
    with proof, the finding after and with its figure.
    """
    if analysis.abstained:
        return f"Could not read this Shot: {analysis.abstained}"
    seen = ", ".join(_seen(analysis))
    wrong = findings.FINDINGS.get(analysis.findings[0].finding_id, "") if analysis.findings else ""
    title = " · ".join(part for part in (seen, wrong) if part) or "Nothing clear enough to call"
    if experiment and experiment.criteria_notice:
        return f"Criteria correction · {experiment.title} · {title}"
    if verdict and experiment:
        met = "MATCHED" if verdict.criteria_met else "NOT YET"
        title = f"{met} · {experiment.title} · {title}"
    return title


def review_body(
    analysis: Analysis, verdict: Verdict | None, grid: Grid, experiment: Experiment | None = None
) -> list[str]:
    body: list[str] = []
    if experiment and experiment.criteria_notice:
        body.append(experiment.criteria_notice)
    # An abstention is stated before anything else, because everything after it
    # has to be read differently: three readers each saw something and no two
    # saw the same thing, so nothing below is a verdict (decision 38). The
    # findings are the exception and stay exactly as true - they are arithmetic.
    if analysis.abstained:
        body.append(f"Shoots could not read this one confidently: {analysis.abstained}.")
    if analysis.critique.strip():
        body.append(analysis.critique.strip())
    # Findings before advice: each carries the figure it was computed from, which
    # is the only thing here the reader can check against their own histogram.
    # The rubric's element scores are deliberately absent — they correlate at
    # r = 0.89, so printing five of them prints one number five times.
    for finding in analysis.findings:
        label = findings.FINDINGS.get(finding.finding_id, "Finding")
        body.append(f"{label}: {finding.what} ({finding.why}).")
    for index, move in enumerate(analysis.composition.moves, 1):
        where = ""
        if move.kind is MoveKind.MOVE and move.from_cells and move.to_cells:
            where = f": {grid.place(move.from_cells)} → {grid.place(move.to_cells)}"
        elif move.kind is MoveKind.CROP and move.to_cells:
            where = f": keep {grid.place(move.to_cells)}"
        body.append(f"{index}. {move.what}{where}. {move.reason}")
    if verdict:
        label = (
            "Original feedback, kept for history: "
            if experiment and experiment.criteria_notice
            else ""
        )
        body.append(label + verdict.feedback.strip())
    return body


def review_description(
    shot: Shot, analysis: Analysis, experiment: Experiment | None, verdict: Verdict | None
) -> str:
    lines = [review_title(analysis, experiment, verdict), ""]
    lines += review_body(analysis, verdict, _grid(shot), experiment)
    # No grid legend: cells never reach this text, so nothing needs explaining.
    lines += ["", "Reviewed by Shoots."]
    return "\n".join(lines)[:4000]


# --- the stage ----------------------------------------------------------------


async def write_review(
    ctx: Context, message: dict, publisher: ReviewPublisher | None = None
) -> str | None:
    """Returns the review file id, or None when there was nothing to write."""
    shot = await repo.get_shot(ctx.store, message["shot_id"])
    analysis = await repo.find_analysis(ctx.store, shot.id)
    if shot.status is not ShotStatus.ANALYZED or analysis is None:
        logger.info("scribe: %s is %s, nothing to write", shot.id, shot.status.value)
        return None
    if ANNOTATED not in shot.blobs:
        logger.warning("scribe: %s has no annotated frame", shot.id)
        await repo.record(
            ctx.store,
            shot.user_id,
            AGENT,
            "write_skipped",
            {"reason": "no annotated frame was produced"},
            shot_id=shot.id,
            experiment_id=shot.experiment_id,
        )
        return None

    user = await repo.get_user(ctx.store, shot.user_id)
    publisher = publisher or await _publisher_for(ctx, user.id)
    if publisher is None:
        logger.info("scribe: no Drive token for %s, skipping", user.id)
        await repo.record(
            ctx.store,
            shot.user_id,
            AGENT,
            "write_skipped",
            {"reason": "Drive output is not connected"},
            shot_id=shot.id,
            experiment_id=shot.experiment_id,
        )
        return None

    experiment = verdict = None
    if shot.experiment_id:
        try:
            experiment = await repo.get_experiment(ctx.store, shot.experiment_id)
            verdict = next((v for v in experiment.verdicts if v.shot_id == shot.id), None)
        except repo.UnknownEntity:
            experiment = None

    name = review_name(shot, analysis, verdict)
    description = review_description(shot, analysis, experiment, verdict)

    if shot.drive_review_id and experiment and experiment.criteria_notice:
        await repo.record(
            ctx.store,
            shot.user_id,
            AGENT,
            "review_preserved",
            {"reason": "Historical review kept unchanged; correction is on the Experiment."},
            shot_id=shot.id,
            experiment_id=experiment.id,
        )
        return shot.drive_review_id
    if shot.drive_review_id:
        await publisher.update(shot.drive_review_id, name, description)
        stage = "updated"
    else:
        folder_id = await publisher.ensure_folder(
            user.drive_folder_id, REVIEW_FOLDER, user.drive_review_folder_id
        )
        if folder_id != user.drive_review_folder_id:
            user.drive_review_folder_id = folder_id
            await repo.put_user(ctx.store, user)
        frame = canvas.load_bytes(await ctx.blobs.read(shot.blobs[ANNOTATED]))
        # Zebras over the clipped area, so "8.3% above 250" is visible and not
        # merely asserted. Draws nothing when no finding has a region to point at.
        frame = mark_findings(frame, analysis.findings)
        captioned = add_caption(
            frame,
            review_title(analysis, experiment, verdict),
            review_body(analysis, verdict, _grid(shot), experiment),
            footer=f"Reviewed by Shoots · {shot.filename}",
        )
        data = canvas.to_jpeg_bytes(captioned, quality=88)
        shot.drive_review_id = await publisher.upload(
            folder_id, name, data, "image/jpeg", description
        )
        shot.drive_review_url = publisher.url(shot.drive_review_id)
        await repo.put_shot(ctx.store, shot)
        stage = "reviewed"

    await repo.record(
        ctx.store,
        shot.user_id,
        AGENT,
        stage,
        {"name": name, "file_id": shot.drive_review_id, "verdict": bool(verdict)},
        shot_id=shot.id,
        experiment_id=shot.experiment_id,
    )
    return shot.drive_review_id


async def _publisher_for(ctx: Context, user_id: str) -> ReviewPublisher | None:
    if settings.drive_local_folder:
        return LocalReviewPublisher(settings.drive_local_folder)
    token = await ctx.tokens.get(user_id)
    if not token or not token.get("refresh_token"):
        return None
    return DriveReviewPublisher(UserDrive(user_credentials(token)))


# --- publishers ---------------------------------------------------------------


class DriveReviewPublisher:
    def __init__(self, drive: UserDrive):
        self._drive = drive

    async def ensure_folder(self, parent_id: str, name: str, existing: str) -> str:
        if existing:
            return existing
        return await self._drive.create_folder(name, parent_id=parent_id)

    async def upload(
        self, folder_id: str, name: str, data: bytes, mime_type: str, description: str
    ) -> str:
        return await self._drive.upload(folder_id, name, data, mime_type, description=description)

    async def update(self, file_id: str, name: str, description: str) -> None:
        await self._drive.update(file_id, name=name, description=description)

    def url(self, file_id: str) -> str:
        return f"https://drive.google.com/file/d/{file_id}/view"


class LocalReviewPublisher:
    """The local folder stands in for Drive: ``<root>/Reviewed/<name>`` plus a
    ``.txt`` sidecar with the description. Ids are paths relative to root."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    async def ensure_folder(self, parent_id: str, name: str, existing: str) -> str:
        folder = self.root / name
        folder.mkdir(parents=True, exist_ok=True)
        return name

    async def upload(
        self, folder_id: str, name: str, data: bytes, mime_type: str, description: str
    ) -> str:
        path = self.root / folder_id / name
        path.write_bytes(data)
        path.with_suffix(".txt").write_text(description, encoding="utf-8")
        return f"{folder_id}/{name}"

    async def update(self, file_id: str, name: str, description: str) -> None:
        path = self.root / file_id
        target = path.with_name(name)
        if path.exists() and target != path:
            path.rename(target)
            old_sidecar = path.with_suffix(".txt")
            if old_sidecar.exists():
                old_sidecar.unlink()
        target.with_suffix(".txt").write_text(description, encoding="utf-8")

    def url(self, file_id: str) -> str:
        return (self.root / file_id).as_posix()


def _grid(shot: Shot) -> Grid:
    return Grid(
        cols=shot.grid.cols, rows=shot.grid.rows, width=shot.grid.width, height=shot.grid.height
    )
