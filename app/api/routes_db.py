# app/api/routes_db.py
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any

from app.repositories.story_repository import (
    save_story, get_story_by_id, get_all_stories,
)
from app.repositories.analysis_repository import (
    get_analyses_by_story, get_latest_analysis,
)
from app.repositories.scenario_repository import (
    get_scenarios_by_story, get_all_scenarios,
)

db_router = APIRouter(prefix="/db", tags=["Database"])


# ══════════════════════════════════════════════════════
#  STORIES
# ══════════════════════════════════════════════════════

@db_router.get("/stories", response_model=List[Dict[str, Any]])
def list_stored_stories():
    """Liste toutes les stories stockées en base."""
    return get_all_stories()


@db_router.get("/stories/{story_id}")
def get_stored_story(story_id: str):
    """Récupère une story par son ID."""
    story = get_story_by_id(story_id)
    if not story:
        raise HTTPException(status_code=404, detail=f"Story {story_id} introuvable en base")
    return story


# ══════════════════════════════════════════════════════
#  ANALYSES
# ══════════════════════════════════════════════════════

@db_router.get("/stories/{story_id}/analyses")
def list_analyses(story_id: str):
    """Récupère toutes les analyses LLM pour une story."""
    analyses = get_analyses_by_story(story_id)
    return {"story_id": story_id, "count": len(analyses), "analyses": analyses}


@db_router.get("/stories/{story_id}/analysis/latest")
def latest_analysis(story_id: str, model: str = Query(None, description="qwen3 | llama4")):
    """Récupère la dernière analyse pour une story (optionnel : par modèle)."""
    analysis = get_latest_analysis(story_id, model)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Aucune analyse trouvée pour {story_id}")
    return analysis


# ══════════════════════════════════════════════════════
#  SCÉNARIOS
# ══════════════════════════════════════════════════════

@db_router.get("/stories/{story_id}/scenarios")
def list_scenarios(story_id: str):
    """Récupère les scénarios générés pour une story."""
    scenarios = get_scenarios_by_story(story_id)
    return {"story_id": story_id, "count": len(scenarios), "scenarios": scenarios}


@db_router.get("/scenarios")
def list_all_scenarios():
    """Liste tous les scénarios générés."""
    scenarios = get_all_scenarios()
    return {"count": len(scenarios), "scenarios": scenarios}
