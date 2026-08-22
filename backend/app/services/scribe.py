"""Scribe stage: ``media.judged`` → the review written back into the user's Drive.

The photographer's workflow ends in a folder, so the agent's answer lands
in that folder too: ``Shoots/Reviewed/<name> — <score> of 10.jpg`` is the
frame with the composition read drawn on it and the critique as a caption
band, plus the verdict if the shot was a quest attempt. It shows up in the
Drive and Files apps on the phone without opening this app, and it can be
shared as-is. The file is written *as the user* (``drive.file`` token), the
only thing that token is used for besides creating the folder.

Runs after the Judge on the same shot, so the first write already carries
the verdict. A redelivery updates name and caption instead of uploading twice.
"""

import logging
from pathlib import Path
from typing import Protocol

from app.config import settings
from app.domain import taxonomy
from app.domain.entities import Analysis, Quest, Shot, ShotStatus, Verdict
from app.imaging import canvas
from app.imaging.caption import add_caption
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


def review_name(shot: Shot, analysis: Analysis, verdict: Verdict | None) -> str:
    stem = Path(shot.filename).stem or shot.id
    mark = "" if verdict is None else ("✔ " if verdict.passed else "✘ ")
    return f"{mark}{stem} — {analysis.score} of 10.jpg"


def review_title(analysis: Analysis, quest: Quest | None, verdict: Verdict | None) -> str:
    seen = ", ".join(
        taxonomy.BY_ID[t.technique_id].name
        for t in analysis.techniques
        if t.technique_id in taxonomy.BY_ID
    )
    title = f"{analysis.score}/10" + (f" · {seen}" if seen else "")
    if verdict and quest:
        title = f"{'PASSED' if verdict.passed else 'NOT YET'} · {quest.title}  —  {title}"
    return title


def review_body(analysis: Analysis, verdict: Verdict | None) -> list[str]:
    body = [analysis.critique.strip()] if analysis.critique.strip() else []
    if analysis.elements:
        body.append(
            "Elements: "
            + " · ".join(f"{k} {v}/10" for k, v in analysis.elements.items())
            + " (PPA merit-image rubric)"
        )
    for index, move in enumerate(analysis.composition.moves, 1):
        body.append(
            f"{index}. {move.what}: {','.join(move.from_cells)} → {','.join(move.to_cells)}. "
            f"{move.reason}"
        )
    if verdict:
        body.append(verdict.feedback.strip())
    return body


def review_description(
    shot: Shot, analysis: Analysis, quest: Quest | None, verdict: Verdict | None
) -> str:
    lines = [review_title(analysis, quest, verdict), ""]
    lines += review_body(analysis, verdict)
    grid = shot.grid
    if grid:
        lines += ["", f"Cells: {grid.cols}×{grid.rows} grid, A1 top-left. Reviewed by Shoots."]
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
        return None

    user = await repo.get_user(ctx.store, shot.user_id)
    publisher = publisher or await _publisher_for(ctx, user.id)
    if publisher is None:
        logger.info("scribe: no Drive token for %s, skipping", user.id)
        return None

    quest = verdict = None
    if shot.quest_id:
        try:
            quest = await repo.get_quest(ctx.store, shot.quest_id)
            verdict = next((v for v in quest.verdicts if v.shot_id == shot.id), None)
        except repo.UnknownEntity:
            quest = None

    name = review_name(shot, analysis, verdict)
    description = review_description(shot, analysis, quest, verdict)

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
        captioned = add_caption(
            frame,
            review_title(analysis, quest, verdict),
            review_body(analysis, verdict),
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
        quest_id=shot.quest_id,
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
