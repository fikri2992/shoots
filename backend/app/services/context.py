"""What every service stage needs, passed explicitly. No globals in services."""

from dataclasses import dataclass

from app.infra.bus import Bus
from app.infra.drive import DriveClient
from app.infra.mobile_push import MobilePush
from app.infra.secrets import TokenStore
from app.infra.storage import BlobStore
from app.infra.store import Store


@dataclass
class Context:
    store: Store
    blobs: BlobStore
    bus: Bus
    drive: DriveClient
    tokens: TokenStore
    mobile_push: MobilePush | None = None
