import os
import sys
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://unused:unused@127.0.0.1/unused")

from app.security import hash_password, verify_password  # noqa: E402


def test_bcrypt_password_roundtrip():
    password_hash = hash_password("SecurePass123")

    assert verify_password("SecurePass123", password_hash) is True
    assert verify_password("WrongPass123", password_hash) is False


def test_bcrypt_rejects_password_over_72_utf8_bytes():
    with pytest.raises(ValueError, match="72"):
        hash_password("a" * 73)

    password_hash = hash_password("a" * 72)
    assert verify_password("a" * 73, password_hash) is False


def test_bcrypt_counts_unicode_utf8_bytes():
    with pytest.raises(ValueError, match="72"):
        hash_password("á" * 37)
