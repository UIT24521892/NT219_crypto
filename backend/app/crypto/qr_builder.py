"""
Citizen Services Portal — QR code builder for signed documents.

The QR payload is intentionally COMPACT — only contains the verification URL
and a short integrity hash. The actual FALCON-512 signature (666 bytes) is
NOT embedded; the verify endpoint fetches it from the database by doc_id.

This keeps the QR small enough to scan reliably from a phone camera at
distance (target: ≤ 400 alphanumeric chars / version-15 QR).

⚠ Member A may replace this with a more sophisticated qr_builder that
embeds the full signature for offline verification. The interface below
(build_payload + render_png) should stay backward-compatible.
"""
import json
import base64
import binascii
import time
from io import BytesIO
from typing import Any, Final


QR_ALGORITHM: Final[str] = "FALCON-512"
OFFLINE_PAYLOAD_FIELDS: Final[set[str]] = {"v", "id", "h", "s", "ts", "ex", "alg"}


def b64url_encode(data: bytes) -> str:
    """Encode bytes as unpadded URL-safe Base64."""

    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def b64url_decode(value: str) -> bytes:
    """Decode unpadded URL-safe Base64."""

    if not isinstance(value, str):
        raise TypeError("value must be a string")
    padded = value + ("=" * (-len(value) % 4))
    try:
        return base64.urlsafe_b64decode(padded.encode("ascii"))
    except (binascii.Error, UnicodeEncodeError) as exc:
        raise ValueError("invalid base64url value") from exc


def build_payload(
    doc_id: str,
    file_hash: str | None = None,
    verify_url: str | None = None,
    *,
    doc_hash_hex: str | None = None,
    signature: bytes | None = None,
    issued_at: int | None = None,
    expires_at: int | None = None,
    algorithm: str = QR_ALGORITHM,
) -> dict[str, Any] | str:
    """
    Build the JSON payload embedded in the QR.

    The deployed backend uses the online compact dict form. The offline
    verifier/tests use the minified JSON form with embedded signature.

    Fields:
        v:        schema version (start at 1)
        doc_id:   UUID of the signed document
        hash:     SHA-256 hex of the original PDF (64 chars)
        url:      verify endpoint URL the scanner should hit
    """
    offline_requested = any(
        value is not None
        for value in (doc_hash_hex, signature, issued_at, expires_at)
    )
    if offline_requested:
        if doc_hash_hex is None:
            doc_hash_hex = file_hash
        if doc_hash_hex is None:
            raise ValueError("doc_hash_hex is required for offline QR payload")
        if signature is None:
            raise ValueError("signature is required for offline QR payload")
        if issued_at is None or expires_at is None:
            raise ValueError("issued_at and expires_at are required for offline QR payload")

        payload = {
            "v": 1,
            "id": doc_id,
            "h": doc_hash_hex,
            "s": b64url_encode(signature),
            "ts": int(issued_at),
            "ex": int(expires_at),
            "alg": algorithm,
        }
        return json.dumps(payload, separators=(",", ":"))

    if file_hash is None:
        raise ValueError("file_hash is required for online QR payload")
    if verify_url is None:
        raise ValueError("verify_url is required for online QR payload")

    return {
        "v": 1,
        "doc_id": doc_id,
        "hash": file_hash,
        "url": verify_url,
    }


def parse_payload(payload_json: str) -> dict[str, Any]:
    """Parse and validate an offline QR payload JSON string."""

    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError as exc:
        raise ValueError("payload must be valid JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    if set(payload) != OFFLINE_PAYLOAD_FIELDS:
        raise ValueError(f"payload must contain exactly {sorted(OFFLINE_PAYLOAD_FIELDS)}")

    if payload["v"] != 1:
        raise ValueError("unsupported payload version")
    if not isinstance(payload["id"], str) or not payload["id"]:
        raise ValueError("id must be a non-empty string")
    if not isinstance(payload["h"], str):
        raise ValueError("h must be a string")
    try:
        if len(bytes.fromhex(payload["h"])) != 32:
            raise ValueError
    except ValueError as exc:
        raise ValueError("h must be a SHA-256 hex digest") from exc
    if not isinstance(payload["s"], str):
        raise ValueError("s must be a string")
    b64url_decode(payload["s"])
    if not isinstance(payload["ts"], int):
        raise ValueError("ts must be an integer")
    if not isinstance(payload["ex"], int):
        raise ValueError("ex must be an integer")
    if not isinstance(payload["alg"], str) or not payload["alg"]:
        raise ValueError("alg must be a non-empty string")

    return payload


def is_expired(payload: dict[str, Any], now: int | None = None) -> bool:
    """Return True when an offline QR payload is expired."""

    expires_at = payload.get("ex")
    if not isinstance(expires_at, int):
        raise ValueError("payload ex must be an integer")
    current_time = int(time.time()) if now is None else int(now)
    return current_time >= expires_at


def render_png(payload: dict[str, Any]) -> bytes:
    """
    Render the payload as a PNG-encoded QR code.

    Uses error-correction level M (~15% recovery — good for printed
    documents that may get smudged) and auto-fit version selection.
    """
    import qrcode
    from qrcode.constants import ERROR_CORRECT_M

    qr = qrcode.QRCode(
        version=None,            # auto-select smallest version that fits
        error_correction=ERROR_CORRECT_M,
        box_size=8,              # 8 pixels per QR module
        border=2,                # 2-module quiet zone (minimum allowed: 4 by spec, 2 works for most scanners)
    )
    qr.add_data(json.dumps(payload, separators=(",", ":")))
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
