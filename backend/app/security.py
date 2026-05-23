"""
Citizen Services Portal — Security utilities.
Password hashing (bcrypt) + JWT encode/decode.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import jwt

from app.config import settings

# Bcrypt cost factor (~ 250 ms / hash on modern CPUs)
BCRYPT_ROUNDS = 12

# Bcrypt has a hard 72-byte limit on password input — industry-standard behavior
BCRYPT_MAX_BYTES = 72


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password with bcrypt. Returns the bcrypt hash string."""
    password_bytes = plain_password.encode("utf-8")[:BCRYPT_MAX_BYTES]
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Constant-time bcrypt verification. Returns True if password matches hash."""
    password_bytes = plain_password.encode("utf-8")[:BCRYPT_MAX_BYTES]
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))


def create_access_token(
    subject: str,
    extra_claims: Optional[dict] = None,
    expires_minutes: Optional[int] = None,
) -> str:
    """
    Create a signed JWT access token.

    `subject` becomes the `sub` claim (typically the user ID as a string).
    `extra_claims` are merged into the token payload (e.g. {"role": "citizen"}).
    `expires_minutes` overrides settings.jwt_expires_minutes when provided.
    """
    now = datetime.now(timezone.utc)
    expires_in = (
        expires_minutes
        if expires_minutes is not None
        else settings.jwt_expires_minutes
    )
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_in)).timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(
        payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT. Returns the decoded payload as a dict.
    Raises `jose.JWTError` (or a subclass) if the token is invalid or expired.
    """
    return jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
