"""
Citizen Services Portal - document upload, signing, QR and offline package APIs.
"""
import hashlib
import uuid as uuid_lib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

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

from app.audit_utils import record_audit
from app.auth_middleware import get_current_user, require_admin
from app.config import settings
from app.crypto.falcon_service import sign_document as falcon_sign
from app.crypto.qr_builder import (
    QR_ALGORITHM,
    b64url_encode,
    build_offline_payload,
    build_online_payload,
    render_png,
)
from app.database import get_session
from app.models import Document, DocumentStatus, User, UserRole
from app.schemas import DocumentResponse

router = APIRouter(prefix="/documents", tags=["documents"])

PDF_MAGIC = b"%PDF-"
CHUNK_SIZE = 8192
BACKEND_DIR = Path(__file__).resolve().parents[2]


def resolve_upload_dir() -> Path:
    """Resolve relative upload paths from the backend directory."""

    upload_dir = Path(settings.upload_dir)
    return upload_dir if upload_dir.is_absolute() else BACKEND_DIR / upload_dir


def _unix_timestamp(value: datetime) -> int:
    return int(value.timestamp())


def _new_qr_window() -> tuple[datetime, datetime]:
    issued_at = datetime.now(timezone.utc)
    return issued_at, issued_at + timedelta(days=settings.qr_validity_days)


def _require_signed_material(doc: Document) -> None:
    if doc.status != DocumentStatus.SIGNED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document not signed (status={doc.status.value})",
        )
    if doc.falcon_signature is None or doc.signing_public_key is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Signed document is missing verification key material",
        )


async def _get_doc_or_404(
    doc_id: uuid_lib.UUID,
    current_user: User,
    session: AsyncSession,
) -> Document:
    """Fetch a document by ID and enforce owner-or-admin access."""

    result = await session.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    if current_user.role != UserRole.ADMIN and doc.uploader_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return doc


async def _audit_upload_failure(
    session: AsyncSession,
    request: Request,
    current_user: User,
    outcome: str,
    detail: str,
    status_code: int,
) -> None:
    await record_audit(
        session,
        action="upload",
        outcome=outcome,
        request=request,
        actor_id=current_user.id,
        target_type="document",
        extra={"detail": detail},
    )
    raise HTTPException(status_code=status_code, detail=detail)


async def _audit_sign_failure(
    session: AsyncSession,
    request: Request,
    current_admin: User,
    doc_id: uuid_lib.UUID,
    outcome: str,
    detail: str,
    status_code: int,
) -> None:
    await record_audit(
        session,
        action="sign",
        outcome=outcome,
        request=request,
        actor_id=current_admin.id,
        target_type="document",
        target_id=doc_id,
        extra={"detail": detail},
    )
    raise HTTPException(status_code=status_code, detail=detail)


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Upload a PDF document with size, magic-byte and SHA-256 checks."""

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    contents = bytearray()
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        contents.extend(chunk)
        if len(contents) > max_bytes:
            await _audit_upload_failure(
                session,
                request,
                current_user,
                "file_too_large",
                f"File exceeds {settings.max_upload_size_mb} MB limit",
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

    if not contents:
        await _audit_upload_failure(
            session,
            request,
            current_user,
            "empty_file",
            "Uploaded file is empty",
            status.HTTP_400_BAD_REQUEST,
        )
    if bytes(contents[:5]) != PDF_MAGIC:
        await _audit_upload_failure(
            session,
            request,
            current_user,
            "invalid_pdf_magic",
            "File is not a valid PDF (magic-byte check failed)",
            status.HTTP_400_BAD_REQUEST,
        )

    file_bytes = bytes(contents)
    doc_id = uuid_lib.uuid4()
    upload_dir = resolve_upload_dir()
    storage_path = upload_dir / f"{doc_id}.pdf"

    try:
        upload_dir.mkdir(parents=True, exist_ok=True)
        storage_path.write_bytes(file_bytes)
        doc = Document(
            id=doc_id,
            uploader_id=current_user.id,
            filename=file.filename or "untitled.pdf",
            storage_path=str(storage_path),
            file_size=len(file_bytes),
            file_hash=hashlib.sha256(file_bytes).hexdigest(),
            status=DocumentStatus.PENDING,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
    except Exception:
        await session.rollback()
        storage_path.unlink(missing_ok=True)
        await _audit_upload_failure(
            session,
            request,
            current_user,
            "storage_or_database_error",
            "Unable to store uploaded document",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    await record_audit(
        session,
        action="upload",
        outcome="success",
        request=request,
        actor_id=current_user.id,
        target_type="document",
        target_id=doc.id,
        extra={"filename": doc.filename, "file_hash": doc.file_hash},
    )
    return doc


@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List documents: citizens see their own rows, admins see all rows."""

    query = select(Document).order_by(Document.created_at.desc())
    if current_user.role != UserRole.ADMIN:
        query = query.where(Document.uploader_id == current_user.id)
    result = await session.execute(query.limit(limit).offset(offset))
    return list(result.scalars().all())


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: uuid_lib.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await _get_doc_or_404(doc_id, current_user, session)


@router.get("/{doc_id}/download")
async def download_document(
    doc_id: uuid_lib.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    doc = await _get_doc_or_404(doc_id, current_user, session)
    file_path = Path(doc.storage_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File missing on disk",
        )
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=doc.filename,
    )


@router.post("/{doc_id}/sign", response_model=DocumentResponse)
async def sign_document_endpoint(
    doc_id: uuid_lib.UUID,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Sign an unchanged uploaded document with FALCON-512. Admin only."""

    result = await session.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        await _audit_sign_failure(
            session, request, current_admin, doc_id, "not_found",
            "Document not found", status.HTTP_404_NOT_FOUND,
        )
    if doc.status == DocumentStatus.SIGNED:
        await _audit_sign_failure(
            session, request, current_admin, doc_id, "already_signed",
            "Document already signed", status.HTTP_409_CONFLICT,
        )

    file_path = Path(doc.storage_path)
    if not file_path.exists():
        await _audit_sign_failure(
            session, request, current_admin, doc_id, "file_missing",
            "File missing on disk", status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    try:
        pdf_bytes = file_path.read_bytes()
    except OSError:
        await _audit_sign_failure(
            session, request, current_admin, doc_id, "file_read_error",
            "Unable to read document from disk", status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    current_hash = hashlib.sha256(pdf_bytes).hexdigest()
    if current_hash != doc.file_hash:
        await _audit_sign_failure(
            session, request, current_admin, doc_id, "hash_mismatch_before_sign",
            "Document hash changed after upload; refusing to sign",
            status.HTTP_409_CONFLICT,
        )

    try:
        signature, public_key = falcon_sign(pdf_bytes)
        doc.falcon_signature = signature
        doc.signing_public_key = public_key
        doc.signed_by = current_admin.id
        doc.signed_at = datetime.now(timezone.utc)
        doc.status = DocumentStatus.SIGNED
        doc.public_key_ref = hashlib.sha256(public_key).hexdigest()[:16]
        doc.qr_payload = None
        doc.qr_issued_at = None
        doc.qr_expires_at = None
        await session.commit()
        await session.refresh(doc)
    except Exception:
        await session.rollback()
        await _audit_sign_failure(
            session, request, current_admin, doc_id, "crypto_or_database_error",
            "Unable to sign document", status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    await record_audit(
        session,
        action="sign",
        outcome="success",
        request=request,
        actor_id=current_admin.id,
        target_type="document",
        target_id=doc.id,
        extra={"file_hash": doc.file_hash, "public_key_ref": doc.public_key_ref},
    )
    return doc


@router.post("/{doc_id}/qr")
async def generate_qr(
    doc_id: uuid_lib.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Generate a phone-scannable QR PNG that encodes a public verify URL."""

    doc = await _get_doc_or_404(doc_id, current_user, session)
    _require_signed_material(doc)

    issued_at, expires_at = _new_qr_window()
    verify_url = f"{str(request.base_url).rstrip('/')}/verify?d={doc.id}"
    doc.qr_issued_at = issued_at
    doc.qr_expires_at = expires_at
    doc.qr_payload = {
        "v": 1,
        "id": str(doc.id),
        "h": doc.file_hash,
        "ts": _unix_timestamp(issued_at),
        "ex": _unix_timestamp(expires_at),
        "alg": QR_ALGORITHM,
        "url": verify_url,
    }
    await session.commit()
    return Response(
        content=render_png(build_online_payload(verify_url)),
        media_type="image/png",
    )


@router.get("/{doc_id}/verification-package")
async def export_verification_package(
    doc_id: uuid_lib.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Export the signed payload and public key required by the offline CLI."""

    doc = await _get_doc_or_404(doc_id, current_user, session)
    _require_signed_material(doc)
    if doc.qr_issued_at is None or doc.qr_expires_at is None:
        doc.qr_issued_at, doc.qr_expires_at = _new_qr_window()
        await session.commit()

    offline_payload = build_offline_payload(
        doc_id=str(doc.id),
        doc_hash_hex=doc.file_hash,
        signature=doc.falcon_signature,
        issued_at=_unix_timestamp(doc.qr_issued_at),
        expires_at=_unix_timestamp(doc.qr_expires_at),
    )
    return {
        "v": 1,
        "document_id": str(doc.id),
        "document_hash": doc.file_hash,
        "offline_payload": offline_payload,
        "signature_b64url": b64url_encode(doc.falcon_signature),
        "algorithm": QR_ALGORITHM,
        "issued_at": _unix_timestamp(doc.qr_issued_at),
        "expires_at": _unix_timestamp(doc.qr_expires_at),
        "public_key_ref": doc.public_key_ref,
        "public_key_b64url": b64url_encode(doc.signing_public_key),
    }
