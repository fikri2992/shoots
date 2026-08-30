"""Google Drive behind a small interface, with two real implementations.

* ``GoogleDriveClient`` — the service account reads the folder the user shared
  with it. On Cloud Run the service identity *is* that account; locally the
  developer's ADC impersonates it (``settings.drive_service_account``).
* ``LocalDriveClient`` — a directory on disk is the folder. Runs the pipeline
  with no Google at all, which is how the test suite and ``scripts/check_*``
  exercise Ingest against real files.

The user-side operations (create the folder, share it) use the user's own
``drive.file`` token, which only ever touches files this app created. They live
in ``UserDrive`` because they need different credentials from the reader.
"""

import asyncio
import hashlib
import io
import mimetypes
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from app.config import settings
from app.domain.entities import DriveChannel

FOLDER_MIME = "application/vnd.google-apps.folder"
READ_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
#: Only these land in the pipeline; Drive folders collect all sorts of things.
MEDIA_PREFIXES = ("image/", "video/")
FIELDS = "id,name,mimeType,size,modifiedTime,md5Checksum"


@dataclass(frozen=True)
class DriveFile:
    id: str
    name: str
    mime_type: str
    size: int
    modified_at: datetime

    @property
    def is_media(self) -> bool:
        return self.mime_type.startswith(MEDIA_PREFIXES)


@runtime_checkable
class DriveClient(Protocol):
    async def list_media(self, folder_id: str) -> list[DriveFile]: ...

    async def get_file(self, file_id: str) -> DriveFile: ...

    async def download(self, file_id: str) -> bytes: ...

    async def watch(
        self, folder_id: str, channel_id: str, address: str, token: str, hours: int
    ) -> DriveChannel | None: ...

    async def stop(self, channel_id: str, resource_id: str) -> None: ...


# --- local -----------------------------------------------------------------


class LocalDriveClient:
    """A directory as a Drive folder. File ids are content hashes so a renamed
    file is still the same shot, matching Drive's stable ids."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def _index(self) -> dict[str, Path]:
        files = sorted(p for p in self.root.iterdir() if p.is_file())
        return {self._id_for(p): p for p in files}

    @staticmethod
    def _id_for(path: Path) -> str:
        digest = hashlib.sha1(path.read_bytes()).hexdigest()[:24]
        return f"local_{digest}"

    async def list_media(self, folder_id: str) -> list[DriveFile]:
        # folder_id is accepted for interface parity; the root is the folder.
        out = []
        for file_id, path in self._index().items():
            mime = mimetypes.guess_type(path.name)[0] or ""
            if not mime.startswith(MEDIA_PREFIXES):
                continue
            stat = path.stat()
            out.append(
                DriveFile(
                    id=file_id,
                    name=path.name,
                    mime_type=mime,
                    size=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
                )
            )
        return out

    async def get_file(self, file_id: str) -> DriveFile:
        path = self._index().get(file_id)
        if path is None:
            raise FileNotFoundError(file_id)
        mime = mimetypes.guess_type(path.name)[0] or ""
        stat = path.stat()
        return DriveFile(
            id=file_id,
            name=path.name,
            mime_type=mime,
            size=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
        )

    async def download(self, file_id: str) -> bytes:
        path = self._index().get(file_id)
        if path is None:
            raise FileNotFoundError(file_id)
        return path.read_bytes()

    async def watch(
        self, folder_id: str, channel_id: str, address: str, token: str, hours: int
    ) -> DriveChannel | None:
        return None  # a directory does not call back; /tasks/sync polls it

    async def stop(self, channel_id: str, resource_id: str) -> None:
        return None


# --- google ----------------------------------------------------------------


def reader_credentials() -> Any:
    """Credentials for the service account that reads shared folders.

    On Cloud Run ADC already *is* the service account. On a dev machine ADC is
    the developer's user account, so it impersonates the service account; that
    needs ``roles/iam.serviceAccountTokenCreator`` on it, granted in day 1.
    """
    import google.auth
    from google.auth import impersonated_credentials
    from google.oauth2.credentials import Credentials as UserCredentials

    source, _ = google.auth.default()
    if isinstance(source, UserCredentials) and settings.drive_service_account:
        return impersonated_credentials.Credentials(
            source_credentials=source,
            target_principal=settings.drive_service_account,
            target_scopes=READ_SCOPES,
            lifetime=3600,
        )
    # Service-account ADC: scope it for Drive.
    if hasattr(source, "with_scopes"):
        return source.with_scopes(READ_SCOPES)
    return source


def _service(credentials: Any) -> Any:
    from googleapiclient.discovery import build

    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def _to_drive_file(item: dict) -> DriveFile:
    modified = item.get("modifiedTime", "1970-01-01T00:00:00Z").replace("Z", "+00:00")
    return DriveFile(
        id=item["id"],
        name=item.get("name", ""),
        mime_type=item.get("mimeType", ""),
        size=int(item.get("size", 0) or 0),
        modified_at=datetime.fromisoformat(modified),
    )


class GoogleDriveClient:
    def __init__(self, credentials: Any = None):
        self._credentials = credentials

    def _svc(self) -> Any:
        if self._credentials is None:
            self._credentials = reader_credentials()
        return _service(self._credentials)

    async def list_media(self, folder_id: str) -> list[DriveFile]:
        def run() -> list[DriveFile]:
            svc = self._svc()
            out: list[DriveFile] = []
            token = None
            while True:
                resp = (
                    svc.files()
                    .list(
                        q=f"'{folder_id}' in parents and trashed = false",
                        fields=f"nextPageToken, files({FIELDS})",
                        pageSize=200,
                        pageToken=token,
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                    )
                    .execute()
                )
                out.extend(_to_drive_file(f) for f in resp.get("files", []))
                token = resp.get("nextPageToken")
                if not token:
                    return [f for f in out if f.is_media]

        return await asyncio.to_thread(run)

    async def get_file(self, file_id: str) -> DriveFile:
        def run() -> DriveFile:
            item = (
                self._svc()
                .files()
                .get(fileId=file_id, fields=FIELDS, supportsAllDrives=True)
                .execute()
            )
            return _to_drive_file(item)

        return await asyncio.to_thread(run)

    async def download(self, file_id: str) -> bytes:
        def run() -> bytes:
            from googleapiclient.http import MediaIoBaseDownload

            svc = self._svc()
            request = svc.files().get_media(fileId=file_id, supportsAllDrives=True)
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request, chunksize=8 * 1024 * 1024)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            return buffer.getvalue()

        return await asyncio.to_thread(run)

    async def watch(
        self, folder_id: str, channel_id: str, address: str, token: str, hours: int
    ) -> DriveChannel | None:
        """Ask Drive to POST to ``address`` when the folder's children change.

        Drive caps a files.watch channel at one day; the caller renews."""

        def run() -> DriveChannel:
            expiration_ms = int((time.time() + hours * 3600) * 1000)
            body = {
                "id": channel_id,
                "type": "web_hook",
                "address": address,
                "token": token,
                "expiration": str(expiration_ms),
            }
            resp = (
                self._svc()
                .files()
                .watch(fileId=folder_id, body=body, supportsAllDrives=True)
                .execute()
            )
            expires_ms = int(resp.get("expiration", expiration_ms))
            return DriveChannel(
                channel_id=resp.get("id", channel_id),
                resource_id=resp["resourceId"],
                expires_at=datetime.fromtimestamp(expires_ms / 1000, tz=UTC),
            )

        return await asyncio.to_thread(run)

    async def stop(self, channel_id: str, resource_id: str) -> None:
        def run() -> None:
            self._svc().channels().stop(
                body={"id": channel_id, "resourceId": resource_id}
            ).execute()

        await asyncio.to_thread(run)


class UserDrive:
    """What the app does *as the user* with ``drive.file``: make the folder and
    hand the reader access to it. Nothing else, ever."""

    def __init__(self, credentials: Any):
        self._credentials = credentials

    async def get_file(self, file_id: str) -> DriveFile:
        """Canonical metadata for one file explicitly granted through Picker."""

        def run() -> DriveFile:
            item = (
                _service(self._credentials)
                .files()
                .get(fileId=file_id, fields=FIELDS, supportsAllDrives=True)
                .execute()
            )
            return _to_drive_file(item)

        return await asyncio.to_thread(run)

    async def download(self, file_id: str) -> bytes:
        """Download only a file the app created or the user selected in Picker."""

        def run() -> bytes:
            from googleapiclient.http import MediaIoBaseDownload

            request = (
                _service(self._credentials)
                .files()
                .get_media(
                    fileId=file_id,
                    supportsAllDrives=True,
                )
            )
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request, chunksize=8 * 1024 * 1024)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            return buffer.getvalue()

        return await asyncio.to_thread(run)

    async def create_folder(self, name: str, parent_id: str = "") -> str:
        def run() -> str:
            svc = _service(self._credentials)
            body: dict[str, Any] = {"name": name, "mimeType": FOLDER_MIME}
            if parent_id:
                body["parents"] = [parent_id]
            created = svc.files().create(body=body, fields="id").execute()
            return created["id"]

        return await asyncio.to_thread(run)

    async def update(self, file_id: str, name: str = "", description: str = "") -> None:
        """Rename and/or re-caption a file the app created."""

        def run() -> None:
            body: dict[str, Any] = {}
            if name:
                body["name"] = name
            if description:
                body["description"] = description
            if body:
                _service(self._credentials).files().update(
                    fileId=file_id, body=body, fields="id"
                ).execute()

        await asyncio.to_thread(run)

    async def share_with(self, folder_id: str, email: str, role: str = "reader") -> None:
        def run() -> None:
            svc = _service(self._credentials)
            svc.permissions().create(
                fileId=folder_id,
                body={"type": "user", "role": role, "emailAddress": email},
                sendNotificationEmail=False,
                fields="id",
            ).execute()

        await asyncio.to_thread(run)

    async def unshare_with(self, folder_id: str, email: str) -> None:
        """Remove only the reader permission Shoots previously created."""

        def run() -> None:
            svc = _service(self._credentials)
            permissions = (
                svc.permissions()
                .list(
                    fileId=folder_id,
                    fields="permissions(id,emailAddress,type)",
                )
                .execute()
                .get("permissions", [])
            )
            for permission in permissions:
                if permission.get("type") == "user" and permission.get("emailAddress") == email:
                    svc.permissions().delete(
                        fileId=folder_id,
                        permissionId=permission["id"],
                    ).execute()

        await asyncio.to_thread(run)

    async def upload(
        self, folder_id: str, name: str, data: bytes, mime_type: str, description: str = ""
    ) -> str:
        """The PWA Shoot button and the Scribe's reviews. Files the app uploads
        are visible to both the user token (drive.file) and the reader."""

        def run() -> str:
            from googleapiclient.http import MediaIoBaseUpload

            svc = _service(self._credentials)
            media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime_type, resumable=False)
            body: dict[str, Any] = {"name": name, "parents": [folder_id]}
            if description:
                body["description"] = description
            created = svc.files().create(body=body, media_body=media, fields="id").execute()
            return created["id"]

        return await asyncio.to_thread(run)


def user_credentials(token: dict) -> Any:
    """Build google-auth credentials from the OAuth token authlib handed us."""
    from google.oauth2.credentials import Credentials

    granted_scopes = str(token.get("scope", "")).split() or None
    return Credentials(
        token=token.get("access_token"),
        refresh_token=token.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=granted_scopes,
    )


async def picker_access_token(token: dict) -> str:
    """Return a fresh, short-lived drive.file token for Google Picker."""
    credentials = user_credentials(token)
    if credentials.refresh_token:
        from google.auth.transport.requests import Request

        await asyncio.to_thread(credentials.refresh, Request())
    if not credentials.token:
        raise ValueError("Google returned no Drive access token")
    return credentials.token
