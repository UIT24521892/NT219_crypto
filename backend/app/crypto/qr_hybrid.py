"""
Self-contained hybrid QR payload (offline Ed25519 verification).

The QR encodes a pipe-delimited, self-contained string — NOT a URL — so it can
be verified offline at the point of scan (like a paper travel permit):

    payload  = b64url(qr_signature) | <canonical>
    canonical = doc_id | file_hash | signer_email | signed_at | valid_from
                | valid_until | qr_public_key_ref

The Ed25519 signature is computed over the UTF-8 bytes of ``canonical``. Because
the payload is just ``signature | canonical``, a verifier rebuilds the signed
bytes by dropping the first field and re-joining the rest — no date re-formatting,
no re-encoding — guaranteeing a byte-for-byte match between signer and verifier
(server Python and client JS alike).

Delimiter ``|`` is safe: UUIDs, hex hashes, ISO-8601 timestamps, email addresses
and ``<alg>:<fp>`` key ids cannot contain it; builders reject any field that does.
"""
import base64
from datetime import datetime, timezone
from typing import Final

QR_SIG_ALGORITHM: Final[str] = "ed25519"
FIELD_SEP: Final[str] = "|"


def iso_utc(value: datetime) -> str:
    """Deterministic UTC ISO-8601 at seconds resolution (e.g. 2026-06-20T10:30:00+00:00)."""

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def b64url_encode(data: bytes) -> str:
    """Unpadded URL-safe Base64."""
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def b64url_decode(value: str) -> bytes:
    """Decode unpadded URL-safe Base64."""
    padded = value + ("=" * (-len(value) % 4))
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _field(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if FIELD_SEP in value:
        raise ValueError(f"{name} must not contain {FIELD_SEP!r}")
    return value


def build_qr_canonical(
    *,
    doc_id: str,
    file_hash: str,
    signer_email: str,
    signed_at: datetime,
    valid_from: datetime,
    valid_until: datetime,
    qr_public_key_ref: str,
) -> bytes:
    """Build the deterministic canonical byte-string that Ed25519 signs."""

    fields = [
        _field(doc_id, "doc_id"),
        _field(file_hash, "file_hash"),
        _field(signer_email, "signer_email"),
        iso_utc(signed_at),
        iso_utc(valid_from),
        iso_utc(valid_until),
        _field(qr_public_key_ref, "qr_public_key_ref"),
    ]
    return FIELD_SEP.join(fields).encode("utf-8")


def build_qr_payload(
    *,
    qr_signature: bytes,
    doc_id: str,
    file_hash: str,
    signer_email: str,
    signed_at: datetime,
    valid_from: datetime,
    valid_until: datetime,
    qr_public_key_ref: str,
) -> str:
    """Build the full self-contained QR string: ``b64url(sig) | <canonical>``."""

    if not isinstance(qr_signature, bytes) or not qr_signature:
        raise ValueError("qr_signature is required")
    canonical = build_qr_canonical(
        doc_id=doc_id,
        file_hash=file_hash,
        signer_email=signer_email,
        signed_at=signed_at,
        valid_from=valid_from,
        valid_until=valid_until,
        qr_public_key_ref=qr_public_key_ref,
    ).decode("utf-8")
    return FIELD_SEP.join([b64url_encode(qr_signature), canonical])


def signature_from_payload(payload: str) -> bytes:
    """Extract and decode the Ed25519 signature (first field) from a QR payload."""

    sig_field = payload.split(FIELD_SEP, 1)[0]
    return b64url_decode(sig_field)


def canonical_from_payload(payload: str) -> bytes:
    """Reconstruct the signed canonical bytes (everything after the signature field)."""

    _, sep, rest = payload.partition(FIELD_SEP)
    if not sep:
        raise ValueError("payload missing canonical section")
    return rest.encode("utf-8")
