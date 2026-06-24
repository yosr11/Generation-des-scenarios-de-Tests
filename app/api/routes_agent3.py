"""
Agent 3 — validateur pur (FastAPI).

Charge automatiquement depuis la base SQLite :
- testable_points (dernière analyse Agent 1) ;
- tests manuels (dernier résultat Agent 2 enregistré).

Aucune génération, aucun appel Agent 2 ici (sauf route /correct qui lance la boucle corrective).
Option : feedback qualitatif LLM (narratif) dans le rapport.
"""

import logging
from typing import List, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.agent3_validation import Agent3StoryDashboard, Agent3ValidationResult
from app.models.test_manual import ManualTestCase
from app.repositories.analysis_repository import get_latest_analysis
from app.repositories.manual_tests_repository import get_latest_manual_tests, save_manual_tests_snapshot
from app.repositories.story_repository import get_story_by_id
from app.repositories.validation_repository import save_validation_result
from app.services.agent3_test_validator_service import validate_and_improve_tests
from app.services.agent3_correction_loop import run_agent2_gap_fill

router = APIRouter(prefix="/agent3", tags=["Agent 3 — Test Validator"])
logger = logging.getLogger(__name__)


class Agent3ThresholdsBody(BaseModel):
    """Seuils + modèle d'embedding (les données Agent 1 / 2 viennent de la base)."""

    coverage_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    coverage_similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    duplicate_similarity_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    embedding_model: str = Field(default="paraphrase-multilingual-MiniLM-L12-v2")

    # Optionnel : feedback LLM (narratif)
    run_llm_quality_feedback: bool = Field(
        default=False,
        description="Si true : génère un feedback qualitatif via LLM (ne change pas la décision).",
    )
    quality_model_alias: str = Field(default="llama4", description="Alias modèle Groq pour feedback qualitatif.")

    # Optionnel : détection d'ambiguïtés sémantiques via LLM
    run_llm_ambiguity_detection: bool = Field(
        default=True,
        description="Si true : complète la détection regex par une analyse LLM des ambiguïtés.",
    )


class Agent3ValidateFromDbRequest(Agent3ThresholdsBody):
    """Validation pour une story identifiée dans le corps."""

    story_id: str = Field(..., min_length=1, description="Identifiant story (même id qu'en base)")


def _load_testable_points_and_tests(story_id: str) -> Tuple[List[str], List[ManualTestCase], str]:
    row = get_story_by_id(story_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Story introuvable : {story_id}")

    analysis = get_latest_analysis(story_id)
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail=f"Aucune analyse Agent 1 pour {story_id}. Lancez /analysis/{story_id}.",
        )

    points = list(analysis.get("testable_points") or [])

    raw_tests = get_latest_manual_tests(story_id)
    if not raw_tests:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Aucun test Agent 2 enregistré pour {story_id}. "
                f"Lancez d'abord la génération Agent 2, puis réessayez."
            ),
        )

    try:
        tests = [ManualTestCase(**t) for t in raw_tests]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Tests en base invalides (schéma ManualTestCase) : {e}",
        ) from e

    story_summary = ""
    try:
        story_summary = (dict(row).get("summary") or "") if row else ""
    except Exception:
        story_summary = (row.get("summary") or "") if isinstance(row, dict) else ""

    return points, tests, story_summary


@router.post(
    "/story/{story_id}/dashboard",
    response_model=Agent3StoryDashboard,
    summary="Tableau de bord validation (données Agent 1 + 2 depuis la base)",
)
def post_agent3_story_dashboard(story_id: str, body: Agent3ThresholdsBody):
    points, tests, story_summary = _load_testable_points_and_tests(story_id)

    result = validate_and_improve_tests(
        story_id=story_id,
        testable_points=points,
        tests=tests,
        story_summary=story_summary,
        coverage_threshold=body.coverage_threshold,
        coverage_similarity_threshold=body.coverage_similarity_threshold,
        duplicate_similarity_threshold=body.duplicate_similarity_threshold,
        embedding_model=body.embedding_model,
        run_llm_quality_feedback=body.run_llm_quality_feedback,
        quality_model_alias=body.quality_model_alias,
        run_llm_ambiguity_detection=body.run_llm_ambiguity_detection,
    )
    
    # Save validation result to database
    save_validation_result(story_id, result)

    r = result.report
    return Agent3StoryDashboard(
        story_id=story_id,
        coverage_rate=r.coverage_rate,
        uncovered_testable_points=r.uncovered_testable_points,
        duplicate_pairs=r.duplicate_pairs,
        ambiguity_findings=r.ambiguity_findings,
        validation_status=r.validation_status,
        correction_instructions=r.correction_instructions,
        llm_quality_feedback=r.llm_quality_feedback,
        llm_quality_model_alias=r.llm_quality_model_alias,
    )


@router.post(
    "/validate-and-improve",
    response_model=Agent3ValidationResult,
    summary="Valider les tests (Agent 3) — story_id dans le corps",
    response_description="Tests lus depuis la base + rapport de validation",
)
def post_validate_and_improve(body: Agent3ValidateFromDbRequest):
    points, tests, story_summary = _load_testable_points_and_tests(body.story_id)

    result = validate_and_improve_tests(
        story_id=body.story_id,
        testable_points=points,
        tests=tests,
        story_summary=story_summary,
        coverage_threshold=body.coverage_threshold,
        coverage_similarity_threshold=body.coverage_similarity_threshold,
        duplicate_similarity_threshold=body.duplicate_similarity_threshold,
        embedding_model=body.embedding_model,
        run_llm_quality_feedback=body.run_llm_quality_feedback,
        quality_model_alias=body.quality_model_alias,
        run_llm_ambiguity_detection=body.run_llm_ambiguity_detection,
    )
    
    # Save validation result to database
    save_validation_result(body.story_id, result)
    
    return result


@router.post(
    "/validate-and-improve/by-story/{story_id}",
    response_model=Agent3ValidationResult,
    summary="Valider les tests (Agent 3) — story_id dans l'URL",
)
def post_validate_and_improve_by_story(story_id: str, body: Agent3ThresholdsBody):
    points, tests, story_summary = _load_testable_points_and_tests(story_id)

    result = validate_and_improve_tests(
        story_id=story_id,
        testable_points=points,
        tests=tests,
        story_summary=story_summary,
        coverage_threshold=body.coverage_threshold,
        coverage_similarity_threshold=body.coverage_similarity_threshold,
        duplicate_similarity_threshold=body.duplicate_similarity_threshold,
        embedding_model=body.embedding_model,
        run_llm_quality_feedback=body.run_llm_quality_feedback,
        quality_model_alias=body.quality_model_alias,
        run_llm_ambiguity_detection=body.run_llm_ambiguity_detection,
    )
    
    # Save validation result to database
    save_validation_result(story_id, result)
    
    return result


# ── CORRECTION LOOP ──────────────────────────────────────────


class Agent3CorrectBody(Agent3ThresholdsBody):
    """Paramètres pour la boucle corrective (validation + gap-fill Agent 2)."""

    max_iterations: int = Field(default=2, ge=1, le=5, description="Nombre max de tentatives de correction")
    gap_fill_model_alias: str = Field(default="llama4", description="Modèle LLM pour la génération gap-fill Agent 2")


@router.post(
    "/correct/{story_id}",
    response_model=Agent3ValidationResult,
    summary="Validation + boucle corrective (rappel Agent 2 si couverture insuffisante)",
)
def post_validate_and_correct(story_id: str, body: Agent3CorrectBody):
    """
    1. Valide les tests existants (comme validate-and-improve)
    2. Si couverture < seuil : appelle Agent 2 pour générer des tests sur les points manquants
    3. Fusionne les nouveaux tests avec les existants, re-valide
    4. Répète jusqu'à couverture OK ou max_iterations atteint
    """
    story = get_story_by_id(story_id)
    if not story:
        raise HTTPException(status_code=404, detail=f"Story introuvable : {story_id}")

    analysis = get_latest_analysis(story_id)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Aucune analyse Agent 1 pour {story_id}")

    points = list(analysis.get("testable_points") or [])

    raw_tests = get_latest_manual_tests(story_id)
    if not raw_tests:
        raise HTTPException(status_code=404, detail=f"Aucun test Agent 2 pour {story_id}")

    try:
        tests = [ManualTestCase(**t) for t in raw_tests]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tests invalides : {e}") from e

    story_summary = (story.get("summary") or "") if isinstance(story, dict) else ""
    best_result = None

    for iteration in range(1, body.max_iterations + 1):
        logger.info(f"[Agent3-Correct] Iteration {iteration}/{body.max_iterations} for {story_id}")

        # Validate current tests
        result = validate_and_improve_tests(
            story_id=story_id,
            testable_points=points,
            tests=tests,
            story_summary=story_summary,
            coverage_threshold=body.coverage_threshold,
            coverage_similarity_threshold=body.coverage_similarity_threshold,
            duplicate_similarity_threshold=body.duplicate_similarity_threshold,
            embedding_model=body.embedding_model,
            run_llm_quality_feedback=body.run_llm_quality_feedback,
            quality_model_alias=body.quality_model_alias,
            run_llm_ambiguity_detection=body.run_llm_ambiguity_detection,
        )

        # Keep best result (highest coverage)
        if best_result is None or result.report.coverage_rate > best_result.report.coverage_rate:
            best_result = result

        # Check if coverage is sufficient
        if result.report.coverage_rate >= body.coverage_threshold:
            logger.info(
                f"[Agent3-Correct] Coverage OK ({result.report.coverage_rate:.1%}) at iteration {iteration}"
            )
            break

        uncovered = result.report.uncovered_testable_points
        if not uncovered:
            break

        # Call Agent 2 gap-fill
        logger.info(
            f"[Agent3-Correct] Coverage {result.report.coverage_rate:.1%} < {body.coverage_threshold:.1%}, "
            f"calling Agent 2 for {len(uncovered)} uncovered points"
        )
        try:
            gap_result = run_agent2_gap_fill(
                story=story,
                analysis=analysis,
                missing_testable_points=uncovered,
                current_tests=tests,
                rag_context=None,
                model_alias=body.gap_fill_model_alias,
            )

            if gap_result.tests:
                tests = tests + gap_result.tests
                logger.info(f"[Agent3-Correct] +{len(gap_result.tests)} tests from gap-fill")
            else:
                logger.warning("[Agent3-Correct] Gap-fill returned 0 tests, stopping")
                break

        except Exception as e:
            logger.error(f"[Agent3-Correct] Gap-fill failed: {e}")
            break

    # Persist the best test set and validation
    final_tests_dicts = [t.model_dump() for t in best_result.tests]
    save_manual_tests_snapshot(story_id, final_tests_dicts, generation_model=body.gap_fill_model_alias)
    save_validation_result(story_id, best_result)

    return best_result