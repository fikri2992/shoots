"""Pairing a camera to an account: the phone is handed an identity, never
given a way to authenticate on its own."""

from datetime import timedelta

from app.api import pairing
from app.domain.entities import now
from app.infra import repository as repo
from app.infra.store import InMemoryStore


async def test_a_code_is_spent_the_first_time_it_is_used():
    """A code read off a screen by someone else is worth one attempt inside
    its window, not an open door."""
    store = InMemoryStore()
    await repo.put_pairing_code(store, "ABC123", "u1", now() + timedelta(minutes=10))
    assert await repo.spend_pairing_code(store, "ABC123", now()) == "u1"
    assert await repo.spend_pairing_code(store, "ABC123", now()) is None


async def test_an_expired_code_pairs_nothing_and_is_cleared():
    store = InMemoryStore()
    await repo.put_pairing_code(store, "OLD999", "u1", now() - timedelta(seconds=1))
    assert await repo.spend_pairing_code(store, "OLD999", now()) is None
    assert await store.get(repo.PAIRING, "OLD999") is None


async def test_an_unknown_code_pairs_nothing():
    assert await repo.spend_pairing_code(InMemoryStore(), "NOPE12", now()) is None


async def test_the_store_never_holds_a_working_credential():
    """A device token is a bearer credential. What is stored is its hash, so a
    leaked store is not a set of keys."""
    store = InMemoryStore()
    token = "a-real-device-token"
    await repo.put_device(store, pairing.token_fingerprint(token), "u1", "Pixel")
    rows = await store.query(repo.DEVICES)
    assert rows and token not in str(rows)
    assert (await repo.find_device(store, pairing.token_fingerprint(token)))["user_id"] == "u1"


async def test_a_wrong_token_finds_no_device():
    store = InMemoryStore()
    await repo.put_device(store, pairing.token_fingerprint("right"), "u1", "Pixel")
    assert await repo.find_device(store, pairing.token_fingerprint("wrong")) is None


def test_codes_avoid_the_characters_people_mistype():
    """Read aloud across a room, I/1 and O/0 are the same character."""
    assert not set("IO01") & set(pairing.CODE_ALPHABET)
    assert len(pairing.new_code()) == pairing.CODE_LENGTH


def test_codes_are_not_predictable():
    assert len({pairing.new_code() for _ in range(200)}) > 190
