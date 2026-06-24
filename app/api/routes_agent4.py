"""
Routes FastAPI pour l'Agent 4 — Classifieur d'automatisation.

- GET  /agent4/{story_id}                  → lit le dernier snapshot persisté
- POST /agent4/{story_id}/classify         → relance la classification sur les tests existants
- POST /agent4/{story_id}/feedback         → met à jour le retour du PO sur un test
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.automation_classification import (
    AutomationDecision,
    ConfidenceLevel,
    PoFeedback,
    StoryAutomationClassificationResult,
    TestAutomationClassification,
)
from app.repositories.automation_classifier_repository import (
    get_classifications,
    save_classifications,
    update_po_feedback,
)
from app.repositories.manual_tests_repository import get_latest_manual_tests
from app.services.agent4_automation_classifier_service import classify_tests_for_story

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent4", tags=["Agent 4 — Automation Classifier"])


class ClassificationItem(BaseModel):
    test_name: str
    classification: AutomationDecision
    confidence: ConfidenceLevel
    raison: str = ""
    po_feedback: PoFeedback = PoFeedback.PENDING
    error: Optional[str] = None


class ClassificationResponse(BaseModel):
    story_id: str
    model: str = ""
    total: int
    to_automate: int
    to_manual: int
    classifications: List[ClassificationItem] = Field(default_factory=list)


class ClassifyRequest(BaseModel):
    model: str = Field(default="qwen3", description="Alias LLM (qwen3 recommandé)")


class FeedbackRequest(BaseModel):
    test_name: str
    feedback: PoFeedback


def _to_response(result: StoryAutomationClassificationResult) -> ClassificationResponse:
    return ClassificationResponse(
        story_id=result.story_id,
        model=result.model,
        total=result.total,
        to_automate=result.to_automate,
        to_manual=result.to_manual,
        classifications=[
            ClassificationItem(
                test_name=c.test_name,
                classification=c.classification,
                confidence=c.confidence,
                raison=c.raison,
                po_feedback=c.po_feedback,
                error=c.error,
            )
            for c in result.classifications
        ],
    )


@router.get("/{story_id}", response_model=ClassificationResponse)
def get_story_classifications(story_id: str):
    """Renvoie le dernier snapshot persisté de classifications pour la story."""
    result = get_classifications(story_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Aucune classification trouvée pour {story_id}. Lancez d'abord le pipeline ou POST /agent4/{story_id}/classify.",
        )
    return _to_response(result)


@router.post("/{story_id}/classify", response_model=ClassificationResponse)
def classify_story_tests(story_id: str, body: ClassifyRequest = None):
    """Relance la classification sur les tests actuellement en base pour la story."""
    params = body or ClassifyRequest()
    tests = get_latest_manual_tests(story_id)
    if not tests:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun test trouvé en base pour {story_id}. Lancez d'abord Agent 2 ou le pipeline.",
        )
    try:
        result = classify_tests_for_story(story_id, tests, model_alias=params.model)
        save_classifications(result)
        return _to_response(result)
    except Exception as e:
        logger.error(f"[Agent4 route] classify failed for {story_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Classification error: {e}")


@router.post("/{story_id}/feedback", response_model=ClassificationResponse)
def submit_po_feedback(story_id: str, body: FeedbackRequest):
    """Le PO valide ou rejette la suggestion de l'agent pour un test donné."""
    updated = update_po_feedback(story_id, body.test_name, body.feedback)
    if not updated:
        raise HTTPException(
            status_code=404,
            detail=f"Aucune classification trouvée pour test '{body.test_name}' (story {story_id}).",
        )
    result = get_classifications(story_id)
    return _to_response(result)
