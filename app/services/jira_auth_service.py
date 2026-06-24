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


async def validate_jira_credentials(username: str, password: str) -> Dict[str, Any]:
    """Vérifie les identifiants via l'API Jira /myself."""
    url = _jira_url("/rest/api/2/myself")
    async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
        resp = await client.get(url, auth=(username, password))
        if resp.status_code == 401:
            return {"valid": False, "error": "Invalid Jira credentials"}
        if resp.status_code != 200:
            return {
                "valid": False,
                "error": f"Jira API error ({resp.status_code}): {resp.text[:500]}",
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
