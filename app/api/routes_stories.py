# app/api/routes_stories.py
from fastapi import APIRouter, HTTPException, Query, Body
from app.services.jira_service import (
    get_story_byID,
    find_stories_with_linked_tests,
    get_test_byID,
    enrich_dataset_with_test_details,
    get_stories_without_description,
)
from typing import Dict, Any, Optional
from app.utils.cleaning import (
    clean_story_dict,
    enrich_story_for_llm,
    flatten_issuelinks,
)

router = APIRouter(prefix="/projects", tags=["User_stories"])


# -------- Dataset : stories avec tests Xray liés --------
@router.get("/{project_key}/stories-with-tests")
def list_stories_with_linked_tests(
    project_key: str,
    min_tests: int = Query(1, ge=1, description="Nombre minimum de tests liés"),
    max_stories: int = Query(
        50, ge=1, le=500, description="Nombre maximum de stories à retourner"
    ),
    extra_jql: str = Query(
        "", description="Fragment JQL additionnel (ex: 'AND status = Done')"
    ),
):
    """
    Retourne les User Stories d'un projet qui ont au moins `min_tests` tests Xray liés
    (via issuelinks de type 'tests' / 'is tested by' ou cible de type Test).

    Utile pour constituer un dataset d'évaluation : comparer les tests générés par
    le pipeline aux tests humains existants.
    """
    result = find_stories_with_linked_tests(
        project_key=project_key,
        min_tests=min_tests,
        max_stories=max_stories,
        extra_jql=extra_jql,
    )
    if result.get("error"):
        raise HTTPException(
            status_code=result.get("status_code", 500),
            detail=result.get("body") or "Jira search failed",
        )
    return result


# -------- Détail d'un test Xray (étapes, résultat attendu, priorité) --------
@router.get("/tests/{test_key}")
def get_test_details(test_key: str):
    """
    Récupère le contenu détaillé d'un cas de test Xray (ex: YOUQA-17500).
    Retourne summary, description, priority, status, labels, et la liste des steps.
    """
    result = get_test_byID(test_key)
    if result.get("error"):
        raise HTTPException(
            status_code=result.get("status_code", 500),
            detail=result.get("body") or "Test fetch failed",
        )
    return result


# -------- Enrichir un dataset complet avec le contenu de chaque test --------
@router.post("/dataset/enrich")
def enrich_dataset(
    dataset: Dict[str, Any] = Body(
        ..., description="Sortie de /projects/{KEY}/stories-with-tests"
    ),
    max_tests_per_story: Optional[int] = Query(
        None, ge=1, description="Limiter le nb de tests par story (debug)"
    ),
):
    """
    Enrichit un dataset (sortie de /projects/{KEY}/stories-with-tests) en récupérant
    pour chaque test lié : summary, description, priority, status et les étapes Xray.

    Usage : récupérer d'abord la liste, puis poster le JSON ici pour avoir les détails.
    Le résultat peut être sauvegardé tel quel pour servir de dataset d'évaluation Agent 2.
    """
    if "stories" not in dataset:
        raise HTTPException(
            status_code=400, detail="Le JSON doit contenir un champ 'stories'."
        )
    return enrich_dataset_with_test_details(
        dataset, max_tests_per_story=max_tests_per_story
    )


# -------- User Stories sans description (renvoie uniquement les IDs) --------
@router.get("/{project_key}/stories-without-description")
def list_stories_without_description(
    project_key: str,
    extra_jql: str = Query(
        "", description="Fragment JQL additionnel (ex: 'AND status != Done')"
    ),
):
    """
    Retourne uniquement les IDs (clés Jira) des User Stories du projet qui n'ont
    pas de description (champ description vide).
    """
    ids = get_stories_without_description(project_key=project_key, extra_jql=extra_jql)
    return {"project": project_key, "count": len(ids), "ids": ids}


# -------- Route UNITÉ (récupérés les champs nécessaires pour une user story) --------
@router.get("/{issue_key}")
def get_story_raw_simplified(issue_key: str):
    """
    Retourne une version brute simplifiée d'une User Story,

    """
    result = get_story_byID(issue_key)

    if result["status"] != 200:
        raise HTTPException(result["status"], f"Story {issue_key} introuvable")

    data = result["data"]
    fields = data.get("fields", {}) or {}

    story = {
        "id": issue_key,
        "summary": fields.get("summary") or "",
        "description": fields.get("description") or "",
        "labels": fields.get("labels") or [],
        "components": [c.get("name") for c in (fields.get("components") or [])],
        "issuelinks": flatten_issuelinks(fields.get("issuelinks") or []),
        "priority": (fields.get("priority") or {}).get("name"),
        "status": (fields.get("status") or {}).get("name"),
        "fixVersions": [v.get("name") for v in (fields.get("fixVersions") or [])],
        "requirement_status": fields.get("customfield_14422"),
    }

    return story


@router.get("/{issue_key}/debug")
def debug_story(issue_key: str):
    """
    Retourne la story au format brut ET nettoyé.
    """
    result = get_story_byID(issue_key)

    if result["status"] == 404:
        raise HTTPException(status_code=404, detail=f"Story {issue_key} introuvable")
    if result["status"] != 200:
        raise HTTPException(
            status_code=result["status"], detail=result.get("error", "Erreur Jira")
        )

    fields = result["data"].get("fields", {}) or {}

    raw_story = {
        "id": issue_key,
        "summary": fields.get("summary", ""),
        "description": fields.get("description", ""),
        "labels": fields.get("labels", []) or [],
        "components": [c.get("name") for c in (fields.get("components") or [])],
        "issuelinks": flatten_issuelinks(fields.get("issuelinks") or []),
        "priority": (fields.get("priority") or {}).get("name"),
        "status": (fields.get("status") or {}).get("name"),
        "fixVersions": [v.get("name") for v in (fields.get("fixVersions") or [])],
        "requirement_status": fields.get("customfield_14422") or [],
    }

    cleaned_story = clean_story_dict(raw_story)

    return {
        "raw": raw_story,
        "cleaned": cleaned_story,
    }


# -------- Route COMPLÈTE (tous les champs Jira d'une seule user story) --------
@router.get("/{issue_key}/full")
def get_story_full(issue_key: str):
    """
    Retourne TOUS les champs Jira d'une User Story, sans filtrage.
    """
    result = get_story_byID(issue_key)

    if result["status"] == 404:
        raise HTTPException(404, f"Story {issue_key} introuvable")
    if result["status"] != 200:
        raise HTTPException(result["status"], result["error"])

    return result["data"]


# -------- Route NETTOYÉE (story après cleaning + enrichissement LLM) --------
@router.get("/{issue_key}/cleaned")
def get_cleaned_story(issue_key: str):
    """
    Retourne une User Story après nettoyage complet et enrichissement LLM :
    description_clean, description_llm, references, flags, story_context_llm, etc.
    """
    result = get_story_byID(issue_key)

    if result["status"] == 404:
        raise HTTPException(status_code=404, detail=f"Story {issue_key} introuvable")
    if result["status"] != 200:
        raise HTTPException(
            status_code=result["status"], detail=result.get("error", "Erreur Jira")
        )

    fields = result["data"].get("fields", {}) or {}

    raw_story = {
        "id": issue_key,
        "summary": fields.get("summary") or "",
        "description": fields.get("description") or "",
        "labels": fields.get("labels") or [],
        "components": [c.get("name") for c in (fields.get("components") or [])],
        "issuelinks": flatten_issuelinks(fields.get("issuelinks") or []),
        "priority": (fields.get("priority") or {}).get("name"),
        "status": (fields.get("status") or {}).get("name"),
        "fixVersions": [v.get("name") for v in (fields.get("fixVersions") or [])],
        "requirement_status": fields.get("customfield_14422") or [],
    }

    cleaned = clean_story_dict(raw_story)
    enriched = enrich_story_for_llm(cleaned)

    return enriched
