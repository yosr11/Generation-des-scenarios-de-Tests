"""API pour l'édition et le refinement IA des tests manuels."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.repositories.manual_tests_repository import save_manual_tests_snapshot
from app.services.llm_client import ALL_MODELS, build_llm_client
from app.services.test_refinement_service import TestRefinementService
from app.utils.test_steps_utils import finalize_edited_test

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/manual-tests", tags=["Manual Test Editing"])


class ChatMessage(BaseModel):
    role: str
    content: str


class RefineChatRequest(BaseModel):
    test: Dict[str, Any]
    message: str = Field(..., min_length=1)
    chat_history: List[ChatMessage] = Field(default_factory=list)
    story_id: str = ""
    story_summary: str = ""
    story_actors: List[str] = Field(default_factory=list)
    model_alias: str = "llama4"


class RefineChatResponse(BaseModel):
    test: Dict[str, Any]
    assistant_message: str


class SaveEditedTestsRequest(BaseModel):
    tests: List[Dict[str, Any]]
    generation_model: str = "manual-edit"


@router.post("/refine-chat", response_model=RefineChatResponse)
def refine_test_chat(body: RefineChatRequest) -> RefineChatResponse:
    """Affiner un cas de test via instruction en langage naturel."""
    if body.model_alias not in ALL_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Modèle inconnu : {body.model_alias}. Valeurs : {list(ALL_MODELS.keys())}",
        )
    try:
        llm_client, model_name = build_llm_client(body.model_alias)
        service = TestRefinementService(llm_client=llm_client, model_name=model_name)
        story_context = {
            "story_id": body.story_id,
            "summary": body.story_summary,
            "actors": body.story_actors,
        }
        history = [{"role": m.role, "content": m.content} for m in body.chat_history]
        result = service.refine(
            test=body.test,
            user_message=body.message,
            chat_history=history,
            story_context=story_context,
        )
        return RefineChatResponse(**result)
    except Exception as exc:
        logger.exception("refine-chat failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/save-edited/{story_id}")
def save_edited_tests(story_id: str, body: SaveEditedTestsRequest) -> Dict[str, Any]:
    """Persiste les tests édités manuellement ou via l'assistant IA."""
    if not body.tests:
        raise HTTPException(status_code=400, detail="Aucun test à enregistrer.")
    finalized = [finalize_edited_test(t) for t in body.tests]
    row_id = save_manual_tests_snapshot(
        story_id,
        finalized,
        generation_model=body.generation_model,
    )
    return {"status": "ok", "story_id": story_id, "tests_count": len(finalized), "snapshot_id": row_id}
