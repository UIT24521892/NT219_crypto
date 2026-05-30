import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://unused:unused@127.0.0.1/unused")

from app.api.verify import is_qr_expired  # noqa: E402


def test_online_qr_expiry_boundary():
    expires_at = datetime(2030, 1, 1, tzinfo=timezone.utc)

    assert is_qr_expired(expires_at, now=expires_at - timedelta(seconds=1)) is False
    assert is_qr_expired(expires_at, now=expires_at) is True
