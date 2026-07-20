"""Service d'authentification unifié — un seul point d'entrée pour admin et testeur."""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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


# ── Seed ──────────────────────────────────────────────────────────────────────

async def seed_admin_user(db: AsyncSession) -> None:
    """Crée l'admin par défaut UNIQUEMENT si aucun admin n'existe déjà."""
    result = await db.execute(select(User).where(User.role == "admin"))
    if result.scalars().first():
        return
    admin = User(
        email=settings.ADMIN_EMAIL,
        hashed_password=hash_password(settings.ADMIN_PASSWORD),
        role="admin",
    )
    db.add(admin)
    await db.commit()


# ── User creation ─────────────────────────────────────────────────────────────

async def create_user(
    db: AsyncSession,
    email: str,
    password: str,
    role: str = "tester",
    display_name: Optional[str] = None,
    jira_username: Optional[str] = None,
) -> dict:
    """Crée un utilisateur PostgreSQL (outil admin)."""
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        return {"ok": False, "error": "Cet email est déjà utilisé."}

    user = User(
        email=email,
        hashed_password=hash_password(password),
        role=role,
        display_name=display_name,
        jira_username=jira_username,
    )
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError as exc:
        await db.rollback()
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "user": user}


# ── Admin auth helpers (kept for internal use) ────────────────────────────────


async def _authenticate_admin(db: AsyncSession, email: str, password: str) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.email == email, User.role == "admin")
    )
    user = result.scalar_one_or_none()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def build_admin_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": "admin",
    }
    payload["display_name"] = user.display_name or user.email.split("@")[0]
    return create_access_token(payload)

def build_user_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
    }
    if user.display_name:
        payload["display_name"] = user.display_name
    if user.jira_username:
        payload["jira_username"] = user.jira_username
    return create_access_token(payload)

# ── Tester auth helpers (kept for internal use) ───────────────────────────────

async def _authenticate_tester(username: str, password: str) -> Dict[str, Any]:
    """Valide les credentials Jira et retourne token + projets."""
    validation = await validate_jira_credentials(username, password)
    if not validation.get("valid"):
        return {
            "success": False,
            "error": validation.get("error", "Identifiants Jira invalides."),
        }

    projects = await get_accessible_projects(username, password)
    if not projects:
        return {
            "success": False,
            "error": "Aucun projet accessible. Contactez votre administrateur.",
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


# ── Unified entry-point ───────────────────────────────────────────────────────

async def authenticate_user(
    db: AsyncSession,
    *,
    identifier: str,
    password: str,
) -> Dict[str, Any]:
    """
    Point d'entrée unique pour l'authentification.

    Stratégie de détection du rôle :
      1. On cherche d'abord un compte admin en base (email + hash bcrypt).
      2. Si trouvé → flux admin.
      3. Sinon → flux testeur Jira (l'identifier est le username Jira).

    Retourne un dict standardisé :
      {
        "success": bool,
        "role": "admin" | "tester",          # présent si success
        "access_token": str,                  # présent si success
        "user": { ... },                      # présent si success
        "projects": [...] | None,             # présent si success (None pour admin)
        "error": str,                         # présent si not success
        "no_projects": bool,                  # présent si not success + no_projects
      }
    """
    # ── 1. Tentative admin ────────────────────────────────────────────────────
    admin_user = await _authenticate_admin(db, email=identifier, password=password)
    if admin_user is not None:
        if not admin_user.is_active:
            return {
                "success": False,
                "error": "Ce compte est désactivé. Contactez un administrateur.",
            }
        token = build_admin_token(admin_user)
        return {
            "success": True,
            "role": "admin",
            "access_token": token,
            "user": {
                "id": admin_user.id,
                "email": admin_user.email,
                "role": "admin",
                "display_name": admin_user.display_name or admin_user.email.split("@")[0],
            },
            "projects": None,
        }

    # ── 2. Tentative testeur Jira ─────────────────────────────────────────────
    tester_result = await _authenticate_tester(username=identifier, password=password)
    if not tester_result.get("success"):
        # Propagate no_projects flag if present
        return tester_result

    # Vérification que le testeur est bien enregistré et actif en base
    from app.services.user_service import get_user_by_jira_username  # local import to avoid circular
    db_tester = await get_user_by_jira_username(db, identifier)
    if not db_tester:
        return {
            "success": False,
            "error": (
                "Votre compte n'est pas autorisé sur cette application. "
                "Contactez votre administrateur."
            ),
        }
    if not db_tester.is_active:
        return {
            "success": False,
            "error": "Ce compte est désactivé. Contactez votre administrateur.",
        }

    return {**tester_result, "role": "tester"}


# ── Logout ────────────────────────────────────────────────────────────────────

def logout_tester(session_id: Optional[str]) -> None:
    if session_id:
        remove_credentials(session_id)


# ── Legacy aliases (backward-compat, keep until all callers migrated) ─────────
authenticate_admin = _authenticate_admin
authenticate_tester = _authenticate_tester