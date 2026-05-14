"""
Agent 3 — validateur pur (FastAPI).

Charge automatiquement depuis la base SQLite :
- les testable_points (dernière analyse Agent 1) ;
- les tests manuels (dernier résultat Agent 2 enregistré après POST /manual-tests/generate/...).

Le corps des requêtes ne contient que les seuils (optionnels). Aucune génération ni Agent 2 ici.
"""

from typing import List, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.agent3_validation import Agent3StoryDashboard, Agent3ValidationResult
from app.models.test_manual import ManualTestCase
from app.repositories.analysis_repository import get_latest_analysis
from app.repositories.manual_tests_repository import get_latest_manual_tests
from app.repositories.story_repository import get_story_by_id
from app.services.agent3_story_dashboard_service import build_story_dashboard
from app.services.agent3_test_validator_service import validate_and_improve_tests

router = APIRouter(prefix="/agent3", tags=["Agent 3 — Test Validator"])


class Agent3ThresholdsBody(BaseModel):
    """Seuils et modèle d’embedding uniquement (les données Agent 1 / 2 viennent de la base)."""

    coverage_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    coverage_similarity_threshold: float = Field(default=0.52, ge=0.0, le=1.0)
    duplicate_similarity_threshold: float = Field(default=0.88, ge=0.0, le=1.0)
    embedding_model: str = Field(default="paraphrase-multilingual-MiniLM-L12-v2")


class Agent3ValidateFromDbRequest(Agent3ThresholdsBody):
    """Validation pour une story identifiée dans le corps (sans renvoyer les tests dans la requête)."""

    story_id: str = Field(..., min_length=1, description="Identifiant story (même id qu’en base)")


def _load_testable_points_and_tests(story_id: str) -> Tuple[List[str], List[ManualTestCase]]:
    if not get_story_by_id(story_id):
        raise HTTPException(status_code=404, detail=f"Story introuvable : {story_id}")
    analysis = get_latest_analysis(story_id)
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail=f"Aucune analyse Agent 1 pour {story_id}. Lancez /analysis/{story_id}.",
        )
    points = list(analysis.get("testable_points") or [])
    raw = get_latest_manual_tests(story_id)
    if not raw:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Aucun test Agent 2 enregistré pour {story_id}. "
                f"Lancez d’abord POST /manual-tests/generate/{story_id} (après l’analyse), puis réessayez."
            ),
        )
    try:
        tests = [ManualTestCase(**t) for t in raw]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Tests en base invalides (schéma ManualTestCase) : {e}",
        ) from e
    return points, tests


@router.post(
    "/story/{story_id}/dashboard",
    response_model=Agent3StoryDashboard,
    summary="Tableau de bord validation (données Agent 1 + 2 depuis la base)",
)
def post_agent3_story_dashboard(story_id: str, body: Agent3ThresholdsBody):
    points, tests = _load_testable_points_and_tests(story_id)
    return build_story_dashboard(
        story_id,
        points,
        tests,
        coverage_threshold=body.coverage_threshold,
        coverage_similarity_threshold=body.coverage_similarity_threshold,
        duplicate_similarity_threshold=body.duplicate_similarity_threshold,
        embedding_model=body.embedding_model,
    )


@router.post(
    "/validate-and-improve",
    response_model=Agent3ValidationResult,
    summary="Valider les tests (Agent 3) — story_id dans le corps",
    response_description="Tests lus depuis la base + rapport de validation",
)
def post_validate_and_improve(body: Agent3ValidateFromDbRequest):
    points, tests = _load_testable_points_and_tests(body.story_id)
    return validate_and_improve_tests(
        body.story_id,
        points,
        tests,
        coverage_threshold=body.coverage_threshold,
        coverage_similarity_threshold=body.coverage_similarity_threshold,
        duplicate_similarity_threshold=body.duplicate_similarity_threshold,
        embedding_model=body.embedding_model,
    )


@router.post(
    "/validate-and-improve/by-story/{story_id}",
    response_model=Agent3ValidationResult,
    summary="Valider les tests (Agent 3) — story_id dans l’URL",
)
def post_validate_and_improve_by_story(story_id: str, body: Agent3ThresholdsBody):
    points, tests = _load_testable_points_and_tests(story_id)
    return validate_and_improve_tests(
        story_id,
        points,
        tests,
        coverage_threshold=body.coverage_threshold,
        coverage_similarity_threshold=body.coverage_similarity_threshold,
        duplicate_similarity_threshold=body.duplicate_similarity_threshold,
        embedding_model=body.embedding_model,
    )
