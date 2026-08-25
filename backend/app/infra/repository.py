"""Typed persistence on top of the four-method Store.

One function per read or write the services need, pydantic in and out. The
collection names and document ids are decided here and nowhere else.
"""

from datetime import datetime

from app.domain.entities import (
    ActivityEvent,
    Analysis,
    JourneyUpdate,
    Quest,
    QuestStatus,
    Shot,
    SkillState,
    User,
    new_id,
    now,
)
from app.infra.store import Store

USERS = "users"
SHOTS = "shots"
ANALYSES = "analyses"
SKILLS = "skills"
QUESTS = "quests"
EVENTS = "events"
JOURNEY = "journey"
PAIRING = "pairing_codes"
DEVICES = "devices"


class UnknownEntity(LookupError):
    pass


def _dump(model) -> dict:
    return model.model_dump(mode="json")


# --- users ----------------------------------------------------------------


async def put_user(store: Store, user: User) -> None:
    await store.put(USERS, user.id, _dump(user))


async def get_user(store: Store, user_id: str) -> User:
    data = await store.get(USERS, user_id)
    if data is None:
        raise UnknownEntity(f"user {user_id}")
    return User.model_validate(data)


async def find_user(store: Store, user_id: str) -> User | None:
    data = await store.get(USERS, user_id)
    return User.model_validate(data) if data else None


async def list_users(store: Store) -> list[User]:
    return [User.model_validate(d) for d in await store.query(USERS)]


# --- shots ----------------------------------------------------------------


def shot_id_for(user_id: str, drive_file_id: str) -> str:
    """Deterministic: the same Drive file can never become two shots."""
    return f"shot_{user_id[-8:]}_{drive_file_id}"


async def put_shot(store: Store, shot: Shot) -> None:
    await store.put(SHOTS, shot.id, _dump(shot))


async def get_shot(store: Store, shot_id: str) -> Shot:
    data = await store.get(SHOTS, shot_id)
    if data is None:
        raise UnknownEntity(f"shot {shot_id}")
    return Shot.model_validate(data)


async def find_shot(store: Store, shot_id: str) -> Shot | None:
    data = await store.get(SHOTS, shot_id)
    return Shot.model_validate(data) if data else None


async def list_shots(store: Store, user_id: str, limit: int | None = None) -> list[Shot]:
    rows = await store.query(
        SHOTS, where={"user_id": user_id}, order_by="ingested_at", descending=True, limit=limit
    )
    return [Shot.model_validate(d) for d in rows]


# --- analyses -------------------------------------------------------------


async def put_analysis(store: Store, analysis: Analysis) -> None:
    await store.put(ANALYSES, analysis.shot_id, _dump(analysis))


async def find_analysis(store: Store, shot_id: str) -> Analysis | None:
    data = await store.get(ANALYSES, shot_id)
    return Analysis.model_validate(data) if data else None


# --- skills ---------------------------------------------------------------


def skill_id_for(user_id: str, technique_id: str) -> str:
    return f"{user_id}__{technique_id}"


async def put_skill(store: Store, skill: SkillState) -> None:
    await store.put(SKILLS, skill_id_for(skill.user_id, skill.technique_id), _dump(skill))


async def list_skills(store: Store, user_id: str) -> list[SkillState]:
    rows = await store.query(SKILLS, where={"user_id": user_id})
    return [SkillState.model_validate(d) for d in rows]


# --- quests ---------------------------------------------------------------


async def put_quest(store: Store, quest: Quest) -> None:
    await store.put(QUESTS, quest.id, _dump(quest))


async def get_quest(store: Store, quest_id: str) -> Quest:
    data = await store.get(QUESTS, quest_id)
    if data is None:
        raise UnknownEntity(f"quest {quest_id}")
    return Quest.model_validate(data)


async def open_quest(store: Store, user_id: str) -> Quest | None:
    rows = await store.query(
        QUESTS, where={"user_id": user_id, "status": QuestStatus.OPEN.value}, limit=1
    )
    return Quest.model_validate(rows[0]) if rows else None


async def list_quests(store: Store, user_id: str, limit: int | None = None) -> list[Quest]:
    rows = await store.query(
        QUESTS, where={"user_id": user_id}, order_by="issued_at", descending=True, limit=limit
    )
    return [Quest.model_validate(d) for d in rows]


# --- events ---------------------------------------------------------------


async def record(
    store: Store,
    user_id: str,
    agent: str,
    stage: str,
    detail: dict | None = None,
    shot_id: str = "",
    quest_id: str = "",
) -> ActivityEvent:
    event = ActivityEvent(
        id=new_id("evt"),
        user_id=user_id,
        agent=agent,
        stage=stage,
        detail=detail or {},
        shot_id=shot_id,
        quest_id=quest_id,
    )
    await store.put(EVENTS, event.id, _dump(event))
    return event


async def list_events(store: Store, user_id: str, limit: int = 100) -> list[ActivityEvent]:
    rows = await store.query(
        EVENTS, where={"user_id": user_id}, order_by="at", descending=True, limit=limit
    )
    return [ActivityEvent.model_validate(d) for d in rows]


# --- journey updates -------------------------------------------------------


async def put_journey_update(store: Store, update: JourneyUpdate) -> None:
    await store.put(JOURNEY, update.id, _dump(update))


async def list_journey_updates(
    store: Store, user_id: str, limit: int = 20
) -> list[JourneyUpdate]:
    """Newest first: the photographer reads the current conclusion, and the
    older ones are the record of how it changed."""
    rows = await store.query(
        JOURNEY, where={"user_id": user_id}, order_by="created_at", descending=True, limit=limit
    )
    return [JourneyUpdate.model_validate(d) for d in rows]


async def latest_journey_update(store: Store, user_id: str) -> JourneyUpdate | None:
    found = await list_journey_updates(store, user_id, limit=1)
    return found[0] if found else None


# --- pairing a camera to an account ----------------------------------------


async def put_pairing_code(store: Store, code: str, user_id: str, expires_at: datetime) -> None:
    await store.put(
        PAIRING, code, {"code": code, "user_id": user_id, "expires_at": expires_at.isoformat()}
    )


async def spend_pairing_code(store: Store, code: str, at: datetime) -> str | None:
    """The user id the code stands for, and the code is gone either way.

    Single use is the point: a code read off a screen by someone else is worth
    one attempt within its window, not an open door. Deleting an expired code
    on the way past keeps the collection from growing without a sweeper.
    """
    data = await store.get(PAIRING, code)
    if data is None:
        return None
    await store.delete(PAIRING, code)
    if datetime.fromisoformat(data["expires_at"]) < at:
        return None
    return data["user_id"]


async def put_device(store: Store, fingerprint: str, user_id: str, label: str) -> None:
    """Devices are keyed by the hash of their token: the store never holds a
    credential that would work if it leaked."""
    await store.put(
        DEVICES,
        fingerprint,
        {
            "fingerprint": fingerprint,
            "user_id": user_id,
            "label": label,
            "paired_at": now().isoformat(),
        },
    )


async def find_device(store: Store, fingerprint: str) -> dict | None:
    return await store.get(DEVICES, fingerprint)
