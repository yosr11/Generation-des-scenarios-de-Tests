import os
import re
import json
import requests
import urllib3

from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

from app.utils.cleaning import clean_text


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


def _create_session() -> requests.Session:
    """
    Crée une session Jira avec auth et headers JSON.
    """
    session = requests.Session()
    session.auth = (JIRA_USERNAME, JIRA_PASSWORD)
    session.verify = False
    session.headers.update(
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
    )
    return session


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

    return [
        issue.get("key")
        for issue in result.get("issues", [])
        if issue.get("key")
    ]


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
    Récupère l'Epic parent d'une story.
    """
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

def _extract_xray_steps_from_customfields(fields: Dict[str, Any]) -> List[Dict[str, Any]]:
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
                            step_fields.get("action")
                            or step_fields.get("Action")
                            or ""
                        ),
                        "data": (
                            step_fields.get("data")
                            or step_fields.get("Data")
                            or ""
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
                    data_raw.get("value")
                    if isinstance(data_raw, dict)
                    else data_raw
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

def _is_field_rejected_error(body: Any, field_name: str) -> bool:
    """
    Détecte si Jira a rejeté un champ spécifique.
    """
    if isinstance(body, dict):
        errors = body.get("errors") or {}

        if field_name in errors:
            return True

        for value in errors.values():
            if isinstance(value, str) and field_name in value:
                return True

        error_messages = body.get("errorMessages") or []

        for message in error_messages:
            if isinstance(message, str) and field_name in message:
                return True

    elif isinstance(body, str):
        return field_name in body

    return False


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
) -> Dict[str, Any]:
    """
    Met à jour des champs Jira.
    """
    jira_url = JIRA_TEST_URL if use_test_jira else JIRA_PROD_URL
    session = _session_test if use_test_jira else _session_prod

    url = f"{jira_url}/rest/api/2/issue/{issue_key}"

    payload = {
        "fields": fields,
    }

    try:
        resp = session.put(url, json=payload, timeout=30)
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
    Format Xray Server/DC pour Manual Test Steps.

    Important :
    - Xray attend généralement : action, data, expected result.
    - Pas Action/Data/Expected Result.
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
                    "action": step.get("action", "") or "",
                    "data": step.get("data", "") or "",
                    "expected result": expected_result,
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
) -> Dict[str, Any]:
    """
    Crée une issue Jira de type Test avec steps Xray dès la création.

    C'est la correction principale :
    On évite de créer le test puis de modifier les steps après,
    car ton Jira retourne un problème de permission sur l'édition.
    """
    import logging

    logger = logging.getLogger(__name__)

    jira_url = JIRA_TEST_URL if use_test_jira else JIRA_PROD_URL
    session = _session_test if use_test_jira else _session_prod

    url = f"{jira_url}/rest/api/2/issue"

    fields: Dict[str, Any] = {
        "project": {"key": project_key},
        "summary": summary,
        "description": description or "",
        "issuetype": {"name": issue_type},
    }

    # Type de test Xray = Manual
    fields[XRAY_FIELD_TEST_TYPE] = {"value": "Manual"}

    # Steps Xray directement dans la création
    if steps:
        fields[XRAY_FIELD_STEPS] = {
            "steps": _build_xray_step_payload(steps)
        }

    payload = {
        "fields": fields,
    }

    logger.info(
        f"[create_test_issue] Creating Test in {jira_url}, "
        f"project={project_key}, steps={len(steps or [])}"
    )
    logger.debug(
        f"[create_test_issue] Payload={json.dumps(payload, ensure_ascii=False)}"
    )

    result = _post_jira_issue(
        session=session,
        url=url,
        payload=payload,
    )

    # Si Jira refuse uniquement Test Type, on réessaie sans ce champ.
    if result.get("error") and _is_field_rejected_error(
        result.get("body"),
        XRAY_FIELD_TEST_TYPE,
    ):
        logger.warning(
            f"[create_test_issue] Jira rejected {XRAY_FIELD_TEST_TYPE}. "
            "Retrying without Test Type field."
        )

        fields_without_test_type = dict(fields)
        fields_without_test_type.pop(XRAY_FIELD_TEST_TYPE, None)

        result = _post_jira_issue(
            session=session,
            url=url,
            payload={"fields": fields_without_test_type},
        )

    # Si Jira refuse les steps, on retente sans steps puis on les ajoute
    # via l'API Xray de test/{key}/step.
    if result.get("error") and _is_field_rejected_error(
        result.get("body"),
        XRAY_FIELD_STEPS,
    ):
        logger.warning(
            "[create_test_issue] Jira rejected %s. Creating test without steps then adding steps via Xray API.",
            XRAY_FIELD_STEPS,
        )

        fields_without_steps = dict(fields)
        fields_without_steps.pop(XRAY_FIELD_STEPS, None)

        retry_result = _post_jira_issue(
            session=session,
            url=url,
            payload={"fields": fields_without_steps},
        )

        if retry_result.get("error"):
            return retry_result

        issue_key = retry_result.get("key")
        if not issue_key:
            return {
                "error": True,
                "message": (
                    "Test créé sans steps, mais Jira n'a pas renvoyé de clé d'issue."
                ),
                "body": retry_result,
            }

        add_steps_result = add_xray_test_steps(
            test_key=issue_key,
            steps=steps,
            use_test_jira=use_test_jira,
        )

        if add_steps_result.get("error"):
            return {
                "error": True,
                "message": (
                    f"Test créé ({issue_key}) mais impossible d'ajouter les étapes "
                    f"via l'API Xray: {add_steps_result.get('message') or add_steps_result.get('body')}"
                ),
                "issue_key": issue_key,
                "steps_error": add_steps_result,
            }

        return retry_result

    return result


def add_xray_test_steps(
    test_key: str,
    steps: List[Dict[str, str]],
    use_test_jira: bool = False,
) -> Dict[str, Any]:
    """
    Ajoute des steps à un test existant.

    Ce fallback peut échouer si ton compte n'a pas Edit/Browse.
    L'intégration principale utilise create_test_issue avec steps directement.
    """
    import logging

    logger = logging.getLogger(__name__)

    if not steps:
        return {
            "ok": True,
            "note": "No steps to add",
        }

    jira_url = JIRA_TEST_URL if use_test_jira else JIRA_PROD_URL
    session = _session_test if use_test_jira else _session_prod

    candidate_urls = [
        f"{jira_url}/rest/raven/1.0/api/test/{test_key}/step",
        f"{jira_url}/rest/raven/2.0/api/test/{test_key}/step",
    ]

    api_errors: List[str] = []

    for url in candidate_urls:
        logger.info(f"[add_xray_test_steps] Trying endpoint: {url}")

        success_count = 0

        for index, step in enumerate(steps, start=1):
            payload = {
                "step": step.get("action", "") or "",
                "data": step.get("data", "") or "",
                "result": (
                    step.get("result")
                    or step.get("expected_result")
                    or ""
                ),
            }

            step_ok = False

            for method in ("post", "put"):
                try:
                    resp = getattr(session, method)(
                        url,
                        json=payload,
                        timeout=30,
                    )
                except requests.RequestException as exc:
                    api_errors.append(
                        f"{method.upper()} {url} step {index}: {exc}"
                    )
                    continue

                logger.info(
                    f"[add_xray_test_steps] {method.upper()} step {index}: "
                    f"status={resp.status_code}"
                )

                if resp.status_code in (200, 201, 204):
                    step_ok = True
                    break

                api_errors.append(
                    f"{method.upper()} {url} step {index}: "
                    f"HTTP {resp.status_code} - {resp.text[:500]}"
                )

            if step_ok:
                success_count += 1

        if success_count == len(steps):
            return {
                "ok": True,
                "method": url,
            }

    # Fallback Jira REST custom field
    fallback_result = _update_issue_fields(
        issue_key=test_key,
        fields={
            XRAY_FIELD_STEPS: {
                "steps": _build_xray_step_payload(steps)
            }
        },
        use_test_jira=use_test_jira,
    )

    if not fallback_result.get("error"):
        return {
            "ok": True,
            "fallback": XRAY_FIELD_STEPS,
        }

    return {
        "error": True,
        "message": (
            "Impossible d'ajouter les steps après création. "
            "Les endpoints Xray et le fallback Jira REST ont échoué. "
            "Cause probable : permission Edit/Browse insuffisante ou champ Xray "
            "non disponible sur l'écran Edit."
        ),
        "api_errors": api_errors,
        "fallback_error": fallback_result,
    }


def search_test_issue_by_summary(
    project_key: str,
    summary: str,
    use_test_jira: bool = False,
) -> Optional[str]:
    """
    Recherche un Test existant par summary pour éviter les doublons.
    """
    safe_summary = summary.replace('"', '\\"')

    jql = (
        f'project = "{project_key}" '
        f'AND issuetype = Test '
        f'AND summary ~ "{safe_summary}"'
    )

    if use_test_jira:
        result = search_issues_with_session(
            jql=jql,
            session=_session_test,
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

    project_key = (
        (fields.get("project") or {}).get("key")
        or (key.split("-", 1)[0] if "-" in key else "")
    )

    links = _parse_issue_links(fields.get("issuelinks"))
    covered = _extract_covered_stories(links)

    return {
        "test_id": key,
        "project": project_key,
        "title": clean_text(fields.get("summary") or ""),
        "description": clean_text(fields.get("description") or ""),
        "preconditions": _parse_precondition_keys(
            fields.get(XRAY_FIELD_PRECONDITIONS)
        ),
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