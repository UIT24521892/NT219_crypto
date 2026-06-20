"""
Citizen Services Portal — signed-PDF builder.

Produces a self-contained *signed* PDF from the original upload:

  1. The offline QR (self-contained Ed25519 payload) is stamped onto the first
     page, bottom-right corner, so a verifier can scan straight from a printout.
  2. Both signatures and both key references are written into the PDF's document
     information dictionary (hidden metadata): the post-quantum ML-DSA-44
     signature and the small Ed25519 QR signature, plus ``signed_at``.

The original page content is never modified — the QR is laid *over* page 1 with
pikepdf's ``add_overlay`` (which scales/places without touching the source
stream), and the SHA-256 over the original bytes (what ML-DSA signed) is recorded
in metadata so a verifier can confirm which bytes the PQC signature covers.

Metadata keys (all under the docinfo dictionary, prefixed to avoid clashes):
    /CSP_Signed              ISO-8601 UTC timestamp
    /CSP_MLDSA_Algorithm     "ML-DSA-44"
    /CSP_MLDSA_Signature     base64(ML-DSA signature)
    /CSP_MLDSA_KeyRef        trust-registry key id of the ML-DSA public key
    /CSP_OriginalSHA256      hex SHA-256 of the original (signed) PDF bytes
    /CSP_QR_Algorithm        "ed25519"
    /CSP_QR_Signature        base64(Ed25519 QR signature)
    /CSP_QR_KeyRef           trust-registry key id of the Ed25519 public key
    /CSP_QR_Payload          the full self-contained QR string
"""
import base64
import hashlib
import io
from datetime import datetime, timezone
from typing import Final, Optional

QR_SIZE_PT: Final[float] = 96.0   # ~1.33 inch square on the page
QR_MARGIN_PT: Final[float] = 18.0  # 0.25 inch from the page edges

_MLDSA_ALGORITHM: Final[str] = "ML-DSA-44"
_QR_ALGORITHM: Final[str] = "ed25519"


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _qr_overlay_pdf(qr_png: bytes) -> bytes:
    """Wrap a QR PNG in a single-page PDF so pikepdf can overlay it.

    The image is flattened to RGB on a white background first — img2pdf refuses
    images with an alpha channel, and qrcode can emit one.
    """

    import img2pdf
    from PIL import Image

    image = Image.open(io.BytesIO(qr_png))
    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        background = Image.new("RGBA", image.size, (255, 255, 255, 255))
        image = Image.alpha_composite(background, image).convert("RGB")
    else:
        image = image.convert("RGB")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return img2pdf.convert(buffer.getvalue())


def build_signed_pdf(
    *,
    pdf_bytes: bytes,
    qr_png: bytes,
    mldsa_signature: bytes,
    qr_signature: bytes,
    public_key_ref: str,
    qr_public_key_ref: str,
    qr_payload: str,
    signed_at: datetime,
    signer_email: Optional[str] = None,
    issuer: Optional[str] = None,
) -> bytes:
    """Return new PDF bytes: original + stamped QR + embedded signature metadata."""

    import pikepdf

    original_sha256 = hashlib.sha256(pdf_bytes).hexdigest()

    with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
        # 1) Stamp the QR onto the first page, bottom-right corner.
        overlay_bytes = _qr_overlay_pdf(qr_png)
        with pikepdf.open(io.BytesIO(overlay_bytes)) as overlay_pdf:
            first_page = pdf.pages[0]
            box = first_page.mediabox
            page_x1 = float(box[2])
            page_y0 = float(box[1])
            x1 = page_x1 - QR_MARGIN_PT
            x0 = x1 - QR_SIZE_PT
            y0 = page_y0 + QR_MARGIN_PT
            y1 = y0 + QR_SIZE_PT
            rect = pikepdf.Rectangle(x0, y0, x1, y1)
            pikepdf.Page(first_page).add_overlay(overlay_pdf.pages[0], rect)

        # 2) Embed both signatures + key refs + timestamps in hidden metadata.
        meta = {
            "/CSP_Signed": _iso_utc(signed_at),
            "/CSP_MLDSA_Algorithm": _MLDSA_ALGORITHM,
            "/CSP_MLDSA_Signature": base64.b64encode(mldsa_signature).decode("ascii"),
            "/CSP_MLDSA_KeyRef": public_key_ref,
            "/CSP_OriginalSHA256": original_sha256,
            "/CSP_QR_Algorithm": _QR_ALGORITHM,
            "/CSP_QR_Signature": base64.b64encode(qr_signature).decode("ascii"),
            "/CSP_QR_KeyRef": qr_public_key_ref,
            "/CSP_QR_Payload": qr_payload,
        }
        if signer_email:
            meta["/CSP_Signer"] = signer_email
        if issuer:
            meta["/CSP_Issuer"] = issuer
        for key, value in meta.items():
            pdf.docinfo[pikepdf.Name(key)] = value

        out = io.BytesIO()
        pdf.save(out)
        return out.getvalue()
