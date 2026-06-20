#!/usr/bin/env python3
"""Demonstrate that tampering a self-contained QR breaks offline Ed25519 verify.

The self-contained QR (``b64url(sig)|<canonical>``) is verified entirely offline:
the verifier rebuilds the signed canonical bytes from the payload and checks the
Ed25519 signature. Changing ANY field of the canonical (e.g. the signer email or
the document hash) invalidates the signature — exactly what an attacker who edits
a scanned QR would attempt.
"""

from __future__ import annotations

import contextlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

with contextlib.redirect_stdout(sys.stderr):
    from backend.app.crypto import ed25519_qr_service as ed25519  # noqa: E402
    from backend.app.crypto.qr_hybrid import (  # noqa: E402
        build_qr_canonical,
        build_qr_payload,
        canonical_from_payload,
        signature_from_payload,
    )


def _verify_offline(payload: str, public_key: bytes) -> dict[str, object]:
    """Mirror the client offline verifier: rebuild signed bytes, check Ed25519."""

    try:
        signature = signature_from_payload(payload)
        canonical = canonical_from_payload(payload)
    except ValueError as exc:
        return {"valid": False, "reason": f"malformed: {exc}"}
    valid = ed25519.verify_qr(canonical, signature, public_key)
    return {"valid": valid, "reason": "ok" if valid else "bad_signature"}


def run_demo() -> dict[str, object]:
    public_key, private_key = ed25519.generate_keypair()
    qr_public_key_ref = "ed25519:demo000000000000"

    signed_at = datetime(2026, 6, 20, 10, 30, 0, tzinfo=timezone.utc)
    fields = dict(
        doc_id="demo-qr-tamper-attack",
        file_hash="a" * 64,
        issuer="Chính phủ",
        signer_email="signer@portal.gov.vn",
        signed_at=signed_at,
        valid_from=signed_at,
        valid_until=signed_at + timedelta(days=365),
        qr_public_key_ref=qr_public_key_ref,
    )

    canonical = build_qr_canonical(**fields)
    signature = ed25519.sign_qr(canonical, private_key)
    payload = build_qr_payload(qr_signature=signature, **fields)

    # Attacker rewrites a field inside the scanned QR string.
    tampered_payload = payload.replace(
        "signer@portal.gov.vn", "attacker@evil.example"
    )

    original_result = _verify_offline(payload, public_key)
    tampered_result = _verify_offline(tampered_payload, public_key)

    attack_blocked = (
        original_result["valid"] is True
        and tampered_payload != payload
        and tampered_result["valid"] is False
    )
    return {
        "attack": "qr_field_tamper",
        "attack_blocked": attack_blocked,
        "original": original_result,
        "tampered": tampered_result,
    }


def main() -> int:
    try:
        demo = run_demo()
    except Exception as exc:
        print(json.dumps({"attack": "qr_field_tamper", "error": str(exc)}, separators=(",", ":")))
        return 2

    print(json.dumps(demo, separators=(",", ":")))
    return 0 if demo["attack_blocked"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
