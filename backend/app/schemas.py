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
    is_active: bool
    created_at: datetime


# ---------- Documents ----------

class DocumentResponse(BaseModel):
    """Document metadata returned from /documents endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    uploader_id: uuid.UUID
    filename: str
    file_size: int
    file_hash: str
    status: DocumentStatus
    signed_by: Optional[uuid.UUID] = None
    signed_at: Optional[datetime] = None
    public_key_ref: Optional[str] = None
    qr_issued_at: Optional[datetime] = None
    qr_expires_at: Optional[datetime] = None
    created_at: datetime
