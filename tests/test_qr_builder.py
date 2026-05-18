import json

import pytest

from backend.app.crypto.qr_builder import (
    b64url_decode,
    b64url_encode,
    build_payload,
    is_expired,
    parse_payload,
)


def test_qr_payload_has_exact_required_fields():
    payload_json = build_payload(
        doc_id="doc-123",
        doc_hash_hex="a" * 64,
        signature=b"signature-bytes",
        issued_at=1_700_000_000,
        expires_at=1_700_000_100,
    )
    payload = json.loads(payload_json)

    assert set(payload) == {"v", "id", "h", "s", "ts", "ex", "alg"}
    assert payload == parse_payload(payload_json)
    assert " " not in payload_json
    assert "\n" not in payload_json
    assert payload["alg"] == "FALCON-512"


def test_qr_signature_base64url_roundtrip():
    signature = b"\xfb\xffsignature bytes?\x00"
    encoded = b64url_encode(signature)

    assert "=" not in encoded
    assert b64url_decode(encoded) == signature


def test_expired_payload_detection():
    payload = parse_payload(
        build_payload(
            doc_id="doc-123",
            doc_hash_hex="b" * 64,
            signature=b"signature",
            issued_at=100,
            expires_at=200,
        )
    )

    assert is_expired(payload, now=199) is False
    assert is_expired(payload, now=200) is True


def test_parse_payload_rejects_missing_or_extra_fields():
    payload = json.loads(
        build_payload(
            doc_id="doc-123",
            doc_hash_hex="c" * 64,
            signature=b"signature",
            issued_at=100,
            expires_at=200,
        )
    )
    payload["extra"] = "not allowed"

    with pytest.raises(ValueError, match="exactly"):
        parse_payload(json.dumps(payload))
