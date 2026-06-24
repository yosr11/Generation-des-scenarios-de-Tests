"""Service d'authentification admin (PostgreSQL) et testeur (Jira)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.pg_models import User
from app.services.credential_store import remove_credentials, store_credentials
from app.services.jira_auth_service import (
    create_tester_session_id,
    get_accessible_projects,
    validate_jira_credentials,
)


async def seed_admin_user(db: AsyncSession) -> None:
    """Crée l'admin par défaut depuis .env s'il n'existe pas."""
    result = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
    existing = result.scalar_one_or_none()
    if existing:
        return
    admin = User(
        email=settings.ADMIN_EMAIL,
        hashed_password=hash_password(settings.ADMIN_PASSWORD),
        role="admin",
    )
    db.add(admin)
    await db.commit()


async def authenticate_admin(db: AsyncSession, email: str, password: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or user.role != "admin":
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def build_admin_token(user: User) -> str:
    return create_access_token(
        {
            "sub": str(user.id),
            "email": user.email,
            "role": "admin",
        }
    )


async def authenticate_tester(username: str, password: str) -> Dict[str, Any]:
    """Valide les credentials Jira et retourne token + projets."""
    validation = await validate_jira_credentials(username, password)
    if not validation.get("valid"):
        return {
            "success": False,
            "error": validation.get("error", "Invalid Jira credentials"),
        }

    projects = await get_accessible_projects(username, password)
    if not projects:
        return {
            "success": False,
            "error": "No project access. Contact your administrator.",
            "no_projects": True,
        }

    session_id = create_tester_session_id()
    store_credentials(session_id, username, password)

    token = create_access_token(
        {
            "sub": validation["account_id"],
            "email": validation.get("email") or username,
            "role": "tester",
            "jira_username": username,
            "display_name": validation.get("display_name"),
            "session_id": session_id,
        }
    )

    return {
        "success": True,
        "access_token": token,
        "user": {
            "email": validation.get("email") or username,
            "display_name": validation.get("display_name"),
            "role": "tester",
            "jira_username": username,
        },
        "projects": projects,
    }


def logout_tester(session_id: Optional[str]) -> None:
    if session_id:
        remove_credentials(session_id)
