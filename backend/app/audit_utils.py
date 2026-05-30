"""Best-effort helpers for security audit logging."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def record_audit(
    session: AsyncSession,
    *,
    action: str,
    outcome: str,
    request: Request | None = None,
    actor_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Write one audit row without allowing log failure to break the API."""

    metadata = {"outcome": outcome, **(extra or {})}
    try:
        session.add(
            AuditLog(
                actor_id=actor_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                extra_metadata=metadata,
                ip_address=(request.client.host if request and request.client else None),
                user_agent=(request.headers.get("user-agent") if request else None),
            )
        )
        await session.commit()
    except Exception:
        await session.rollback()
