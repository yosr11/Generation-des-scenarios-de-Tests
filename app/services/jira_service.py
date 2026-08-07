import os
import re
import json
import logging
import requests
import urllib3

from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

from app.utils.cleaning import clean_text

logger = logging.getLogger(__name__)


# ============================================================
# Configuration générale
# ============================================================

load_dotenv()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

JIRA_PROD_URL = os.getenv(
    "JIRA_PROD_URL",
    "https://hra-jira.ptx.fr.sopra",
).rstrip("/")

JIRA_TEST_URL = os.getenv(
    "JIRA_TEST_URL",
    "https://hra-test-jira.ptx.fr.sopra",
).rstrip("/")

JIRA_BASE_URL = JIRA_PROD_URL

JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_PASSWORD = os.getenv("JIRA_PASSWORD")

JIRA_EPIC_LINK_FIELD = os.getenv("JIRA_EPIC_LINK_FIELD", "customfield_12402")

# Champs Xray de ton Jira Sopra
XRAY_FIELD_TEST_TYPE = os.getenv("XRAY_FIELD_TEST_TYPE", "customfield_14400")
XRAY_FIELD_STEPS = os.getenv("XRAY_FIELD_STEPS", "customfield_14404")
XRAY_FIELD_REPO_PATH = os.getenv("XRAY_FIELD_REPO_PATH", "customfield_14410")
XRAY_FIELD_PRECONDITIONS = os.getenv("XRAY_FIELD_PRECONDITIONS", "customfield_14407")
XRAY_FIELD_STEPS_COUNT = os.getenv("XRAY_FIELD_STEPS_COUNT", "customfield_14405")
XRAY_TEST_ISSUETYPE_ID = os.getenv("XRAY_TEST_ISSUETYPE_ID")


def _create_session(
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> requests.Session:
    """Crée une session Jira avec auth et headers JSON."""
    if not username and not JIRA_USERNAME:
        raise RuntimeError("JIRA_USERNAME is not configured")
    if not password and not JIRA_PASSWORD:
        raise RuntimeError("JIRA_PASSWORD is not configured")

    session = requests.Session()
    session.auth = (username or JIRA_USERNAME, password or JIRA_PASSWORD)
    session.verify = False
    session.headers.update(
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
    )
    return session


def create_user_jira_session(username: str, password: str) -> requests.Session:
    """Session Jira pour un utilisateur authentifié (testeur)."""
    return _create_session(username=username, password=password)


_session_prod = _create_session()
_session_test = _create_session()
_session = _session_prod


# ============================================================
# Fonctions de recherche Jira
# ============================================================


def search_issues_with_session(
    jql: str,
    session: requests.Session,
    jira_url: str,
    fields: Optional[str] = None,
    max_per_page: int = 100,
    timeout_sec: int = 60,
) -> Dict[str, Any]:
    """
    Recherche des issues Jira sur une instance spécifique.
    """
    url = f"{jira_url}/rest/api/2/search"

    start_at = 0
    all_issues: List[Dict[str, Any]] = []
    total_seen = None

    while True:
        params: Dict[str, Any] = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_per_page,
        }

        if fields is not None:
            params["fields"] = fields

        try:
            resp = session.get(url, params=params, timeout=timeout_sec)
        except requests.RequestException as exc:
            logger.warning("Jira request failed: %s", exc)
            return {
                "error": True,
                "detail": str(exc),
            }

        if resp.status_code != 200:
            return {
                "error": True,
                "status_code": resp.status_code,
                "request": {"url": url, "params": params},
                "body": resp.text[:2000],
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
        "issues": all_issues,
    }


def search_issues(
    jql: str,
    fields: Optional[str] = None,
    max_per_page: int = 100,
    timeout_sec: int = 60,
) -> Dict[str, Any]:
    """
    Recherche Jira par défaut sur Jira PROD.
    """
    return search_issues_with_session(
        jql=jql,
        session=_session_prod,
        jira_url=JIRA_PROD_URL,
        fields=fields,
        max_per_page=max_per_page,
        timeout_sec=timeout_sec,
    )


def get_project_stories(
    project_key: str,
    extra_jql: str = "",
    fields: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Récupère les User Stories d'un projet.
    """
    base = f'project = "{project_key}" AND issuetype = Story'
    jql = f"{base} {extra_jql}" if extra_jql else base

    if fields is None:
        fields = (
            "summary,description,labels,components,issuelinks,"
            "priority,status,fixVersions,customfield_14422"
        )

    return search_issues(
        jql=jql,
        fields=fields,
        max_per_page=100,
    )


def get_stories_without_description(
    project_key: str,
    extra_jql: str = "",
) -> List[str]:
    """
    Retourne les clés des User Stories sans description.
    """
    base = f'project = "{project_key}" AND issuetype = Story AND description is EMPTY'
    jql = f"{base} {extra_jql}" if extra_jql else base

    result = search_issues(
        jql=jql,
        fields="summary",
        max_per_page=100,
    )

    if result.get("error"):
        return []

    return [issue.get("key") for issue in result.get("issues", []) if issue.get("key")]


def get_story_byID(issue_key: str) -> Dict[str, Any]:
    """
    Récupère une User Story par clé.
    """
    url = f"{JIRA_PROD_URL}/rest/api/2/issue/{issue_key}"

    try:
        response = _session_prod.get(url, timeout=20)
    except requests.RequestException as exc:
        return {
            "status": 0,
            "data": None,
            "error": str(exc),
        }

    return {
        "status": response.status_code,
        "data": response.json() if response.status_code == 200 else None,
        "error": response.text if response.status_code != 200 else None,
    }


def get_epic_for_story(issue_key: str) -> Optional[Dict[str, Any]]:
    """
    Récupère l'Epic parent d'une story (cache DB d'abord, puis Jira).
    """
    from app.repositories.story_repository import get_story_by_id

    db_story = get_story_by_id(issue_key)
    if db_story and db_story.get("epic_key"):
        return {
            "key": db_story["epic_key"],
            "summary": db_story.get("epic_summary") or "",
            "description": db_story.get("epic_description") or "",
        }

    url = f"{JIRA_PROD_URL}/rest/api/2/issue/{issue_key}"
    params = {"fields": f"{JIRA_EPIC_LINK_FIELD},parent"}

    try:
        resp = _session_prod.get(url, params=params, timeout=20)
    except requests.RequestException:
        return None

    if resp.status_code != 200:
        return None

    fields = resp.json().get("fields", {}) or {}

    epic_key = fields.get(JIRA_EPIC_LINK_FIELD)

    if not epic_key:
        parent = fields.get("parent") or {}
        parent_fields = parent.get("fields", {}) or {}
        parent_type = parent_fields.get("issuetype", {}) or {}

        if parent_type.get("name") == "Epic":
            epic_key = parent.get("key")

    if not epic_key:
        return None

    epic_url = f"{JIRA_PROD_URL}/rest/api/2/issue/{epic_key}"

    try:
        epic_resp = _session_prod.get(
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


# ============================================================
# Enrichissement des issuelinks avec leur description
# ============================================================


def enrich_issuelinks_with_description(
    issuelinks: List[Dict[str, Any]],
    max_workers: int = 4,
) -> List[Dict[str, Any]]:
    """
    Enrichit chaque issuelink (déjà aplati/nettoyé) avec la description
    du ticket lié, récupérée via un fetch Jira supplémentaire par clé.
    Parallélisé pour limiter la latence quand une story a plusieurs liens.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if not issuelinks:
        return []

    from app.repositories.story_repository import get_stories_by_ids

    enriched_links = [dict(link) for link in issuelinks]
    keys = [link.get("key") for link in enriched_links if link.get("key")]
    db_by_key = {s["id"]: s for s in get_stories_by_ids(keys)}

    keys_to_fetch: list[tuple[int, str]] = []
    for idx, link in enumerate(enriched_links):
        if (link.get("description") or "").strip():
            continue
        key = link.get("key")
        if not key:
            continue
        db_story = db_by_key.get(key)
        if db_story:
            desc = db_story.get("description_clean") or ""
            if desc.strip():
                enriched_links[idx]["description"] = desc
                continue
        keys_to_fetch.append((idx, key))

    if not keys_to_fetch:
        return enriched_links

    def _fetch_description(key: str) -> str:
        if not key:
            return ""
        try:
            resp = get_story_byID(key)
            if resp.get("status") == 200 and resp.get("data"):
                fields = resp["data"].get("fields", {}) or {}
                raw_desc = fields.get("description") or ""
                return clean_text(raw_desc) if raw_desc else ""
        except Exception:
            pass
        return ""

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(_fetch_description, key): idx for idx, key in keys_to_fetch
        }
        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            try:
                enriched_links[idx]["description"] = future.result()
            except Exception:
                enriched_links[idx]["description"] = ""

    return enriched_links


# ============================================================
# Recherche stories avec tests liés
# ============================================================

_TEST_LINK_TYPES = {
    "is tested by",
    "tests",
    "test",
    "verified by",
    "tested by",
}


def _extract_linked_tests(issue: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Renvoie la liste des tests liés à une issue via issuelinks.
    """
    linked_tests: List[Dict[str, str]] = []

    fields = issue.get("fields") or {}
    issuelinks = fields.get("issuelinks") or []

    for link in issuelinks:
        link_type = link.get("type") or {}

        link_type_name = (link_type.get("name") or "").lower()
        link_type_outward = (link_type.get("outward") or "").lower()
        link_type_inward = (link_type.get("inward") or "").lower()

        is_test_link = any(
            value in (link_type_name, link_type_outward, link_type_inward)
            for value in _TEST_LINK_TYPES
        )

        for direction in ("outwardIssue", "inwardIssue"):
            target = link.get(direction)

            if not target:
                continue

            target_fields = target.get("fields") or {}
            target_issuetype = target_fields.get("issuetype") or {}
            target_type = (target_issuetype.get("name") or "").lower()

            if is_test_link or target_type == "test":
                linked_tests.append(
                    {
                        "key": target.get("key", ""),
                        "summary": target_fields.get("summary", ""),
                        "issuetype": target_issuetype.get("name", ""),
                        "link_type": link_type_name,
                    }
                )

    seen = set()
    unique: List[Dict[str, str]] = []

    for test in linked_tests:
        key = test.get("key")

        if key and key not in seen:
            seen.add(key)
            unique.append(test)

    return unique


def find_stories_with_linked_tests(
    project_key: str,
    min_tests: int = 1,
    max_stories: int = 50,
    extra_jql: str = "",
) -> Dict[str, Any]:
    """
    Cherche les User Stories ayant au moins min_tests tests liés.
    """
    base = f'project = "{project_key}" AND issuetype = Story'
    jql = f"{base} {extra_jql}" if extra_jql else base

    result = search_issues(
        jql=jql,
        fields="summary,issuetype,status,issuelinks",
        max_per_page=100,
    )

    if result.get("error"):
        return result

    stories_with_tests: List[Dict[str, Any]] = []
    total_scanned = 0

    for issue in result.get("issues", []):
        total_scanned += 1

        linked_tests = _extract_linked_tests(issue)

        if len(linked_tests) < min_tests:
            continue

        fields_data = issue.get("fields") or {}

        stories_with_tests.append(
            {
                "key": issue.get("key", ""),
                "summary": fields_data.get("summary", ""),
                "status": ((fields_data.get("status") or {}).get("name") or ""),
                "linked_tests_count": len(linked_tests),
                "linked_tests": linked_tests,
            }
        )

        if len(stories_with_tests) >= max_stories:
            break

    stories_with_tests.sort(
        key=lambda story: story["linked_tests_count"],
        reverse=True,
    )

    return {
        "project_key": project_key,
        "jql": jql,
        "min_tests": min_tests,
        "total_stories_scanned": total_scanned,
        "total_stories_with_tests": len(stories_with_tests),
        "stories": stories_with_tests,
    }


# ============================================================
# Extraction steps Xray
# ============================================================


def _extract_xray_steps_from_customfields(
    fields: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Extrait les steps depuis les custom fields Jira/Xray si présents.
    """
    steps: List[Dict[str, Any]] = []

    for key, value in (fields or {}).items():
        if not key.startswith("customfield_"):
            continue

        if isinstance(value, dict) and isinstance(value.get("steps"), list):
            for step in value.get("steps", []):
                step_fields = (step or {}).get("fields") or {}

                steps.append(
                    {
                        "index": step.get("index", len(steps) + 1),
                        "action": (
                            step_fields.get("action") or step_fields.get("Action") or ""
                        ),
                        "data": (
                            step_fields.get("data") or step_fields.get("Data") or ""
                        ),
                        "expected_result": (
                            step_fields.get("expected result")
                            or step_fields.get("Expected Result")
                            or step_fields.get("expectedresult")
                            or step_fields.get("Expected_Result")
                            or ""
                        ),
                    }
                )

        elif isinstance(value, list) and value and isinstance(value[0], dict):
            for index, step in enumerate(value, start=1):
                lowered = {str(k).lower(): v for k, v in step.items()}

                if "action" not in lowered:
                    continue

                steps.append(
                    {
                        "index": index,
                        "action": lowered.get("action") or "",
                        "data": lowered.get("data") or "",
                        "expected_result": (
                            lowered.get("expected result")
                            or lowered.get("expectedresult")
                            or ""
                        ),
                    }
                )

    return steps


def _fetch_xray_steps_api(
    test_key: str,
    use_test_jira: bool = False,
) -> List[Dict[str, Any]]:
    """
    Récupère les steps via API Xray.
    """
    jira_url = JIRA_TEST_URL if use_test_jira else JIRA_PROD_URL
    session = _session_test if use_test_jira else _session_prod

    candidate_urls = [
        f"{jira_url}/rest/raven/1.0/api/test/{test_key}/step",
        f"{jira_url}/rest/raven/2.0/api/test/{test_key}/step",
    ]

    for url in candidate_urls:
        try:
            resp = session.get(url, timeout=20)
        except requests.RequestException:
            continue

        if resp.status_code != 200:
            continue

        try:
            data = resp.json()
        except ValueError:
            continue

        steps: List[Dict[str, Any]] = []

        if isinstance(data, list):
            for raw_step in data:
                fields = (raw_step or {}).get("fields") or {}

                action_raw = fields.get("action")
                data_raw = fields.get("data")
                expected_raw = fields.get("expected result")

                action = (
                    action_raw.get("value")
                    if isinstance(action_raw, dict)
                    else action_raw
                )

                data_value = (
                    data_raw.get("value") if isinstance(data_raw, dict) else data_raw
                )

                expected_result = (
                    expected_raw.get("value")
                    if isinstance(expected_raw, dict)
                    else expected_raw
                )

                steps.append(
                    {
                        "index": raw_step.get("index", len(steps) + 1),
                        "action": action or raw_step.get("step") or "",
                        "data": data_value or raw_step.get("data") or "",
                        "expected_result": (
                            expected_result
                            or raw_step.get("result")
                            or raw_step.get("expectedResult")
                            or ""
                        ),
                    }
                )

        if steps:
            return steps

    return []


def get_test_byID(test_key: str, use_test_jira: bool = False) -> Dict[str, Any]:
    """
    Récupère un test Xray par clé.
    """
    jira_url = JIRA_TEST_URL if use_test_jira else JIRA_PROD_URL
    session = _session_test if use_test_jira else _session_prod

    url = f"{jira_url}/rest/api/2/issue/{test_key}"

    try:
        resp = session.get(url, timeout=20)
    except requests.RequestException as exc:
        return {
            "key": test_key,
            "error": str(exc),
        }

    if resp.status_code != 200:
        return {
            "key": test_key,
            "error": True,
            "status_code": resp.status_code,
            "body": resp.text[:1000],
        }

    issue = resp.json() or {}
    fields = issue.get("fields") or {}

    steps = _fetch_xray_steps_api(
        test_key=test_key,
        use_test_jira=use_test_jira,
    )

    if not steps:
        steps = _extract_xray_steps_from_customfields(fields)

    return {
        "key": test_key,
        "summary": fields.get("summary") or "",
        "description": fields.get("description") or "",
        "issuetype": ((fields.get("issuetype") or {}).get("name") or ""),
        "priority": ((fields.get("priority") or {}).get("name") or ""),
        "status": ((fields.get("status") or {}).get("name") or ""),
        "labels": fields.get("labels") or [],
        "components": [
            component.get("name")
            for component in (fields.get("components") or [])
            if component.get("name")
        ],
        "steps": steps,
        "steps_count": len(steps),
    }


# ============================================================
# Création issue Jira/Xray
# ============================================================


def _collect_rejected_fields(body: Any) -> set:
    """Collect field names rejected by Jira create/update APIs."""
    rejected: set = set()

    if not isinstance(body, dict):
        return rejected

    errors = body.get("errors") or {}
    if isinstance(errors, dict):
        rejected.update(errors.keys())

    for message in body.get("errorMessages") or []:
        if not isinstance(message, str):
            continue
        match = re.search(r"Field '([^']+)' cannot be set", message)
        if match:
            rejected.add(match.group(1))

    return rejected


def _is_field_rejected_error(body: Any, field_name: str) -> bool:
    """
    Détecte si Jira a rejeté un champ spécifique.
    """
    return field_name in _collect_rejected_fields(body)


def fetch_create_meta(
    session: requests.Session,
    jira_url: str,
    project_key: str,
    issue_type_name: str = "Test",
) -> Dict[str, Any]:
    """
    Récupère les champs autorisés à la création pour un type d'issue.
    """
    url = f"{jira_url}/rest/api/2/issue/createmeta"
    params = {
        "projectKeys": project_key,
        "issuetypeNames": issue_type_name,
        "expand": "projects.issuetypes.fields",
    }

    try:
        resp = session.get(url, params=params, timeout=30)
    except requests.RequestException as exc:
        return {"error": str(exc)}

    if resp.status_code != 200:
        return {
            "error": True,
            "status_code": resp.status_code,
            "body": resp.text[:2000],
        }

    data = resp.json() or {}
    projects = data.get("projects") or []

    for project in projects:
        if project.get("key") != project_key:
            continue

        for issue_type in project.get("issuetypes") or []:
            name = (issue_type.get("name") or "").strip()
            if name.lower() != issue_type_name.lower():
                continue

            fields = issue_type.get("fields") or {}
            return {
                "issuetype": {
                    "id": issue_type.get("id"),
                    "name": name,
                },
                "allowed_fields": set(fields.keys()),
                "required_fields": {
                    field_key
                    for field_key, field_meta in fields.items()
                    if (field_meta or {}).get("required")
                },
            }

    return {
        "error": True,
        "message": (
            f"Issue type '{issue_type_name}' not found in createmeta "
            f"for project {project_key}"
        ),
    }


def _resolve_test_issuetype(
    issue_type_name: str,
    create_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Résout le type d'issue Test sans forcer un ID d'environnement.
    """
    if create_meta and create_meta.get("issuetype", {}).get("id"):
        return {"id": str(create_meta["issuetype"]["id"])}

    return {"name": issue_type_name}


def _normalize_priority_for_jira(priority: Optional[str]) -> Optional[str]:
    """Retourne un nom de priorité Jira compatible avec le projet cible.
    Ce projet Jira n'accepte que 3 valeurs exactes : P1-High, P2-Medium, P3-Low."""
    if not priority:
        return None
    normalized = priority.strip()
    lower = normalized.lower()

    if lower.startswith("p1"):
        return "P1-High"
    if lower.startswith("p2"):
        return "P2-Medium"
    if lower.startswith("p3"):
        return "P3-Low"

    if "high" in lower or "haut" in lower or "critique" in lower or "critical" in lower:
        return "P1-High"
    if "medium" in lower or "moyen" in lower or "moyenne" in lower:
        return "P2-Medium"
    if "low" in lower or "bas" in lower or "faible" in lower:
        return "P3-Low"

    # Valeur non reconnue : ne pas envoyer un champ que Jira rejettera silencieusement
    return None


def _filter_fields_for_create(
    fields: Dict[str, Any],
    allowed_fields: Optional[set],
) -> Dict[str, Any]:
    if not allowed_fields:
        return fields

    filtered = {
        key: value
        for key, value in fields.items()
        if key in allowed_fields or key in {"project", "issuetype", "summary"}
    }

    filtered["project"] = fields["project"]
    filtered["issuetype"] = fields["issuetype"]
    # Ne forcer summary que s'il est dans allowed_fields
    if "summary" in fields and "summary" in allowed_fields:
        filtered["summary"] = fields["summary"]
    elif "summary" in fields:
        # Inclure par défaut même si absent du createmeta (requis par Jira)
        filtered["summary"] = fields["summary"]
    return filtered


def _post_jira_issue(
    session: requests.Session,
    url: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    POST Jira issue.
    """
    try:
        resp = session.post(url, json=payload, timeout=30)
    except requests.RequestException as exc:
        return {
            "error": True,
            "message": str(exc),
        }

    if resp.status_code not in (200, 201):
        raw_body = resp.text

        try:
            parsed_body: Any = resp.json()
        except ValueError:
            parsed_body = raw_body

        return {
            "error": True,
            "status_code": resp.status_code,
            "body": parsed_body,
            "raw_body": raw_body[:3000],
        }

    try:
        result = resp.json()
    except ValueError:
        return {
            "error": True,
            "status_code": resp.status_code,
            "body": "Unable to parse Jira response as JSON",
            "raw_body": resp.text[:3000],
        }

    if isinstance(result, dict) and (
        result.get("errorMessages") or result.get("errors")
    ):
        return {
            "error": True,
            "status_code": resp.status_code,
            "body": result,
        }

    return result


def _update_issue_fields(
    issue_key: str,
    fields: Dict[str, Any],
    use_test_jira: bool = False,
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    """
    Met à jour des champs Jira.
    """
    jira_url = JIRA_TEST_URL if use_test_jira else JIRA_PROD_URL
    jira_session = session or (_session_test if use_test_jira else _session_prod)

    url = f"{jira_url}/rest/api/2/issue/{issue_key}"

    payload = {
        "fields": fields,
    }

    try:
        resp = jira_session.put(url, json=payload, timeout=30)
    except requests.RequestException as exc:
        return {
            "error": True,
            "message": str(exc),
        }

    if resp.status_code not in (200, 204):
        raw_body = resp.text

        try:
            parsed_body: Any = resp.json()
        except ValueError:
            parsed_body = raw_body

        return {
            "error": True,
            "status_code": resp.status_code,
            "body": parsed_body,
            "raw_body": raw_body[:3000],
        }

    return {
        "ok": True,
    }


def _build_xray_step_payload(steps: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Format Xray Server/DC pour Manual Test Steps via l'API REST Jira (create/update).

    Xray Server stocke chaque champ de step comme un objet rich-text :
        {"value": "texte"}
    Passer une simple string fait que Xray accepte le payload sans erreur
    mais n'enregistre aucune étape (comportement silencieux).

    Champs attendus (noms en minuscules) :
        action, data, expected result
    """
    payload: List[Dict[str, Any]] = []

    for index, step in enumerate(steps, start=1):
        expected_result = (
            step.get("result")
            or step.get("expected_result")
            or step.get("expectedResult")
            or ""
        )

        payload.append(
            {
                "index": index,
                "fields": {
                    "action": {"value": step.get("action", "") or ""},
                    "data": {"value": step.get("data", "") or ""},
                    "expected result": {"value": expected_result},
                },
            }
        )

    return payload


def create_test_issue(
    project_key: str,
    summary: str,
    description: str,
    issue_type: str = "Test",
    steps: Optional[List[Dict[str, str]]] = None,
    use_test_jira: bool = False,
    session: Optional[requests.Session] = None,
    priority: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Crée une issue Jira de type Test, puis tente d'ajouter les steps Xray.

    NB : l'ajout des steps nécessite le droit *Edit Issues* dans le projet
    (API Xray Raven PUT .../step). Sans ce droit, le test est créé mais les
    steps ne peuvent pas être posés — voir le warning renvoyé.
    """
    import logging

    logger = logging.getLogger(__name__)

    jira_url = JIRA_TEST_URL if use_test_jira else JIRA_PROD_URL
    jira_session = session or (_session_test if use_test_jira else _session_prod)

    url = f"{jira_url}/rest/api/2/issue"

    # Tronquer le summary par sécurité (limite Jira = 255 chars)
    safe_summary = summary[:255] if len(summary) > 255 else summary

    create_meta = fetch_create_meta(
        session=jira_session,
        jira_url=jira_url,
        project_key=project_key,
        issue_type_name=issue_type,
    )
    if create_meta.get("error") and not XRAY_TEST_ISSUETYPE_ID:
        logger.warning(
            "[create_test_issue] createmeta unavailable for %s/%s: %s",
            project_key,
            issue_type,
            create_meta.get("message")
            or create_meta.get("body")
            or create_meta.get("error"),
        )

    issuetype_ref = _resolve_test_issuetype(issue_type, create_meta)
    allowed_fields = (
        create_meta.get("allowed_fields") if not create_meta.get("error") else None
    )

    create_fields: Dict[str, Any] = {
        "project": {"key": project_key},
        "issuetype": issuetype_ref,
        "summary": safe_summary,
    }

    # Ajouter la description dès la création si Jira l'autorise
    if description and (not allowed_fields or "description" in allowed_fields):
        create_fields["description"] = description

    # Ajouter la priorité si fournie et autorisée
    normalized_priority = _normalize_priority_for_jira(priority)
    if normalized_priority and (not allowed_fields or "priority" in allowed_fields):
        create_fields["priority"] = {"name": normalized_priority}

    # Test Type = Manual : requis pour activer l'onglet "Test Details".
    if not allowed_fields or XRAY_FIELD_TEST_TYPE in allowed_fields:
        create_fields[XRAY_FIELD_TEST_TYPE] = {"value": "Manual"}

    # NOTE : customfield_14404 (Manual Steps) est intentionnellement ABSENT
    # du payload de création. Xray Server l'ignore silencieusement quand il
    # est posé via POST /rest/api/2/issue — les steps seront ajoutés après
    # la création via l'API Raven /step.

    create_fields = _filter_fields_for_create(create_fields, allowed_fields)

    logger.info(
        "[create_test_issue] Creating Test in %s, project=%s, fields=%s",
        jira_url,
        project_key,
        list(create_fields.keys()),
    )

    result = _post_jira_issue(
        session=jira_session,
        url=url,
        payload={"fields": create_fields},
    )

    if result.get("error"):
        rejected = _collect_rejected_fields(result.get("body"))
        if rejected:
            # Retirer les champs rejetés SAUF project et issuetype (indispensables)
            retry_fields = {
                key: value
                for key, value in create_fields.items()
                if key not in rejected or key in {"project", "issuetype"}
            }
            if retry_fields.get("project") and retry_fields.get("issuetype"):
                logger.warning(
                    "[create_test_issue] Retrying minimal create without fields: %s",
                    sorted(rejected),
                )
                result = _post_jira_issue(
                    session=jira_session,
                    url=url,
                    payload={"fields": retry_fields},
                )

        if result.get("error") and issuetype_ref.get("id"):
            logger.warning(
                "[create_test_issue] Retrying create with issuetype name '%s'",
                issue_type,
            )
            fallback_fields = {
                "project": {"key": project_key},
                "issuetype": {"name": issue_type},
                "summary": safe_summary,
            }
            fallback_fields = _filter_fields_for_create(
                fallback_fields,
                allowed_fields,
            )
            result = _post_jira_issue(
                session=jira_session,
                url=url,
                payload={"fields": fallback_fields},
            )

    if result.get("error"):
        return result

    issue_key = result.get("key")
    if not issue_key:
        return {
            "error": True,
            "message": "Jira n'a pas renvoyé de clé d'issue après création.",
            "body": result,
        }

    post_create_errors: List[str] = []

    if steps:
        # Ajouter les steps via l'API Raven après création.
        # Même si customfield_14404 est présent sur l'écran de création,
        # Xray Server l'ignore silencieusement via POST /rest/api/2/issue.
        # La seule voie fiable est l'API Raven /step.
        logger.info(
            "[create_test_issue] Ajout de %d step(s) sur %s via Raven API",
            len(steps),
            issue_key,
        )
        add_steps_result = add_xray_test_steps(
            test_key=issue_key,
            steps=steps,
            use_test_jira=use_test_jira,
            session=jira_session,
        )
        logger.info(
            "[create_test_issue] Raven step result for %s: %s",
            issue_key,
            add_steps_result,
        )
        if add_steps_result.get("error"):
            post_create_errors.append(
                json.dumps(add_steps_result, ensure_ascii=False, indent=2)
            )

    if post_create_errors:
        logger.warning(
            "[create_test_issue] Test %s created with post-create warnings: %s",
            issue_key,
            post_create_errors,
        )
        result["warnings"] = post_create_errors

    return result


def add_xray_test_steps(
    test_key: str,
    steps: List[Dict[str, str]],
    use_test_jira: bool = False,
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    """
    Ajoute des steps à un Test Xray existant via l'API Raven.

    Endpoint correct sur Xray Server/DC :
        PUT /rest/raven/1.0/api/test/{key}/step   (le POST renvoie 405)

    ⚠ Nécessite le droit *Edit Issues* sur le projet. Sans ce droit,
    l'API renvoie HTTP 403 et les steps ne peuvent PAS être ajoutés
    (aucun contournement côté code — c'est une restriction serveur).
    """
    import logging

    logger = logging.getLogger(__name__)

    if not steps:
        return {
            "ok": True,
            "note": "No steps to add",
        }

    jira_url = JIRA_TEST_URL if use_test_jira else JIRA_PROD_URL
    jira_session = session or (_session_test if use_test_jira else _session_prod)

    url = f"{jira_url}/rest/raven/1.0/api/test/{test_key}/step"

    api_errors: List[str] = []
    permission_denied = False
    success_count = 0

    for index, step in enumerate(steps, start=1):
        payload: Dict[str, Any] = {
            "step": step.get("action", "") or "",
            "result": (step.get("result") or step.get("expected_result") or ""),
            "data": str(step.get("data", "") or "none").strip() or "none",
        }

        try:
            resp = jira_session.put(url, json=payload, timeout=30)
        except requests.RequestException as exc:
            api_errors.append(f"PUT {url} step {index}: {exc}")
            continue

        logger.info(
            "[add_xray_test_steps] PUT step %d → HTTP %d : %s",
            index,
            resp.status_code,
            resp.text[:300],
        )

        if resp.status_code in (200, 201, 204):
            success_count += 1
            continue

        if resp.status_code in (401, 403):
            permission_denied = True

        api_errors.append(
            f"PUT {url} step {index}: HTTP {resp.status_code} - {resp.text[:300]}"
        )

    if success_count == len(steps):
        return {
            "ok": True,
            "method": url,
        }

    if permission_denied:
        return {
            "error": True,
            "code": "PERMISSION_DENIED",
            "message": (
                f"Impossible d'ajouter les steps sur {test_key} : le compte "
                f"utilisé n'a pas le droit *Edit Issues* sur ce projet (HTTP 403). "
                f"Le test est créé mais les étapes doivent être ajoutées à la main, "
                f"ou l'intégration doit utiliser un compte disposant du droit d'édition. "
                f"Aucun contournement possible côté application."
            ),
            "api_errors": api_errors,
        }

    return {
        "error": True,
        "message": (
            f"Échec de l'ajout des steps sur {test_key} via l'API Raven "
            f"({success_count}/{len(steps)} steps ajoutés)."
        ),
        "api_errors": api_errors,
    }


def _fetch_xray_step_ids(
    test_key: str,
    use_test_jira: bool = False,
    session: Optional[requests.Session] = None,
) -> tuple:
    """Récupère les IDs des steps existants (nécessaires pour DELETE)."""
    jira_url = JIRA_TEST_URL if use_test_jira else JIRA_PROD_URL
    jira_session = session or (_session_test if use_test_jira else _session_prod)

    candidate_urls = [
        f"{jira_url}/rest/raven/1.0/api/test/{test_key}/step",
        f"{jira_url}/rest/raven/2.0/api/test/{test_key}/step",
    ]

    for url in candidate_urls:
        try:
            resp = jira_session.get(url, timeout=20)
        except requests.RequestException:
            continue

        if resp.status_code != 200:
            continue

        try:
            data = resp.json()
        except ValueError:
            continue

        if isinstance(data, list):
            ids = [step.get("id") for step in data if step.get("id") is not None]
            return ids, url

    return [], None


def delete_xray_test_steps(
    test_key: str,
    use_test_jira: bool = False,
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    """Supprime tous les steps existants d'un test avant réintégration."""
    jira_session = session or (_session_test if use_test_jira else _session_prod)

    step_ids, base_url = _fetch_xray_step_ids(test_key, use_test_jira, jira_session)

    if not step_ids:
        return {"ok": True, "deleted": 0}

    deleted = 0
    errors: List[str] = []

    for step_id in step_ids:
        url = f"{base_url}/{step_id}"
        try:
            resp = jira_session.delete(url, timeout=30)
        except requests.RequestException as exc:
            errors.append(f"DELETE step {step_id}: {exc}")
            continue

        if resp.status_code in (200, 204):
            deleted += 1
        else:
            errors.append(
                f"DELETE step {step_id}: HTTP {resp.status_code} - {resp.text[:200]}"
            )

    if errors:
        return {
            "error": True,
            "deleted": deleted,
            "total": len(step_ids),
            "errors": errors,
        }

    return {"ok": True, "deleted": deleted}


def replace_xray_test_steps(
    test_key: str,
    steps: List[Dict[str, str]],
    use_test_jira: bool = False,
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    """
    Réintégration : supprime les steps existants puis recrée les steps
    à jour. C'est la seule façon fiable de refléter les modifications
    faites côté app dans Xray (l'API Raven n'a pas de vrai 'update in place'
    exploitable ici).
    """
    jira_session = session or (_session_test if use_test_jira else _session_prod)

    delete_result = delete_xray_test_steps(test_key, use_test_jira, jira_session)

    if delete_result.get("error"):
        return {
            "error": True,
            "stage": "delete",
            "detail": delete_result,
        }

    return add_xray_test_steps(test_key, steps, use_test_jira, jira_session)


def search_test_issue_by_summary(
    project_key: str,
    summary: str,
    use_test_jira: bool = False,
    session: Optional[requests.Session] = None,
) -> Optional[str]:
    """
    Recherche un Test existant par summary pour éviter les doublons.
    """
    safe_summary = summary.replace('"', '\\"')

    jql = (
        f'project = "{project_key}" '
        f"AND issuetype = Test "
        f'AND summary ~ "{safe_summary}"'
    )

    if use_test_jira:
        result = search_issues_with_session(
            jql=jql,
            session=session or _session_test,
            jira_url=JIRA_TEST_URL,
            fields="key,summary",
            max_per_page=10,
        )
    else:
        result = search_issues(
            jql=jql,
            fields="key,summary",
            max_per_page=10,
        )

    if result.get("error"):
        return None

    issues = result.get("issues") or []

    if not issues:
        return None

    return issues[0].get("key")


# ============================================================
# Enrichissement tests existants
# ============================================================


def enrich_dataset_with_test_details(
    dataset: Dict[str, Any],
    max_tests_per_story: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Enrichit un dataset story -> tests avec les détails des tests.
    """
    stories = dataset.get("stories") or []
    enriched_stories = []

    for story in stories:
        linked = story.get("linked_tests") or []

        if max_tests_per_story is not None:
            linked = linked[:max_tests_per_story]

        detailed_tests = []

        for test in linked:
            key = test.get("key")

            if not key:
                continue

            details = get_test_byID(key)
            details["link_type"] = test.get("link_type", "")
            detailed_tests.append(details)

        enriched_stories.append(
            {
                **story,
                "linked_tests": detailed_tests,
            }
        )

    return {
        **dataset,
        "enriched": True,
        "stories": enriched_stories,
    }


# ============================================================
# Legacy Xray pivot / RAG
# ============================================================

DEFAULT_LEGACY_TEST_PROJECTS = [
    "YOUQA",
    "QAGT",
    "YTINMA",
    "HRAE2EQA",
    "PLD4UE2E",
]

LEGACY_TEST_FIELDS = ",".join(
    [
        "summary",
        "description",
        "labels",
        "components",
        "fixVersions",
        "issuelinks",
        "priority",
        "status",
        "created",
        "updated",
        "issuetype",
        "project",
        XRAY_FIELD_STEPS,
        XRAY_FIELD_REPO_PATH,
        XRAY_FIELD_TEST_TYPE,
        XRAY_FIELD_PRECONDITIONS,
        XRAY_FIELD_STEPS_COUNT,
        JIRA_EPIC_LINK_FIELD,
    ]
)


def _parse_repo_path(raw: Any) -> Dict[str, Optional[str]]:
    """
    Extrait le chemin du Test Repository Xray.
    """
    if raw is None:
        return {
            "path": None,
            "root": None,
        }

    path = ""

    if isinstance(raw, str):
        path = raw

    elif isinstance(raw, dict):
        path = raw.get("path") or raw.get("value") or ""

    elif isinstance(raw, list) and raw:
        first = raw[0]

        if isinstance(first, dict):
            path = first.get("path") or first.get("value") or ""
        else:
            path = str(first)

    path = clean_text(path).strip() if path else ""

    if not path:
        return {
            "path": None,
            "root": None,
        }

    normalized = path.strip("/").strip()

    if not normalized:
        return {
            "path": path,
            "root": None,
        }

    root = normalized.split("/", 1)[0].strip()

    return {
        "path": path,
        "root": root or None,
    }


def _parse_precondition_keys(raw: Any) -> List[str]:
    """
    Extrait les clés de preconditions Xray.
    """
    if not raw:
        return []

    pattern = re.compile(r"[A-Z][A-Z0-9_]+-\d+")

    if isinstance(raw, list):
        keys: List[str] = []

        for item in raw:
            if isinstance(item, dict):
                key = item.get("key") or item.get("value")

                if key:
                    keys.append(key)

            elif isinstance(item, str):
                keys.extend(pattern.findall(item))

        return keys

    if isinstance(raw, str):
        return pattern.findall(raw)

    return []


def _parse_test_type(raw: Any) -> str:
    """
    Extrait le type de test Xray.
    """
    if not raw:
        return ""

    if isinstance(raw, dict):
        return (raw.get("value") or raw.get("name") or "").strip()

    if isinstance(raw, str):
        return raw.strip()

    return ""


def _coerce_step_field(raw: Any) -> str:
    """
    Normalise un champ step en texte.
    """
    if raw is None:
        return ""

    if isinstance(raw, str):
        return raw

    if isinstance(raw, dict):
        for key in ("value", "raw", "rendered", "text", "html"):
            value = raw.get(key)

            if isinstance(value, str) and value:
                return value

        return ""

    if isinstance(raw, list):
        parts = [_coerce_step_field(item) for item in raw]
        return "\n".join(part for part in parts if part)

    return str(raw)


def _parse_issue_links(raw: Any) -> Dict[str, List[Dict[str, str]]]:
    """
    Normalise les liens Jira.
    """
    output: Dict[str, List[Dict[str, str]]] = {
        "outward": [],
        "inward": [],
    }

    if not isinstance(raw, list):
        return output

    for link in raw:
        if not isinstance(link, dict):
            continue

        link_type = link.get("type") or {}
        type_name = link_type.get("name") or ""

        outward_issue = link.get("outwardIssue")

        if isinstance(outward_issue, dict) and outward_issue.get("key"):
            outward_fields = outward_issue.get("fields") or {}

            output["outward"].append(
                {
                    "key": outward_issue.get("key"),
                    "type": type_name,
                    "direction": link_type.get("outward") or "",
                    "summary": outward_fields.get("summary") or "",
                }
            )

        inward_issue = link.get("inwardIssue")

        if isinstance(inward_issue, dict) and inward_issue.get("key"):
            inward_fields = inward_issue.get("fields") or {}

            output["inward"].append(
                {
                    "key": inward_issue.get("key"),
                    "type": type_name,
                    "direction": link_type.get("inward") or "",
                    "summary": inward_fields.get("summary") or "",
                }
            )

    return output


LEGACY_TEST_PROJECT_PREFIXES = {
    "YOUQA",
    "QAGT",
    "YTINMA",
    "HRAE2EQA",
    "PLD4UE2E",
}

COVERAGE_LINK_TYPES = {
    "tests",
    "resolve",
}


def _extract_covered_stories(
    links: Dict[str, List[Dict[str, str]]],
) -> List[str]:
    """
    Extrait les stories couvertes par un test.
    """
    covered: List[str] = []

    for group in ("outward", "inward"):
        for link in links.get(group, []):
            link_type = (link.get("type") or "").lower()

            if link_type not in COVERAGE_LINK_TYPES:
                continue

            key = link.get("key") or ""

            if not key:
                continue

            target_project = key.split("-", 1)[0] if "-" in key else key

            if target_project in LEGACY_TEST_PROJECT_PREFIXES:
                continue

            if key not in covered:
                covered.append(key)

    return covered


def get_legacy_test_pivot(test_key: str) -> Dict[str, Any]:
    """
    Récupère un test Xray au format pivot pour RAG.
    """
    url = f"{JIRA_PROD_URL}/rest/api/2/issue/{test_key}"

    try:
        resp = _session_prod.get(
            url,
            params={"fields": LEGACY_TEST_FIELDS},
            timeout=30,
        )
    except requests.RequestException as exc:
        return {
            "test_id": test_key,
            "error": True,
            "body": str(exc),
        }

    if resp.status_code != 200:
        return {
            "test_id": test_key,
            "error": True,
            "status_code": resp.status_code,
            "body": resp.text[:1000],
        }

    issue = resp.json() or {}
    fields = issue.get("fields") or {}

    steps_raw = _fetch_xray_steps_api(test_key)

    if not steps_raw:
        steps_raw = _extract_xray_steps_from_customfields(fields)

    steps_clean: List[Dict[str, Any]] = []

    for step in steps_raw:
        steps_clean.append(
            {
                "index": step.get("index"),
                "action": clean_text(_coerce_step_field(step.get("action"))),
                "data": clean_text(_coerce_step_field(step.get("data"))),
                "expected_result": clean_text(
                    _coerce_step_field(step.get("expected_result"))
                ),
            }
        )

    repo = _parse_repo_path(fields.get(XRAY_FIELD_REPO_PATH))

    key = issue.get("key") or test_key

    project_key = (fields.get("project") or {}).get("key") or (
        key.split("-", 1)[0] if "-" in key else ""
    )

    links = _parse_issue_links(fields.get("issuelinks"))
    covered = _extract_covered_stories(links)

    return {
        "test_id": key,
        "project": project_key,
        "title": clean_text(fields.get("summary") or ""),
        "description": clean_text(fields.get("description") or ""),
        "preconditions": _parse_precondition_keys(fields.get(XRAY_FIELD_PRECONDITIONS)),
        "covered_stories": covered,
        "steps": steps_clean,
        "metadata": {
            "module_path": repo["path"],
            "module_root": repo["root"],
            "components": [
                component.get("name")
                for component in (fields.get("components") or [])
                if component.get("name")
            ],
            "labels": fields.get("labels") or [],
            "fix_versions": [
                version.get("name")
                for version in (fields.get("fixVersions") or [])
                if version.get("name")
            ],
            "epic_link": fields.get(JIRA_EPIC_LINK_FIELD) or None,
            "test_type": _parse_test_type(fields.get(XRAY_FIELD_TEST_TYPE)),
            "priority": ((fields.get("priority") or {}).get("name") or ""),
            "status": ((fields.get("status") or {}).get("name") or ""),
            "issuetype": ((fields.get("issuetype") or {}).get("name") or ""),
            "steps_count": len(steps_clean),
            "created": fields.get("created"),
            "updated": fields.get("updated"),
            "issue_links": links,
        },
    }


DEFAULT_LEGACY_JQL_FILTER = '"Test Type" = Manual'


def list_project_legacy_tests(
    project_key: str,
    extra_jql: str = "",
    max_results: Optional[int] = None,
    apply_default_filter: bool = True,
) -> Dict[str, Any]:
    """
    Liste les tests Xray d'un projet.
    """
    base = f'project = "{project_key}" AND issuetype = Test'

    if apply_default_filter:
        base = f"{base} AND {DEFAULT_LEGACY_JQL_FILTER}"

    jql = f"{base} AND ({extra_jql})" if extra_jql else base

    result = search_issues(
        jql=jql,
        fields="summary,status,updated",
        max_per_page=100,
    )

    if result.get("error"):
        return result

    issues = result.get("issues") or []

    if max_results is not None:
        issues = issues[:max_results]

    return {
        "project": project_key,
        "jql": jql,
        "total": result.get("total"),
        "returned": len(issues),
        "tests": [
            {
                "key": issue.get("key"),
                "summary": (issue.get("fields") or {}).get("summary"),
                "status": (
                    ((issue.get("fields") or {}).get("status") or {}).get("name")
                ),
                "updated": (issue.get("fields") or {}).get("updated"),
            }
            for issue in issues
        ],
    }


def extract_legacy_tests_pivot(
    project_keys: List[str],
    extra_jql: str = "",
    limit_per_project: Optional[int] = None,
    apply_default_filter: bool = True,
) -> Dict[str, Any]:
    """
    Extrait les tests Xray au format pivot.
    """
    results: Dict[str, Any] = {
        "projects": {},
        "total": 0,
        "errors": [],
    }

    for project in project_keys:
        listing = list_project_legacy_tests(
            project_key=project,
            extra_jql=extra_jql,
            max_results=limit_per_project,
            apply_default_filter=apply_default_filter,
        )

        if listing.get("error"):
            results["errors"].append(
                {
                    "project": project,
                    "error": listing,
                }
            )
            continue

        tests_pivot: List[Dict[str, Any]] = []

        for test in listing.get("tests", []):
            key = test.get("key")

            if not key:
                continue

            pivot = get_legacy_test_pivot(key)

            if pivot.get("error"):
                results["errors"].append(
                    {
                        "project": project,
                        "test_id": key,
                        "error": pivot.get("body") or "unknown",
                    }
                )
                continue

            tests_pivot.append(pivot)

        results["projects"][project] = {
            "count": len(tests_pivot),
            "total_in_jira": listing.get("total"),
            "tests": tests_pivot,
        }

        results["total"] += len(tests_pivot)

    return results


# ============================================================
# Liens Jira : Story <-> Test, Test <-> Test (Relates)
# ============================================================


def create_issue_link(
    from_key: str,
    to_key: str,
    link_type_name: str,
    use_test_jira: bool = False,
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    """
    Crée un lien Jira entre deux issues.
    from_key = outwardIssue, to_key = inwardIssue.
    """
    jira_url = JIRA_TEST_URL if use_test_jira else JIRA_PROD_URL
    jira_session = session or (_session_test if use_test_jira else _session_prod)

    url = f"{jira_url}/rest/api/2/issueLink"
    payload = {
        "type": {"name": link_type_name},
        "inwardIssue": {"key": to_key},
        "outwardIssue": {"key": from_key},
    }

    try:
        resp = jira_session.post(url, json=payload, timeout=30)
    except requests.RequestException as exc:
        return {"error": True, "message": str(exc)}

    if resp.status_code not in (200, 201):
        return {
            "error": True,
            "status_code": resp.status_code,
            "body": resp.text[:1000],
        }

    return {"ok": True}


def _story_remote_link_exists(
    test_key: str,
    story_url: str,
    use_test_jira: bool = True,
    session: Optional[requests.Session] = None,
) -> bool:
    """Évite de dupliquer le remote link si on réintègre le même test."""
    jira_url = JIRA_TEST_URL if use_test_jira else JIRA_PROD_URL
    jira_session = session or (_session_test if use_test_jira else _session_prod)

    url = f"{jira_url}/rest/api/2/issue/{test_key}/remotelink"
    try:
        resp = jira_session.get(url, timeout=20)
    except requests.RequestException:
        return False

    if resp.status_code != 200:
        return False

    for link in resp.json() or []:
        if (link.get("object") or {}).get("url") == story_url:
            return True
    return False


def create_remote_link_to_story(
    test_key: str,
    story_key: str,
    prod_base_url: Optional[str] = None,
    use_test_jira: bool = True,
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    """
    Crée un lien externe (remote link) depuis un test Xray (Jira TEST)
    vers sa story sur Jira PROD, puisque issueLink ne fonctionne pas
    entre deux instances Jira différentes.
    """
    prod_url = (prod_base_url or JIRA_PROD_URL).rstrip("/")
    jira_url = JIRA_TEST_URL if use_test_jira else JIRA_PROD_URL
    jira_session = session or (_session_test if use_test_jira else _session_prod)

    story_url = f"{prod_url}/browse/{story_key}"

    if _story_remote_link_exists(test_key, story_url, use_test_jira, jira_session):
        return {"ok": True, "note": "already linked"}

    url = f"{jira_url}/rest/api/2/issue/{test_key}/remotelink"
    payload = {
        "object": {
            "url": story_url,
            "title": f"Story liée : {story_key}",
            "icon": {"url16x16": f"{prod_url}/favicon.ico"},
        }
    }

    try:
        resp = jira_session.post(url, json=payload, timeout=30)
    except requests.RequestException as exc:
        return {"error": True, "message": str(exc)}

    if resp.status_code not in (200, 201):
        return {
            "error": True,
            "status_code": resp.status_code,
            "body": resp.text[:1000],
        }

    return {"ok": True}


def get_tests_linked_to_story(
    story_key: str,
    use_test_jira: bool = False,
    session: Optional[requests.Session] = None,
) -> List[Dict[str, str]]:
    """Récupère les tests déjà liés à une story."""
    jira_url = JIRA_TEST_URL if use_test_jira else JIRA_PROD_URL
    jira_session = session or (_session_test if use_test_jira else _session_prod)

    url = f"{jira_url}/rest/api/2/issue/{story_key}"
    try:
        resp = jira_session.get(url, params={"fields": "issuelinks"}, timeout=20)
    except requests.RequestException:
        return []

    if resp.status_code != 200:
        return []

    return _extract_linked_tests(resp.json() or {})


def link_test_to_story_and_related_tests(
    test_key: str,
    story_key: Optional[str],
    project_key: str,
    relates_link_type: str = "Relates",
    use_test_jira: bool = False,
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    results: Dict[str, Any] = {
        "story_link": None,
        "label_result": None,
        "related_test_links": [],
    }

    if not story_key:
        return results

    results["story_link"] = create_remote_link_to_story(
        test_key=test_key,
        story_key=story_key,
        prod_base_url=JIRA_PROD_URL,
        use_test_jira=use_test_jira,
        session=session,
    )

    results["label_result"] = add_story_label_to_test(
        test_key=test_key,
        story_key=story_key,
        use_test_jira=use_test_jira,
        session=session,
    )

    other_test_keys = get_tests_with_story_label(
        story_key=story_key,
        project_key=project_key,
        use_test_jira=use_test_jira,
        session=session,
    )
    other_test_keys = [k for k in other_test_keys if k != test_key]

    for other_key in other_test_keys:
        link_result = create_issue_link(
            from_key=test_key,
            to_key=other_key,
            link_type_name=relates_link_type,
            use_test_jira=use_test_jira,
            session=session,
        )
        results["related_test_links"].append({"test": other_key, "result": link_result})

    return results


def _story_label(story_key: str) -> str:
    """
    Convertit une clé de story en label Jira valide.
    Jira interdit les espaces dans les labels ; les clés (ex: NUXEPM-1842)
    sont déjà sans espace donc pas de transformation nécessaire au-delà
    d'un préfixe pour éviter toute collision avec d'autres labels.
    """
    return f"STORY_{story_key}"


def get_tests_with_story_label(
    story_key: str,
    project_key: str,
    use_test_jira: bool = True,
    session: Optional[requests.Session] = None,
) -> List[str]:
    """
    Cherche les tests (sur Jira TEST) qui portent le label STORY_<story_key>,
    pour identifier les tests 'frères' (même story) à relier en 'Relates'.
    """
    jira_url = JIRA_TEST_URL if use_test_jira else JIRA_PROD_URL
    jira_session = session or (_session_test if use_test_jira else _session_prod)

    label = _story_label(story_key)
    jql = f'project = "{project_key}" AND issuetype = Test AND labels = "{label}"'
    url = f"{jira_url}/rest/api/2/search"

    try:
        resp = jira_session.get(
            url,
            params={"jql": jql, "fields": "key", "maxResults": 50},
            timeout=30,
        )
    except requests.RequestException:
        return []

    if resp.status_code != 200:
        return []

    return [
        issue.get("key") for issue in resp.json().get("issues", []) if issue.get("key")
    ]


def add_story_label_to_test(
    test_key: str,
    story_key: str,
    use_test_jira: bool = True,
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    """
    Ajoute le label STORY_<story_key> au test, sans écraser les labels
    existants (utilise l'opération 'add' de l'API update).
    """
    jira_url = JIRA_TEST_URL if use_test_jira else JIRA_PROD_URL
    jira_session = session or (_session_test if use_test_jira else _session_prod)

    label = _story_label(story_key)
    url = f"{jira_url}/rest/api/2/issue/{test_key}"
    payload = {"update": {"labels": [{"add": label}]}}

    try:
        resp = jira_session.put(url, json=payload, timeout=30)
    except requests.RequestException as exc:
        return {"error": True, "message": str(exc)}

    if resp.status_code not in (200, 204):
        return {
            "error": True,
            "status_code": resp.status_code,
            "body": resp.text[:1000],
        }

    return {"ok": True}
