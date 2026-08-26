"""Google ID tokens are actually signed, scoped, current, and nonce-bound."""

import json
import time
from datetime import UTC, datetime, timedelta

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi import HTTPException
from google.auth import crypt, jwt

from app.api.auth import (
    AndroidSessionIn,
    validate_android_claims,
    verify_google_id_token,
)


class CertificateResponse:
    status = 200
    headers: dict[str, str] = {}

    def __init__(self, certificates: dict[str, str]):
        self.data = json.dumps(certificates).encode()


class CertificateRequest:
    def __init__(self, certificates: dict[str, str]):
        self.certificates = certificates

    def __call__(self, _url, **_kwargs):
        return CertificateResponse(self.certificates)


def signed_token(**overrides) -> tuple[str, CertificateRequest]:
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-google")])
    at = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(at - timedelta(minutes=1))
        .not_valid_after(at + timedelta(days=1))
        .sign(private, hashes.SHA256())
    )
    private_pem = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    certificate_pem = certificate.public_bytes(serialization.Encoding.PEM).decode()
    seconds = int(time.time())
    payload = {
        "iss": "accounts.google.com",
        "aud": "android-server-client",
        "sub": "google-subject",
        "iat": seconds - 2,
        "exp": seconds + 300,
        "email": "verified@example.test",
        "email_verified": True,
        "nonce": "nonce-1",
        **overrides,
    }
    signer = crypt.RSASigner.from_string(private_pem, key_id="cert-1")
    encoded = jwt.encode(signer, payload, key_id="cert-1").decode()
    return encoded, CertificateRequest({"cert-1": certificate_pem})


def test_valid_google_identity_is_verified_cryptographically():
    encoded, request = signed_token()
    claims = verify_google_id_token(encoded, "android-server-client", request)
    assert claims["sub"] == "google-subject"
    validate_android_claims(
        claims,
        AndroidSessionIn(id_token=encoded, nonce="nonce-1", device="Xiaomi"),
    )


@pytest.mark.parametrize(
    ("overrides", "audience"),
    [
        ({"aud": "wrong-client"}, "android-server-client"),
        ({"exp": int(time.time()) - 60}, "android-server-client"),
        ({"iss": "https://attacker.example"}, "android-server-client"),
    ],
)
def test_google_identity_rejects_audience_expiry_and_issuer(overrides, audience):
    encoded, request = signed_token(**overrides)
    with pytest.raises(ValueError):
        verify_google_id_token(encoded, audience, request)


def test_google_identity_rejects_signature_and_nonce_mismatch():
    encoded, _ = signed_token()
    _, unrelated_certificates = signed_token()
    with pytest.raises(ValueError):
        verify_google_id_token(encoded, "android-server-client", unrelated_certificates)

    valid, request = signed_token()
    claims = verify_google_id_token(valid, "android-server-client", request)
    with pytest.raises(HTTPException, match="nonce"):
        validate_android_claims(
            claims,
            AndroidSessionIn(id_token=valid, nonce="other-nonce", device="Xiaomi"),
        )
