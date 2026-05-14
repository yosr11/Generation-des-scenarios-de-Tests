# app/api/routes_xray_tests.py
"""
Routes pour récupérer les tests Xray (Generic / Cucumber) depuis Jira Server.
Xray Server stocke les tests comme des issues Jira de type "Test"
avec un champ personnalisé pour le type de test (Manual, Generic, Cucumber).
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from app.services.jira_service import _session, JIRA_BASE_URL, search_issues

router = APIRouter(prefix="/xray", tags=["Xray Tests"])


# ---------- Helpers ----------

def _get_xray_test_type(issue: Dict[str, Any]) -> str:
    """
    Extrait le type de test Xray depuis les champs de l'issue.
    Xray Server utilise un champ personnalisé (souvent customfield_XXXXX)
    ou le endpoint /rest/raven/1.0/api/test/{key}.
    On essaie d'abord via l'API Xray, puis fallback sur les champs.
    """
    key = issue.get("key", "")
    try:
        resp = _session.get(
            f"{JIRA_BASE_URL}/rest/raven/1.0/api/test/{key}",
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("type", "Unknown")
    except Exception:
        pass
    return "Unknown"


def _get_xray_test_details(test_key: str) -> Dict[str, Any]:
    """
    Récupère les détails complets d'un test Xray via l'API Raven.
    - Pour Cucumber : retourne le Gherkin (definition)
    - Pour Generic : retourne la generic definition
    """
    result: Dict[str, Any] = {"key": test_key}

    # 1) Infos de base du test via Xray API
    try:
        resp = _session.get(
            f"{JIRA_BASE_URL}/rest/raven/1.0/api/test/{test_key}",
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            result["type"] = data.get("type", "Unknown")
            result["definition"] = data.get("definition", "")
        else:
            result["type"] = "Unknown"
            result["definition"] = ""
            result["xray_api_error"] = resp.status_code
    except Exception as e:
        result["type"] = "Unknown"
        result["definition"] = ""
        result["xray_api_error"] = str(e)

    # 2) Infos Jira standard (summary, labels, status, etc.)
    try:
        resp = _session.get(
            f"{JIRA_BASE_URL}/rest/api/2/issue/{test_key}",
            params={"fields": "summary,status,labels,components,description,issuelinks,priority"},
            timeout=15,
        )
        if resp.status_code == 200:
            fields = resp.json().get("fields", {})
            result["summary"] = fields.get("summary", "")
            result["status"] = (fields.get("status") or {}).get("name", "")
            result["priority"] = (fields.get("priority") or {}).get("name", "")
            result["labels"] = fields.get("labels", [])
            result["components"] = [
                c.get("name", "") for c in (fields.get("components") or [])
            ]
            result["description"] = fields.get("description", "")
            # Linked stories
            links = fields.get("issuelinks") or []
            result["linked_stories"] = []
            for link in links:
                for direction in ("inwardIssue", "outwardIssue"):
                    target = link.get(direction)
                    if target:
                        target_type = (
                            (target.get("fields") or {})
                            .get("issuetype", {})
                            .get("name", "")
                        )
                        if target_type in ("Story", "User Story", "Récit"):
                            result["linked_stories"].append({
                                "key": target.get("key", ""),
                                "summary": (target.get("fields") or {}).get("summary", ""),
                                "link_type": (link.get("type") or {}).get("name", ""),
                            })
    except Exception:
        pass

    return result


# ---------- Routes ----------

@router.get("/tests/{project_key}")
def get_xray_tests(
    project_key: str,
    test_type: Optional[str] = Query(
        None,
        description="Filtrer par type: 'Generic', 'Cucumber', ou None pour les deux",
    ),
    max_results: int = Query(50, ge=1, le=500),
    story_key: Optional[str] = Query(
        None,
        description="Filtrer les tests liés à une story spécifique (ex: YOUQA-123)",
    ),
):
    """
    Récupère les tests Xray (Generic et/ou Cucumber) d'un projet.
    Utilise la recherche JQL Jira + l'API Xray Raven pour les détails.
    """
    # Build JQL
    jql_parts = [f'project = "{project_key}"', 'issuetype = Test']

    if story_key:
        jql_parts.append(f'issue in testsOf("{story_key}")')

    jql = " AND ".join(jql_parts) + " ORDER BY key ASC"

    # Fetch test issues from Jira
    raw = search_issues(
        jql=jql,
        fields="summary,status,labels,priority",
        max_per_page=min(max_results, 100),
    )

    if raw.get("error"):
        raise HTTPException(
            status_code=raw.get("status_code", 500),
            detail=f"Jira search failed: {raw.get('body', '')[:500]}",
        )

    issues = raw.get("issues", [])

    # Enrich each test with Xray details
    tests: List[Dict[str, Any]] = []
    for issue in issues:
        key = issue.get("key", "")
        details = _get_xray_test_details(key)

        # Filter by test type if requested
        if test_type:
            if details.get("type", "").lower() != test_type.lower():
                continue

        tests.append(details)

        if len(tests) >= max_results:
            break

    return {
        "project": project_key,
        "filter": test_type or "all (Generic + Cucumber)",
        "total_found": raw.get("total", 0),
        "returned": len(tests),
        "tests": tests,
    }


@router.get("/test/{test_key}")
def get_single_xray_test(test_key: str):
    """
    Récupère les détails complets d'un seul test Xray (Generic ou Cucumber).
    Retourne le Gherkin pour Cucumber, la definition pour Generic.
    """
    details = _get_xray_test_details(test_key)

    if details.get("xray_api_error") and not details.get("summary"):
        raise HTTPException(
            status_code=404,
            detail=f"Test {test_key} not found or Xray API unavailable",
        )

    return details


@router.get("/tests/{project_key}/cucumber")
def get_cucumber_tests(
    project_key: str,
    max_results: int = Query(50, ge=1, le=500),
    story_key: Optional[str] = Query(None),
):
    """Raccourci pour récupérer uniquement les tests Cucumber d'un projet."""
    return get_xray_tests(
        project_key=project_key,
        test_type="Cucumber",
        max_results=max_results,
        story_key=story_key,
    )


@router.get("/tests/{project_key}/generic")
def get_generic_tests(
    project_key: str,
    max_results: int = Query(50, ge=1, le=500),
    story_key: Optional[str] = Query(None),
):
    """Raccourci pour récupérer uniquement les tests Generic d'un projet."""
    return get_xray_tests(
        project_key=project_key,
        test_type="Generic",
        max_results=max_results,
        story_key=story_key,
    )
