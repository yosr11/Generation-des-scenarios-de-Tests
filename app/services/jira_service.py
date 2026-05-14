import os
import requests
import urllib3
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from app.utils.cleaning import clean_text

# Charger .env (JIRA_BASE_URL, JIRA_USERNAME, JIRA_PASSWORD)
load_dotenv()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "https://hra-jira.ptx.fr.sopra").rstrip("/")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")  
JIRA_PASSWORD = os.getenv("JIRA_PASSWORD") 

# Session HTTP partagée
_session = requests.Session()
_session.auth = (JIRA_USERNAME, JIRA_PASSWORD)
_session.verify = False
_session.headers.update({"Accept": "application/json"})



######### Fonction pour rechercher des issues #########
def search_issues(
    jql: str,
    fields: Optional[str] = None,
    max_per_page: int = 100,
    timeout_sec: int = 60,
) -> Dict[str, Any]:
    """
    Récupère les issues Jira 'telles quelles' avec pagination.
    - jql: ex. 'project = YOUQA AND issuetype = Story'
    - fields: None => champs par défaut (brut). Sinon: 'summary,description,...'
    - max_per_page: 100 recommandé si autorisé
    - max_total: garde-fou pour éviter de rapatrier trop de données
    """
    url = f"{JIRA_BASE_URL}/rest/api/2/search"
    start_at = 0
    all_issues: List[Dict[str, Any]] = []
    total_seen = None

    while True:
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_per_page
        }
        if fields is not None:
            params["fields"] = fields

        resp = _session.get(url, params=params, timeout=timeout_sec)
        if resp.status_code != 200:
            return {
                "error": True,
                "status_code": resp.status_code,
                "request": {"url": url, "params": params},
                "body": resp.text[:1000],
            }

        page = resp.json()
        issues = page.get("issues", [])
        all_issues.extend(issues)

        if total_seen is None:
            total_seen = page.get("total", len(issues))

        fetched = len(issues)
        if fetched == 0:
            break
        start_at += fetched

        if start_at >= total_seen or len(all_issues) >= total_seen:
            break

    return {
        "expand": "names,schema,operations",
        "startAt": 0,
        "maxResults": len(all_issues),
        "total": total_seen if total_seen is not None else len(all_issues),
        "issues": all_issues
    }


######### Fonction pour récupérer les user stories  #########
def get_project_stories(
    project_key: str,
    extra_jql: str = "",
    fields: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Stories 'telles quelles' (brut). Ajoute un fragment JQL optionnel (ex: 'AND status != Done').
    """
    base = f'project = "{project_key}" AND issuetype = Story'
    jql = f"{base} {extra_jql}" if extra_jql else base
    
    if fields is None:
        fields = "summary,description,labels,components,issuelinks,priority,status,fixVersions,customfield_14422"

    return search_issues(jql=jql, fields=fields, max_per_page=100)


############## Fonction pour récupérer une seule user_story  #########
def get_story_byID(issue_key: str) -> Dict[str, Any]:
    """
    Récupère une User Story spécifique par sa clé (ex: YOUQA-123).
    """
    url = f"{JIRA_BASE_URL}/rest/api/2/issue/{issue_key}"

    response = _session.get(url, timeout=20)

    return {
        "status": response.status_code,
        "data": response.json() if response.status_code == 200 else None,
        "error": response.text if response.status_code != 200 else None
    }


JIRA_EPIC_LINK_FIELD = os.getenv("JIRA_EPIC_LINK_FIELD", "customfield_12402")


def get_epic_for_story(issue_key: str) -> Optional[Dict[str, Any]]:
    """
    Récupère l'Epic parent d'une story via Jira.
    Retourne {key, summary, description} ou None si pas d'epic lié.
    """
    # 1) Récupérer le champ Epic Link de la story
    url = f"{JIRA_BASE_URL}/rest/api/2/issue/{issue_key}"
    params = {"fields": f"{JIRA_EPIC_LINK_FIELD},parent"}

    try:
        resp = _session.get(url, params=params, timeout=20)
    except requests.RequestException:
        return None

    if resp.status_code != 200:
        return None

    fields = resp.json().get("fields", {}) or {}

    # Try Epic Link custom field first, then parent (Jira Next-Gen)
    epic_key = fields.get(JIRA_EPIC_LINK_FIELD)
    if not epic_key:
        parent = fields.get("parent") or {}
        if (parent.get("fields", {}) or {}).get("issuetype", {}).get("name") == "Epic":
            epic_key = parent.get("key")

    if not epic_key:
        return None

    # 2) Récupérer les infos de l'Epic
    epic_url = f"{JIRA_BASE_URL}/rest/api/2/issue/{epic_key}"
    try:
        epic_resp = _session.get(
            epic_url,
            params={"fields": "summary,description"},
            timeout=20,
        )
    except requests.RequestException:
        return None

    if epic_resp.status_code != 200:
        return None

    epic_fields = epic_resp.json().get("fields", {}) or {}
    return {
        "key": epic_key,
        "summary": epic_fields.get("summary") or "",
        "description": epic_fields.get("description") or "",
    }


