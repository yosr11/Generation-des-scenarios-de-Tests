"""Dépendances FastAPI : utilisateur courant et protection par rôle."""

from __future__ import annotations

from typing import Annotated, Callable, Optional

from fastapi import Cookie, Depends, HTTPException, Request, status
from jwt import PyJWTError

from app.core.config import settings
from app.core.security import decode_access_token
from app.services.credential_store import JiraCredentials, get_credentials


class CurrentUser:
    def __init__(
        self,
        user_id: str,
        role: str,
        email: str,
        jira_username: Optional[str] = None,
        display_name: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        self.user_id = user_id
        self.role = role
        self.email = email
        self.jira_username = jira_username
        self.display_name = display_name
        self.session_id = session_id

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_tester(self) -> bool:
        return self.role == "tester"

    @property
    def user_id_int(self) -> Optional[int]:
        """Retourne user_id converti en int si possible (cas admin, id PostgreSQL).
        Retourne None si non convertible (cas testeur, où user_id est un
        account_id Jira alphanumérique, pas un id PostgreSQL)."""
        try:
            return int(self.user_id)
        except (TypeError, ValueError):
            return None


def _extract_token(access_token: Optional[str]) -> str:
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return access_token


async def get_current_user(
    access_token: Annotated[Optional[str], Cookie(alias=settings.COOKIE_NAME)] = None,
) -> CurrentUser:
    token = _extract_token(access_token)
    try:
        payload = decode_access_token(token)
    except PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    role = payload.get("role")
    if role not in ("admin", "tester"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid role"
        )

    return CurrentUser(
        user_id=str(payload.get("sub", "")),
        role=role,
        email=payload.get("email", ""),
        jira_username=payload.get("jira_username"),
        display_name=payload.get("display_name"),
        session_id=payload.get("session_id"),
    )


async def get_optional_user(
    access_token: Annotated[Optional[str], Cookie(alias=settings.COOKIE_NAME)] = None,
) -> Optional[CurrentUser]:
    if not access_token:
        return None
    try:
        return await get_current_user(access_token)
    except HTTPException:
        return None


def require_role(*roles: str) -> Callable:
    async def _checker(
        user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {', '.join(roles)}",
            )
        return user

    return _checker


require_admin = require_role("admin")
require_tester = require_role("tester")
require_any_auth = require_role("admin", "tester")


def get_tester_jira_credentials(user: CurrentUser) -> JiraCredentials:
    if not user.is_tester or not user.session_id:
        raise HTTPException(status_code=403, detail="Tester session required")
    creds = get_credentials(user.session_id)
    if not creds:
        raise HTTPException(
            status_code=401, detail="Jira session expired. Please log in again."
        )
    return creds


def get_client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None
