"""
Détection de doublons sémantiques entre ManualTestCase (embedding du cas entier).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from app.models.test_manual import ManualTestCase
from app.services.agent3_coverage_service import manual_test_to_embedding_text
from app.services.agent3_semantic_similarity import encode_texts, pairwise_max_similarity_matrix


@dataclass
class DuplicateRemovalResult:
    kept_indices: List[int]
    removed_indices: List[int]
    removed_as_duplicate_of: List[int]
    pairs_reported: List[Tuple[int, int, float]]


def find_semantic_duplicate_removal(
    tests: List[ManualTestCase],
    duplicate_threshold: float = 0.88,
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
) -> DuplicateRemovalResult:
    """
    Garde le premier test de chaque cluster ; les suivants très similaires à un test déjà gardé sont supprimés.
    """
    n = len(tests)
    if n <= 1:
        return DuplicateRemovalResult(
            kept_indices=list(range(n)),
            removed_indices=[],
            removed_as_duplicate_of=[],
            pairs_reported=[],
        )

    texts = [manual_test_to_embedding_text(t) for t in tests]
    emb = encode_texts(texts, embedding_model)
    sim = pairwise_max_similarity_matrix(emb)

    kept: List[int] = []
    removed: List[int] = []
    removed_of: List[int] = []
    pairs: List[Tuple[int, int, float]] = []

    for i in range(n):
        duplicate_of: int | None = None
        for j in kept:
            if i != j and sim[i, j] >= duplicate_threshold:
                duplicate_of = j
                pairs.append((i, j, float(sim[i, j])))
                break
        if duplicate_of is not None:
            removed.append(i)
            removed_of.append(duplicate_of)
        else:
            kept.append(i)

    return DuplicateRemovalResult(
        kept_indices=kept,
        removed_indices=removed,
        removed_as_duplicate_of=removed_of,
        pairs_reported=pairs,
    )


def remove_duplicate_tests(
    tests: List[ManualTestCase],
    duplicate_threshold: float = 0.88,
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
) -> Tuple[List[ManualTestCase], DuplicateRemovalResult]:
    dr = find_semantic_duplicate_removal(tests, duplicate_threshold, embedding_model)
    kept_tests = [tests[i] for i in dr.kept_indices]
    return kept_tests, dr
