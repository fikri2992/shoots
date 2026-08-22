"""Blob storage for images, behind the same two-implementations pattern as Store.

Paths are built in exactly one place (AGENTS.md) so originals, grid overlays and
annotated renders stay findable and a change of layout is a one-line change.
"""

from pathlib import Path
from typing import Protocol, runtime_checkable

from app.config import settings

ORIGINAL = "original"
GRIDDED = "gridded"
ANNOTATED = "annotated"
VIDEO = "video"


def blob_path(project_id: str, image_id: str, kind: str, extension: str = "png") -> str:
    """``projects/<project>/images/<image>/<kind>.png`` — stable and inspectable."""
    return f"projects/{project_id}/images/{image_id}/{kind}.{extension}"


@runtime_checkable
class BlobStore(Protocol):
    async def write(self, path: str, data: bytes, content_type: str = "image/png") -> str: ...

    async def read(self, path: str) -> bytes: ...

    async def exists(self, path: str) -> bool: ...

    async def delete(self, path: str) -> None: ...

    def public_url(self, path: str) -> str: ...


class LocalBlobStore:
    """Real files on disk. Used for local development and the test suite."""

    def __init__(self, root: str | Path = "./.blobs"):
        self.root = Path(root)

    def _full(self, path: str) -> Path:
        return self.root / path

    async def write(self, path: str, data: bytes, content_type: str = "image/png") -> str:
        target = self._full(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return path

    async def read(self, path: str) -> bytes:
        return self._full(path).read_bytes()

    async def exists(self, path: str) -> bool:
        return self._full(path).exists()

    async def delete(self, path: str) -> None:
        self._full(path).unlink(missing_ok=True)

    def public_url(self, path: str) -> str:
        """Served back through the API rather than the filesystem, so the same URL
        shape works in both environments."""
        return f"/api/blobs/{path}"


class GcsBlobStore:
    """Production storage in Google Cloud Storage."""

    def __init__(self, bucket_name: str | None = None, client=None):
        from google.cloud import storage

        self._client = client or storage.Client(project=settings.gcp_project or None)
        self._bucket = self._client.bucket(bucket_name or settings.gcs_bucket)

    async def write(self, path: str, data: bytes, content_type: str = "image/png") -> str:
        import asyncio

        blob = self._bucket.blob(path)
        await asyncio.to_thread(blob.upload_from_string, data, content_type=content_type)
        return path

    async def read(self, path: str) -> bytes:
        import asyncio

        return await asyncio.to_thread(self._bucket.blob(path).download_as_bytes)

    async def exists(self, path: str) -> bool:
        import asyncio

        return await asyncio.to_thread(self._bucket.blob(path).exists)

    async def delete(self, path: str) -> None:
        import asyncio
        import contextlib

        from google.cloud.exceptions import NotFound

        with contextlib.suppress(NotFound):
            await asyncio.to_thread(self._bucket.blob(path).delete)

    def public_url(self, path: str) -> str:
        return f"/api/blobs/{path}"
