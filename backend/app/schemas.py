"""
Citizen Services Portal — Pydantic request/response schemas.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import DocumentStatus, UserRole


# ---------- Authentication ----------

class RegisterRequest(BaseModel):
    """POST /auth/register body."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, password: str) -> str:
        if len(password.encode("utf-8")) > 72:
            raise ValueError("password must not exceed 72 UTF-8 bytes")
        return password


class LoginRequest(BaseModel):
    """POST /auth/login body."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """POST /auth/login response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """Public user info returned from /auth/register and /auth/me."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    role: UserRole
    agency_id: Optional[int] = None
    is_active: bool
    created_at: datetime


# ---------- Agencies (issuing government bodies) ----------

class AgencyResponse(BaseModel):
    """A government body / state agency on whose behalf signers issue documents."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    level: str


class AssignAgencyRequest(BaseModel):
    """Admin assigns (or clears) the agency a signer/reviewer acts for."""
    user_email: EmailStr
    agency_code: Optional[str] = Field(default=None, max_length=32)


# ---------- Documents ----------

class ReviewRequest(BaseModel):
    """POST /documents/{id}/approve and /reject body."""
    note: Optional[str] = Field(default=None, max_length=2000)


class DocumentResponse(BaseModel):
    """Document metadata returned from /documents endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    uploader_id: uuid.UUID
    filename: str
    file_size: int
    file_hash: str
    status: DocumentStatus
    reviewed_by: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    review_note: Optional[str] = None
    signed_by: Optional[uuid.UUID] = None
    signed_at: Optional[datetime] = None
    signing_agency_id: Optional[int] = None
    signing_agency_name: Optional[str] = None
    has_signed_pdf: bool = False
    public_key_ref: Optional[str] = None
    qr_public_key_ref: Optional[str] = None
    qr_issued_at: Optional[datetime] = None
    qr_expires_at: Optional[datetime] = None
    created_at: datetime
