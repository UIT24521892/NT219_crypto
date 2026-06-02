"""
Citizen Services Portal — Document endpoints.

Flow đúng theo threat model:
Citizen upload PDF -> pending_review -> Admin approve/reject -> Admin sign approved doc
-> generate QR -> public verify.
"""
import hashlib
import uuid as uuid_lib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_middleware import get_current_user, require_admin
from app.config import settings
from app.crypto.falcon_service import sign_document as falcon_sign
from app.crypto.qr_builder import build_payload as qr_build_payload
from app.crypto.qr_builder import render_png as qr_render_png
from app.database import get_session
from app.models import (
    AuditLog,
    Document,
    DocumentStatus,
    PublicKey,
    PublicKeyStatus,
    User,
    UserRole,
)
from app.schemas import DocumentResponse, ReviewRequest

router = APIRouter(prefix="/documents", tags=["documents"])

PDF_MAGIC = b"%PDF-"
STORAGE_DIR = Path("storage/uploads")
CHUNK_SIZE = 8192


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


async def _add_audit(
    session: AsyncSession,
    request: Request,
    *,
    actor_id: uuid_lib.UUID | None,
    action: str,
    target_id: uuid_lib.UUID | None,
    extra: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            target_type="document" if target_id else None,
            target_id=target_id,
            extra_metadata=extra or {},
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    )


def _public_key_identity(public_key: bytes) -> tuple[str, str]:
    """Return (key_id, fingerprint). key_id là public_key_ref lưu trong document."""
    fingerprint = hashlib.sha256(public_key).hexdigest()
    key_id = f"falcon-512:{fingerprint[:16]}"
    return key_id, fingerprint


async def _ensure_public_key_record(session: AsyncSession, public_key: bytes) -> str:
    """
    Đưa public key vào Trust Registry nếu chưa có.
    verify endpoint sẽ dùng public_key_ref để lấy public key từ bảng này.
    """
    key_id, fingerprint = _public_key_identity(public_key)
    result = await session.execute(select(PublicKey).where(PublicKey.key_id == key_id))
    record = result.scalar_one_or_none()

    if record is None:
        session.add(
            PublicKey(
                key_id=key_id,
                algorithm="FALCON-512",
                public_key_bytes=public_key,
                fingerprint=fingerprint,
                owner_name="Issuing Authority",
                status=PublicKeyStatus.ACTIVE,
            )
        )
    elif record.status != PublicKeyStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Signing public key is not active (status={record.status.value})",
        )

    return key_id


async def _get_doc_or_404(
    doc_id: uuid_lib.UUID,
    current_user: User,
    session: AsyncSession,
) -> Document:
    """Fetch a document by ID and enforce RBAC. 404 on miss OR forbidden."""
    result = await session.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if current_user.role != UserRole.ADMIN and doc.uploader_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    return doc


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Upload PDF; hệ thống chỉ đưa vào hàng chờ duyệt, chưa được ký ngay."""
    max_bytes = settings.max_upload_size_mb * 1024 * 1024

    contents = bytearray()
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        contents.extend(chunk)
        if len(contents) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds {settings.max_upload_size_mb} MB limit",
            )

    if len(contents) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    if not bytes(contents[:5]) == PDF_MAGIC:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is not a valid PDF (magic-byte check failed)",
        )

    file_bytes = bytes(contents)
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    doc_id = uuid_lib.uuid4()
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    storage_path = STORAGE_DIR / f"{doc_id}.pdf"
    storage_path.write_bytes(file_bytes)

    doc = Document(
        id=doc_id,
        uploader_id=current_user.id,
        filename=file.filename or "untitled.pdf",
        storage_path=str(storage_path),
        file_size=len(file_bytes),
        file_hash=file_hash,
        status=DocumentStatus.PENDING_REVIEW,
    )
    session.add(doc)
    await _add_audit(
        session,
        request,
        actor_id=current_user.id,
        action="upload",
        target_id=doc_id,
        extra={"filename": doc.filename, "sha256": file_hash},
    )
    await session.commit()
    await session.refresh(doc)
    return doc


@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List documents (citizen: own only, admin: all). Newest first."""
    query = select(Document).order_by(Document.created_at.desc())
    if current_user.role != UserRole.ADMIN:
        query = query.where(Document.uploader_id == current_user.id)
    query = query.limit(limit).offset(offset)

    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: uuid_lib.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get document metadata. Owner or admin only."""
    return await _get_doc_or_404(doc_id, current_user, session)


@router.get("/{doc_id}/download")
async def download_document(
    doc_id: uuid_lib.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Stream the PDF file. Owner or admin only."""
    doc = await _get_doc_or_404(doc_id, current_user, session)
    file_path = Path(doc.storage_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="File missing on disk")

    return FileResponse(path=str(file_path), media_type="application/pdf", filename=doc.filename)


@router.post("/{doc_id}/approve", response_model=DocumentResponse)
async def approve_document(
    doc_id: uuid_lib.UUID,
    request: Request,
    body: ReviewRequest | None = None,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Admin duyệt nghiệp vụ. Chỉ doc đã approved mới được ký."""
    doc = await _get_doc_or_404(doc_id, current_admin, session)

    if doc.status == DocumentStatus.SIGNED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Signed document cannot be approved again")

    doc.status = DocumentStatus.APPROVED
    doc.reviewed_by = current_admin.id
    doc.reviewed_at = datetime.now(timezone.utc)
    doc.review_note = body.note if body else None

    await _add_audit(
        session,
        request,
        actor_id=current_admin.id,
        action="approve",
        target_id=doc.id,
        extra={"note": doc.review_note},
    )
    await session.commit()
    await session.refresh(doc)
    return doc


@router.post("/{doc_id}/reject", response_model=DocumentResponse)
async def reject_document(
    doc_id: uuid_lib.UUID,
    request: Request,
    body: ReviewRequest | None = None,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Admin từ chối hồ sơ. Rejected doc không được ký."""
    doc = await _get_doc_or_404(doc_id, current_admin, session)

    if doc.status == DocumentStatus.SIGNED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Signed document cannot be rejected")

    doc.status = DocumentStatus.REJECTED
    doc.reviewed_by = current_admin.id
    doc.reviewed_at = datetime.now(timezone.utc)
    doc.review_note = body.note if body else None

    await _add_audit(
        session,
        request,
        actor_id=current_admin.id,
        action="reject",
        target_id=doc.id,
        extra={"note": doc.review_note},
    )
    await session.commit()
    await session.refresh(doc)
    return doc


@router.post("/{doc_id}/sign", response_model=DocumentResponse)
async def sign_document_endpoint(
    doc_id: uuid_lib.UUID,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Sign a document with FALCON-512. Admin only; document must be approved first."""
    doc = await _get_doc_or_404(doc_id, current_admin, session)

    if doc.status == DocumentStatus.SIGNED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document already signed")

    if doc.status != DocumentStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document must be approved before signing (current status={doc.status.value})",
        )

    file_path = Path(doc.storage_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="File missing on disk")

    pdf_bytes = file_path.read_bytes()
    current_hash = hashlib.sha256(pdf_bytes).hexdigest()
    if current_hash != doc.file_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stored PDF hash changed before signing. Refusing to sign tampered file.",
        )

    signature, public_key = falcon_sign(pdf_bytes)
    public_key_ref = await _ensure_public_key_record(session, public_key)

    doc.falcon_signature = signature
    doc.signed_by = current_admin.id
    doc.signed_at = datetime.now(timezone.utc)
    doc.status = DocumentStatus.SIGNED
    doc.public_key_ref = public_key_ref

    await _add_audit(
        session,
        request,
        actor_id=current_admin.id,
        action="sign",
        target_id=doc.id,
        extra={"public_key_ref": public_key_ref, "sha256": doc.file_hash},
    )
    await session.commit()
    await session.refresh(doc)
    return doc


@router.post("/{doc_id}/qr")
async def generate_qr(
    doc_id: uuid_lib.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Generate PNG QR for a signed document.

    QR chỉ chứa URL/doc_id/hash để mở endpoint verify public.
    Signature vẫn ở server/database; client không tự verify.
    """
    doc = await _get_doc_or_404(doc_id, current_user, session)

    if doc.status != DocumentStatus.SIGNED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document not signed (status={doc.status.value})",
        )

    base_url = str(request.base_url).rstrip("/")
    verify_url = f"{base_url}/verify?d={doc.id}"
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.qr_expires_minutes)

    payload = qr_build_payload(doc_id=str(doc.id), file_hash=doc.file_hash, verify_url=verify_url)
    payload["issued_at"] = int(now.timestamp())
    payload["expires_at"] = int(expires_at.timestamp())

    png_bytes = qr_render_png(payload)

    doc.qr_payload = payload
    await _add_audit(
        session,
        request,
        actor_id=current_user.id,
        action="qr_issued",
        target_id=doc.id,
        extra={"expires_at": payload["expires_at"]},
    )
    await session.commit()

    return Response(content=png_bytes, media_type="image/png")
