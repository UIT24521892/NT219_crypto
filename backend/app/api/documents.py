"""
Citizen Services Portal — Document endpoints.

POST /documents/upload         — upload a PDF (any authenticated user)
GET  /documents                — list documents (citizen: own, admin: all)
GET  /documents/{id}           — get document metadata (owner or admin)
GET  /documents/{id}/download  — download PDF binary (owner or admin)
POST /documents/{id}/sign      — sign with FALCON-512 (admin only)
POST /documents/{id}/qr        — generate QR code for signed document (owner or admin)
"""
import hashlib
import uuid as uuid_lib
from datetime import datetime, timezone
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

from app.auth_middleware import get_current_user, require_admin
from app.config import settings
from app.crypto.falcon_service import sign_document as falcon_sign
from app.crypto.qr_builder import build_payload as qr_build_payload
from app.crypto.qr_builder import render_png as qr_render_png
from app.database import get_session
from app.models import Document, DocumentStatus, User, UserRole
from app.schemas import DocumentResponse

router = APIRouter(prefix="/documents", tags=["documents"])

PDF_MAGIC = b"%PDF-"
STORAGE_DIR = Path("storage/uploads")
CHUNK_SIZE = 8192


async def _get_doc_or_404(
    doc_id: uuid_lib.UUID,
    current_user: User,
    session: AsyncSession,
) -> Document:
    """Fetch a document by ID and enforce RBAC. 404 on miss OR forbidden."""
    result = await session.execute(
        select(Document).where(Document.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    if (
        current_user.role != UserRole.ADMIN
        and doc.uploader_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return doc


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Upload a PDF document; PDF-magic + size + SHA-256 enforced."""
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

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
        status=DocumentStatus.PENDING,
    )
    session.add(doc)
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
    """Get document metadata. Owner or admin only (404 otherwise)."""
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
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Sign a document with FALCON-512. Admin only. 409 if already signed."""
    result = await session.execute(
        select(Document).where(Document.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    if doc.status == DocumentStatus.SIGNED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document already signed",
        )

    file_path = Path(doc.storage_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File missing on disk",
        )

    pdf_bytes = file_path.read_bytes()
    signature, public_key = falcon_sign(pdf_bytes)

    doc.falcon_signature = signature
    doc.signed_by = current_admin.id
    doc.signed_at = datetime.now(timezone.utc)
    doc.status = DocumentStatus.SIGNED
    doc.public_key_ref = hashlib.sha256(public_key).hexdigest()[:16]

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
    Generate a PNG QR code for a SIGNED document.

    The QR encodes a compact JSON payload with the verification URL.
    The full FALCON signature stays server-side (too large for QR);
    the scanner hits /verify?d=<doc_id> to validate.

    Returns PNG image (200) for signed docs, 400 if doc is still pending,
    404 if doc doesn't exist or caller lacks access.
    """
    doc = await _get_doc_or_404(doc_id, current_user, session)

    if doc.status != DocumentStatus.SIGNED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document not signed (status={doc.status.value})",
        )

    base_url = str(request.base_url).rstrip("/")
    verify_url = f"{base_url}/verify?d={doc.id}"

    payload = qr_build_payload(
        doc_id=str(doc.id),
        file_hash=doc.file_hash,
        verify_url=verify_url,
    )
    png_bytes = qr_render_png(payload)

    # Cache the payload on the document for later inspection / debugging
    doc.qr_payload = payload
    await session.commit()

    return Response(content=png_bytes, media_type="image/png")
