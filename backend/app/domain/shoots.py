"""Pure capture-continuity rules for Scenes and Shoots."""

from datetime import UTC, datetime, timedelta

from app.domain.entities import Scene, Shoot, Shot, ShotSource
from app.domain.tendency import SCENE_GAP


def capture_instant(shot: Shot) -> datetime | None:
    """Return the best known Camera instant without upgrading guessed EXIF."""
    if shot.source is ShotSource.ANDROID:
        source_time = _android_source_instant(shot.source_id)
        if source_time is not None:
            return source_time
    return _aware(shot.exif.captured_at or shot.captured_at)


def device_id(shot: Shot) -> str:
    if shot.source is not ShotSource.ANDROID or ":external:" not in shot.source_id:
        return ""
    return shot.source_id.split(":external:", 1)[0]


def choose_shoot(shoots: list[Shoot], at: datetime | None, gap: timedelta) -> Shoot | None:
    if at is None:
        return None
    candidates = [
        shoot for shoot in shoots if _within(at, shoot.started_at, shoot.last_capture_at, gap)
    ]
    return min(candidates, key=lambda shoot: _distance(at, shoot), default=None)


def choose_scene(scenes: list[Scene], at: datetime | None) -> Scene | None:
    if at is None:
        return None
    candidates = [
        scene for scene in scenes if _within(at, scene.started_at, scene.ended_at, SCENE_GAP)
    ]
    return min(candidates, key=lambda scene: _distance(at, scene), default=None)


def include_in_scene(scene: Scene, shot_id: str, at: datetime | None) -> Scene:
    if shot_id not in scene.ordered_shot_ids:
        scene.ordered_shot_ids.append(shot_id)
    scene.started_at = _earliest(scene.started_at, at)
    scene.ended_at = _latest(scene.ended_at, at)
    return scene


def include_in_shoot(shoot: Shoot, scene_id: str, shot_id: str, at: datetime | None) -> Shoot:
    if scene_id not in shoot.ordered_scene_ids:
        shoot.ordered_scene_ids.append(scene_id)
    if shot_id not in shoot.ordered_shot_ids:
        shoot.ordered_shot_ids.append(shot_id)
    shoot.started_at = _earliest(shoot.started_at, at)
    shoot.last_capture_at = _latest(shoot.last_capture_at, at)
    return shoot


def _android_source_instant(source_id: str) -> datetime | None:
    try:
        _, volume, _, date_added, _ = source_id.rsplit(":", 4)
        if volume != "external":
            return None
        value = int(date_added)
        if value <= 0:
            return None
        return datetime.fromtimestamp(value, UTC)
    except (TypeError, ValueError):
        return None


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _within(
    at: datetime,
    started_at: datetime | None,
    ended_at: datetime | None,
    gap: timedelta,
) -> bool:
    if started_at is None or ended_at is None:
        return False
    return started_at - gap <= at <= ended_at + gap


def _distance(at: datetime, item: Scene | Shoot) -> timedelta:
    started_at = item.started_at
    ended_at = item.ended_at if isinstance(item, Scene) else item.last_capture_at
    if started_at is None or ended_at is None or started_at <= at <= ended_at:
        return timedelta(0)
    return started_at - at if at < started_at else at - ended_at


def _earliest(current: datetime | None, candidate: datetime | None) -> datetime | None:
    if current is None:
        return candidate
    if candidate is None:
        return current
    return min(current, candidate)


def _latest(current: datetime | None, candidate: datetime | None) -> datetime | None:
    if current is None:
        return candidate
    if candidate is None:
        return current
    return max(current, candidate)
