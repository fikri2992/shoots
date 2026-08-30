"""Native Drive authority is separate from identity and account-matched."""

from fastapi.testclient import TestClient

from app.api import deps, drive_auth, main
from app.api.auth import current_user
from app.config import settings
from app.domain.entities import User
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.drive import user_credentials
from app.infra.secrets import LocalTokenStore
from app.infra.storage import LocalBlobStore
from app.infra.store import InMemoryStore
from app.services.context import Context


def test_user_credentials_refresh_with_the_tokens_granted_scopes(monkeypatch):
    drive_scope = "https://www.googleapis.com/auth/drive.file"
    stored_scopes = f"https://www.googleapis.com/auth/userinfo.email openid {drive_scope}"
    monkeypatch.setattr(
        settings,
        "oauth_scopes",
        f"openid email profile {drive_scope}",
    )

    credentials = user_credentials(
        {
            "access_token": "short-lived",
            "refresh_token": "refresh-token",
            "scope": stored_scopes,
        }
    )

    assert credentials.scopes == stored_scopes.split()


async def test_native_drive_code_must_match_and_disconnect_preserves_files(tmp_path, monkeypatch):
    tokens = LocalTokenStore(tmp_path / "tokens")
    folder = tmp_path / "drive"
    folder.mkdir()
    owned_file = folder / "keeper.jpg"
    owned_file.write_bytes(b"owned by photographer")
    monkeypatch.setattr(settings, "drive_local_folder", str(folder))
    user_id = "google-sub-1"
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=tokens,
    )
    await repo.put_user(ctx.store, User(id=user_id, email="drive@example.test"))
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user_id}

    async def wrong_account() -> dict:
        return {
            "token": {"refresh_token": "refresh-wrong"},
            "claims": {"sub": "other-google-sub"},
        }

    main.app.dependency_overrides[drive_auth.exchange_drive_code] = wrong_account
    try:
        with TestClient(main.app) as client:
            mismatch = client.post("/api/drive/authorization-code", json={"code": "offline-code"})
            assert mismatch.status_code == 409, mismatch.text
            assert await tokens.get(user_id) is None

            async def matching_account() -> dict:
                return {
                    "token": {
                        "refresh_token": "refresh-right",
                        "access_token": "short-lived",
                        "scope": "drive.file",
                    },
                    "claims": {"sub": user_id},
                }

            main.app.dependency_overrides[drive_auth.exchange_drive_code] = matching_account
            connected = client.post("/api/drive/authorization-code", json={"code": "offline-code"})
            assert connected.status_code == 200, connected.text
            assert (await tokens.get(user_id))["refresh_token"] == "refresh-right"

            disconnected = client.delete("/api/drive")
            assert disconnected.status_code == 204, disconnected.text
            assert await tokens.get(user_id) is None
            assert owned_file.read_bytes() == b"owned by photographer"
            assert (await repo.get_user(ctx.store, user_id)).drive_folder_id == ""
    finally:
        main.app.dependency_overrides.clear()
