#!/usr/bin/env python3
"""Demonstrate that PDF tampering invalidates a FALCON QR signature."""

from __future__ import annotations

import json
import sys
import contextlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

with contextlib.redirect_stdout(sys.stderr):
    from backend.app.crypto.falcon_service import generate_keypair, sign_document  # noqa: E402
    from backend.app.crypto.qr_builder import build_payload  # noqa: E402
    from scripts.verify_qr import verify_qr_payload  # noqa: E402


def run_demo() -> dict[str, object]:
    original_pdf = b"%PDF-1.4\nCitizen service approval: Nguyen Van A\n"
    tampered_pdf = b"%PDF-1.4\nCitizen service approval: Nguyen Van B\n"
    public_key, private_key = generate_keypair()

    doc_hash_hex, signature = sign_document(original_pdf, private_key)
    payload_json = build_payload(
        doc_id="demo-forgery-attack",
        doc_hash_hex=doc_hash_hex,
        signature=signature,
        issued_at=1_700_000_000,
        expires_at=1_800_000_000,
    )

    original_result = verify_qr_payload(
        original_pdf,
        payload_json,
        public_key,
        now=1_700_000_100,
    )
    tampered_result = verify_qr_payload(
        tampered_pdf,
        payload_json,
        public_key,
        now=1_700_000_100,
    )

    attack_blocked = original_result["valid"] is True and tampered_result["valid"] is False
    return {
        "attack": "pdf_tampering",
        "attack_blocked": attack_blocked,
        "original": original_result,
        "tampered": tampered_result,
    }


def main() -> int:
    try:
        demo = run_demo()
    except Exception as exc:
        print(json.dumps({"attack": "pdf_tampering", "error": str(exc)}, separators=(",", ":")))
        return 2

    print(json.dumps(demo, separators=(",", ":")))
    return 0 if demo["attack_blocked"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
