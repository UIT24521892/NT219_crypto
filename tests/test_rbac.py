"""RBAC guard tests: reviewer/signer/admin separation of duties.

These exercise the FastAPI role dependencies directly (no DB / no running
server) by awaiting them with a constructed user. The endpoint-level checks
(document_not_approved -> 409, separation_of_duty -> 403) are covered by the
opt-in integration suite in test_api.py against a running backend.
"""
import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

# auth_middleware uses absolute ``app.*`` imports (it runs under uvicorn from
# backend/), so put backend/ on the path and import the API layer the same way
# to keep a single module identity for the SQLAlchemy models.
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.auth_middleware import (  # noqa: E402
    require_admin,
    require_reviewer,
    require_signer,
)
from app.models import User, UserRole  # noqa: E402


def _user(role: UserRole) -> User:
    return User(email=f"{role.value}@portal.gov.vn", role=role)


def _run(coro):
    return asyncio.run(coro)


# --- reviewer guard -------------------------------------------------------- #

def test_signer_cannot_approve():
    with pytest.raises(HTTPException) as exc:
        _run(require_reviewer(_user(UserRole.SIGNER)))
    assert exc.value.status_code == 403


def test_citizen_cannot_approve():
    with pytest.raises(HTTPException) as exc:
        _run(require_reviewer(_user(UserRole.CITIZEN)))
    assert exc.value.status_code == 403


def test_reviewer_can_approve():
    user = _user(UserRole.REVIEWER)
    assert _run(require_reviewer(user)) is user


# --- signer guard ---------------------------------------------------------- #

def test_reviewer_cannot_sign():
    with pytest.raises(HTTPException) as exc:
        _run(require_signer(_user(UserRole.REVIEWER)))
    assert exc.value.status_code == 403


def test_citizen_cannot_sign():
    with pytest.raises(HTTPException) as exc:
        _run(require_signer(_user(UserRole.CITIZEN)))
    assert exc.value.status_code == 403


def test_signer_can_sign():
    user = _user(UserRole.SIGNER)
    assert _run(require_signer(user)) is user


# --- admin is the super-role ----------------------------------------------- #

def test_admin_passes_every_guard():
    admin = _user(UserRole.ADMIN)
    assert _run(require_admin(admin)) is admin
    assert _run(require_reviewer(admin)) is admin
    assert _run(require_signer(admin)) is admin
