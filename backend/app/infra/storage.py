"""Blob storage for shots, behind the same two-implementations pattern as Store.

Paths are built in exactly one place so originals, gridded frames, contact
sheets and thumbnails stay findable, and the blob API can check that a path
belongs to the signed-in user by prefix alone.
"""

from pathlib import Path
from typing import BinaryIO, Protocol, runtime_checkable
from urllib.parse import quote

from app.config import settings

#: The media types the pipeline stores, and the extension each is written with.
#: The extension is the only carrier of the content type once a blob is on disk:
#: the blob endpoint has a path, not a Shot. Anything absent here is stored as
#: ``.bin`` and sniffed on read.
EXTENSIONS: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/avif": "avif",
    "image/gif": "gif",
    "image/heic": "heic",
    "image/heif": "heif",
    "video/mp4": "mp4",
    "video/quicktime": "mov",
}
CONTENT_TYPES: dict[str, str] = {ext: mime for mime, ext in EXTENSIONS.items()}
CONTENT_TYPES["jpeg"] = "image/jpeg"
OCTET_STREAM = "application/octet-stream"

#: Leading bytes that identify a format, for blobs whose extension says nothing.
#: ISO base media files (mp4, avif, heic) share the ``ftyp`` box at offset 4 and
#: are told apart by the brand that follows it.
_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (bytes.fromhex("ffd8ff"), "image/jpeg"),
    (bytes.fromhex("89504e470d0a1a0a"), "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)
_BRANDS: tuple[tuple[bytes, str], ...] = (
    (b"avif", "image/avif"),
    (b"avis", "image/avif"),
    (b"heic", "image/heic"),
    (b"heix", "image/heic"),
    (b"mif1", "image/heif"),
    (b"qt  ", "video/quicktime"),
)

ORIGINAL = "original"
GRIDDED = "gridded"
SHEET = "sheet"
THUMB = "thumb"
ANNOTATED = "annotated"
FINDING_MARKED = "finding_marked"
CROP = "crop"  # the crop that won the crop loop, as a finished frame
CLIP = "clip"


def extension_for(mime_type: str) -> str:
    """The extension a blob of this media type is written with."""
    return EXTENSIONS.get((mime_type or "").split(";", 1)[0].strip().lower(), "bin")


def sniff(data: bytes) -> str:
    """The media type of these bytes, or the octet stream when unrecognised."""
    for signature, mime in _SIGNATURES:
        if data.startswith(signature):
            return mime
    if len(data) >= 12 and data[4:8] == b"ftyp":
        brand = data[8:12]
        for candidate, mime in _BRANDS:
            if brand == candidate:
                return mime
        return "video/mp4"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return OCTET_STREAM


def content_type_for(path: str, data: bytes = b"") -> str:
    """The type to serve a stored blob as. The extension decides; when it says
    nothing (older blobs written before ``EXTENSIONS`` covered their format) the
    bytes do."""
    extension = path.rsplit(".", 1)[-1].lower()
    mime = CONTENT_TYPES.get(extension)
    if mime:
        return mime
    return sniff(data) if data else OCTET_STREAM


def user_prefix(user_id: str) -> str:
    # Dev identities contain ``:`` and emails contain characters Windows will
    # not accept in a directory name. Production Google subjects are unchanged.
    return f"users/{quote(user_id, safe='')}/"


def requested_user_path(user_id: str, path: str) -> str:
    """Map FastAPI's decoded path back to the encoded storage prefix."""
    stored = user_prefix(user_id)
    if path.startswith(stored):
        return path
    decoded = f"users/{user_id}/"
    if path.startswith(decoded):
        return stored + path.removeprefix(decoded)
    return ""


def blob_path(user_id: str, shot_id: str, kind: str, extension: str = "png") -> str:
    """``users/<user>/shots/<shot>/<kind>.<ext>`` — stable and inspectable."""
    return f"{user_prefix(user_id)}shots/{shot_id}/{kind}.{extension}"


def experiment_blob_path(
    user_id: str, experiment_id: str, kind: str, extension: str = "mp4"
) -> str:
    return f"{user_prefix(user_id)}experiments/{experiment_id}/{kind}.{extension}"


@runtime_checkable
class BlobStore(Protocol):
    async def write(self, path: str, data: bytes, content_type: str = "image/png") -> str: ...

    async def write_file(
        self, path: str, source: BinaryIO, content_type: str = "image/png"
    ) -> str: ...

    async def read(self, path: str) -> bytes: ...

    async def exists(self, path: str) -> bool: ...

    async def delete(self, path: str) -> None: ...

    async def delete_prefix(self, prefix: str) -> None: ...

    def public_url(self, path: str) -> str: ...


class LocalBlobStore:
    """Real files on disk. Used for local development and the test suite."""

    def __init__(self, root: str | Path | None = None):
        self.root = Path(root or settings.blob_root)

    def _full(self, path: str) -> Path:
        return self.root / path

    async def write(self, path: str, data: bytes, content_type: str = "image/png") -> str:
        target = self._full(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return path

    async def write_file(self, path: str, source: BinaryIO, content_type: str = "image/png") -> str:
        import asyncio
        import os
        import shutil
        import tempfile

        target = self._full(path)
        target.parent.mkdir(parents=True, exist_ok=True)

        def copy() -> None:
            source.seek(0)
            descriptor, temporary_name = tempfile.mkstemp(
                dir=target.parent, prefix=f".{target.name}.", suffix=".upload"
            )
            try:
                with os.fdopen(descriptor, "wb") as temporary:
                    shutil.copyfileobj(source, temporary, length=1024 * 1024)
                os.replace(temporary_name, target)
            finally:
                Path(temporary_name).unlink(missing_ok=True)

        await asyncio.to_thread(copy)
        return path

    async def read(self, path: str) -> bytes:
        return self._full(path).read_bytes()

    async def exists(self, path: str) -> bool:
        return self._full(path).exists()

    async def delete(self, path: str) -> None:
        self._full(path).unlink(missing_ok=True)

    async def delete_prefix(self, prefix: str) -> None:
        import shutil

        root = self.root.resolve()
        target = self._full(prefix).resolve()
        if not prefix or target == root or not target.is_relative_to(root):
            raise ValueError("refusing to delete an unsafe blob prefix")
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()

    def public_url(self, path: str) -> str:
        """Served back through the API so the same URL shape works everywhere."""
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

    async def write_file(self, path: str, source: BinaryIO, content_type: str = "image/png") -> str:
        import asyncio

        blob = self._bucket.blob(path)
        await asyncio.to_thread(
            blob.upload_from_file,
            source,
            content_type=content_type,
            rewind=True,
        )
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

    async def delete_prefix(self, prefix: str) -> None:
        import asyncio

        if not prefix:
            raise ValueError("refusing to delete an empty GCS prefix")

        def remove() -> None:
            for blob in self._client.list_blobs(self._bucket, prefix=prefix):
                blob.delete()

        await asyncio.to_thread(remove)

    def public_url(self, path: str) -> str:
        return f"/api/blobs/{path}"
