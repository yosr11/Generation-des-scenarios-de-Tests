"""
Tableau de bord Agent 4 : mêmes métriques que le validateur (entrée = tests déjà générés ailleurs).
"""

from __future__ import annotations

from typing import List

from app.models.agent4_validation import Agent4StoryDashboard, DuplicatePairReport
from app.models.test_manual import ManualTestCase
from app.services.agent4_coverage_service import analyze_coverage
from app.services.agent4_prescriptive_service import build_validation_envelope


def build_story_dashboard(
    story_id: str,
    testable_points: List[str],
    tests: List[ManualTestCase],
    *,
    coverage_threshold: float = 0.70,
    coverage_similarity_threshold: float = 0.7,
    duplicate_similarity_threshold: float = 0.8,
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
) -> Agent4StoryDashboard:
    cov = analyze_coverage(
        testable_points, tests, coverage_similarity_threshold, embedding_model
    )
    env = build_validation_envelope(
        tests,
        cov,
        duplicate_similarity_threshold,
        embedding_model,
        coverage_threshold,
    )
    dup_reports = [
        DuplicatePairReport.model_validate(x) for x in env["duplicate_pairs"]
    ]

    return Agent4StoryDashboard(
        story_id=story_id,
        coverage_rate=round(cov.coverage_rate, 4),
        uncovered_testable_points=list(cov.uncovered_points),
        duplicate_pairs=dup_reports,
        ambiguity_findings=list(env["ambiguity_findings"]),
        validation_status=env["validation_status"],
        correction_instructions=env["correction_instructions"],
    )
