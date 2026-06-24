"""
Agent 4 — Classifieur d'automatisation.

Pour chaque test manuel généré, demande à un LLM (qwen3) de suggérer
s'il doit être AUTOMATISÉ ou MANUEL, avec un niveau de confiance et une
courte justification.

La décision est uniquement une SUGGESTION : le PO peut valider/rejeter ensuite
(champ `po_feedback`).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

from app.models.automation_classification import (
    AutomationDecision,
    ConfidenceLevel,
    StoryAutomationClassificationResult,
    TestAutomationClassification,
)
from app.prompts.automation_classifier_prompt import (
    build_automation_classifier_system_prompt,
    build_automation_classifier_user_prompt,
)
from app.services.llm_client import call_groq

logger = logging.getLogger(__name__)


_DEFAULT_MODEL = "llama4"


def _extract_json(raw: str) -> Dict[str, Any]:
    """Extrait un objet JSON depuis la sortie LLM (gère les blocs ```json et le bruit)."""
    if not raw:
        return {}
    text = raw.strip()
    # Strip <think>...</think> au cas où
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    # Retirer les fences markdown
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}
    return {}


def _normalize_decision(value: Any) -> AutomationDecision:
    if isinstance(value, str):
        v = value.strip().upper()
        if v.startswith("AUTO"):
            return AutomationDecision.AUTOMATISER
        if v.startswith("MAN"):
            return AutomationDecision.MANUEL
    return AutomationDecision.MANUEL


def _normalize_confidence(value: Any) -> ConfidenceLevel:
    if isinstance(value, str):
        v = value.strip().upper()
        if v.startswith("HAUT"):
            return ConfidenceLevel.HAUTE
        if v.startswith("MOY") or v.startswith("MED"):
            return ConfidenceLevel.MOYENNE
        if v.startswith("FAIB") or v.startswith("LOW"):
            return ConfidenceLevel.FAIBLE
    return ConfidenceLevel.MOYENNE


def classify_test(test: Dict[str, Any], model_alias: str = _DEFAULT_MODEL) -> TestAutomationClassification:
    """Classifie un test unique. Ne lève jamais — encapsule les erreurs dans `error`."""
    test_name = test.get("test_name", "") or "(test sans nom)"
    system_prompt = build_automation_classifier_system_prompt()
    user_prompt = build_automation_classifier_user_prompt(test)

    try:
        raw = call_groq(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model_alias=model_alias,
            temperature=0.1,
            max_tokens=400,
        )
        data = _extract_json(raw)
        if not data:
            return TestAutomationClassification(
                test_name=test_name,
                classification=AutomationDecision.MANUEL,
                confidence=ConfidenceLevel.FAIBLE,
                raison="Réponse LLM non parsable — défaut MANUEL par prudence.",
                error="json_parse_failed",
            )
        return TestAutomationClassification(
            test_name=test_name,
            classification=_normalize_decision(data.get("classification")),
            confidence=_normalize_confidence(data.get("confidence")),
            raison=(data.get("raison") or "").strip()[:300],
        )
    except Exception as e:
        logger.exception(f"[Agent4] classify_test failed for '{test_name}': {e}")
        return TestAutomationClassification(
            test_name=test_name,
            classification=AutomationDecision.MANUEL,
            confidence=ConfidenceLevel.FAIBLE,
            raison="Erreur LLM — défaut MANUEL par prudence.",
            error=str(e),
        )


def classify_tests_for_story(
    story_id: str,
    tests: List[Dict[str, Any]],
    model_alias: str = _DEFAULT_MODEL,
) -> StoryAutomationClassificationResult:
    """Classifie tous les tests d'une story (séquentiel, simple, robuste)."""
    logger.info(f"[Agent4] Classifying {len(tests)} tests for {story_id} (model={model_alias})")
    classifications: List[TestAutomationClassification] = []
    for t in tests:
        classifications.append(classify_test(t, model_alias=model_alias))
    return StoryAutomationClassificationResult(
        story_id=story_id,
        model=model_alias,
        classifications=classifications,
    )
