"""
Routes pour l'extraction des tests Xray "legacy" Sopra HR au format pivot.
Servent à alimenter le RAG few-shot du générateur de tests manuels (Agent 3).
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.jira_service import (
    DEFAULT_LEGACY_TEST_PROJECTS,
    extract_legacy_tests_pivot,
    get_legacy_test_pivot,
    list_project_legacy_tests,
)

router = APIRouter(prefix="/legacy-tests", tags=["legacy-tests"])


class ExtractRequest(BaseModel):
    projects: Optional[List[str]] = None
    extra_jql: str = ""
    limit_per_project: Optional[int] = 10
    apply_default_filter: bool = True


@router.get("/projects")
def get_default_projects():
    """Liste des projets Jira ciblés par défaut pour l'extraction RAG."""
    return {"projects": DEFAULT_LEGACY_TEST_PROJECTS}


@router.get("/test/{test_key}")
def get_one_test(test_key: str):
    """
    Récupère un test Xray donné au format pivot (titre, description,
    préconditions, étapes nettoyées, métadonnées).
    Exemple : `/legacy-tests/test/YOUQA-17641`
    """
    pivot = get_legacy_test_pivot(test_key)
    if pivot.get("error"):
        raise HTTPException(
            status_code=pivot.get("status_code", 500),
            detail=pivot.get("body") or "Erreur Jira inconnue",
        )
    return pivot


@router.get("/project/{project_key}/list")
def list_project_tests_route(
    project_key: str,
    limit: Optional[int] = Query(None, ge=1, le=10000),
    extra_jql: str = Query("", description="JQL supplémentaire, ex: 'status = Open'"),
    apply_default_filter: bool = Query(
        True,
        description='Si True (défaut), filtre "Test Type" = Manual.',
    ),
):
    """
    Liste légère (sans étapes) des tests d'un projet.
    Utile pour estimer le volume avant un extract complet.
    """
    result = list_project_legacy_tests(
        project_key=project_key,
        extra_jql=extra_jql,
        max_results=limit,
        apply_default_filter=apply_default_filter,
    )
    if result.get("error"):
        raise HTTPException(
            status_code=result.get("status_code", 500),
            detail=result.get("body") or "Erreur Jira inconnue",
        )
    return result


@router.get("/project/{project_key}/pivot")
def get_project_pivot(
    project_key: str,
    limit: int = Query(10, ge=1, le=200, description="Nb max de tests à extraire"),
    extra_jql: str = Query("", description="JQL supplémentaire"),
    apply_default_filter: bool = Query(
        True,
        description='Si True (défaut), filtre "Test Type" = Manual.',
    ),
):
    """
    Extrait `limit` tests d'un projet au format pivot.
    Recommandé : commencer avec limit=10 pour valider le format
    avant de lancer un run plus large.
    """
    return extract_legacy_tests_pivot(
        project_keys=[project_key],
        extra_jql=extra_jql,
        limit_per_project=limit,
        apply_default_filter=apply_default_filter,
    )


@router.post("/extract")
def extract_multi_projects(req: ExtractRequest):
    """
    Extraction multi-projets au format pivot.
    Si `projects` est vide, utilise la liste par défaut Sopra HR.
    ATTENTION : peut être long sur de grandes valeurs de `limit_per_project`.
    """
    projects = req.projects or DEFAULT_LEGACY_TEST_PROJECTS
    return extract_legacy_tests_pivot(
        project_keys=projects,
        extra_jql=req.extra_jql,
        limit_per_project=req.limit_per_project,
        apply_default_filter=req.apply_default_filter,
    )
