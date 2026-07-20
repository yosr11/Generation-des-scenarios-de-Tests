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
    model_alias: str = "nova-lite-2",
) -> List[AmbiguityFinding]:
    """
    Désactivé : la seule ambiguïté reconnue est « vérifier », déjà détectée par regex.
    Toute autre « vagueur » (résultat non chiffré, action générique) provient de la
    user story et n'est pas une ambiguïté de test → pas de détection LLM (faux positifs).
    """
    return []


# ── Contradiction entre testable_points ──────────────────────────────────────

_CONTRADICTION_PAIRS: list[tuple[str, str]] = [
    ("droite", "gauche"),
    ("gauche", "droite"),
    ("activé", "désactivé"),
    ("désactivé", "activé"),
    ("affiché", "masqué"),
    ("masqué", "affiché"),
    ("affiché", "caché"),
    ("caché", "affiché"),
    ("visible", "invisible"),
    ("invisible", "visible"),
    ("présent", "absent"),
    ("absent", "présent"),
    ("autorisé", "interdit"),
    ("interdit", "autorisé"),
    ("actif", "inactif"),
    ("inactif", "actif"),
    ("activé", "grisé"),
    ("grisé", "activé"),
]


def detect_testable_point_contradictions(testable_points: List[str]) -> List[dict]:
    """
    Détecte les contradictions internes entre testable_points.
    Ex : TP-1 dit "à droite de la date" et TP-4 dit "à gauche de la date".
    Retourne une liste de findings au format ambiguity_findings (story-level).
    """
    findings: List[dict] = []
    seen_pairs: set[tuple[int, int]] = set()

    for i, tp_a in enumerate(testable_points):
        words_a = set(re.findall(r"\b\w+\b", tp_a.lower()))
        for j, tp_b in enumerate(testable_points):
            if i >= j:
                continue
            words_b = set(re.findall(r"\b\w+\b", tp_b.lower()))
            for word_a, word_b in _CONTRADICTION_PAIRS:
                if word_a in words_a and word_b in words_b:
                    pair_key = (min(i, j), max(i, j), word_a, word_b)
                    canonical = (min(i, j), max(i, j), min(word_a, word_b), max(word_a, word_b))
                    if canonical in seen_pairs:
                        continue
                    seen_pairs.add(canonical)
                    findings.append({
                        "test_name": "[STORY]",
                        "step_index": -1,
                        "field": "testable_points",
                        "reason": (
                            f"Contradiction probable : TP-{i+1} contient '«{word_a}»' "
                            f"et TP-{j+1} contient '«{word_b}»' — "
                            f"vérifier la cohérence avec la User Story source."
                        ),
                        "original_text": f"TP-{i+1}: {tp_a}\nTP-{j+1}: {tp_b}",
                        "source": "heuristic_contradiction",
                    })
    return findings