"""Where the user's Drive refresh token lives. Never Firestore (decision 8).

Two real implementations behind one interface, same pattern as Store:
``LocalTokenStore`` keeps a JSON file per user under ``.blobs/tokens``;
``SecretManagerTokenStore`` keeps one secret per user in Secret Manager.
"""

import asyncio
import contextlib
import json
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from app.config import settings

Token = dict[str, Any]


@runtime_checkable
class TokenStore(Protocol):
    async def put(self, user_id: str, token: Token) -> None: ...

    async def get(self, user_id: str) -> Token | None: ...

    async def delete(self, user_id: str) -> None: ...


class LocalTokenStore:
    def __init__(self, root: str | Path = "./.blobs/tokens"):
        self.root = Path(root)

    def _path(self, user_id: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in user_id)
        return self.root / f"{safe}.json"

    async def put(self, user_id: str, token: Token) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self._path(user_id).write_text(json.dumps(token))

    async def get(self, user_id: str) -> Token | None:
        path = self._path(user_id)
        return json.loads(path.read_text()) if path.exists() else None

    async def delete(self, user_id: str) -> None:
        self._path(user_id).unlink(missing_ok=True)


def _secret_id(user_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in user_id)
    return f"shoots-drive-token-{safe}"


class SecretManagerTokenStore:
    def __init__(self, project: str | None = None, client: Any = None):
        from google.cloud import secretmanager

        self._project = project or settings.gcp_project
        self._client = client or secretmanager.SecretManagerServiceClient()

    def _parent(self) -> str:
        return f"projects/{self._project}"

    def _name(self, user_id: str) -> str:
        return f"{self._parent()}/secrets/{_secret_id(user_id)}"

    async def put(self, user_id: str, token: Token) -> None:
        def run() -> None:
            from google.api_core.exceptions import AlreadyExists

            with contextlib.suppress(AlreadyExists):
                self._client.create_secret(
                    parent=self._parent(),
                    secret_id=_secret_id(user_id),
                    secret={"replication": {"automatic": {}}},
                )
            self._client.add_secret_version(
                parent=self._name(user_id),
                payload={"data": json.dumps(token).encode()},
            )

        await asyncio.to_thread(run)

    async def get(self, user_id: str) -> Token | None:
        def run() -> Token | None:
            from google.api_core.exceptions import NotFound

            try:
                response = self._client.access_secret_version(
                    name=f"{self._name(user_id)}/versions/latest"
                )
            except NotFound:
                return None
            return json.loads(response.payload.data.decode())

        return await asyncio.to_thread(run)

    async def delete(self, user_id: str) -> None:
        def run() -> None:
            from google.api_core.exceptions import NotFound

            with contextlib.suppress(NotFound):
                self._client.delete_secret(name=self._name(user_id))

        await asyncio.to_thread(run)
