import base64
import io
from datetime import datetime, timezone

import pikepdf
import pytest
import qrcode

from backend.app.crypto.pdf_embedder import build_signed_pdf


def _blank_pdf() -> bytes:
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(612, 792))
    buffer = io.BytesIO()
    pdf.save(buffer)
    return buffer.getvalue()


def _qr_png(text: str = "demo|payload") -> bytes:
    buffer = io.BytesIO()
    qrcode.make(text).save(buffer, format="PNG")
    return buffer.getvalue()


def _build(**overrides) -> bytes:
    params = dict(
        pdf_bytes=_blank_pdf(),
        qr_png=_qr_png(),
        mldsa_signature=b"\x11" * 2420,
        qr_signature=b"\x22" * 64,
        public_key_ref="ml-dsa-44:abc123def456",
        qr_public_key_ref="ed25519:0123456789abcdef",
        qr_payload="sig|doc|hash|signer@x.gov|2026|2026|2027|ed25519:0123456789abcdef",
        signed_at=datetime(2026, 6, 20, 10, 30, 0, tzinfo=timezone.utc),
        signer_email="signer@portal.gov.vn",
    )
    params.update(overrides)
    return build_signed_pdf(**params)


def test_signed_pdf_keeps_pages_and_is_valid():
    signed = _build()
    with pikepdf.open(io.BytesIO(signed)) as pdf:
        assert len(pdf.pages) == 1


def test_signatures_roundtrip_through_metadata():
    signed = _build()
    with pikepdf.open(io.BytesIO(signed)) as pdf:
        mldsa = base64.b64decode(str(pdf.docinfo["/CSP_MLDSA_Signature"]))
        qr = base64.b64decode(str(pdf.docinfo["/CSP_QR_Signature"]))
        assert mldsa == b"\x11" * 2420
        assert qr == b"\x22" * 64
        assert str(pdf.docinfo["/CSP_MLDSA_Algorithm"]) == "ML-DSA-44"
        assert str(pdf.docinfo["/CSP_QR_Algorithm"]) == "ed25519"
        assert str(pdf.docinfo["/CSP_MLDSA_KeyRef"]) == "ml-dsa-44:abc123def456"
        assert str(pdf.docinfo["/CSP_QR_KeyRef"]) == "ed25519:0123456789abcdef"
        assert str(pdf.docinfo["/CSP_Signed"]) == "2026-06-20T10:30:00+00:00"


def test_original_hash_is_recorded():
    import hashlib

    original = _blank_pdf()
    signed = _build(pdf_bytes=original)
    with pikepdf.open(io.BytesIO(signed)) as pdf:
        assert str(pdf.docinfo["/CSP_OriginalSHA256"]) == hashlib.sha256(original).hexdigest()
