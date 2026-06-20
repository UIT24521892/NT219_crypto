"""
Citizen Services Portal — Ed25519 QR signing service (offline verification layer).

Ed25519 produces a tiny 64-byte signature that fits inside a QR code, enabling
**offline, on-the-spot** verification of a self-contained QR (like a paper travel
permit) without contacting the server.

⚠️ Honesty note for the report/defense: Ed25519 is a **classical** algorithm — it
is NOT post-quantum. This layer is a convenience for fast offline UX only. The
real integrity + quantum resistance is provided by ML-DSA-44 (``mldsa_service``),
verified online / from PDF metadata. The QR layer could later be upgraded to
FALCON-512 (PQC, 652 B) without changing the architecture.

Interface:
    generate_keypair()                      -> (public_key_raw_32B, private_key_raw_32B)
    sign_qr(canonical: bytes, priv)         -> signature (64 B)
    verify_qr(canonical, signature, pub)    -> bool
    public_key_pem(public_key_raw)          -> str  (SubjectPublicKeyInfo PEM)
"""
from typing import Final

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.exceptions import InvalidSignature

ALGORITHM: Final[str] = "ed25519"
SIGNATURE_BYTES: Final[int] = 64
PUBLIC_KEY_BYTES: Final[int] = 32


def generate_keypair() -> tuple[bytes, bytes]:
    """Generate an Ed25519 key pair. Returns ``(public_key_raw, private_key_raw)``."""

    private_key = Ed25519PrivateKey.generate()
    private_raw = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return public_raw, private_raw


def sign_qr(canonical: bytes, private_key: bytes) -> bytes:
    """Sign the QR canonical byte-string with a raw Ed25519 private key (64-byte sig)."""

    if not isinstance(canonical, bytes):
        raise TypeError("canonical must be bytes")
    if not isinstance(private_key, bytes):
        raise TypeError("private_key must be bytes")

    signer = Ed25519PrivateKey.from_private_bytes(private_key)
    return signer.sign(canonical)


def verify_qr(canonical: bytes, signature: bytes, public_key: bytes) -> bool:
    """Verify an Ed25519 signature over the QR canonical byte-string."""

    try:
        if not isinstance(canonical, bytes) or not isinstance(signature, bytes):
            return False
        if not isinstance(public_key, bytes) or len(public_key) != PUBLIC_KEY_BYTES:
            return False

        verifier = Ed25519PublicKey.from_public_bytes(public_key)
        verifier.verify(signature, canonical)
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


def public_key_pem(public_key: bytes) -> str:
    """Return the SubjectPublicKeyInfo PEM encoding of a raw Ed25519 public key."""

    pub = Ed25519PublicKey.from_public_bytes(public_key)
    return pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
