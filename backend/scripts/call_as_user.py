"""Call the running dev server as the signed-in user, from the shell.

    uv run python scripts/call_as_user.py GET /api/me
    uv run python scripts/call_as_user.py POST /api/quests/<id>/skip

Mints the session cookie the way the app does (SESSION_SECRET from .env)
for the first user in the dev store and prints only the response. Unlike the
check_* scripts this never writes store.json, so it is safe while the server
is up. Dev only: the cookie never leaves this process.
"""

import asyncio
import base64
import json
import sys

import httpx
from itsdangerous import TimestampSigner

from app.api.auth import SESSION_USER_KEY
from app.config import settings
from app.infra import repository as repo
from app.infra.store import FileStore

BASE = "http://127.0.0.1:8000"


def cookie_for(user: dict) -> str:
    payload = base64.b64encode(json.dumps({SESSION_USER_KEY: user}).encode())
    return TimestampSigner(settings.session_secret).sign(payload).decode()


async def main(method: str, path: str, body: str | None) -> None:
    store = FileStore(settings.blob_root + "/store.json")
    users = await repo.list_users(store)
    if not users:
        raise SystemExit("no users in the store")
    user = users[0]
    # Git Bash rewrites a leading "/api/..." argument into a Windows path; pass
    # "api/..." and let this add the slash.
    path = "/" + path.lstrip("/")
    cookies = {"session": cookie_for({"id": user.id, "email": user.email, "name": user.name})}
    async with httpx.AsyncClient(
        base_url=BASE, cookies=cookies, timeout=300, trust_env=False
    ) as client:
        response = await client.request(
            method.upper(), path, content=body, headers={"Content-Type": "application/json"}
        )
    print(response.status_code)
    text = response.text
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False)[:40000])
    except ValueError:
        print(text[:2000])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
