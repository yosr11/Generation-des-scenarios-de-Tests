"""Routes d'authentification : admin (PostgreSQL) et testeur (Jira)."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import CurrentUser, get_client_ip, get_current_user
from app.db.postgres import get_db
from app.services.audit_service import log_action
from app.services.auth_service import authenticate_admin, authenticate_tester, build_admin_token, logout_tester
from app.services.user_service import get_user_by_jira_username, update_last_login

router = APIRouter(prefix="/auth", tags=["Authentication"])


class AdminLoginRequest(BaseModel):
    email: str = Field(..., description="Admin email")
    password: str = Field(..., min_length=1)


class TesterLoginRequest(BaseModel):
    username: str = Field(..., min_length=1, description="Jira username")
    password: str = Field(..., min_length=1, description="Jira password")


class ProjectInfo(BaseModel):
    key: str
    name: str
    id: Optional[str] = None
    project_type: Optional[str] = None


class LoginResponse(BaseModel):
    user: dict
    projects: Optional[List[ProjectInfo]] = None


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.COOKIE_NAME, path="/")


@router.post("/login/admin", response_model=LoginResponse)
async def login_admin(
    body: AdminLoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    user = await authenticate_admin(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Email ou mot de passe invalide.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Ce compte est désactivé. Contactez un administrateur.")

    token = build_admin_token(user)
    _set_auth_cookie(response, token)

    await update_last_login(db, user.id)

    await log_action(
        db,
        user_identifier=user.email,
        role="admin",
        action="login",
        ip_address=get_client_ip(request),
    )

    return LoginResponse(
        user={
            "id": user.id,
            "email": user.email,
            "role": "admin",
            "display_name": user.display_name or user.email.split("@")[0],
        },
    )


@router.post("/login/tester", response_model=LoginResponse)
async def login_tester(
    body: TesterLoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    result = await authenticate_tester(body.username, body.password)
    if not result.get("success"):
        if result.get("no_projects"):
            raise HTTPException(status_code=403, detail=result["error"])
        raise HTTPException(status_code=401, detail=result.get("error", "Authentication failed"))

    # Update last_login if the tester is registered in the DB
    db_tester = await get_user_by_jira_username(db, body.username)
    if not db_tester:
        raise HTTPException(
            status_code=403,
            detail="Votre compte n'est pas autorisé sur cette application. Contactez votre administrateur.",
        )
    if not db_tester.is_active:
        raise HTTPException(
            status_code=403,
            detail="Ce compte est désactivé. Contactez votre administrateur.",
        )
    await update_last_login(db, db_tester.id)

    _set_auth_cookie(response, result["access_token"])

    await log_action(
        db,
        user_identifier=body.username,
        role="tester",
        action="login",
        details=f"Projects: {len(result['projects'])}",
        ip_address=get_client_ip(request),
    )

    return LoginResponse(
        user=result["user"],
        projects=[ProjectInfo(**p) for p in result["projects"]],
    )


@router.get("/me")
async def get_me(user: CurrentUser = Depends(get_current_user)):
    return {
        "user_id": user.user_id,
        "email": user.email,
        "role": user.role,
        "jira_username": user.jira_username,
        "display_name": user.display_name,
    }


@router.get("/projects")
async def get_my_projects(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Projets Jira accessibles (testeur uniquement, fetch live)."""
    if not user.is_tester:
        raise HTTPException(status_code=403, detail="Only testers have Jira projects")

    from app.services.credential_store import get_credentials
    from app.services.jira_auth_service import get_accessible_projects

    creds = get_credentials(user.session_id or "")
    if not creds:
        raise HTTPException(status_code=401, detail="Jira session expired. Please log in again.")

    projects = await get_accessible_projects(creds.username, creds.password)
    if not projects:
        raise HTTPException(
            status_code=403,
            detail="No project access. Contact your administrator.",
        )
    return {"projects": projects}


@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.is_tester:
        logout_tester(user.session_id)

    await log_action(
        db,
        user_identifier=user.email or user.jira_username or user.user_id,
        role=user.role,
        action="logout",
        ip_address=get_client_ip(request),
    )

    _clear_auth_cookie(response)
    return {"status": "ok"}
