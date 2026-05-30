import pytest

from backend.app.crypto.falcon_service import available_signature_algorithms
from scripts.attack_forgery import run_demo as run_forgery_demo
from scripts.attack_replay import run_demo as run_replay_demo


pytestmark = pytest.mark.skipif(
    not available_signature_algorithms(),
    reason="liboqs-python/oqs is not installed or no signature mechanisms are enabled",
)


def test_pdf_tampering_attack_is_blocked():
    result = run_forgery_demo()

    assert result["attack_blocked"] is True
    assert result["original"]["valid"] is True
    assert result["tampered"]["valid"] is False


def test_expired_qr_replay_attack_is_blocked():
    result = run_replay_demo()

    assert result["attack_blocked"] is True
    assert result["before_expiry"]["valid"] is True
    assert result["after_expiry"]["reason"] == "expired"
