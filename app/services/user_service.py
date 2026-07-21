"""Service CRUD utilisateurs — logique métier centralisée."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import case, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.pg_models import User
import secrets
from app.services.email_service import send_account_created_email

# ──────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────


def _user_to_dict(u: User) -> Dict[str, Any]:
    return {
        "id": u.id,
        "email": u.email,
        "role": u.role,
        "display_name": u.display_name,
        "jira_username": u.jira_username,
        "is_active": u.is_active,
        "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


# ──────────────────────────────────────────────────────────
#  Read
# ──────────────────────────────────────────────────────────


async def list_users(db: AsyncSession) -> List[Dict[str, Any]]:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return [_user_to_dict(u) for u in result.scalars().all()]


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[Dict[str, Any]]:
    result = await db.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    return _user_to_dict(u) if u else None


async def get_user_by_email_and_role(
    db: AsyncSession, email: str, role: str
) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.email == email, User.role == role)
    )
    return result.scalar_one_or_none()


async def get_users_by_email(db: AsyncSession, email: str) -> List[User]:
    result = await db.execute(
        select(User)
        .where(User.email == email)
        .order_by(case((User.role == "admin", 0), else_=1))
    )
    return result.scalars().all()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    users = await get_users_by_email(db, email)
    return users[0] if users else None


async def get_user_by_jira_username(
    db: AsyncSession, jira_username: str
) -> Optional[User]:
    result = await db.execute(select(User).where(User.jira_username == jira_username))
    return result.scalar_one_or_none()


# ──────────────────────────────────────────────────────────
#  Create
# ──────────────────────────────────────────────────────────


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    password: Optional[str] = None,
    role: str = "tester",
    display_name: Optional[str] = None,
    jira_username: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new user. Un même email peut être utilisé pour un compte admin
    ET un compte tester (deux comptes distincts), mais pas deux fois pour le même rôle.
    """
    existing = await get_user_by_email_and_role(db, email, role)
    if existing:
        role_label = "administrateur" if role == "admin" else "testeur"
        return {
            "ok": False,
            "error": f"Un compte {role_label} avec cet email existe déjà.",
        }

    if jira_username:
        existing_jira = await get_user_by_jira_username(db, jira_username)
        if existing_jira:
            return {
                "ok": False,
                "error": f"L'identifiant Jira '{jira_username}' est déjà enregistré.",
            }

    # Placeholder aléatoire : jamais utilisé pour se connecter (auth via Jira ou admin dédié)
    placeholder_password = password or secrets.token_urlsafe(32)

    user = User(
        email=email,
        hashed_password=hash_password(placeholder_password),
        role=role,
        display_name=display_name,
        jira_username=jira_username,
        is_active=True,
    )
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError as exc:
        await db.rollback()
        return {"ok": False, "error": str(exc.orig)}

    # Envoi de l'email de bienvenue (best-effort, ne bloque pas la création)
    email_sent = False
    if jira_username:
        email_sent = await send_account_created_email(
            email, jira_username, display_name
        )

    return {"ok": True, "user": _user_to_dict(user), "email_sent": email_sent}


# ──────────────────────────────────────────────────────────
#  Update
# ──────────────────────────────────────────────────────────


async def update_user(
    db: AsyncSession,
    user_id: int,
    *,
    display_name: Optional[str] = None,
    email: Optional[str] = None,
    jira_username: Optional[str] = None,
    password: Optional[str] = None,
    role: Optional[str] = None,
) -> Dict[str, Any]:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return {"ok": False, "error": "Utilisateur introuvable."}

    if display_name is not None:
        user.display_name = display_name
    if email is not None:
        # Unicité vérifiée par rapport au rôle ACTUEL du compte (pas email seul)
        existing_email = await get_user_by_email_and_role(db, email, user.role)
        if existing_email and existing_email.id != user_id:
            return {
                "ok": False,
                "error": f"Un autre compte {user.role} utilise déjà l'email '{email}'.",
            }
        user.email = email
    if jira_username is not None:
        existing_jira = await get_user_by_jira_username(db, jira_username)
        if existing_jira and existing_jira.id != user_id:
            return {
                "ok": False,
                "error": f"L'identifiant Jira '{jira_username}' est déjà utilisé.",
            }
        user.jira_username = jira_username
    if password:
        user.hashed_password = hash_password(password)
    if role and role in ("admin", "tester"):
        user.role = role

    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError as exc:
        await db.rollback()
        return {"ok": False, "error": str(exc.orig)}

    return {"ok": True, "user": _user_to_dict(user)}


# ──────────────────────────────────────────────────────────
#  Activate / Deactivate
# ──────────────────────────────────────────────────────────


async def set_user_active(
    db: AsyncSession, user_id: int, is_active: bool
) -> Dict[str, Any]:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return {"ok": False, "error": "Utilisateur introuvable."}
    if user.role == "admin" and not is_active:
        return {"ok": False, "error": "Impossible de désactiver un compte admin."}

    user.is_active = is_active
    await db.commit()
    return {"ok": True, "is_active": is_active}


# ──────────────────────────────────────────────────────────
#  Delete
# ──────────────────────────────────────────────────────────


async def delete_user(
    db: AsyncSession, user_id: int, current_admin_id: int
) -> Dict[str, Any]:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return {"ok": False, "error": "Utilisateur introuvable."}
    if user.id == current_admin_id:
        return {
            "ok": False,
            "error": "Vous ne pouvez pas supprimer votre propre compte.",
        }

    await db.delete(user)
    await db.commit()
    return {"ok": True}


# ──────────────────────────────────────────────────────────
#  Last login update
# ──────────────────────────────────────────────────────────


async def update_last_login(db: AsyncSession, user_id: int) -> None:
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(last_login_at=datetime.now(timezone.utc))
    )
    await db.commit()


# ──────────────────────────────────────────────────────────
#  Stats
# ──────────────────────────────────────────────────────────


async def get_stats(db: AsyncSession) -> Dict[str, Any]:
    from sqlalchemy import func as sqlfunc
    from app.models.pg_models import PipelineRun

    total_users = (await db.execute(select(sqlfunc.count(User.id)))).scalar() or 0
    active_users = (
        await db.execute(select(sqlfunc.count(User.id)).where(User.is_active))
    ).scalar() or 0
    tester_count = (
        await db.execute(select(sqlfunc.count(User.id)).where(User.role == "tester"))
    ).scalar() or 0
    total_pipelines = (
        await db.execute(select(sqlfunc.count(PipelineRun.id)))
    ).scalar() or 0
    successful_pipelines = (
        await db.execute(
            select(sqlfunc.count(PipelineRun.id)).where(
                PipelineRun.status == "completed"
            )
        )
    ).scalar() or 0

    return {
        "total_users": total_users,
        "active_users": active_users,
        "tester_count": tester_count,
        "admin_count": total_users - tester_count,
        "total_pipelines": total_pipelines,
        "successful_pipelines": successful_pipelines,
    }
