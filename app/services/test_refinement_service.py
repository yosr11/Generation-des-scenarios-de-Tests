"""Service IA pour affiner un cas de test via chat en langage naturel."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.prompts.test_refinement_prompt import (
    build_test_refinement_system_prompt,
    build_test_refinement_user_prompt,
)
from app.services.token_tracker import record_from_response
from app.utils.json_utils import extract_json_from_llm_response
from app.utils.test_steps_utils import finalize_edited_test

logger = logging.getLogger(__name__)


class TestRefinementService:
    def __init__(self, llm_client, model_name: str):
        self.llm_client = llm_client
        self.model_name = model_name

    def refine(
        self,
        test: Dict[str, Any],
        user_message: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        story_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        system_prompt = build_test_refinement_system_prompt()
        user_prompt = build_test_refinement_user_prompt(
            test=test,
            user_message=user_message,
            chat_history=chat_history or [],
            story_context=story_context,
        )

        response = self.llm_client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            response_format={"type": "json_object"},
            max_tokens=8192,
        )
        record_from_response(response, self.model_name)

        content = ""
        if hasattr(response, "choices") and response.choices:
            content = response.choices[0].message.content or ""
        elif isinstance(response, dict):
            content = response.get("output", {}).get("message", {}).get("content", "")

        data = extract_json_from_llm_response(content)
        updated_test = data.get("test") or test
        assistant_message = (data.get("assistant_message") or "").strip()
        if not assistant_message:
            assistant_message = "Test mis à jour selon votre instruction."

        updated_test = finalize_edited_test(updated_test)
        return {
            "test": updated_test,
            "assistant_message": assistant_message,
        }
