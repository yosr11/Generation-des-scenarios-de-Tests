# app/api/routes_epic.py
from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.deps import CurrentUser, require_admin
from app.services.epic_service import (
    get_epics,
    get_stories_by_epic,
    count_stories_by_epic,
    count_epics,
    get_stories_by_epic_detailed,
    _session,
    JIRA_BASE_URL,
)
from app.utils.cleaning import clean_story_dict, enrich_story_for_llm
from app.repositories.story_repository import save_stories_bulk
from typing import List, Dict, Any
import requests

router = APIRouter(prefix="/epics", tags=["Epics"])


# -------- DEBUG : voir la réponse brute Jira --------
@router.get("/debug")
def debug_epics(
    project_key: str = Query(..., description="Clé du projet Jira (ex: YOUQA)"),
    _admin: CurrentUser = Depends(require_admin),
):
    """
    Retourne la réponse brute de Jira pour diagnostiquer les problèmes.
    """
    url = f"{JIRA_BASE_URL}/rest/api/2/search"
    jql = f'project = "{project_key}" AND issuetype = Epic ORDER BY created DESC'
    params = {"jql": jql, "maxResults": 5, "fields": "summary,status,issuetype"}

    try:
        resp = _session.get(url, params=params, timeout=60)
    except requests.RequestException as e:
        return {"error": "network", "detail": str(e)}

    return {
        "status_code": resp.status_code,
        "url_called": resp.url,
        "jql": jql,
        "body": (
            resp.json()
            if resp.headers.get("content-type", "").startswith("application/json")
            else resp.text[:1000]
        ),
    }


# -------- Nombre d'Epics d'un projet --------
@router.get("/count")
def epic_count(
    project_key: str = Query(..., description="Clé du projet Jira (ex: YOUQA)")
):
    """
    Retourne le nombre total d'Epics dans un projet Jira.
    """
    return count_epics(project_key)


# -------- Liste des Epics d'un projet (avec nb de stories) --------
@router.get("/", response_model=List[Dict[str, Any]])
def list_epics(
    project_key: str = Query(..., description="Clé du projet Jira (ex: YOUQA)")
):
    """
    Récupère tous les Epics d'un projet Jira,
    avec pour chacun le nombre de User Stories liées.
    """
    epics = get_epics(project_key)
    if epics is None:
        raise HTTPException(
            status_code=502, detail="Erreur lors de la communication avec Jira"
        )

    for epic in epics:
        epic["story_count"] = count_stories_by_epic(epic["id"])

    return epics


# -------- Stories liées à un Epic --------
@router.get("/{epic_key}/stories", response_model=List[Dict[str, Any]])
def list_stories_by_epic(epic_key: str):
    """
    Récupère toutes les User Stories liées à un Epic.
    """
    stories = get_stories_by_epic(epic_key)
    if stories is None:
        raise HTTPException(
            status_code=502, detail="Erreur lors de la communication avec Jira"
        )
    return stories


# -------- Stories nettoyées + enrichies pour un Epic --------
@router.get("/{epic_key}/stories/cleaned", response_model=List[Dict[str, Any]])
def list_cleaned_stories_by_epic(epic_key: str):
    """
    Récupère les stories d'un Epic, puis applique pour chacune :
      1. Extraction des champs utiles (description, labels, components…)
      2. Nettoyage via clean_story_dict
      3. Enrichissement LLM via enrich_story_for_llm
    Retourne uniquement les champs nettoyés + enrichis.
    """
    raw_stories = get_stories_by_epic_detailed(epic_key)

    if raw_stories is None:
        raise HTTPException(
            status_code=502, detail="Erreur lors de la communication avec Jira"
        )
    if not raw_stories:
        raise HTTPException(
            status_code=404, detail=f"Aucune story trouvée pour l'epic {epic_key}"
        )

    processed = []
    for raw in raw_stories:
        cleaned = clean_story_dict(raw)
        enriched = enrich_story_for_llm(cleaned)
        processed.append(
            {
                "id": enriched.get("id", ""),
                "title": enriched.get("title", ""),
                "summary": enriched.get("summary", ""),
                "description_clean": enriched.get("description_clean", ""),
                "acceptance_criteria_clean": enriched.get(
                    "acceptance_criteria_clean", ""
                ),
                "labels": enriched.get("labels", []),
                "components": enriched.get("components", []),
                "priority": enriched.get("priority", ""),
                "status": enriched.get("status", ""),
                "issuelinks": enriched.get("issuelinks", []),
                "linked_keys_clean": enriched.get("linked_keys_clean", []),
                "linked_summaries_clean": enriched.get("linked_summaries_clean", []),
            }
        )

    # Sauvegarde en SQLite
    save_stories_bulk(processed)

    return processed
