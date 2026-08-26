"""Account deletion through authenticated HTTP and the real local adapters."""

import httpx

from app.api import auth, deps, main, pairing
from app.domain.entities import Shot, ShotKind, ShotSource, User
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.secrets import LocalTokenStore
from app.infra.storage import ORIGINAL, LocalBlobStore, blob_path
from app.infra.store import InMemoryStore
from app.services import account as account_service
from app.services.context import Context


async def test_delete_account_revokes_devices_records_tokens_and_blobs(tmp_path):
    store = InMemoryStore()
    blobs = LocalBlobStore(tmp_path / "blobs")
    tokens = LocalTokenStore(tmp_path / "tokens")
    bus = InProcessBus()
    ctx = Context(store=store, blobs=blobs, bus=bus, drive=None, tokens=tokens)
    user = User(id="delete-user", email="delete@example.test")
    await repo.put_user(store, user)
    token = "device-token"
    await repo.put_device(store, pairing.token_fingerprint(token), user.id, "Xiaomi")
    await tokens.put(user.id, {"refresh_token": "stored-server-side"})
    original = blob_path(user.id, "shot-delete", ORIGINAL, "jpg")
    await blobs.write(original, b"jpeg", "image/jpeg")
    await repo.put_shot(
        store,
        Shot(
            id="shot-delete",
            user_id=user.id,
            kind=ShotKind.PHOTO,
            source=ShotSource.ANDROID,
            filename="delete.jpg",
            mime_type="image/jpeg",
            blobs={ORIGINAL: original},
        ),
    )

    async def verified_claims(body: auth.AndroidSessionIn) -> dict:
        return {
            "sub": user.id,
            "email": user.email,
            "email_verified": True,
            "nonce": body.nonce,
        }

    deps.wire(ctx)
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[auth.verify_android_token] = verified_claims
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=main.app),
            base_url="http://test",
        ) as client:
            deleted = await client.request(
                "DELETE",
                "/api/account",
                headers={"Authorization": f"Bearer {token}"},
                json={"id_token": "verified-by-adapter", "nonce": "delete", "device": "Xiaomi"},
            )
            assert deleted.status_code == 202, deleted.text
        await bus.drain()
    finally:
        main.app.dependency_overrides.clear()

    assert await repo.find_user(store, user.id) is None
    assert await repo.list_shots(store, user.id) == []
    assert await repo.list_devices(store, user.id) == []
    assert await tokens.get(user.id) is None
    assert not await blobs.exists(original)
    await account_service.delete(ctx, user.id)


async def test_delete_account_rejects_fresh_identity_for_another_google_sub(tmp_path):
    store = InMemoryStore()
    ctx = Context(
        store=store,
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=LocalTokenStore(tmp_path / "tokens"),
    )
    user = User(id="kept-user", email="kept@example.test")
    token = "kept-device-token"
    await repo.put_user(store, user)
    await repo.put_device(store, pairing.token_fingerprint(token), user.id, "Xiaomi")

    async def other_identity(body: auth.AndroidSessionIn) -> dict:
        return {
            "sub": "different-google-sub",
            "email": "other@example.test",
            "email_verified": True,
            "nonce": body.nonce,
        }

    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[auth.verify_android_token] = other_identity
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=main.app), base_url="http://test"
        ) as client:
            response = await client.request(
                "DELETE",
                "/api/account",
                headers={"Authorization": f"Bearer {token}"},
                json={"id_token": "other", "nonce": "fresh", "device": "Xiaomi"},
            )
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 409
    assert await repo.find_user(store, user.id) is not None
    assert await repo.list_devices(store, user.id)
