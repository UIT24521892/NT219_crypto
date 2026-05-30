import json
import subprocess
import sys

import pytest

from backend.app.crypto.falcon_service import (
    available_signature_algorithms,
    generate_keypair,
    sign_document,
)
from backend.app.crypto.qr_builder import b64url_encode, build_payload
from scripts.verify_qr import (
    EXIT_INPUT_ERROR,
    EXIT_INVALID,
    EXIT_VALID,
    verify_package,
    verify_qr_payload,
)


pytestmark = pytest.mark.skipif(
    not available_signature_algorithms(),
    reason="liboqs-python/oqs is not installed or no signature mechanisms are enabled",
)


def signed_payload(pdf_bytes: bytes, issued_at: int = 100, expires_at: int = 200):
    public_key, private_key = generate_keypair()
    doc_hash_hex, signature = sign_document(pdf_bytes, private_key)
    payload_json = build_payload(
        doc_id="doc-verify-qr",
        doc_hash_hex=doc_hash_hex,
        signature=signature,
        issued_at=issued_at,
        expires_at=expires_at,
    )
    return public_key, payload_json


def test_verify_qr_accepts_valid_payload():
    pdf_bytes = b"%PDF-1.4\nValid offline QR document\n"
    public_key, payload_json = signed_payload(pdf_bytes)

    verification = verify_qr_payload(pdf_bytes, payload_json, public_key, now=150)

    assert verification == {
        "valid": True,
        "reason": "valid",
        "doc_id": "doc-verify-qr",
        "algorithm": "FALCON-512",
    }


def test_verify_qr_rejects_tampered_pdf():
    original_pdf = b"%PDF-1.4\nOriginal citizen document\n"
    tampered_pdf = b"%PDF-1.4\nTampered citizen document\n"
    public_key, payload_json = signed_payload(original_pdf)

    verification = verify_qr_payload(tampered_pdf, payload_json, public_key, now=150)

    assert verification["valid"] is False
    assert verification["reason"] == "signature_or_hash_mismatch"


def test_verify_qr_rejects_expired_replay():
    pdf_bytes = b"%PDF-1.4\nExpired replay document\n"
    public_key, payload_json = signed_payload(pdf_bytes)

    verification = verify_qr_payload(pdf_bytes, payload_json, public_key, now=200)

    assert verification["valid"] is False
    assert verification["reason"] == "expired"


def test_verify_qr_rejects_invalid_payload():
    verification = verify_qr_payload(
        b"%PDF-1.4\nInvalid payload document\n",
        "not json",
        b"public-key",
        now=150,
    )

    assert verification["valid"] is False
    assert verification["reason"].startswith("invalid_payload")


def test_verify_exported_package_accepts_valid_pdf():
    pdf_bytes = b"%PDF-1.4\nExported offline verification package\n"
    public_key, payload_json = signed_payload(pdf_bytes)
    payload = json.loads(payload_json)
    package_json = json.dumps(
        {
            "v": 1,
            "document_id": payload["id"],
            "document_hash": payload["h"],
            "offline_payload": payload_json,
            "signature_b64url": payload["s"],
            "algorithm": payload["alg"],
            "issued_at": payload["ts"],
            "expires_at": payload["ex"],
            "public_key_ref": "demo-key",
            "public_key_b64url": b64url_encode(public_key),
        }
    )

    assert verify_package(pdf_bytes, package_json, now=150)["valid"] is True


def test_verify_qr_cli_exit_codes(tmp_path):
    pdf_bytes = b"%PDF-1.4\nCLI verified document\n"
    public_key, payload_json = signed_payload(pdf_bytes)
    pdf_path = tmp_path / "document.pdf"
    payload_path = tmp_path / "payload.json"
    public_key_path = tmp_path / "public.key"

    pdf_path.write_bytes(pdf_bytes)
    payload_path.write_text(payload_json, encoding="utf-8")
    public_key_path.write_bytes(public_key)

    valid = subprocess.run(
        [
            sys.executable,
            "scripts/verify_qr.py",
            "--pdf",
            str(pdf_path),
            "--payload",
            str(payload_path),
            "--public-key",
            str(public_key_path),
            "--now",
            "150",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert valid.returncode == EXIT_VALID
    assert json.loads(valid.stdout)["valid"] is True

    expired = subprocess.run(
        [
            sys.executable,
            "scripts/verify_qr.py",
            "--pdf",
            str(pdf_path),
            "--payload",
            str(payload_path),
            "--public-key",
            str(public_key_path),
            "--now",
            "200",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert expired.returncode == EXIT_INVALID
    assert json.loads(expired.stdout)["reason"] == "expired"

    payload_path.write_text("not json", encoding="utf-8")
    invalid_payload = subprocess.run(
        [
            sys.executable,
            "scripts/verify_qr.py",
            "--pdf",
            str(pdf_path),
            "--payload",
            str(payload_path),
            "--public-key",
            str(public_key_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert invalid_payload.returncode == EXIT_INPUT_ERROR
    assert json.loads(invalid_payload.stdout)["reason"].startswith("invalid_payload")


def test_verify_qr_cli_accepts_exported_package(tmp_path):
    pdf_bytes = b"%PDF-1.4\nCLI verification package\n"
    public_key, payload_json = signed_payload(pdf_bytes)
    payload = json.loads(payload_json)
    package = {
        "v": 1,
        "document_id": payload["id"],
        "document_hash": payload["h"],
        "offline_payload": payload_json,
        "signature_b64url": payload["s"],
        "algorithm": payload["alg"],
        "issued_at": payload["ts"],
        "expires_at": payload["ex"],
        "public_key_ref": "demo-key",
        "public_key_b64url": b64url_encode(public_key),
    }
    pdf_path = tmp_path / "document.pdf"
    package_path = tmp_path / "verification-package.json"
    pdf_path.write_bytes(pdf_bytes)
    package_path.write_text(json.dumps(package), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/verify_qr.py",
            "--pdf",
            str(pdf_path),
            "--package",
            str(package_path),
            "--now",
            "150",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == EXIT_VALID
    assert json.loads(completed.stdout)["valid"] is True
