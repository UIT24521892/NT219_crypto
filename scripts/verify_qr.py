#!/usr/bin/env python3
"""Offline verifier for FALCON QR payloads."""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from pathlib import Path
from typing import Any, Final


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

with contextlib.redirect_stdout(sys.stderr):
    from backend.app.crypto.falcon_service import verify_document  # noqa: E402
    from backend.app.crypto.qr_builder import (  # noqa: E402
        QR_ALGORITHM,
        b64url_decode,
        is_expired,
        parse_payload,
    )


EXIT_VALID: Final[int] = 0
EXIT_INVALID: Final[int] = 1
EXIT_INPUT_ERROR: Final[int] = 2


def result(
    valid: bool,
    reason: str,
    doc_id: str | None = None,
    algorithm: str | None = None,
) -> dict[str, Any]:
    return {
        "valid": valid,
        "reason": reason,
        "doc_id": doc_id,
        "algorithm": algorithm,
    }


def verify_qr_payload(
    pdf_bytes: bytes,
    payload_json: str,
    public_key: bytes,
    now: int | None = None,
) -> dict[str, Any]:
    """Verify a PDF against a compact QR payload and raw FALCON public key."""

    try:
        payload = parse_payload(payload_json)
    except Exception as exc:
        return result(False, f"invalid_payload: {exc}")

    doc_id = payload["id"]
    algorithm = payload["alg"]

    if algorithm != QR_ALGORITHM:
        return result(False, f"unsupported_algorithm: {algorithm}", doc_id, algorithm)

    try:
        if is_expired(payload, now=now):
            return result(False, "expired", doc_id, algorithm)
    except Exception as exc:
        return result(False, f"invalid_expiry: {exc}", doc_id, algorithm)

    try:
        signature = b64url_decode(payload["s"])
    except Exception as exc:
        return result(False, f"invalid_signature_encoding: {exc}", doc_id, algorithm)

    is_valid = verify_document(
        pdf_bytes,
        signature,
        public_key,
        expected_hash_hex=payload["h"],
        algorithm=algorithm,
    )
    if not is_valid:
        return result(False, "signature_or_hash_mismatch", doc_id, algorithm)

    return result(True, "valid", doc_id, algorithm)


def exit_code_for_result(verification: dict[str, Any]) -> int:
    reason = str(verification.get("reason", ""))
    if verification.get("valid") is True:
        return EXIT_VALID
    if reason.startswith("invalid_payload") or reason.startswith("invalid_signature_encoding"):
        return EXIT_INPUT_ERROR
    return EXIT_INVALID


def read_text_arg(value: str) -> str:
    if value == "-":
        return sys.stdin.read()
    return Path(value).read_text(encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify a PDF against an offline QR payload.")
    parser.add_argument("--pdf", required=True, help="Path to the PDF/document bytes.")
    parser.add_argument("--payload", required=True, help="Path to QR payload JSON, or '-' for stdin.")
    parser.add_argument("--public-key", required=True, help="Path to raw FALCON public key bytes.")
    parser.add_argument("--now", type=int, default=None, help="Unix timestamp override for expiry checks.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        pdf_bytes = Path(args.pdf).read_bytes()
        payload_json = read_text_arg(args.payload)
        public_key = Path(args.public_key).read_bytes()
    except Exception as exc:
        verification = result(False, f"input_error: {exc}")
        print(json.dumps(verification, separators=(",", ":")))
        return EXIT_INPUT_ERROR

    verification = verify_qr_payload(
        pdf_bytes=pdf_bytes,
        payload_json=payload_json,
        public_key=public_key,
        now=args.now,
    )
    print(json.dumps(verification, separators=(",", ":")))
    return exit_code_for_result(verification)


if __name__ == "__main__":
    raise SystemExit(main())
