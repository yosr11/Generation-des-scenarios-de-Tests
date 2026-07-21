"""
app/api/routes_agent15.py
──────────────────────────
Endpoints REST pour Agent 1.5 — QA Business Modeling.

Endpoints :
  GET  /agent15/{story_id}          — Lancer la modélisation (depuis l'analyse existante en DB)
  POST /agent15/{story_id}/run      — Forcer une nouvelle modélisation (ignore le cache)
  GET  /agent15/{story_id}/latest   — Lire le dernier business model en base
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from app.repositories.analysis_repository import get_latest_analysis
from app.repositories.business_model_repository import (
    get_latest_business_model,
    list_business_models,
    save_business_model,
)
from app.repositories.story_repository import get_story_by_id
from app.services.business_modeling_service import build_business_model
from app.services.llm_client import GROQ_MODELS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent15", tags=["Agent 1.5 — Business Modeling"])


# ─── GET /agent15/{story_id} ────────────────────────────────────────────────


@router.get("/{story_id}")
def run_business_modeling(
    story_id: str,
    model_alias: str = Query(
        "llama4", description=f"Modèle LLM. Valeurs : {list(GROQ_MODELS.keys())}"
    ),
    force: bool = Query(
        False, description="Forcer la modélisation même si un résultat existe en base"
    ),
) -> Dict[str, Any]:
    """
    Lance Agent 1.5 pour une story déjà analysée par Agent 1.

    Pré-requis : l'analyse Agent 1 doit exister en base (appeler /analysis/{story_id} d'abord).

    - Si `force=False` (défaut) et qu'un business model existe déjà → retourne le résultat en cache.
    - Si `force=True` → relance la modélisation même si un résultat existe.
    """
    if model_alias not in GROQ_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Modèle inconnu '{model_alias}'. Valeurs autorisées : {list(GROQ_MODELS.keys())}",
        )

    # Vérifier cache (si force=False)
    if not force:
        cached = get_latest_business_model(story_id, model=model_alias)
        if cached:
            logger.info(
                f"[Agent 1.5 API] Cache hit pour {story_id} (modèle={model_alias})"
            )
            return _build_response(story_id, cached)

    # Charger l'analyse Agent 1 depuis la base
    analysis = get_latest_analysis(story_id)
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Aucune analyse Agent 1 trouvée pour '{story_id}'. "
                f"Lancez d'abord GET /analysis/{story_id} pour analyser la story."
            ),
        )

    story_type = (analysis.get("story_type") or "").lower()
    if story_type != "functional":
        raise HTTPException(
            status_code=422,
            detail=(
                f"La story '{story_id}' est de type '{story_type}'. "
                "Agent 1.5 ne traite que les stories fonctionnelles."
            ),
        )

    # Lancer la modélisation
    logger.info(
        f"[Agent 1.5 API] Modélisation de {story_id} (modèle={model_alias}, force={force})"
    )
    result = build_business_model(analysis=analysis, model_alias=model_alias)

    # Persister
    result_dict = result.model_dump()
    result_dict["model"] = model_alias
    save_business_model(result_dict)

    return _build_response(story_id, result_dict, analysis=analysis)


# ─── GET /agent15/{story_id}/latest ─────────────────────────────────────────


@router.get("/{story_id}/latest")
def get_latest(
    story_id: str,
    model_alias: Optional[str] = Query(None, description="Filtrer par modèle LLM"),
) -> Dict[str, Any]:
    """Retourne le dernier business model en base pour une story, sans relancer l'agent."""
    cached = get_latest_business_model(story_id, model=model_alias)
    if not cached:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun business model trouvé pour '{story_id}'. Lancez d'abord GET /agent15/{story_id}.",
        )
    return _build_response(story_id, cached)


# ─── GET /agent15/{story_id}/history ─────────────────────────────────────────


@router.get("/{story_id}/history")
def get_history(story_id: str) -> Dict[str, Any]:
    """Retourne l'historique complet des business models générés pour une story."""
    history = list_business_models(story_id)
    return {
        "story_id": story_id,
        "count": len(history),
        "history": history,
    }


# ─── Helper ──────────────────────────────────────────────────────────────────


def _build_response(
    story_id: str,
    bm_dict: Dict[str, Any],
    analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Construit la réponse API enrichie avec des métadonnées."""
    story = get_story_by_id(story_id)

    goals = bm_dict.get("business_goals") or []
    workflows = bm_dict.get("business_workflows") or []

    return {
        "story_id": story_id,
        "story_summary": (story or {}).get("summary", ""),
        "model": bm_dict.get("model", ""),
        "stats": {
            "business_goals_count": len(goals),
            "business_workflows_count": len(workflows),
        },
        "business_model": {
            "business_goals": goals,
            "business_workflows": workflows,
            "modeling_notes": bm_dict.get("modeling_notes", ""),
        },
        "source_analysis": (
            {
                "story_type": (analysis or {}).get("story_type", ""),
                "actors_count": len((analysis or {}).get("actors") or []),
                "actions_count": len((analysis or {}).get("actions") or []),
                "user_flows_count": len((analysis or {}).get("user_flows") or []),
            }
            if analysis
            else None
        ),
        "created_at": bm_dict.get("created_at", ""),
    }
