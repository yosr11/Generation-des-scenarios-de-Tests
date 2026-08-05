"""Journalisation des actions utilisateur."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession


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
    # Audit log supprimé : on ne persiste plus d'entrée dans la base.
    return None
