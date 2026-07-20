"""Validation Jira et récupération des projets accessibles pour les testeurs."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

import httpx
import urllib3

from app.core.config import settings

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _jira_url(path: str, base_url: Optional[str] = None) -> str:
    base = (base_url or settings.JIRA_BASE_URL).rstrip("/")
    return f"{base}{path}"


def _extract_jira_error_message(response: httpx.Response) -> Optional[str]:
    try:
        body = response.json()
    except ValueError:
        text = (response.text or "").strip()
        if not text:
            return None
        if text.lower().startswith("<"):
            return None
        return text

    if isinstance(body, dict):
        if error_messages := body.get("errorMessages"):
            if isinstance(error_messages, list):
                return "; ".join(str(msg) for msg in error_messages if msg)
            return str(error_messages)
        if message := body.get("message"):
            return str(message)
        if error := body.get("error"):
            return str(error)
    return None


async def validate_jira_credentials(username: str, password: str) -> Dict[str, Any]:
    """Vérifie les identifiants via l'API Jira /myself."""
    url = _jira_url("/rest/api/2/myself")
    async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
        resp = await client.get(url, auth=(username, password))
        if resp.status_code in (401, 403):
            return {
                "valid": False,
                "error": "Vérifiez vos identifiants Jira et votre mot de passe.",
            }
        if resp.status_code != 200:
            jira_error = _extract_jira_error_message(resp)
            return {
                "valid": False,
                "error": jira_error
                or "Impossible de se connecter à Jira. Vérifiez vos identifiants ou contactez l'administrateur.",
            }
        data = resp.json()
        return {
            "valid": True,
            "display_name": data.get("displayName") or username,
            "email": data.get("emailAddress") or username,
            "account_id": data.get("accountId") or data.get("key") or username,
        }


async def get_accessible_projects(username: str, password: str) -> List[Dict[str, Any]]:
    """Récupère les projets Jira accessibles par l'utilisateur."""
    url = _jira_url("/rest/api/2/project")
    async with httpx.AsyncClient(verify=False, timeout=60.0) as client:
        resp = await client.get(url, auth=(username, password))
        if resp.status_code != 200:
            return []
        projects = resp.json() or []
        return [
            {
                "key": p.get("key"),
                "name": p.get("name"),
                "id": p.get("id"),
                "project_type": p.get("projectTypeKey"),
            }
            for p in projects
            if p.get("key")
        ]


def create_tester_session_id() -> str:
    return str(uuid.uuid4())
