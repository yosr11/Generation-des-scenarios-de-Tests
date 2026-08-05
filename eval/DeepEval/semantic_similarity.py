"""
Utilitaire partagé pour comparer deux textes par le SENS et non par les mots.
Utilisé par metrics.py à la place du matching mot-à-mot (trop fragile en français).

Fonctionnement : on transforme chaque phrase en un vecteur de nombres (embedding)
qui représente son sens. Deux phrases qui veulent dire la même chose auront des
vecteurs proches, même si les mots utilisés sont différents
(ex: "afficher le mot-clé" et "le mot-clé est visible" -> proches).
"""

from functools import lru_cache
from typing import List, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer

# Modèle multilingue, fonctionne bien en français, léger et rapide.
_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_model = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))


@lru_cache(maxsize=4096)
def _embed_cached(text: str) -> Tuple[float, ...]:
    """Cache les embeddings pour ne pas recalculer 10x la même phrase."""
    vec = _get_model().encode(text)
    return tuple(vec.tolist())


def semantic_similarity(text_a: str, text_b: str) -> float:
    """Retourne un score entre -1 et 1 (en pratique 0 à 1) indiquant à quel
    point deux textes ont le même sens. 1 = identique, 0 = sans rapport."""
    if not text_a.strip() or not text_b.strip():
        return 0.0
    emb_a = np.array(_embed_cached(text_a))
    emb_b = np.array(_embed_cached(text_b))
    return _cosine(emb_a, emb_b)


def best_semantic_match(query: str, candidates: List[str]) -> Tuple[float, str | None]:
    """Compare 'query' à une liste de candidats, retourne le meilleur score
    et le candidat correspondant."""
    if not candidates or not query.strip():
        return 0.0, None
    best_score, best_candidate = -1.0, None
    for cand in candidates:
        score = semantic_similarity(query, cand)
        if score > best_score:
            best_score, best_candidate = score, cand
    return best_score, best_candidate
