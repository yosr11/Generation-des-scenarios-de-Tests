"""
app/services/business_modeling_service.py
──────────────────────────────────────────
Service Agent 1.5 — QA Business Modeling.

Transforme l'output structuré d'Agent 1 (acteurs, actions, règles, user_flows)
en business_goals et business_workflows exploitables par Agent 2.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

from pydantic import ValidationError

from app.models.business_model import BusinessModelingResult
from app.prompts.business_modeling_prompt import (
    build_business_modeling_system_prompt,
    build_business_modeling_user_prompt_from_dict,
)
from app.services.llm_client import call_llm, BEDROCK_MODELS

logger = logging.getLogger(__name__)


class BusinessModelingError(Exception):
    pass


# ─── Extraction JSON robuste ────────────────────────────────────────────────


def _extract_json(text: str) -> Dict[str, Any]:
    """Extrait le premier objet JSON d'une réponse LLM brute."""
    text = text.strip()
    # Supprimer les blocs <think>...</think>
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    # Supprimer les fences markdown
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise BusinessModelingError(
            f"Aucun objet JSON trouvé dans la réponse LLM. Début : {text[:300]}"
        )
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise BusinessModelingError(
            f"JSON invalide retourné par le LLM : {exc}"
        ) from exc


# ─── Résultat vide sécurisé ─────────────────────────────────────────────────


def _empty_result(story_id: str, note: str = "") -> BusinessModelingResult:
    return BusinessModelingResult(
        story_id=story_id,
        business_goals=[],
        business_workflows=[],
        modeling_notes=note,
    )


# ─── Service principal ───────────────────────────────────────────────────────


def build_business_model(
    analysis: Dict[str, Any],
    model_alias: str = "nova-lite-2",
    max_retries: int = 2,
) -> BusinessModelingResult:
    """
    Appelle l'Agent 1.5 pour modéliser les business goals et workflows d'une story.

    Args:
        analysis   : analysis_dict produit par Agent 1 (résultat de model_dump()).
        model_alias: alias LLM Groq à utiliser.
        max_retries: nombre maximum de tentatives en cas d'erreur LLM.

    Returns:
        BusinessModelingResult validé par Pydantic.
    """
    story_id = analysis.get("story_id", "")
    story_type = (analysis.get("story_type") or "").lower()

    # Court-circuit pour stories non fonctionnelles
    if story_type != "functional":
        logger.info(
            f"[Agent 1.5] Story {story_id} type='{story_type}' → non fonctionnelle, modélisation ignorée"
        )
        return _empty_result(
            story_id,
            note=f"Story de type '{story_type}' — modélisation métier ignorée.",
        )

    # Court-circuit si pas d'actions (rien à modéliser)
    actions = analysis.get("actions") or []
    if not actions:
        logger.info(
            f"[Agent 1.5] Story {story_id} — aucune action extraite, modélisation vide"
        )
        return _empty_result(story_id, note="Aucune action extraite par Agent 1.")

    system_prompt = build_business_modeling_system_prompt()
    user_prompt = build_business_modeling_user_prompt_from_dict(analysis)

    last_error: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                f"[Agent 1.5] Modélisation de {story_id} (modèle={model_alias}, tentative={attempt})"
            )
            raw = call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model_alias=model_alias,
                provider="bedrock" if model_alias in BEDROCK_MODELS else "groq",
                temperature=0.0,
                max_tokens=2500,
            )
            data = _extract_json(raw)

            # Garantir story_id
            if not data.get("story_id"):
                data["story_id"] = story_id

            result = BusinessModelingResult(**data)

            logger.info(
                f"[Agent 1.5] {story_id} → {len(result.business_goals)} goals, "
                f"{len(result.business_workflows)} workflows"
            )
            return result

        except (BusinessModelingError, ValidationError, Exception) as exc:
            last_error = exc
            logger.warning(
                f"[Agent 1.5] Tentative {attempt}/{max_retries} échouée pour {story_id}: {exc}"
            )

    # Toutes les tentatives ont échoué — retourner un résultat vide (non bloquant)
    logger.error(
        f"[Agent 1.5] Impossible de modéliser {story_id} après {max_retries} tentatives : {last_error}"
    )
    return _empty_result(
        story_id,
        note=f"Modélisation échouée après {max_retries} tentatives : {last_error}",
    )
