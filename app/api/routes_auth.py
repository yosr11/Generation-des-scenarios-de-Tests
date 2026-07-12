"""Routes d'authentification — endpoint unique POST /auth/login."""

from __future__ import annotations

from typing import List, Optional

from urllib.parse import urlencode, urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import CurrentUser, get_client_ip, get_current_user
from app.db.postgres import get_db
from app.services.audit_service import log_action
from app.services.auth_service import authenticate_user, build_admin_token, build_user_token, logout_tester
from app.services.user_service import get_user_by_email, get_user_by_jira_username, update_last_login

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """
    Corps de la requête de connexion unifiée.

    - Pour un admin    : identifier = email,          password = mot de passe DB.
    - Pour un testeur  : identifier = username Jira,  password = mot de passe Jira.
    Le backend détecte le rôle automatiquement.
    """
    identifier: str = Field(..., min_length=1, description="Email admin ou username Jira")
    password: str   = Field(..., min_length=1)


class ProjectInfo(BaseModel):
    key:          str
    name:         str
    id:           Optional[str] = None
    project_type: Optional[str] = None


class LoginResponse(BaseModel):
    user:     dict
    role:     str
    projects: Optional[List[ProjectInfo]] = None


# ── Cookie helpers ────────────────────────────────────────────────────────────

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


def _is_microsoft_oauth_ready() -> bool:
    return bool(
        settings.MICROSOFT_CLIENT_ID
        and settings.MICROSOFT_CLIENT_SECRET
        and settings.MICROSOFT_TENANT_ID
        and settings.MICROSOFT_REDIRECT_URI
    )


def _resolve_frontend_redirect(state: str | None) -> str:
    if not state:
        return f"{settings.FRONTEND_BASE_URL.rstrip('/')}/pipeline"

    parsed = urlparse(state)
    if parsed.scheme or parsed.netloc:
        return f"{settings.FRONTEND_BASE_URL.rstrip('/')}/pipeline"

    if not state.startswith('/'):
        state = f"/{state}"

    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}{state}"


def _build_microsoft_authorize_url(next_path: str = "/pipeline") -> str:
    params = {
        "client_id": settings.MICROSOFT_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
        "response_mode": "query",
        "scope": settings.MICROSOFT_SCOPES,
        "state": next_path,
        "prompt": settings.MICROSOFT_PROMPT,
    }
    return (
        f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}"
        f"/oauth2/v2.0/authorize?{urlencode(params)}"
    )


def _build_microsoft_token_payload(
    user,
    *,
    microsoft_email: str,
    microsoft_display_name: str | None,
    session_id: str | None = None,
) -> dict:
    payload = {
        "sub": str(user.id),
        "email": microsoft_email,
        "role": user.role,
        "display_name": microsoft_display_name or user.display_name or microsoft_email,
    }
    if user.jira_username:
        payload["jira_username"] = user.jira_username
    if session_id:
        payload["session_id"] = session_id
    return payload


# ── Unified login ─────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint de connexion unique.
    Le backend tente d'abord une authentification admin (email + bcrypt),
    puis une authentification testeur Jira si l'admin échoue.
    """
    result = await authenticate_user(db, identifier=body.identifier, password=body.password)

    if not result.get("success"):
        # no_projects → 403, autres erreurs → 401
        status = 403 if result.get("no_projects") else 401
        raise HTTPException(status_code=status, detail=result.get("error", "Échec de connexion."))

    role = result["role"]

    # ── Post-auth side effects ────────────────────────────────────────────────
    if role == "admin":
        user_id = result["user"]["id"]
        await update_last_login(db, user_id)

    elif role == "tester":
        db_tester = await get_user_by_jira_username(db, body.identifier)
        if db_tester:
            await update_last_login(db, db_tester.id)

    # Pose le cookie JWT
    _set_auth_cookie(response, result["access_token"])

    # Audit
    await log_action(
        db,
        user_identifier=body.identifier,
        role=role,
        action="login",
        details=f"Projects: {len(result['projects'])}" if result.get("projects") else None,
        ip_address=get_client_ip(request),
    )

    return LoginResponse(
        user=result["user"],
        role=role,
        projects=[ProjectInfo(**p) for p in result["projects"]] if result.get("projects") else None,
    )


# ── Microsoft OAuth login ─────────────────────────────────────────────────────

@router.get("/microsoft/login")
async def microsoft_login(next: str | None = "/pipeline"):
    if not _is_microsoft_oauth_ready():
        raise HTTPException(status_code=500, detail="Microsoft OAuth is not configured.")
    authorize_url = _build_microsoft_authorize_url(next_path=next or "/pipeline")
    response = RedirectResponse(url=authorize_url)
    _clear_auth_cookie(response)
    return response


@router.get("/microsoft/callback")
async def microsoft_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    if not _is_microsoft_oauth_ready():
        raise HTTPException(status_code=500, detail="Microsoft OAuth is not configured.")

    if error:
        response = RedirectResponse(url=f"{settings.FRONTEND_BASE_URL.rstrip('/')}/login?error=oauth_failed")
        _clear_auth_cookie(response)
        return response
    if not code:
        response = RedirectResponse(url=f"{settings.FRONTEND_BASE_URL.rstrip('/')}/login?error=oauth_failed")
        _clear_auth_cookie(response)
        return response

    token_url = (
        f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}"
        "/oauth2/v2.0/token"
    )
    token_payload = {
        "client_id": settings.MICROSOFT_CLIENT_ID,
        "client_secret": settings.MICROSOFT_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
        "scope": settings.MICROSOFT_SCOPES,
    }

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(token_url, data=token_payload, headers={"Accept": "application/json"})
    if token_resp.status_code != 200:
        response = RedirectResponse(url=f"{settings.FRONTEND_BASE_URL.rstrip('/')}/login?error=oauth_failed")
        _clear_auth_cookie(response)
        return response

    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        response = RedirectResponse(url=f"{settings.FRONTEND_BASE_URL.rstrip('/')}/login?error=oauth_failed")
        _clear_auth_cookie(response)
        return response

    graph_url = "https://graph.microsoft.com/v1.0/me"
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            graph_url,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )

    if user_resp.status_code != 200:
        response = RedirectResponse(url=f"{settings.FRONTEND_BASE_URL.rstrip('/')}/login?error=oauth_failed")
        _clear_auth_cookie(response)
        return response

    microsoft_user = user_resp.json()
    email = (microsoft_user.get("mail") or microsoft_user.get("userPrincipalName") or "").strip().lower()
    display_name = microsoft_user.get("displayName")
    if not email:
        response = RedirectResponse(url=f"{settings.FRONTEND_BASE_URL.rstrip('/')}/login?error=oauth_failed")
        _clear_auth_cookie(response)
        return response

    allowed_domain = settings.MICROSOFT_ALLOWED_EMAIL_DOMAIN.strip().lower()
    if allowed_domain and not email.endswith(f"@{allowed_domain}"):
        response = RedirectResponse(url=f"{settings.FRONTEND_BASE_URL.rstrip('/')}/login?error=unauthorized")
        _clear_auth_cookie(response)
        return response

    # Search in a case-insensitive way
    user = await get_user_by_email(db, email)
    if not user:
        response = RedirectResponse(url=f"{settings.FRONTEND_BASE_URL.rstrip('/')}/login?error=unauthorized")
        _clear_auth_cookie(response)
        return response
    if not user.is_active:
        response = RedirectResponse(url=f"{settings.FRONTEND_BASE_URL.rstrip('/')}/login?error=disabled")
        _clear_auth_cookie(response)
        return response
    if user.role not in {"admin", "tester"}:
        response = RedirectResponse(url=f"{settings.FRONTEND_BASE_URL.rstrip('/')}/login?error=unauthorized")
        _clear_auth_cookie(response)
        return response

    from app.core.security import create_access_token

    token = create_access_token(
        _build_microsoft_token_payload(
            user,
            microsoft_email=email,
            microsoft_display_name=display_name,
        )
    )

    # ── Provide Jira session for Microsoft users ─────────────────────────────
    # Microsoft-authenticated testers don't have per-user Jira creds.
    # Assign them a session that uses the global JIRA_USERNAME / JIRA_PASSWORD
    # so that /auth/projects works immediately after OAuth redirect.
    if user.role == "tester" and settings.JIRA_USERNAME and settings.JIRA_PASSWORD:
        try:
            from app.services.credential_store import store_credentials
            import uuid

            ms_session_id = str(uuid.uuid4())
            store_credentials(ms_session_id, settings.JIRA_USERNAME, settings.JIRA_PASSWORD)

            # Rebuild token with session_id so /auth/projects can find the creds
            token = create_access_token(
                _build_microsoft_token_payload(
                    user,
                    microsoft_email=email,
                    microsoft_display_name=display_name,
                    session_id=ms_session_id,
                )
            )
        except Exception as _e:
            pass  # Fall back to token without session_id — AuthContext will handle gracefully

    frontend_redirect = _resolve_frontend_redirect(state)
    response = RedirectResponse(url=frontend_redirect)
    _set_auth_cookie(response, token)

    await update_last_login(db, user.id)
    await log_action(
        db,
        user_identifier=email,
        role=user.role,
        action="microsoft_login",
        details=f"Microsoft login redirected to {frontend_redirect}",
        ip_address=get_client_ip(request),
    )

    return response


# ── /me ───────────────────────────────────────────────────────────────────────

@router.get("/me")
async def get_me(user: CurrentUser = Depends(get_current_user)):
    return {
        "user_id":      user.user_id,
        "email":        user.email,
        "role":         user.role,
        "jira_username": user.jira_username,
        "display_name": user.display_name,
    }


# ── /profile ─────────────────────────────────────────────────────────────────

class UpdateProfileRequest(BaseModel):
    """Mise à jour du profil utilisateur connecté."""
    display_name: Optional[str] = None
    jira_username: Optional[str] = None  # testeur uniquement
    current_password: Optional[str] = None  # requis si new_password est fourni
    new_password: Optional[str] = Field(default=None, min_length=6)


@router.get("/profile")
async def get_profile(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retourne le profil complet de l'utilisateur connecté."""
    from app.services.user_service import get_user_by_id
    if user.user_id:
        profile = await get_user_by_id(db, user.user_id)
        if profile:
            return profile
    # Fallback depuis le token
    return {
        "id": user.user_id,
        "email": user.email,
        "role": user.role,
        "display_name": user.display_name,
        "jira_username": user.jira_username,
        "is_active": True,
        "last_login_at": None,
        "created_at": None,
    }


@router.patch("/profile")
async def update_profile(
    body: UpdateProfileRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mise à jour du profil de l'utilisateur connecté."""
    from app.services.user_service import get_user_by_id, update_user
    from app.models.pg_models import User
    from sqlalchemy import select
    from app.core.security import verify_password

    if not user.user_id:
        raise HTTPException(status_code=400, detail="Utilisateur introuvable.")

    # Si nouveau mot de passe demandé, vérifier l'ancien
    new_password = None
    if body.new_password:
        if not body.current_password:
            raise HTTPException(
                status_code=400,
                detail="Le mot de passe actuel est requis pour en définir un nouveau.",
            )
        result = await db.execute(select(User).where(User.id == user.user_id))
        db_user = result.scalar_one_or_none()
        if not db_user or not verify_password(body.current_password, db_user.hashed_password):
            raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect.")
        new_password = body.new_password

    # Les testeurs ne peuvent pas changer le rôle
    result = await update_user(
        db,
        user.user_id,
        display_name=body.display_name,
        jira_username=body.jira_username if user.role == "tester" else None,
        password=new_password,
    )

    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result["user"]


# ── /password-reset ───────────────────────────────────────────────────────────
import secrets
import time
from typing import Dict as _Dict

# In-memory store: token -> {email, expires_at}
_reset_tokens: _Dict[str, dict] = {}
RESET_TOKEN_TTL = 3600  # 1 heure


class PasswordResetRequestBody(BaseModel):
    email: str = Field(..., min_length=1, description="Email du compte à réinitialiser")


class PasswordResetConfirmBody(BaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)


@router.post("/password-reset/request")
async def request_password_reset(
    body: PasswordResetRequestBody,
    db: AsyncSession = Depends(get_db),
):
    """Génère un token de réinitialisation et l'affiche dans les logs (mode dev)."""
    import logging
    logger = logging.getLogger(__name__)

    from app.services.user_service import get_user_by_email as _get_by_email
    user = await _get_by_email(db, body.email.strip().lower())

    # Réponse identique que l'email existe ou non (sécurité)
    if not user:
        logger.warning("[PasswordReset] Email introuvable: %s", body.email)
        return {"status": "ok", "message": "Si ce compte existe, un lien de réinitialisation a été généré."}

    token = secrets.token_urlsafe(32)
    _reset_tokens[token] = {
        "email": user.email,
        "expires_at": time.time() + RESET_TOKEN_TTL,
    }

    reset_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/reset-password?token={token}"
    logger.warning(
        "[PasswordReset][DEV] Lien de réinitialisation pour %s:\n%s",
        user.email,
        reset_url,
    )

    return {
        "status": "ok",
        "message": "Si ce compte existe, un lien de réinitialisation a été généré.",
        "dev_reset_url": reset_url,
    }


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    body: PasswordResetConfirmBody,
    db: AsyncSession = Depends(get_db),
):
    """Valide le token et met à jour le mot de passe."""
    token_data = _reset_tokens.get(body.token)
    if not token_data:
        raise HTTPException(status_code=400, detail="Token invalide ou expiré.")

    if time.time() > token_data["expires_at"]:
        if body.token in _reset_tokens:
            del _reset_tokens[body.token]
        raise HTTPException(status_code=400, detail="Token expiré. Veuillez recommencer.")

    from app.services.user_service import get_user_by_email as _get_by_email, update_user
    user = await _get_by_email(db, token_data["email"])
    if not user:
        raise HTTPException(status_code=404, detail="Compte introuvable.")

    result = await update_user(db, user.id, password=body.new_password)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    del _reset_tokens[body.token]

    return {"status": "ok", "message": "Mot de passe mis à jour avec succès."}


# ── /projects ─────────────────────────────────────────────────────────────────

@router.get("/projects")
async def get_my_projects(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Projets Jira accessibles (testeur uniquement, fetch live)."""
    if not user.is_tester:
        raise HTTPException(status_code=403, detail="Only testers have Jira projects.")

    from app.services.credential_store import get_credentials
    from app.services.jira_auth_service import get_accessible_projects

    creds = get_credentials(user.session_id or "")
    if not creds and settings.JIRA_USERNAME and settings.JIRA_PASSWORD:
        # Microsoft-auth users: fall back to global Jira credentials
        from app.services.credential_store import store_credentials
        import uuid
        fallback_sid = str(uuid.uuid4())
        store_credentials(fallback_sid, settings.JIRA_USERNAME, settings.JIRA_PASSWORD)
        creds_username = settings.JIRA_USERNAME
        creds_password = settings.JIRA_PASSWORD
    elif not creds:
        raise HTTPException(status_code=401, detail="Session Jira expirée. Veuillez vous reconnecter.")
    else:
        creds_username = creds.username
        creds_password = creds.password

    projects = await get_accessible_projects(creds_username, creds_password)
    if not projects:
        raise HTTPException(status_code=403, detail="Aucun projet accessible. Contactez votre administrateur.")

    return {"projects": projects}


# ── /logout ───────────────────────────────────────────────────────────────────

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
        user_identifier=user.email or user.jira_username or str(user.user_id),
        role=user.role,
        action="logout",
        ip_address=get_client_ip(request),
    )

    _clear_auth_cookie(response)
    return {"status": "ok"}