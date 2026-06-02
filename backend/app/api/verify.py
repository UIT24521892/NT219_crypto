"""
Citizen Services Portal — Public verification endpoint.

GET /verify?d=<doc_id> — public; verify signed PDF using:
1) stored PDF bytes -> recompute SHA-256
2) stored FALCON signature
3) public key from Trust Registry / Public Key Directory
"""
import hashlib
import time
import uuid as uuid_lib
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto.falcon_service import verify_signature
from app.database import get_session
from app.models import AuditLog, Document, DocumentStatus, PublicKey, PublicKeyStatus, User

router = APIRouter(tags=["verify"])


async def _log_verify_attempt(
    session: AsyncSession,
    request: Request,
    doc_id: uuid_lib.UUID,
    outcome: str,
    extra: dict[str, Any] | None = None,
) -> None:
    """Insert an audit_log row for a /verify request. Best-effort."""
    try:
        log = AuditLog(
            actor_id=None,
            action="verify_qr",
            target_type="document",
            target_id=doc_id,
            extra_metadata={"outcome": outcome, **(extra or {})},
            ip_address=(request.client.host if request.client else None),
            user_agent=request.headers.get("user-agent"),
        )
        session.add(log)
        await session.commit()
    except Exception:
        await session.rollback()


def _qr_expired(doc: Document) -> bool:
    """Check latest QR expiry if a QR payload exists."""
    payload = doc.qr_payload or {}
    expires_at = payload.get("expires_at")
    if expires_at is None:
        return False
    try:
        return int(time.time()) >= int(expires_at)
    except (TypeError, ValueError):
        return True


@router.get("/verify")
async def verify_document(
    request: Request,
    d: uuid_lib.UUID = Query(..., description="Document UUID from QR code"),
    session: AsyncSession = Depends(get_session),
):
    """Public verification. Does not require JWT."""
    result = await session.execute(select(Document).where(Document.id == d))
    doc = result.scalar_one_or_none()

    if doc is None:
        await _log_verify_attempt(session, request, d, "not_found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    response: dict[str, Any] = {
        "doc_id": str(doc.id),
        "filename": doc.filename,
        "file_hash": doc.file_hash,
        "file_size": doc.file_size,
        "status": doc.status.value,
        "signed_at": doc.signed_at.isoformat() if doc.signed_at else None,
        "public_key_ref": doc.public_key_ref,
        "qr_expires_at": (doc.qr_payload or {}).get("expires_at"),
    }

    if doc.signed_by:
        sres = await session.execute(select(User).where(User.id == doc.signed_by))
        signer = sres.scalar_one_or_none()
        response["signer_email"] = signer.email if signer else None
    else:
        response["signer_email"] = None

    if doc.status != DocumentStatus.SIGNED or doc.falcon_signature is None:
        response["valid"] = False
        response["reason"] = f"Document not signed (status={doc.status.value})"
        await _log_verify_attempt(session, request, d, "not_signed")
        return response

    if _qr_expired(doc):
        response["valid"] = False
        response["reason"] = "QR code expired. Please request a new QR code."
        await _log_verify_attempt(session, request, d, "qr_expired")
        return response

    file_path = Path(doc.storage_path)
    if not file_path.exists():
        response["valid"] = False
        response["reason"] = "File missing on server"
        await _log_verify_attempt(session, request, d, "file_missing")
        return response

    pdf_bytes = file_path.read_bytes()
    current_hash = hashlib.sha256(pdf_bytes).hexdigest()
    response["current_hash"] = current_hash

    if current_hash != doc.file_hash:
        response["valid"] = False
        response["reason"] = "SHA-256 hash mismatch — document may have been modified after upload/signing"
        await _log_verify_attempt(
            session,
            request,
            d,
            "hash_mismatch",
            {"expected_hash": doc.file_hash, "current_hash": current_hash},
        )
        return response

    if not doc.public_key_ref:
        response["valid"] = False
        response["reason"] = "Missing public_key_ref for signed document"
        await _log_verify_attempt(session, request, d, "missing_public_key_ref")
        return response

    pk_result = await session.execute(select(PublicKey).where(PublicKey.key_id == doc.public_key_ref))
    public_key_record = pk_result.scalar_one_or_none()

    if public_key_record is None:
        response["valid"] = False
        response["reason"] = "Public key not found in Trust Registry"
        await _log_verify_attempt(session, request, d, "public_key_not_found")
        return response

    response["public_key_status"] = public_key_record.status.value
    response["public_key_fingerprint"] = public_key_record.fingerprint

    if public_key_record.status != PublicKeyStatus.ACTIVE:
        response["valid"] = False
        response["reason"] = f"Public key is not active (status={public_key_record.status.value})"
        await _log_verify_attempt(session, request, d, "public_key_not_active")
        return response

    is_valid = verify_signature(pdf_bytes, doc.falcon_signature, public_key_record.public_key_bytes)
    response["valid"] = is_valid

    if not is_valid:
        response["reason"] = "Signature verification failed — document may have been tampered with"

    await _log_verify_attempt(session, request, d, "valid" if is_valid else "invalid")
    return response
