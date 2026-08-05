# app/api/routes_db.py
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from sqlalchemy import delete

from app.db.postgres import get_sync_session
from app.models.pg_models import (
    Story,
    StoryAnalysis,
    Agent4Validation,
    GeneratedScenario,
    StoryBusinessModel,
)

from app.repositories.story_repository import (
    get_story_by_id,
    get_all_stories,
)
from app.repositories.analysis_repository import (
    get_analyses_by_story,
    get_latest_analysis,
)
from app.repositories.scenario_repository import (
    get_scenarios_by_story,
    get_all_scenarios,
)
from app.repositories.manual_tests_repository import get_latest_manual_tests

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
        raise HTTPException(
            status_code=404, detail=f"Story {story_id} introuvable en base"
        )
    return story


@db_router.delete("/stories/{story_id}")
def delete_stored_story(story_id: str):
    """Supprime une story et toutes les données associées de la base."""
    session = get_sync_session()
    try:
        # Supprimer toutes les dépendances liées à la story_id
        session.execute(delete(StoryAnalysis).where(StoryAnalysis.story_id == story_id))
        session.execute(
            delete(Agent4Validation).where(Agent4Validation.story_id == story_id)
        )
        session.execute(
            delete(GeneratedScenario).where(GeneratedScenario.story_id == story_id)
        )
        session.execute(
            delete(StoryBusinessModel).where(StoryBusinessModel.story_id == story_id)
        )

        # Supprimer la story elle-même
        result = session.execute(delete(Story).where(Story.id == story_id))
        session.commit()

        if result.rowcount == 0:
            raise HTTPException(
                status_code=404, detail=f"Story {story_id} introuvable en base"
            )
        return {"status": "ok", "story_id": story_id}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


# ══════════════════════════════════════════════════════
#  ANALYSES
# ══════════════════════════════════════════════════════


@db_router.get("/stories/{story_id}/analyses")
def list_analyses(story_id: str):
    """Récupère toutes les analyses LLM pour une story."""
    return get_analyses_by_story(story_id)


@db_router.get("/stories/{story_id}/analysis/latest")
def latest_analysis(
    story_id: str, model: str = Query(None, description="qwen3 | llama4")
):
    """Récupère la dernière analyse pour une story (optionnel : par modèle)."""
    analysis = get_latest_analysis(story_id, model)
    if not analysis:
        raise HTTPException(
            status_code=404, detail=f"Aucune analyse trouvée pour {story_id}"
        )
    return analysis


# ══════════════════════════════════════════════════════
#  SCÉNARIOS
# ══════════════════════════════════════════════════════


@db_router.get("/stories/{story_id}/scenarios")
def list_scenarios(story_id: str):
    """Récupère les scénarios générés pour une story."""
    scenarios = get_scenarios_by_story(story_id)
    return {"story_id": story_id, "count": len(scenarios), "scenarios": scenarios}


@db_router.get("/stories/{story_id}/manual-tests")
def get_manual_tests(story_id: str):
    """Récupère les scénarios générés pour une story, utilisés comme source de tests manuels."""
    tests = get_latest_manual_tests(story_id)
    if not tests:
        raise HTTPException(
            status_code=404, detail=f'Aucun jeu de tests trouvé pour {story_id}'
        )
    return {"story_id": story_id, "tests": tests}


@db_router.get("/stories/{story_id}/validations")
def get_validations(story_id: str):
    """Récupère la validation enregistrée pour une story."""
    from app.repositories.validation_repository import fetch_validation_by_story_id

    val = fetch_validation_by_story_id(story_id)
    if not val:
        raise HTTPException(
            status_code=404, detail=f"Aucune validation trouvée pour {story_id}"
        )
    return val


@db_router.get("/scenarios")
def list_all_scenarios():
    """Liste tous les scénarios générés."""
    scenarios = get_all_scenarios()
    return {"count": len(scenarios), "scenarios": scenarios}
