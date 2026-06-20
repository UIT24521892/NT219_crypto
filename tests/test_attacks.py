import pytest

from backend.app.crypto.mldsa_service import available_signature_algorithms
from scripts.attack_forgery import run_demo as run_forgery_demo
from scripts.attack_qr_tamper import run_demo as run_qr_tamper_demo
from scripts.attack_replay import run_demo as run_replay_demo


requires_oqs = pytest.mark.skipif(
    not available_signature_algorithms(),
    reason="liboqs-python/oqs is not installed or no signature mechanisms are enabled",
)


@requires_oqs
def test_pdf_tampering_attack_is_blocked():
    result = run_forgery_demo()

    assert result["attack_blocked"] is True
    assert result["original"]["valid"] is True
    assert result["tampered"]["valid"] is False


def test_qr_field_tamper_attack_is_blocked():
    # Ed25519 offline QR — does not depend on liboqs.
    result = run_qr_tamper_demo()

    assert result["attack_blocked"] is True
    assert result["original"]["valid"] is True
    assert result["tampered"]["valid"] is False


@requires_oqs
def test_expired_qr_replay_attack_is_blocked():
    result = run_replay_demo()

    assert result["attack_blocked"] is True
    assert result["before_expiry"]["valid"] is True
    assert result["after_expiry"]["reason"] == "expired"
