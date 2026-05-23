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
from io import BytesIO
from typing import Any

import qrcode
from qrcode.constants import ERROR_CORRECT_M


def build_payload(doc_id: str, file_hash: str, verify_url: str) -> dict[str, Any]:
    """
    Build the JSON payload embedded in the QR.

    Fields:
        v:        schema version (start at 1)
        doc_id:   UUID of the signed document
        hash:     SHA-256 hex of the original PDF (64 chars)
        url:      verify endpoint URL the scanner should hit
    """
    return {
        "v": 1,
        "doc_id": doc_id,
        "hash": file_hash,
        "url": verify_url,
    }


def render_png(payload: dict[str, Any]) -> bytes:
    """
    Render the payload as a PNG-encoded QR code.

    Uses error-correction level M (~15% recovery — good for printed
    documents that may get smudged) and auto-fit version selection.
    """
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
