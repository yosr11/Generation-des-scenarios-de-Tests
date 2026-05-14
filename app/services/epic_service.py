"""
Récupération des Epics depuis Jira via API REST
"""

import requests
import urllib3
import os
from dotenv import load_dotenv

load_dotenv()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "https://hra-jira.ptx.fr.sopra").rstrip("/")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_PASSWORD = os.getenv("JIRA_PASSWORD")
JIRA_AC_FIELD = os.getenv("JIRA_AC_FIELD", "customfield_11700")

# Session HTTP partagée
_session = requests.Session()
_session.auth = (JIRA_USERNAME, JIRA_PASSWORD)
_session.verify = False
_session.headers.update({"Accept": "application/json"})


# ══════════════════════════════════════════════════════════════
#  Récupère tous les Epics d'un projet Jira
# ══════════════════════════════════════════════════════════════
def get_epics(project_key: str):
    """
    Récupère tous les Epics d'un projet Jira.
    project_key : clé du projet fournie par l'utilisateur (ex: "YOUQA")
    """
    if not project_key or not project_key.strip():
        print("❌ project_key est requis")
        return []

    url = f"{JIRA_BASE_URL}/rest/api/2/search"
    jql = f'project = "{project_key}" AND issuetype = Epic ORDER BY created DESC'

    params = {
        "jql":        jql,
        "maxResults": 100,
        "fields":     "summary,description,status,priority,labels,issuetype"
    }

    try:
        response = _session.get(url, params=params, timeout=60)
    except requests.RequestException as e:
        print(f"❌ Erreur réseau : {e}")
        return []

    if response.status_code != 200:
        print(f"❌ Erreur {response.status_code} : {response.text[:500]}")
        return []

    data   = response.json()
    issues = data.get("issues", [])

    Epic = []
    for issue in issues:
        f = issue.get("fields", {})
        Epic.append({
            "id":          issue.get("key"),
            "title":       f.get("summary", ""),
            "description": f.get("description", ""),
            "status":      (f.get("status") or {}).get("name", ""),
            "priority":    (f.get("priority") or {}).get("name", ""),
            "labels":      f.get("labels", []),
            "issuetype":   (f.get("issuetype") or {}).get("name", ""),
        })

    print(f"✅ {len(Epic)} Epic récupérés pour le projet {project_key}")
    return Epic


# ══════════════════════════════════════════════════════════════
#  Compte le nombre total d'Epics dans un projet Jira
# ══════════════════════════════════════════════════════════════
def count_epics(project_key: str) -> dict:
    """
    Retourne le nombre total d'Epics dans un projet Jira.
    project_key : clé du projet fournie par l'utilisateur (ex: "YOUQA")
    """
    if not project_key or not project_key.strip():
        return {"project_key": project_key, "total_epics": 0, "error": "project_key est requis"}

    url = f"{JIRA_BASE_URL}/rest/api/2/search"
    jql = f'project = "{project_key}" AND issuetype = Epic'

    params = {
        "jql":        jql,
        "maxResults": 0,
        "fields":     "key"
    }

    try:
        response = _session.get(url, params=params, timeout=60)
    except requests.RequestException as e:
        return {"project_key": project_key, "total_epics": 0, "error": str(e)}

    if response.status_code != 200:
        return {"project_key": project_key, "total_epics": 0, "error": f"Jira {response.status_code}"}

    total = response.json().get("total", 0)
    return {"project_key": project_key, "total_epics": total}


# ══════════════════════════════════════════════════════════════
#  Récupère toutes les User Stories liées à un Epic.
# ══════════════════════════════════════════════════════════════
def get_stories_by_epic(epic_key: str):
    """
    Récupère toutes les User Stories liées à un Epic.
    epic_key : clé de l'epic fournie par l'utilisateur (ex: "YOUQA-123")
    """
    if not epic_key or not epic_key.strip():
        print("❌ epic_key est requis")
        return []

    url = f"{JIRA_BASE_URL}/rest/api/2/search"

    # Méthode 1 — via "Epic Link" (Jira classique)
    jql = f'"Epic Link" = {epic_key} ORDER BY created DESC'

    params = {
        "jql":        jql,
        "maxResults": 100,
        "fields":     "summary,description,status,priority,labels,issuetype"
    }

    try:
        response = _session.get(url, params=params, timeout=60)
    except requests.RequestException as e:
        print(f"❌ Erreur réseau : {e}")
        return []

    if response.status_code != 200:
        # Méthode 2 — via "parent" (Jira Next-gen)
        jql = f'parent = {epic_key} ORDER BY created DESC'
        params["jql"] = jql
        try:
            response = _session.get(url, params=params, timeout=60)
        except requests.RequestException as e:
            print(f"❌ Erreur réseau : {e}")
            return []

    if response.status_code != 200:
        print(f"❌ Erreur {response.status_code} : {response.text[:500]}")
        return []

    data   = response.json()
    issues = data.get("issues", [])

    stories = []
    for issue in issues:
        f = issue.get("fields", {})
        stories.append({
            "id":        issue.get("key"),
            "title":     f.get("summary", ""),
            "status":    (f.get("status") or {}).get("name", ""),
            "issuetype": (f.get("issuetype") or {}).get("name", ""),
        })

    print(f"✅ {len(stories)} stories liées à {epic_key}")
    return stories


# ══════════════════════════════════════════════════════════════
#  Récupère les stories d'un Epic avec tous les champs détaillés
#  (nécessaires au nettoyage + enrichissement LLM)
# ══════════════════════════════════════════════════════════════
def get_stories_by_epic_detailed(epic_key: str) -> list:
    """
    Récupère les stories liées à un Epic avec tous les champs utiles
    pour le pipeline cleaning + enrichissement LLM :
    description, labels, components, issuelinks, priority, status, fixVersions…
    """
    if not epic_key or not epic_key.strip():
        return []

    url = f"{JIRA_BASE_URL}/rest/api/2/search"
    fields = f"summary,description,labels,components,issuelinks,priority,status,fixVersions,customfield_14422,{JIRA_AC_FIELD},issuetype"

    for jql in [
        f'"Epic Link" = {epic_key} ORDER BY created DESC',
        f'parent = {epic_key} ORDER BY created DESC',
    ]:
        try:
            resp = _session.get(
                url,
                params={"jql": jql, "maxResults": 200, "fields": fields},
                timeout=60,
            )
            if resp.status_code == 200:
                issues = resp.json().get("issues", [])
                if issues:
                    return _parse_issues_detailed(issues)
        except requests.RequestException:
            continue

    return []


def _flatten_issuelinks(raw_links: list) -> list:
    out = []
    for link in raw_links:
        link_type = (link.get("type") or {}).get("name", "")
        for direction in ("inwardIssue", "outwardIssue"):
            target = link.get(direction)
            if target:
                out.append({
                    "type": link_type,
                    "direction": direction.replace("Issue", ""),
                    "key": target.get("key", ""),
                    "summary": (target.get("fields") or {}).get("summary", ""),
                    "status": ((target.get("fields") or {}).get("status") or {}).get("name", ""),
                })
    return out


def _parse_issues_detailed(issues: list) -> list:
    stories = []
    for issue in issues:
        f = issue.get("fields", {}) or {}
        stories.append({
            "id":                 issue.get("key", ""),
            "summary":            f.get("summary", ""),
            "description":        f.get("description", ""),
            "labels":             f.get("labels", []),
            "components":         [c.get("name") for c in (f.get("components") or [])],
            "issuelinks":         _flatten_issuelinks(f.get("issuelinks") or []),
            "priority":           (f.get("priority") or {}).get("name", ""),
            "status":             (f.get("status") or {}).get("name", ""),
            "fixVersions":        [v.get("name") for v in (f.get("fixVersions") or [])],
            "requirement_status":      f.get("customfield_14422"),
            "acceptance_criteria_raw": f.get(JIRA_AC_FIELD) or "",
            "issuetype":              (f.get("issuetype") or {}).get("name", ""),
        })
    return stories
# ══════════════════════════════════════════════════════════════
#  Compte le nombre de User Stories liées à un Epic
# ══════════════════════════════════════════════════════════════
def count_stories_by_epic(epic_key: str) -> int:
    """
    Retourne le nombre de User Stories liées à un Epic (sans récupérer les champs).
    Essaie d'abord via "Epic Link" (Jira classique), puis via "parent" (Next-gen).
    """
    if not epic_key or not epic_key.strip():
        return 0

    url = f"{JIRA_BASE_URL}/rest/api/2/search"

    for jql in [
        f'"Epic Link" = {epic_key}',
        f'parent = {epic_key}',
    ]:
        try:
            resp = _session.get(
                url,
                params={"jql": jql, "maxResults": 0, "fields": "key"},
                timeout=60,
            )
            if resp.status_code == 200:
                return resp.json().get("total", 0)
        except requests.RequestException:
            continue

    return 0