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
from app.auth_middleware import (
    get_current_user,
    require_admin,
    require_reviewer,
    require_signer,
)
from app.api.public_keys import (
    ALG_ED25519,
    ALG_MLDSA,
    make_key_id,
    register_public_key,
)
from app.config import settings
from app.crypto import ed25519_qr_service as ed25519
from app.crypto.mldsa_service import sign_document_async as mldsa_sign
from app.crypto.mldsa_service import verify_document as mldsa_verify_document
from app.crypto.qr_builder import (
    QR_ALGORITHM,
    b64url_encode,
    build_offline_payload,
    render_png,
)
from app.crypto.qr_hybrid import (
    QR_SIG_ALGORITHM,
    build_qr_canonical,
    build_qr_payload,
)
from app.database import get_session
from app.models import Document, DocumentStatus, User, UserRole
from app.schemas import DocumentResponse, ReviewRequest

router = APIRouter(prefix="/documents", tags=["documents"])

PDF_MAGIC = b"%PDF-"
CHUNK_SIZE = 8192
BACKEND_DIR = Path(__file__).resolve().parents[2]

# Staff roles can see and act on every document; citizens only see their own.
STAFF_ROLES = (UserRole.ADMIN, UserRole.REVIEWER, UserRole.SIGNER)


def _is_staff(user: User) -> bool:
    return user.role in STAFF_ROLES


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
    if doc.mldsa_signature is None or doc.signing_public_key is None:
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
    if not _is_staff(current_user) and doc.uploader_id != current_user.id:
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
            status=DocumentStatus.PENDING_REVIEW,
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
    if not _is_staff(current_user):
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


async def _load_reviewable_doc(
    session: AsyncSession,
    request: Request,
    reviewer: User,
    doc_id: uuid_lib.UUID,
    action: str,
) -> Document:
    """Fetch a document that is in a reviewable state, else audit + raise."""

    result = await session.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        await record_audit(
            session, action=action, outcome="not_found", request=request,
            actor_id=reviewer.id, target_type="document", target_id=doc_id,
        )
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    if doc.status not in (DocumentStatus.PENDING_REVIEW, DocumentStatus.PENDING):
        await record_audit(
            session, action=action, outcome="invalid_state", request=request,
            actor_id=reviewer.id, target_type="document", target_id=doc_id,
            extra={"status": doc.status.value},
        )
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Only a document awaiting review can be {action}d "
            f"(status={doc.status.value})",
        )
    return doc


@router.post("/{doc_id}/approve", response_model=DocumentResponse)
async def approve_document(
    doc_id: uuid_lib.UUID,
    request: Request,
    body: ReviewRequest | None = None,
    current_reviewer: User = Depends(require_reviewer),
    session: AsyncSession = Depends(get_session),
):
    """Approve a document for signing. Reviewer role only."""

    doc = await _load_reviewable_doc(session, request, current_reviewer, doc_id, "approve")
    doc.status = DocumentStatus.APPROVED
    doc.reviewed_by = current_reviewer.id
    doc.reviewed_at = datetime.now(timezone.utc)
    doc.review_note = body.note if body else None
    await session.commit()
    await session.refresh(doc)

    await record_audit(
        session, action="approve", outcome="success", request=request,
        actor_id=current_reviewer.id, target_type="document", target_id=doc.id,
        extra={"actor_role": current_reviewer.role.value},
    )
    return doc


@router.post("/{doc_id}/reject", response_model=DocumentResponse)
async def reject_document(
    doc_id: uuid_lib.UUID,
    request: Request,
    body: ReviewRequest,
    current_reviewer: User = Depends(require_reviewer),
    session: AsyncSession = Depends(get_session),
):
    """Reject a document with a mandatory review note. Reviewer role only."""

    if not body.note or not body.note.strip():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "A review note is required when rejecting a document",
        )

    doc = await _load_reviewable_doc(session, request, current_reviewer, doc_id, "reject")
    doc.status = DocumentStatus.REJECTED
    doc.reviewed_by = current_reviewer.id
    doc.reviewed_at = datetime.now(timezone.utc)
    doc.review_note = body.note
    await session.commit()
    await session.refresh(doc)

    await record_audit(
        session, action="reject", outcome="success", request=request,
        actor_id=current_reviewer.id, target_type="document", target_id=doc.id,
        extra={"actor_role": current_reviewer.role.value},
    )
    return doc


@router.post("/{doc_id}/sign", response_model=DocumentResponse)
async def sign_document_endpoint(
    doc_id: uuid_lib.UUID,
    request: Request,
    current_signer: User = Depends(require_signer),
    session: AsyncSession = Depends(get_session),
):
    """Sign an approved, unchanged document with ML-DSA-44. Signer role only.

    Enforces the review workflow (document must be APPROVED) and separation of
    duty (the reviewer who approved a document may not also sign it).
    """

    result = await session.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        await _audit_sign_failure(
            session, request, current_signer, doc_id, "not_found",
            "Document not found", status.HTTP_404_NOT_FOUND,
        )
    if doc.status == DocumentStatus.SIGNED:
        await _audit_sign_failure(
            session, request, current_signer, doc_id, "already_signed",
            "Document already signed", status.HTTP_409_CONFLICT,
        )
    if doc.status != DocumentStatus.APPROVED:
        await _audit_sign_failure(
            session, request, current_signer, doc_id, "document_not_approved",
            f"Document must be approved by a reviewer before signing "
            f"(status={doc.status.value})",
            status.HTTP_409_CONFLICT,
        )
    if doc.reviewed_by is not None and doc.reviewed_by == current_signer.id:
        await _audit_sign_failure(
            session, request, current_signer, doc_id, "separation_of_duty",
            "The reviewer who approved a document may not also sign it",
            status.HTTP_403_FORBIDDEN,
        )

    file_path = Path(doc.storage_path)
    if not file_path.exists():
        await _audit_sign_failure(
            session, request, current_signer, doc_id, "file_missing",
            "File missing on disk", status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    try:
        pdf_bytes = file_path.read_bytes()
    except OSError:
        await _audit_sign_failure(
            session, request, current_signer, doc_id, "file_read_error",
            "Unable to read document from disk", status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    current_hash = hashlib.sha256(pdf_bytes).hexdigest()
    if current_hash != doc.file_hash:
        await _audit_sign_failure(
            session, request, current_signer, doc_id, "hash_mismatch_before_sign",
            "Document hash changed after upload; refusing to sign",
            status.HTTP_409_CONFLICT,
        )

    try:
        # 1) Primary post-quantum signature: ML-DSA-44 over SHA-256(PDF).
        signature, public_key = await mldsa_sign(pdf_bytes)

        # 2) Small offline QR signature: Ed25519 over the QR canonical string.
        issued_at, expires_at = _new_qr_window()
        signed_at = datetime.now(timezone.utc)
        qr_public_key, _ = await ed25519.load_or_create_keys()
        qr_public_key_ref = make_key_id(ALG_ED25519, qr_public_key)
        canonical = build_qr_canonical(
            doc_id=str(doc.id),
            file_hash=doc.file_hash,
            signer_email=current_signer.email,
            signed_at=signed_at,
            valid_from=issued_at,
            valid_until=expires_at,
            qr_public_key_ref=qr_public_key_ref,
        )
        qr_signature, _ = await ed25519.sign_qr_async(canonical)

        # 3) Self-check: verify both signatures before persisting.
        if not mldsa_verify_document(pdf_bytes, signature, public_key,
                                     expected_hash_hex=doc.file_hash):
            raise RuntimeError("ML-DSA self-check failed")
        if not ed25519.verify_qr(canonical, qr_signature, qr_public_key):
            raise RuntimeError("Ed25519 QR self-check failed")

        qr_payload_str = build_qr_payload(
            qr_signature=qr_signature,
            doc_id=str(doc.id),
            file_hash=doc.file_hash,
            signer_email=current_signer.email,
            signed_at=signed_at,
            valid_from=issued_at,
            valid_until=expires_at,
            qr_public_key_ref=qr_public_key_ref,
        )

        doc.mldsa_signature = signature
        doc.signing_public_key = public_key
        doc.qr_signature = qr_signature
        doc.signed_by = current_signer.id
        doc.signed_at = signed_at
        doc.status = DocumentStatus.SIGNED
        doc.public_key_ref = await register_public_key(
            session, algorithm=ALG_MLDSA, public_key=public_key
        )
        doc.qr_public_key_ref = await register_public_key(
            session, algorithm=ALG_ED25519, public_key=qr_public_key
        )
        doc.qr_issued_at = issued_at
        doc.qr_expires_at = expires_at
        doc.qr_payload = {
            "v": 2,
            "format": "hybrid-ed25519",
            "alg": QR_SIG_ALGORITHM,
            "payload": qr_payload_str,
        }
        await session.commit()
        await session.refresh(doc)
    except Exception:
        await session.rollback()
        await _audit_sign_failure(
            session, request, current_signer, doc_id, "crypto_or_database_error",
            "Unable to sign document", status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    await record_audit(
        session,
        action="sign",
        outcome="success",
        request=request,
        actor_id=current_signer.id,
        target_type="document",
        target_id=doc.id,
        extra={
            "file_hash": doc.file_hash,
            "public_key_ref": doc.public_key_ref,
            "actor_role": current_signer.role.value,
        },
    )
    return doc


@router.post("/{doc_id}/qr")
async def generate_qr(
    doc_id: uuid_lib.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Render the signed document's self-contained offline QR (Ed25519) as a PNG.

    The QR payload is produced at sign time and stored on the document; this
    endpoint just renders it. Accessible to the document owner or staff.
    """

    doc = await _get_doc_or_404(doc_id, current_user, session)
    _require_signed_material(doc)

    payload = doc.qr_payload or {}
    payload_str = payload.get("payload") if isinstance(payload, dict) else None
    if not payload_str:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Signed document has no offline QR payload; re-sign required",
        )
    return Response(content=render_png(payload_str), media_type="image/png")


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
        signature=doc.mldsa_signature,
        issued_at=_unix_timestamp(doc.qr_issued_at),
        expires_at=_unix_timestamp(doc.qr_expires_at),
    )
    return {
        "v": 1,
        "document_id": str(doc.id),
        "document_hash": doc.file_hash,
        "offline_payload": offline_payload,
        "signature_b64url": b64url_encode(doc.mldsa_signature),
        "algorithm": QR_ALGORITHM,
        "issued_at": _unix_timestamp(doc.qr_issued_at),
        "expires_at": _unix_timestamp(doc.qr_expires_at),
        "public_key_ref": doc.public_key_ref,
        "public_key_b64url": b64url_encode(doc.signing_public_key),
    }
