"""Journalisation des actions utilisateur."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pg_models import AuditLog


async def log_action(
    db: AsyncSession,
    *,
    user_identifier: str,
    role: str,
    action: str,
    resource: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> None:
    entry = AuditLog(
        user_identifier=user_identifier,
        role=role,
        action=action,
        resource=resource,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.commit()
