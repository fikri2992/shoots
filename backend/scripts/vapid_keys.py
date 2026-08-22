"""Print a fresh VAPID key pair as .env lines.

uv run python scripts/vapid_keys.py >> .env
"""

import base64

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid


def main() -> None:
    vapid = Vapid()
    vapid.generate_keys()
    private = vapid.private_key.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public = vapid.public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    print("VAPID_PUBLIC_KEY=" + base64.urlsafe_b64encode(public).decode().rstrip("="))
    print("VAPID_PRIVATE_KEY=" + base64.urlsafe_b64encode(private).decode().rstrip("="))


if __name__ == "__main__":
    main()
