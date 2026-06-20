#!/usr/bin/env python3
"""Demonstrate that an expired QR payload is rejected as replay."""

from __future__ import annotations

import json
import sys
import contextlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

with contextlib.redirect_stdout(sys.stderr):
    from backend.app.crypto.mldsa_service import generate_keypair, sign_document  # noqa: E402
    from backend.app.crypto.qr_builder import build_offline_payload  # noqa: E402
    from scripts.verify_qr import verify_qr_payload  # noqa: E402


def run_demo() -> dict[str, object]:
    pdf_bytes = b"%PDF-1.4\nExpired citizen service certificate\n"
    public_key, private_key = generate_keypair()
    doc_hash_hex, signature = sign_document(pdf_bytes, private_key)
    payload_json = build_offline_payload(
        doc_id="demo-replay-attack",
        doc_hash_hex=doc_hash_hex,
        signature=signature,
        issued_at=100,
        expires_at=200,
    )

    before_expiry = verify_qr_payload(pdf_bytes, payload_json, public_key, now=199)
    after_expiry = verify_qr_payload(pdf_bytes, payload_json, public_key, now=200)
    replay_blocked = before_expiry["valid"] is True and after_expiry["reason"] == "expired"

    return {
        "attack": "expired_qr_replay",
        "attack_blocked": replay_blocked,
        "before_expiry": before_expiry,
        "after_expiry": after_expiry,
    }


def main() -> int:
    try:
        demo = run_demo()
    except Exception as exc:
        print(json.dumps({"attack": "expired_qr_replay", "error": str(exc)}, separators=(",", ":")))
        return 2

    print(json.dumps(demo, separators=(",", ":")))
    return 0 if demo["attack_blocked"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
