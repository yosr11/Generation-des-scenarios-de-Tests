# app/api/routes_stories.py
from fastapi import APIRouter, HTTPException
from app.services.jira_service import get_story_byID
from app.models.story import Story
from typing import List, Dict, Any
from app.utils.cleaning import clean_story_dict, enrich_story_for_llm

router = APIRouter(prefix="/projects", tags=["User_stories"])


def _flatten_issuelinks(raw_links: list) -> List[Dict[str, str]]:
    """Transforme les issuelinks Jira (très imbriqués) en liste plate."""
    out: List[Dict[str, str]] = []
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
        "issuelinks": _flatten_issuelinks(fields.get("issuelinks") or []),
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
        raise HTTPException(status_code=result["status"], detail=result.get("error", "Erreur Jira"))

    fields = result["data"].get("fields", {}) or {}

    raw_story = {
        "id": issue_key,
        "summary": fields.get("summary", ""),
        "description": fields.get("description", ""),
        "labels": fields.get("labels", []) or [],
        "components": [c.get("name") for c in (fields.get("components") or [])],
        "issuelinks": _flatten_issuelinks(fields.get("issuelinks") or []),
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
        raise HTTPException(status_code=result["status"], detail=result.get("error", "Erreur Jira"))

    fields = result["data"].get("fields", {}) or {}

    raw_story = {
        "id": issue_key,
        "summary": fields.get("summary") or "",
        "description": fields.get("description") or "",
        "labels": fields.get("labels") or [],
        "components": [c.get("name") for c in (fields.get("components") or [])],
        "issuelinks": _flatten_issuelinks(fields.get("issuelinks") or []),
        "priority": (fields.get("priority") or {}).get("name"),
        "status": (fields.get("status") or {}).get("name"),
        "fixVersions": [v.get("name") for v in (fields.get("fixVersions") or [])],
        "requirement_status": fields.get("customfield_14422") or [],
    }

    cleaned = clean_story_dict(raw_story)
    enriched = enrich_story_for_llm(cleaned)

    return enriched
