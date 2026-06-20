from datetime import datetime, timezone

import pytest

from backend.app.crypto import ed25519_qr_service as ed25519
from backend.app.crypto.qr_hybrid import (
    build_qr_canonical,
    build_qr_payload,
    canonical_from_payload,
    signature_from_payload,
)


def _fields(email="signer@portal.gov.vn"):
    signed_at = datetime(2026, 6, 20, 10, 30, 0, tzinfo=timezone.utc)
    return dict(
        doc_id="11111111-1111-1111-1111-111111111111",
        file_hash="a" * 64,
        signer_email=email,
        signed_at=signed_at,
        valid_from=signed_at,
        valid_until=datetime(2027, 6, 20, 10, 30, 0, tzinfo=timezone.utc),
        qr_public_key_ref="ed25519:0123456789abcdef",
    )


def test_canonical_is_deterministic():
    f = _fields()
    assert build_qr_canonical(**f) == build_qr_canonical(**f)


def test_payload_roundtrips_and_verifies_offline():
    public_key, private_key = ed25519.generate_keypair()
    f = _fields()
    canonical = build_qr_canonical(**f)
    signature = ed25519.sign_qr(canonical, private_key)
    payload = build_qr_payload(qr_signature=signature, **f)

    # A verifier rebuilds the signed bytes from the payload alone.
    assert canonical_from_payload(payload) == canonical
    assert signature_from_payload(payload) == signature
    assert ed25519.verify_qr(
        canonical_from_payload(payload),
        signature_from_payload(payload),
        public_key,
    )


def test_tampering_any_field_breaks_offline_verify():
    public_key, private_key = ed25519.generate_keypair()
    f = _fields()
    canonical = build_qr_canonical(**f)
    signature = ed25519.sign_qr(canonical, private_key)
    payload = build_qr_payload(qr_signature=signature, **f)

    tampered = payload.replace("signer@portal.gov.vn", "attacker@evil.example")
    assert tampered != payload
    assert not ed25519.verify_qr(
        canonical_from_payload(tampered),
        signature_from_payload(tampered),
        public_key,
    )


def test_field_separator_is_rejected():
    f = _fields(email="a|b@portal.gov.vn")
    with pytest.raises(ValueError):
        build_qr_canonical(**f)
