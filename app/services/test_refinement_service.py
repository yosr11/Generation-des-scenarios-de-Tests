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

# Nombre max de messages d'historique envoyés au modèle (les plus récents).
MAX_HISTORY_MESSAGES = 6
# Longueur max (caractères) tolérée pour le résumé de story injecté dans le prompt.
MAX_STORY_SUMMARY_CHARS = 1500
# Tokens de sortie autorisés : assez pour un test complet en JSON, sans exploser le TPM.
MAX_OUTPUT_TOKENS = 6000
# Nombre de tentatives si le modèle renvoie un JSON invalide/tronqué (erreur transitoire).
MAX_GENERATION_RETRIES = 2


class TestRefinementError(Exception):
    """Erreur métier lisible à remonter au frontend (ex: quota LLM dépassé)."""


class TestRefinementService:
    def __init__(self, llm_client, model_name: str):
        self.llm_client = llm_client
        self.model_name = model_name

    @staticmethod
    def _truncate_history(chat_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Ne garde que les derniers messages pour limiter la taille du prompt."""
        if len(chat_history) <= MAX_HISTORY_MESSAGES:
            return chat_history
        return chat_history[-MAX_HISTORY_MESSAGES:]

    @staticmethod
    def _truncate_story_context(story_context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not story_context:
            return story_context
        summary = story_context.get("summary") or ""
        if len(summary) > MAX_STORY_SUMMARY_CHARS:
            story_context = {
                **story_context,
                "summary": summary[:MAX_STORY_SUMMARY_CHARS] + " […]",
            }
        return story_context

    def _call_llm(self, system_prompt: str, user_prompt: str):
        status_code = None
        error_code = ""
        try:
            return self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
                response_format={"type": "json_object"},
                max_tokens=MAX_OUTPUT_TOKENS,
            )
        except Exception as exc:
            status_code = getattr(exc, "status_code", None)
            body = getattr(exc, "body", None) or {}
            if isinstance(body, dict):
                error_code = (body.get("error") or {}).get("code", "")

            if status_code == 413 or error_code == "rate_limit_exceeded":
                logger.warning("refine-chat: quota/taille LLM dépassé (%s)", exc)
                raise TestRefinementError(
                    "La conversation est devenue trop longue pour le modèle "
                    f"« {self.model_name} ». Démarrez une nouvelle conversation "
                    "de refinement pour ce test, ou réduisez le message envoyé."
                ) from exc

            # json_validate_failed (ou autre) : on laisse remonter tel quel,
            # c'est refine() qui décide de retenter ou d'abandonner.
            raise

    def refine(
        self,
        test: Dict[str, Any],
        user_message: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        story_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        chat_history = self._truncate_history(chat_history or [])
        story_context = self._truncate_story_context(story_context)

        system_prompt = build_test_refinement_system_prompt()
        user_prompt = build_test_refinement_user_prompt(
            test=test,
            user_message=user_message,
            chat_history=chat_history,
            story_context=story_context,
        )

        last_exc: Optional[Exception] = None
        response = None
        for attempt in range(1, MAX_GENERATION_RETRIES + 1):
            try:
                response = self._call_llm(system_prompt, user_prompt)
                last_exc = None
                break
            except TestRefinementError:
                raise
            except Exception as exc:
                body = getattr(exc, "body", None) or {}
                error_code = (body.get("error") or {}).get("code", "") if isinstance(body, dict) else ""
                if error_code == "json_validate_failed" and attempt < MAX_GENERATION_RETRIES:
                    logger.warning(
                        "refine-chat: JSON invalide généré par %s (tentative %d/%d), retry...",
                        self.model_name, attempt, MAX_GENERATION_RETRIES,
                    )
                    last_exc = exc
                    continue
                last_exc = exc
                break

        if response is None:
            logger.error("refine-chat: échec définitif de génération JSON (%s)", last_exc)
            raise TestRefinementError(
                "Le modèle n'a pas réussi à produire une réponse exploitable. "
                "Reformulez votre instruction ou réessayez."
            ) from last_exc

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