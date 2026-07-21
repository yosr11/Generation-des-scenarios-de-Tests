"""
Embeddings et similarité cosinus pour Agent 3 (couverture, doublons).
Utilise sentence-transformers (même famille que semantic_vague_detector).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Sequence

import numpy as np
from sentence_transformers import SentenceTransformer

DEFAULT_EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=4)
def get_sentence_transformer(
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> SentenceTransformer:
    return SentenceTransformer(model_name)


def encode_texts(
    texts: Sequence[str],
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> np.ndarray:
    """Matrice (n, d) L2-normalisée pour cosinus = produit scalaire."""
    model = get_sentence_transformer(model_name)
    cleaned = [t if (t and str(t).strip()) else " " for t in texts]
    emb = model.encode(
        list(cleaned),
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.asarray(emb, dtype=np.float32)


def max_cosine_similarity(query_emb: np.ndarray, corpus_emb: np.ndarray) -> np.ndarray:
    """
    query_emb: (nq, d), corpus_emb: (nc, d), normalisés.
    Retourne pour chaque requête le max cosinus sur le corpus : shape (nq,).
    """
    if corpus_emb.size == 0:
        return np.zeros((query_emb.shape[0],), dtype=np.float32)
    return np.max(query_emb @ corpus_emb.T, axis=1)


def pairwise_max_similarity_matrix(emb: np.ndarray) -> np.ndarray:
    """Sim cosinus entre toutes les paires i,j : matrice symétrique (n, n)."""
    if emb.size == 0:
        return np.zeros((0, 0), dtype=np.float32)
    return emb @ emb.T
