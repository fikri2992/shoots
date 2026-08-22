"""Upload local files into the user's connected Shoots folder, as the user.

    uv run python scripts/check_drive_upload.py <folder_id> <file> [<file> ...]

Uses the refresh token LocalTokenStore saved at sign-in (first token file
found), the same UserDrive.upload the PWA Shoot button will use. Then call
POST /drive/sync and the service-account reader should pick the files up.
"""

import asyncio
import json
import mimetypes
import sys
from pathlib import Path

from app.infra.drive import UserDrive, user_credentials


async def main(folder_id: str, paths: list[str]) -> None:
    tokens = sorted(Path(".blobs/tokens").glob("*.json"))
    if not tokens:
        raise SystemExit("no token in .blobs/tokens; sign in first")
    token = json.loads(tokens[0].read_text())
    drive = UserDrive(user_credentials(token))
    for raw in paths:
        path = Path(raw)
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        file_id = await drive.upload(folder_id, path.name, path.read_bytes(), mime)
        print(f"uploaded {path.name} ({path.stat().st_size // 1000} KB, {mime}) -> {file_id}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    asyncio.run(main(sys.argv[1], sys.argv[2:]))
