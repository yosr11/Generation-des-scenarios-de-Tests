"""
Détection d'étapes ambiguës (heuristiques / regex). Agent 3 ne réécrit pas le contenu des tests.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from app.models.test_manual import ManualTestCase

AMBIGUITY_REGEX = [
    (re.compile(r"(?i)\bremplir le formulaire\b"), "action générique « remplir le formulaire » sans précision"),
    (re.compile(r"(?i)\bremplir le(s)?\s+champ(s)?\b"), "champs non nommés"),
    (re.compile(r"(?i)\ble système réag(it|is)\b"), "résultat attendu vague (réaction système)"),
    (re.compile(r"(?i)\bcorrectement\b|\bcomme prévu\b|\bde manière attendue\b"), "adverbe de vagueur"),
    (re.compile(r"(?i)\bvalider que\b|\bvérifier que\b"), "formulation non actionnable en étape"),
    (re.compile(r"(?i)\bfonctionne\b.*\b(sans erreur|correctement)\b"), "résultat peu observable"),
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
    if len(text.strip()) < 12 and re.search(
        r"(?i)^(saisir|remplir|ouvrir|cliquer|consulter)\b", text.strip()
    ):
        return "étape trop courte / objet d'action implicite"
    return None


def detect_ambiguous_steps(test: ManualTestCase) -> List[AmbiguityFinding]:
    out: List[AmbiguityFinding] = []
    if (test.objective or "").strip():
        r = _regex_reason(test.objective)
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
