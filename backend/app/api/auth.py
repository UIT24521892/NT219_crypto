"""
Citizen Services Portal — Authentication endpoints.
POST /auth/register, POST /auth/login, GET /auth/me
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit_utils import record_audit
from app.auth_middleware import get_current_user
from app.config import settings
from app.database import get_session
from app.models import User, UserRole
from app.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create a new citizen account."""
    existing = await session.execute(
        select(User).where(User.email == body.email)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        role=UserRole.CITIZEN,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Exchange email + password for a JWT access token."""
    result = await session.execute(
        select(User).where(User.email == body.email)
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        await record_audit(
            session,
            action="login",
            outcome="invalid_credentials",
            request=request,
            actor_id=(user.id if user else None),
            target_type="user",
            target_id=(user.id if user else None),
            extra={"email": str(body.email)},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not user.is_active:
        await record_audit(
            session,
            action="login",
            outcome="account_disabled",
            request=request,
            actor_id=user.id,
            target_type="user",
            target_id=user.id,
            extra={"email": user.email},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )
    token = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role.value, "email": user.email},
    )
    response = TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.jwt_expires_minutes * 60,
    )
    await record_audit(
        session,
        action="login",
        outcome="success",
        request=request,
        actor_id=user.id,
        target_type="user",
        target_id=user.id,
        extra={"email": user.email},
    )
    return response


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    """Return info about the currently authenticated user."""
    return current_user
