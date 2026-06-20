"""
Citizen Services Portal — government agencies (issuing authorities).

A signer acts on behalf of an agency; the agency is recorded per signed document
and bound into the signed QR + PDF. There is a single State post-quantum signing
key — agencies are organizational attribution, not separate key holders.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit_utils import record_audit
from app.auth_middleware import get_current_user, require_admin
from app.database import get_session
from app.models import Agency, User
from app.schemas import AgencyResponse, AssignAgencyRequest, UserResponse

router = APIRouter(prefix="/agencies", tags=["agencies"])


@router.get("", response_model=List[AgencyResponse])
async def list_agencies(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List active government bodies (for display and signer assignment)."""

    result = await session.execute(
        select(Agency).where(Agency.is_active.is_(True)).order_by(Agency.id)
    )
    return list(result.scalars().all())


@router.put("/assign", response_model=UserResponse)
async def assign_agency(
    payload: AssignAgencyRequest,
    request: Request,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Admin sets (or clears) the agency a signer/reviewer acts for."""

    user_result = await session.execute(
        select(User).where(User.email == payload.user_email)
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    agency_id = None
    agency_code = None
    if payload.agency_code:
        agency_result = await session.execute(
            select(Agency).where(Agency.code == payload.agency_code)
        )
        agency = agency_result.scalar_one_or_none()
        if agency is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found"
            )
        agency_id = agency.id
        agency_code = agency.code

    user.agency_id = agency_id
    await session.commit()
    await session.refresh(user)

    await record_audit(
        session,
        action="assign_agency",
        outcome="success",
        request=request,
        actor_id=admin.id,
        target_type="user",
        target_id=user.id,
        extra={"agency_code": agency_code, "agency_id": agency_id},
    )
    return user
