"""
Citizen Services Portal — public Trust Registry / Public Key Directory.

GET /public-keys           — list ACTIVE issuing public keys (no auth).
GET /public-keys/{key_id}  — one key's detail incl. PEM + fingerprint (no auth).

Holds both signing keys of the hybrid scheme:
  - ml-dsa-44:<fp>  — the primary post-quantum key (FIPS 204).
  - ed25519:<fp>    — the small offline QR key (classical convenience layer).

A verifier can fetch a key by id to check fingerprints out-of-band; the offline
verifier additionally bundles the Ed25519 key at build time as a trust anchor.
"""
import hashlib
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto import ed25519_qr_service as ed25519
from app.database import get_session
from app.models import PublicKey, PublicKeyStatus

router = APIRouter(prefix="/public-keys", tags=["trust-registry"])

# Public-facing algorithm labels used in key_id prefixes and the registry.
ALG_MLDSA = "ml-dsa-44"
ALG_ED25519 = "ed25519"


def fingerprint(public_key: bytes) -> str:
    """SHA-256 fingerprint (hex) of a raw public key."""
    return hashlib.sha256(public_key).hexdigest()


def make_key_id(algorithm: str, public_key: bytes) -> str:
    """Build the stable ``<algorithm>:<fingerprint-prefix>`` key id."""
    return f"{algorithm}:{fingerprint(public_key)[:16]}"


async def register_public_key(
    session: AsyncSession,
    *,
    algorithm: str,
    public_key: bytes,
    owner_name: str = "Issuing Authority",
) -> str:
    """
    Idempotently register an ACTIVE public key in the directory, keyed by its
    fingerprint. Returns the ``key_id``. Caller is responsible for committing.
    """

    fp = fingerprint(public_key)
    key_id = f"{algorithm}:{fp[:16]}"

    existing = await session.execute(
        select(PublicKey).where(PublicKey.fingerprint == fp)
    )
    if existing.scalar_one_or_none() is None:
        session.add(
            PublicKey(
                key_id=key_id,
                algorithm=algorithm,
                public_key_bytes=public_key,
                fingerprint=fp,
                owner_name=owner_name,
                status=PublicKeyStatus.ACTIVE,
            )
        )
        await session.flush()
    return key_id


def _summary(row: PublicKey) -> dict[str, Any]:
    return {
        "key_id": row.key_id,
        "algorithm": row.algorithm,
        "fingerprint": row.fingerprint,
        "owner_name": row.owner_name,
        "status": row.status.value,
        "valid_from": row.created_at.isoformat() if row.created_at else None,
        "valid_until": row.revoked_at.isoformat() if row.revoked_at else None,
    }


def _pem_for(row: PublicKey) -> str | None:
    """Best-effort PEM encoding; only Ed25519 raw keys have a standard PEM here."""
    if row.algorithm == ALG_ED25519:
        try:
            return ed25519.public_key_pem(row.public_key_bytes)
        except Exception:
            return None
    return None


@router.get("")
async def list_public_keys(session: AsyncSession = Depends(get_session)):
    """List every ACTIVE public key in the Trust Registry. No authentication."""

    result = await session.execute(
        select(PublicKey)
        .where(PublicKey.status == PublicKeyStatus.ACTIVE)
        .order_by(PublicKey.algorithm, PublicKey.created_at)
    )
    return {"keys": [_summary(row) for row in result.scalars().all()]}


@router.get("/{key_id}")
async def get_public_key_detail(
    key_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Return one key's detail including its base16 bytes and PEM. No authentication."""

    result = await session.execute(
        select(PublicKey).where(PublicKey.key_id == key_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Public key not found")

    detail = _summary(row)
    detail["public_key_hex"] = row.public_key_bytes.hex()
    detail["public_key_pem"] = _pem_for(row)
    return detail
