"""
Citizen Services Portal — Audit log endpoint.

GET /audit  — admin only; view audit_log entries with optional filters.

Mỗi action quan trọng (verify_qr, sign, login...) được ghi vào audit_log.
Endpoint này cho admin tra cứu — phục vụ non-repudiation + demo compliance.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_middleware import require_admin
from app.database import get_session
from app.models import AuditLog, User

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
async def list_audit_logs(
    action: Optional[str] = Query(
        None, description="Filter by action, e.g. verify_qr / sign / login"
    ),
    outcome: Optional[str] = Query(
        None, description="Filter by metadata outcome, e.g. valid / invalid / not_found"
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    List audit log entries (admin only). Newest first.

    Filters:
        action  — exact match on the action column
        outcome — match on extra_metadata->>'outcome'

    Returns:
        {
            "count":  number of entries in this page,
            "limit":  page size,
            "offset": page offset,
            "entries": [ { id, actor_id, action, target_type, target_id,
                           outcome, metadata, ip_address, user_agent,
                           created_at }, ... ]
        }
    """
    query = select(AuditLog).order_by(AuditLog.created_at.desc())

    if action:
        query = query.where(AuditLog.action == action)
    if outcome:
        # JSONB key lookup: extra_metadata->>'outcome' = :outcome
        query = query.where(AuditLog.extra_metadata["outcome"].astext == outcome)

    query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    logs = result.scalars().all()

    return {
        "count": len(logs),
        "limit": limit,
        "offset": offset,
        "entries": [
            {
                "id": str(log.id),
                "actor_id": str(log.actor_id) if log.actor_id else None,
                "action": log.action,
                "target_type": log.target_type,
                "target_id": str(log.target_id) if log.target_id else None,
                "outcome": (log.extra_metadata or {}).get("outcome"),
                "metadata": log.extra_metadata,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
    }
