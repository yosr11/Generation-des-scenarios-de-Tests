"""
Détection d'étapes ambiguës (heuristiques regex + LLM sémantique). Agent 3 ne réécrit pas le contenu des tests.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import List, Optional

from app.models.test_manual import ManualTestCase

logger = logging.getLogger(__name__)

AMBIGUITY_REGEX = [
    # Seule ambiguïté retenue : "vérifier" utilisé comme verbe d'action / d'objectif.
    # Toute autre formulation vague provient de la user story elle-même et ne peut
    # être corrigée dans le test → ce n'est pas une ambiguïté de test.
    (re.compile(r"(?i)\bv[eé]rifier\b"), "verbe interdit « vérifier » dans action/résultat/objectif"),
]


@dataclass
class AmbiguityFinding:
    test_name: str
    step_index: int
    field: str
    original_text: str
    reason: str


def _regex_reason(text: str) -> Optional[str]:
    for rx, label in AMBIGUITY_REGEX:
        if rx.search(text):
            return label
    return None


def detect_ambiguous_steps(test: ManualTestCase) -> List[AmbiguityFinding]:
    out: List[AmbiguityFinding] = []

    if (test.objective or "").strip():
        r = None
        for rx, label in AMBIGUITY_REGEX:
            if rx.search(test.objective):
                r = label
                break
        if r:
            out.append(
                AmbiguityFinding(
                    test_name=test.test_name,
                    step_index=0,
                    field="objective",
                    original_text=test.objective,
                    reason=r,
                )
            )

    for step in test.steps:
        for field, val in (("action", step.action), ("expected_result", step.expected_result)):
            r = _regex_reason(val or "")
            if r:
                out.append(
                    AmbiguityFinding(
                        test_name=test.test_name,
                        step_index=step.index,
                        field=field,
                        original_text=val or "",
                        reason=r,
                    )
                )

    return out


def detect_ambiguous_steps_with_llm(
    tests: List[ManualTestCase],
    model_alias: str = "llama4",
) -> List[AmbiguityFinding]:
    """
    Désactivé : la seule ambiguïté reconnue est « vérifier », déjà détectée par regex.
    Toute autre « vagueur » (résultat non chiffré, action générique) provient de la
    user story et n'est pas une ambiguïté de test → pas de détection LLM (faux positifs).
    """
    return []