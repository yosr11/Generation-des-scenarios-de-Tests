"""
Analyse de couverture : chaque testable_point vs texte agrégé des tests (similarité sémantique).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

from app.models.test_manual import ManualTestCase
from app.services.agent3_semantic_similarity import encode_texts, max_cosine_similarity


def manual_test_to_embedding_text(test: ManualTestCase) -> str:
    parts: List[str] = [test.test_name, test.objective, test.execution_context or ""]
    parts.extend(" ".join(test.preconditions or []))
    for step in test.steps:
        parts.append(step.action)
        parts.append(step.expected_result or "")
        if step.data:
            parts.append(step.data)
    return " ".join(p for p in parts if p)


@dataclass
class CoverageAnalysisResult:
    testable_points: List[str]
    covered_mask: List[bool]
    best_similarity_per_point: List[float]
    best_test_index_per_point: List[int]
    coverage_rate: float
    covered_count: int
    uncovered_points: List[str]

    @property
    def total_points(self) -> int:
        return len(self.testable_points)


def analyze_coverage(
    testable_points: List[str],
    tests: List[ManualTestCase],
    similarity_threshold: float = 0.52,
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
) -> CoverageAnalysisResult:
    if not testable_points:
        return CoverageAnalysisResult(
            testable_points=[],
            covered_mask=[],
            best_similarity_per_point=[],
            best_test_index_per_point=[],
            coverage_rate=1.0,
            covered_count=0,
            uncovered_points=[],
        )

    test_texts = [manual_test_to_embedding_text(t) for t in tests]
    point_emb = encode_texts(testable_points, embedding_model)

    if not tests:
        return CoverageAnalysisResult(
            testable_points=list(testable_points),
            covered_mask=[False] * len(testable_points),
            best_similarity_per_point=[0.0] * len(testable_points),
            best_test_index_per_point=[-1] * len(testable_points),
            coverage_rate=0.0,
            covered_count=0,
            uncovered_points=list(testable_points),
        )

    test_emb = encode_texts(test_texts, embedding_model)
    sim_matrix = point_emb @ test_emb.T
    best_per_point = np.max(sim_matrix, axis=1)
    best_idx = np.argmax(sim_matrix, axis=1)

    covered_mask: List[bool] = []
    uncovered: List[str] = []
    best_sims: List[float] = []
    best_ix: List[int] = []

    for i, point in enumerate(testable_points):
        s = float(best_per_point[i])
        j = int(best_idx[i])
        best_sims.append(s)
        best_ix.append(j)
        ok = s >= similarity_threshold
        covered_mask.append(ok)
        if not ok:
            uncovered.append(point)

    n = len(testable_points)
    rate = sum(covered_mask) / n if n else 1.0

    return CoverageAnalysisResult(
        testable_points=list(testable_points),
        covered_mask=covered_mask,
        best_similarity_per_point=best_sims,
        best_test_index_per_point=best_ix,
        coverage_rate=rate,
        covered_count=sum(covered_mask),
        uncovered_points=uncovered,
    )
