import base64
import binascii
import json
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
        return base64.b64decode(padded.encode("ascii"), altchars=b"-_", validate=True)
    except (binascii.Error, UnicodeEncodeError) as exc:
        raise ValueError("invalid base64url value") from exc


def build_online_payload(verify_url: str) -> str:
    """Return the URL encoded by the phone-scannable online QR code."""

    if not isinstance(verify_url, str) or not verify_url:
        raise ValueError("verify_url is required for online QR payload")
    return verify_url


def build_offline_payload(
    doc_id: str,
    doc_hash_hex: str,
    signature: bytes,
    issued_at: int,
    expires_at: int,
    algorithm: str = QR_ALGORITHM,
) -> str:
    """Build the signed minified JSON payload used by the offline verifier."""

    if not isinstance(signature, bytes) or not signature:
        raise ValueError("signature is required for offline QR payload")
    payload = {
        "v": 1,
        "id": doc_id,
        "h": doc_hash_hex,
        "s": b64url_encode(signature),
        "ts": int(issued_at),
        "ex": int(expires_at),
        "alg": algorithm,
    }
    payload_json = json.dumps(payload, separators=(",", ":"))
    parse_payload(payload_json)
    return payload_json


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
) -> str:
    """Backward-compatible wrapper for existing scripts and callers."""

    offline_requested = any(
        value is not None
        for value in (doc_hash_hex, signature, issued_at, expires_at)
    )
    if not offline_requested:
        return build_online_payload(verify_url or "")

    return build_offline_payload(
        doc_id=doc_id,
        doc_hash_hex=doc_hash_hex or file_hash or "",
        signature=signature or b"",
        issued_at=issued_at if issued_at is not None else 0,
        expires_at=expires_at if expires_at is not None else 0,
        algorithm=algorithm,
    )


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
    if payload["ex"] <= payload["ts"]:
        raise ValueError("ex must be greater than ts")
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


def render_png(payload: dict[str, Any] | str) -> bytes:
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
        border=4,                # QR quiet zone minimum for reliable scanning
    )
    encoded_data = (
        json.dumps(payload, separators=(",", ":"))
        if isinstance(payload, dict)
        else payload
    )
    qr.add_data(encoded_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
