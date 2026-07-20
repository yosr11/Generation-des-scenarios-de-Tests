"""Routes Admin — CRUD utilisateurs, historique pipelines, audit."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_current_user
from app.db.postgres import get_db
from app.models.pg_models import AuditLog, PipelineRun ,User
from app.services.user_service import (
    create_user,
    delete_user,
    get_user_by_id,
    list_users,
    set_user_active,
    update_user,
    get_stats,
)
from app.core.cookies import set_auth_cookie
from app.services.auth_service import build_admin_token, build_user_token
router = APIRouter(prefix="/admin", tags=["Admin"])


# ──────────────────────────────────────────────────────────
#  Guard helper
# ──────────────────────────────────────────────────────────

def _require_admin(user: CurrentUser) -> None:
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Réservé aux administrateurs.")


# ──────────────────────────────────────────────────────────
#  Schemas
# ──────────────────────────────────────────────────────────

class CreateUserRequest(BaseModel):
    email: EmailStr
    role: str = Field(default="tester", pattern="^(admin|tester)$")
    display_name: Optional[str] = None
    jira_username: Optional[str] = None


class UpdateUserRequest(BaseModel):
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None
    jira_username: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=6)
    role: Optional[str] = Field(default=None, pattern="^(admin|tester)$")


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    display_name: Optional[str]
    jira_username: Optional[str]
    is_active: bool
    last_login_at: Optional[str]
    created_at: Optional[str]
    email_sent: Optional[bool] = None


# ──────────────────────────────────────────────────────────
#  Stats
# ──────────────────────────────────────────────────────────

@router.get("/stats")
async def admin_stats(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    return await get_stats(db)


# ──────────────────────────────────────────────────────────
#  Users CRUD
# ──────────────────────────────────────────────────────────

@router.get("/users", response_model=List[UserOut])
async def admin_list_users(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    return await list_users(db)


@router.post("/users", response_model=UserOut, status_code=201)
async def admin_create_user(
    body: CreateUserRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    result = await create_user(
        db,
        email=body.email,
        role=body.role,
        display_name=body.display_name,
        jira_username=body.jira_username,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return {**result["user"], "email_sent": result.get("email_sent", False)}


@router.get("/users/{user_id}", response_model=UserOut)
async def admin_get_user(
    user_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
async def admin_update_user(
    user_id: int,
    body: UpdateUserRequest,
    response: Response,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    target_user = await get_user_by_id(db, user_id)
    if target_user and target_user["role"] == "tester":
        raise HTTPException(
            status_code=403,
            detail="Modification des comptes testeur non autorisée depuis cet écran.",
        )

    result = await update_user(
        db,
        user_id,
        display_name=body.display_name,
        email=body.email,
        jira_username=body.jira_username,
        password=body.password,
        role=body.role,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    # Si l'admin modifie SON PROPRE compte, réémet le cookie avec les infos à jour
    if user_id == current_user.user_id_int:
        fresh_result = await db.execute(select(User).where(User.id == user_id))
        fresh_user = fresh_result.scalar_one_or_none()
        if fresh_user:
            new_token = build_admin_token(fresh_user) if fresh_user.role == "admin" else build_user_token(fresh_user)
            set_auth_cookie(response, new_token)

    return result["user"]


@router.delete("/users/{user_id}", status_code=204)
async def admin_delete_user(
    user_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    result = await delete_user(db, user_id, current_admin_id=current_user.user_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error"))


@router.post("/users/{user_id}/activate", status_code=200)
async def admin_activate_user(
    user_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    result = await set_user_active(db, user_id, is_active=True)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/users/{user_id}/deactivate", status_code=200)
async def admin_deactivate_user(
    user_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    result = await set_user_active(db, user_id, is_active=False)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


# ──────────────────────────────────────────────────────────
#  Pipeline runs history
# ──────────────────────────────────────────────────────────

@router.get("/pipelines")
async def admin_pipeline_history(
    limit: int = 100,
    offset: int = 0,
    launched_by: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    stmt = select(PipelineRun).order_by(desc(PipelineRun.started_at)).limit(limit).offset(offset)
    if launched_by:
        stmt = stmt.where(PipelineRun.launched_by == launched_by)
    result = await db.execute(stmt)
    runs = result.scalars().all()
    return {
        "total": len(runs),
        "runs": [
            {
                "id": r.id,
                "story_id": r.story_id,
                "launched_by": r.launched_by,
                "status": r.status,
                "use_rag": r.use_rag,
                "use_legacy_rag": r.use_legacy_rag,
                "run_agent4": r.run_agent4,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "tests_count": r.tests_count,
                "error_message": r.error_message,
            }
            for r in runs
        ],
    }


# ──────────────────────────────────────────────────────────
#  Audit log
# ──────────────────────────────────────────────────────────

@router.get("/audit")
async def admin_audit_log(
    limit: int = 100,
    offset: int = 0,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    stmt = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit).offset(offset)
    result = await db.execute(stmt)
    logs = result.scalars().all()
    return {
        "total": len(logs),
        "logs": [
            {
                "id": lg.id,
                "user_identifier": lg.user_identifier,
                "role": lg.role,
                "action": lg.action,
                "resource": lg.resource,
                "details": lg.details,
                "ip_address": lg.ip_address,
                "created_at": lg.created_at.isoformat() if lg.created_at else None,
            }
            for lg in logs
        ],
    }
