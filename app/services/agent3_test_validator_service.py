"""
Agent 3 — validateur pur : couverture sémantique, doublons (rapport), ambiguïtés (constats), instructions.
Les tests en entrée sont renvoyés inchangés. Aucun LLM, aucun Agent 2, aucune boucle de régénération.
"""

from __future__ import annotations

from typing import List

from app.models.agent3_validation import Agent3ValidationReport, Agent3ValidationResult
from app.models.test_manual import ManualTestCase
from app.services.agent3_coverage_service import analyze_coverage
from app.services.agent3_prescriptive_service import build_validation_envelope


def validate_and_improve_tests(
    story_id: str,
    testable_points: List[str],
    tests: List[ManualTestCase],
    *,
    coverage_threshold: float = 0.70,
    coverage_similarity_threshold: float = 0.52,
    duplicate_similarity_threshold: float = 0.88,
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
) -> Agent3ValidationResult:
    cov = analyze_coverage(testable_points, tests, coverage_similarity_threshold, embedding_model)

    env = build_validation_envelope(
        tests,
        cov,
        duplicate_similarity_threshold,
        embedding_model,
        coverage_threshold,
    )

    report = Agent3ValidationReport(
        coverage_rate=round(cov.coverage_rate, 4),
        uncovered_testable_points=list(cov.uncovered_points),
        duplicate_pairs=env["duplicate_pairs"],
        ambiguity_findings=env["ambiguity_findings"],
        validation_status=env["validation_status"],
        correction_instructions=env["correction_instructions"],
    )

    sid = story_id or (tests[0].story_id if tests else "")
    return Agent3ValidationResult(story_id=sid, tests=list(tests), report=report)
