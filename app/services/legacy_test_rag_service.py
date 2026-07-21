"""
RAG des tests Xray legacy (Sopra HR).

Recherche sémantique dans la collection Chroma `legacy_tests` (5906 tests
extraits des projets historiques YOUQA / QAGT / YTINMA / HRAE2EQA / PLD4UE2E)
pour fournir à Agent 2 des exemples few-shot du style maison.

API publique : `retrieve_similar(title, description, ...)`.
Tout échec retourne `[]` (fallback graceful : Agent 2 continue sans exemples).
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Constantes (synchronisées avec eval/index_legacy_tests.py) ──
VECTOR_STORE_PATH = Path(__file__).resolve().parents[1] / "data" / "vector_store"
COLLECTION_NAME = "legacy_tests"
EMBED_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
MAX_EMBED_CHARS = 1500

DEFAULT_K = 5
DEFAULT_MIN_SCORE = 0.55
# Filtres qualité pour écarter les tests legacy trop pauvres / mal renseignés :
# ils dégradent la génération Agent 2 en poussant le LLM à imiter une concision excessive
# (ex: action "Accéder" seule au lieu de "Accéder à la démarche X").
DEFAULT_MIN_STEPS = 2
DEFAULT_MIN_ACTION_CHARS = 12
DEFAULT_OVERSAMPLE = 4  # multiplie n_results pour pouvoir filtrer ensuite

# ── Singletons lazy ──
_model = None
_collection = None
_lock = threading.Lock()


def _get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                logger.info(
                    f"[legacy_rag] Loading embedding model '{EMBED_MODEL_NAME}'"
                )
                _model = SentenceTransformer(EMBED_MODEL_NAME)
    return _model


def _get_collection():
    global _collection
    if _collection is None:
        with _lock:
            if _collection is None:
                import chromadb

                logger.info(
                    f"[legacy_rag] Opening Chroma collection '{COLLECTION_NAME}' at {VECTOR_STORE_PATH}"
                )
                client = chromadb.PersistentClient(path=str(VECTOR_STORE_PATH))
                _collection = client.get_collection(COLLECTION_NAME)
    return _collection


def _build_query_text(title: str, description: str) -> str:
    title = (title or "").strip()
    description = (description or "").strip()
    text = f"{title}\n\n{description}".strip()
    if len(text) > MAX_EMBED_CHARS:
        text = text[:MAX_EMBED_CHARS]
    return text


def _deserialize_pivot(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Récupère le pivot complet sérialisé dans metadata.pivot_json."""
    raw = meta.get("pivot_json")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _passes_quality_filter(
    pivot: Dict[str, Any],
    min_steps: int,
    min_action_chars: int,
) -> bool:
    """Écarte les tests legacy trop pauvres pour servir d'exemple few-shot."""
    steps = pivot.get("steps") or []
    if len(steps) < min_steps:
        return False
    # Au moins une étape doit avoir une action assez détaillée
    # (sinon le LLM imite "Accéder" tout court).
    has_detailed_action = False
    for s in steps:
        action = (s.get("action") or "").strip() if isinstance(s, dict) else ""
        if len(action) >= min_action_chars:
            has_detailed_action = True
            break
    return has_detailed_action


def retrieve_similar(
    title: str,
    description: str = "",
    k: int = DEFAULT_K,
    min_score: float = DEFAULT_MIN_SCORE,
    project: Optional[str] = None,
    module_root: Optional[str] = None,
    min_steps: int = DEFAULT_MIN_STEPS,
    min_action_chars: int = DEFAULT_MIN_ACTION_CHARS,
) -> List[Dict[str, Any]]:
    """
    Retourne les top-k tests pivots les plus similaires à (title + description),
    après filtre qualité (min_steps, min_action_chars).

    Filtrage :
      - distance cosinus → score = 1 - distance, on garde score >= min_score
      - `project` : filtre Chroma `where={"project": project}` si fourni
      - `module_root` : filtre Chroma `where={"module_root": module_root}` si fourni
      - qualité : exclut les pivots avec moins de `min_steps` étapes
        ou aucune action ≥ `min_action_chars` caractères

    Format de retour (peut être `[]` si rien ne matche — Agent 2 doit gérer ce cas) :
        [
          {
            "test_id": "YOUQA-1234",
            "title": "...",
            "score": 0.78,
            "project": "YOUQA",
            "module_root": "Démarche RH",
            "pivot": {... pivot complet ...},
          },
          ...
        ]
    """
    query_text = _build_query_text(title, description)
    if not query_text:
        return []

    try:
        model = _get_model()
        collection = _get_collection()
    except Exception as e:
        logger.warning(f"[legacy_rag] Init failed (model/collection): {e}")
        return []

    where: Optional[Dict[str, Any]] = None
    filters = []
    if project:
        filters.append({"project": project})
    if module_root:
        filters.append({"module_root": module_root})
    if len(filters) == 1:
        where = filters[0]
    elif len(filters) > 1:
        where = {"$and": filters}

    try:
        embedding = model.encode(
            [query_text],
            normalize_embeddings=True,
            convert_to_numpy=True,
        ).tolist()
        # On sur-échantillonne (k * OVERSAMPLE) pour pouvoir appliquer le filtre qualité
        # sans perdre tous les résultats.
        n_results = max(k * DEFAULT_OVERSAMPLE, k)
        results = collection.query(
            query_embeddings=embedding,
            n_results=n_results,
            where=where,
            include=["metadatas", "distances", "documents"],
        )
    except Exception as e:
        logger.warning(f"[legacy_rag] Query failed: {e}")
        return []

    ids_batch = (results.get("ids") or [[]])[0]
    metas_batch = (results.get("metadatas") or [[]])[0]
    dists_batch = (results.get("distances") or [[]])[0]

    out: List[Dict[str, Any]] = []
    rejected_score = 0
    rejected_quality = 0
    for test_id, meta, dist in zip(ids_batch, metas_batch, dists_batch):
        if len(out) >= k:
            break
        meta = meta or {}
        score = 1.0 - float(dist) if dist is not None else 0.0
        if score < min_score:
            rejected_score += 1
            continue
        pivot = _deserialize_pivot(meta)
        if not _passes_quality_filter(pivot, min_steps, min_action_chars):
            rejected_quality += 1
            continue
        out.append(
            {
                "test_id": test_id,
                "title": pivot.get("title") or meta.get("title") or "",
                "score": round(score, 4),
                "project": meta.get("project") or "",
                "module_root": meta.get("module_root") or "",
                "pivot": pivot,
            }
        )

    logger.info(
        f"[legacy_rag] query='{query_text[:80]}...' "
        f"k={k} min_score={min_score} min_steps={min_steps} "
        f"min_action_chars={min_action_chars} → {len(out)} kept "
        f"(raw={len(ids_batch)}, rejected_score={rejected_score}, "
        f"rejected_quality={rejected_quality})"
    )
    return out
