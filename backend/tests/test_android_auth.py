"""Native Google identity and revocable device sessions through HTTP."""

from datetime import timedelta

from fastapi.testclient import TestClient

from app.api import auth, deps, main, pairing
from app.domain.entities import User, now
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.storage import LocalBlobStore
from app.infra.store import InMemoryStore
from app.services.context import Context


async def test_android_google_identity_issues_and_revokes_a_device_session(tmp_path):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )

    async def verified_claims(body: auth.AndroidSessionIn) -> dict:
        assert body.nonce == "nonce-123"
        return {
            "sub": "google-user-1",
            "email": "android@example.test",
            "email_verified": True,
            "name": "Android Photographer",
            "picture": "https://example.test/avatar.jpg",
            "nonce": body.nonce,
        }

    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[auth.verify_android_token] = verified_claims
    try:
        with TestClient(main.app) as client:
            signed_in = client.post(
                "/auth/android/session",
                json={
                    "id_token": "cryptographically-checked-by-adapter",
                    "nonce": "nonce-123",
                    "device": "Xiaomi 14T",
                },
            )
            assert signed_in.status_code == 201, signed_in.text
            token = signed_in.json()["token"]
            headers = {"Authorization": f"Bearer {token}"}

            me = client.get("/api/me", headers=headers)
            assert me.status_code == 200, me.text
            assert me.json()["id"] == "google-user-1"
            assert me.json()["email"] == "android@example.test"

            notifications = client.put(
                "/api/devices/current/notifications",
                headers=headers,
                json={"target": "firebase-installation-1"},
            )
            assert notifications.status_code == 204, notifications.text
            devices = await repo.list_devices(ctx.store, "google-user-1")
            assert devices[0]["notification_target"] == "firebase-installation-1"

            revoked = client.delete("/api/devices/current", headers=headers)
            assert revoked.status_code == 204, revoked.text
            assert client.get("/api/me", headers=headers).status_code == 401
    finally:
        main.app.dependency_overrides.clear()


async def test_expired_device_session_is_rejected_and_removed(tmp_path):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user = User(id="expired-user", email="expired@example.test")
    await repo.put_user(ctx.store, user)
    token = "expired-device-token"
    fingerprint = pairing.token_fingerprint(token)
    await repo.put_device(
        ctx.store,
        fingerprint,
        user.id,
        "Old Android",
        expires_at=now() - timedelta(seconds=1),
        auth_method="google",
    )
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    try:
        with TestClient(main.app) as client:
            response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    finally:
        main.app.dependency_overrides.clear()
    assert response.status_code == 401
    assert await repo.find_device(ctx.store, fingerprint) is None
