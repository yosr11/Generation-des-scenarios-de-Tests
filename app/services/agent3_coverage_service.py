"""
Analyse de couverture : chaque testable_point vs texte agrégé des tests (similarité sémantique).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

from app.models.test_manual import ManualTestCase
from app.services.agent3_semantic_similarity import encode_texts, max_cosine_similarity


def _iter_test_steps(test: ManualTestCase):
    """Itère sur les actions d'un test (steps plats ou étapes groupées)."""
    if test.steps:
        yield from test.steps
        return
    for etape in getattr(test, "étapes", None) or []:
        for step in etape.steps or []:
            yield step


def manual_test_to_embedding_text(test: ManualTestCase) -> str:
    parts: List[str] = [test.test_name, test.objective, test.execution_context or ""]
    parts.extend(" ".join(test.preconditions or []))
    for step in _iter_test_steps(test):
        parts.append(step.action)
        parts.append(step.expected_result or "")
        if step.actor:
            parts.append(step.actor)
    return " ".join(p for p in parts if p)


def manual_test_to_fragments(test: ManualTestCase) -> List[str]:
    """
    Découpe un test en fragments sémantiques courts pour comparaison fine
    avec un testable_point. Chaque step devient un fragment indépendant
    pour éviter la dilution du signal dans un texte agrégé.
    """
    fragments: List[str] = []
    header = " ".join(p for p in [test.test_name or "", test.objective or ""] if p)
    if header:
        fragments.append(header)
    for step in _iter_test_steps(test):
        action = step.action or ""
        expected = step.expected_result or ""
        frag = " ".join(p for p in [action, expected] if p)
        if frag:
            fragments.append(frag)
    if not fragments:
        fragments.append(test.test_name or test.objective or "")
    return fragments


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
    similarity_threshold: float = 0.7,
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
) -> CoverageAnalysisResult:
    if not testable_points:
        # Aucun point testable défini : la couverture est indéfinie (N/A).
        # On retourne 0.0 pour ne pas afficher un faux 100% trompeur.
        return CoverageAnalysisResult(
            testable_points=[],
            covered_mask=[],
            best_similarity_per_point=[],
            best_test_index_per_point=[],
            coverage_rate=0.0,
            covered_count=0,
            uncovered_points=[],
        )

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

    # Découpe chaque test en fragments courts (header + chaque step) pour éviter
    # la dilution sémantique d'un texte agrégé. La similarité d'un point vs un test
    # = max des similarités vs ses fragments.
    fragments: List[str] = []
    fragment_to_test: List[int] = []
    for t_idx, t in enumerate(tests):
        for frag in manual_test_to_fragments(t):
            fragments.append(frag)
            fragment_to_test.append(t_idx)

    frag_emb = encode_texts(fragments, embedding_model)
    sim_frag = point_emb @ frag_emb.T  # (n_points, n_fragments)

    n_tests = len(tests)
    n_points = len(testable_points)
    sim_matrix = np.full((n_points, n_tests), -1.0, dtype=np.float32)
    for f_idx, t_idx in enumerate(fragment_to_test):
        col = sim_frag[:, f_idx]
        np.maximum(sim_matrix[:, t_idx], col, out=sim_matrix[:, t_idx])

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
