"""Compact QR payload encoding for offline document verification."""

from __future__ import annotations

import base64
import binascii
import json
import re
import time
from typing import Any, Final


QR_PAYLOAD_VERSION: Final[int] = 1
QR_ALGORITHM: Final[str] = "FALCON-512"
REQUIRED_FIELDS: Final[set[str]] = {"v", "id", "h", "s", "ts", "ex", "alg"}
_B64URL_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9_-]*$")


def _validate_hash_hex(doc_hash_hex: str) -> str:
    if not isinstance(doc_hash_hex, str):
        raise TypeError("doc_hash_hex must be a string")
    try:
        digest = bytes.fromhex(doc_hash_hex)
    except ValueError as exc:
        raise ValueError("doc_hash_hex must be valid hexadecimal") from exc
    if len(digest) != 32:
        raise ValueError("doc_hash_hex must be a SHA-256 hex digest")
    return digest.hex()


def b64url_encode(data: bytes) -> str:
    """Encode bytes as unpadded URL-safe Base64."""

    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")

    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(data: str) -> bytes:
    """Decode unpadded URL-safe Base64 by restoring the required padding."""

    if not isinstance(data, str):
        raise TypeError("data must be a string")
    if not _B64URL_RE.fullmatch(data):
        raise ValueError("data must be unpadded base64url")

    padded = data + ("=" * (-len(data) % 4))
    try:
        return base64.b64decode(padded.encode("ascii"), altchars=b"-_", validate=True)
    except (binascii.Error, UnicodeEncodeError) as exc:
        raise ValueError("data must be valid base64url") from exc


def build_payload(
    doc_id: str,
    doc_hash_hex: str,
    signature: bytes,
    issued_at: int | None = None,
    expires_at: int | None = None,
    ttl_seconds: int = 365 * 24 * 60 * 60,
    algorithm: str = QR_ALGORITHM,
) -> str:
    """Build a compact deterministic JSON payload for a document QR code."""

    if not isinstance(doc_id, str) or not doc_id:
        raise ValueError("doc_id must be a non-empty string")
    if not isinstance(signature, bytes):
        raise TypeError("signature must be bytes")
    if not isinstance(algorithm, str) or not algorithm:
        raise ValueError("algorithm must be a non-empty string")
    if not isinstance(ttl_seconds, int) or ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be a positive integer")

    timestamp = int(time.time()) if issued_at is None else issued_at
    if not isinstance(timestamp, int):
        raise TypeError("issued_at must be an integer")

    expiry = timestamp + ttl_seconds if expires_at is None else expires_at
    if not isinstance(expiry, int):
        raise TypeError("expires_at must be an integer")
    if expiry <= timestamp:
        raise ValueError("expires_at must be after issued_at")

    payload = {
        "v": QR_PAYLOAD_VERSION,
        "id": doc_id,
        "h": _validate_hash_hex(doc_hash_hex),
        "s": b64url_encode(signature),
        "ts": timestamp,
        "ex": expiry,
        "alg": algorithm,
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def parse_payload(payload_json: str) -> dict[str, Any]:
    """Parse and validate a compact QR JSON payload."""

    if not isinstance(payload_json, str):
        raise TypeError("payload_json must be a string")

    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError as exc:
        raise ValueError("payload_json must be valid JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError("payload_json must contain a JSON object")
    if set(payload) != REQUIRED_FIELDS:
        raise ValueError(f"payload must contain exactly these fields: {sorted(REQUIRED_FIELDS)}")
    if payload["v"] != QR_PAYLOAD_VERSION:
        raise ValueError(f"unsupported QR payload version: {payload['v']!r}")
    if not isinstance(payload["id"], str) or not payload["id"]:
        raise ValueError("payload id must be a non-empty string")
    payload["h"] = _validate_hash_hex(payload["h"])
    if not isinstance(payload["s"], str) or not payload["s"]:
        raise ValueError("payload signature must be a non-empty base64url string")
    b64url_decode(payload["s"])
    if not isinstance(payload["ts"], int):
        raise ValueError("payload ts must be an integer")
    if not isinstance(payload["ex"], int):
        raise ValueError("payload ex must be an integer")
    if payload["ex"] <= payload["ts"]:
        raise ValueError("payload ex must be after ts")
    if not isinstance(payload["alg"], str) or not payload["alg"]:
        raise ValueError("payload alg must be a non-empty string")

    return payload


def is_expired(payload: dict[str, Any], now: int | None = None) -> bool:
    """Return True when a parsed QR payload has expired."""

    expires_at = payload.get("ex")
    if not isinstance(expires_at, int):
        raise ValueError("payload ex must be an integer")

    timestamp = int(time.time()) if now is None else now
    if not isinstance(timestamp, int):
        raise TypeError("now must be an integer")

    return timestamp >= expires_at
