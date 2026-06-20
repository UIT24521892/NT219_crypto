"""
Citizen Services Portal — SQLAlchemy ORM models.
Tables: users, documents, audit_log.
"""
import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    LargeBinary,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserRole(str, enum.Enum):
    CITIZEN = "citizen"
    ADMIN = "admin"
    REVIEWER = "reviewer"
    SIGNER = "signer"


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    SIGNED = "signed"
    REJECTED = "rejected"


class PublicKeyStatus(str, enum.Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class User(Base):
    """Nguoi dung — citizen hoac admin."""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role"),
        nullable=False, default=UserRole.CITIZEN,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Document(Base):
    """Tai lieu PDF do citizen upload; reviewer duyet, signer ky hybrid ML-DSA + Ed25519."""
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    uploader_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(DocumentStatus, name="document_status"),
        nullable=False, default=DocumentStatus.PENDING, index=True,
    )

    # --- Review workflow (reviewer approves before a signer can sign) ---
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_note: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # --- Primary post-quantum signature (ML-DSA-44 over SHA-256(PDF)) ---
    mldsa_signature: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    signing_public_key: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    public_key_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # --- Offline QR signature (Ed25519 over the QR canonical string) ---
    qr_signature: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    qr_public_key_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    signed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    signed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    signed_pdf_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    qr_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    qr_issued_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    qr_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class PublicKey(Base):
    """Public Key Directory / Trust Registry — one row per issuing public key.

    Holds both the ML-DSA-44 signing key and the Ed25519 QR key, each addressed by
    a ``key_id`` of the form ``<algorithm>:<fingerprint-prefix>``.
    """
    __tablename__ = "public_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False)
    public_key_bytes: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    fingerprint: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    owner_name: Mapped[str] = mapped_column(
        String(255), nullable=False, default="Issuing Authority"
    )
    status: Mapped[PublicKeyStatus] = mapped_column(
        SQLEnum(PublicKeyStatus, name="public_key_status"),
        nullable=False, default=PublicKeyStatus.ACTIVE, index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AuditLog(Base):
    """Log non-repudiation cho moi action quan trong (login, upload, sign, verify...)."""
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    target_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False, index=True,
    )
