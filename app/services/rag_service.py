"""
app/services/rag_service.py
────────────────────────────
Service RAG (Retrieval-Augmented Generation).

Pipeline :
  1. Chunking  — découpe les documents en morceaux de ~500 caractères
  2. Indexation — transforme chaque morceau en vecteur et le stocke dans ChromaDB
  3. Retrieval  — recherche les morceaux les plus pertinents pour une story donnée
"""

import logging
import os
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# ── Configuration ───────────────────────────────────────────
CHUNK_SIZE = 500        # caractères par morceau
CHUNK_OVERLAP = 100     # chevauchement entre morceaux
TOP_K = 5               # nombre de résultats à retourner

# Dossier persistant pour ChromaDB
CHROMA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "app", "data", "vector_store",
)

# Modèle d'embeddings (léger, ~80Mo, multilingue)
_model: Optional[SentenceTransformer] = None
_chroma_client: Optional[chromadb.ClientAPI] = None


def _get_model() -> SentenceTransformer:
    """Charge le modèle d'embeddings (une seule fois, en lazy)."""
    global _model
    if _model is None:
        logger.info("Chargement du modèle d'embeddings all-MiniLM-L6-v2 ...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Modèle d'embeddings chargé.")
    return _model


def _get_chroma_client() -> chromadb.ClientAPI:
    """Initialise le client ChromaDB persistant (une seule fois)."""
    global _chroma_client
    if _chroma_client is None:
        os.makedirs(CHROMA_DIR, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
        logger.info("ChromaDB initialisé dans %s", CHROMA_DIR)
    return _chroma_client


# ══════════════════════════════════════════════════════════════
#  1. CHUNKING — Découpage en morceaux
# ══════════════════════════════════════════════════════════════

def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> List[str]:
    """
    Découpe un texte en morceaux de `chunk_size` caractères
    avec un chevauchement de `overlap` caractères.
    """
    if not text or not text.strip():
        return []

    text = text.strip()
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += chunk_size - overlap

    return chunks


# ══════════════════════════════════════════════════════════════
#  2. INDEXATION — Embeddings + stockage ChromaDB
# ══════════════════════════════════════════════════════════════

def index_documents(
    epic_key: str,
    documents: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Indexe une liste de documents dans une collection ChromaDB
    dédiée à l'epic.

    Chaque document est découpé en chunks, chaque chunk est
    transformé en vecteur et stocké.

    Paramètres :
      - epic_key : clé de l'epic (ex: "NUXEPM-345"), utilisée
                   comme nom de collection
      - documents : liste de dicts {source, origin_key, filename, text}

    Retourne un résumé : {collection, total_chunks, total_documents}
    """
    client = _get_chroma_client()
    model = _get_model()

    # Nom de collection ChromaDB (alphanumeric + underscores)
    collection_name = epic_key.replace("-", "_").lower()

    # Supprimer l'ancienne collection si elle existe (ré-indexation propre)
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    collection = client.create_collection(
        name=collection_name,
        metadata={"epic_key": epic_key},
    )

    all_ids: List[str] = []
    all_texts: List[str] = []
    all_metadatas: List[Dict[str, str]] = []

    for doc in documents:
        text = doc.get("text", "")
        if not text or len(text.strip()) < 20:
            continue

        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc['origin_key']}_{doc['filename']}_{i}"
            all_ids.append(chunk_id)
            all_texts.append(chunk)
            all_metadatas.append({
                "source": doc.get("source", ""),
                "origin_key": doc.get("origin_key", ""),
                "filename": doc.get("filename", ""),
                "chunk_index": str(i),
            })

    if not all_texts:
        logger.warning("Aucun chunk à indexer pour %s", epic_key)
        return {"collection": collection_name, "total_chunks": 0, "total_documents": 0}

    # Générer les embeddings par batch
    logger.info("Génération des embeddings pour %d chunks ...", len(all_texts))
    embeddings = model.encode(all_texts, show_progress_bar=False).tolist()

    # Indexer par batches de 500 (limite ChromaDB)
    batch_size = 500
    for start in range(0, len(all_ids), batch_size):
        end = start + batch_size
        collection.add(
            ids=all_ids[start:end],
            documents=all_texts[start:end],
            embeddings=embeddings[start:end],
            metadatas=all_metadatas[start:end],
        )

    logger.info(
        "Indexation terminée : %s → %d chunks depuis %d documents",
        collection_name, len(all_ids), len(documents),
    )

    return {
        "collection": collection_name,
        "total_chunks": len(all_ids),
        "total_documents": len(documents),
    }


# ══════════════════════════════════════════════════════════════
#  3. RETRIEVAL — Recherche sémantique
# ══════════════════════════════════════════════════════════════

def retrieve_context(
    epic_key: str,
    query_text: str,
    top_k: int = TOP_K,
    pin_origin_keys: Optional[List[str]] = None,
    exclude_origin_keys: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Recherche les `top_k` chunks les plus pertinents pour le texte donné.

    `pin_origin_keys` : tous les chunks dont l'origin_key est dans cette liste
        sont AJOUTÉS en tête du contexte (dédupliqués avec le top-K sémantique).

    `exclude_origin_keys` : tous les chunks dont l'origin_key est dans cette
        liste sont EXCLUS du top-K sémantique (cas d'usage : les PJ de la story
        analysée sont injectées en direct comme spec, pas comme inspiration RAG).

    Retourne : liste de dicts {text, source, origin_key, filename, distance, pinned}
    """
    client = _get_chroma_client()
    model = _get_model()

    collection_name = epic_key.replace("-", "_").lower()

    try:
        collection = client.get_collection(collection_name)
    except Exception:
        logger.warning("Collection %s introuvable", collection_name)
        return []

    if collection.count() == 0:
        return []

    pinned_chunks: List[Dict[str, Any]] = []
    pinned_ids: set = set()

    # ── 1) Pinned : récupérer TOUS les chunks dont origin_key ∈ pin_origin_keys
    if pin_origin_keys:
        try:
            pinned_res = collection.get(
                where={"origin_key": {"$in": list(pin_origin_keys)}},
                include=["documents", "metadatas"],
            )
            if pinned_res and pinned_res.get("documents"):
                for doc_id, doc, meta in zip(
                    pinned_res.get("ids", []),
                    pinned_res["documents"],
                    pinned_res.get("metadatas") or [{}] * len(pinned_res["documents"]),
                ):
                    pinned_ids.add(doc_id)
                    pinned_chunks.append({
                        "text": doc,
                        "source": meta.get("source", ""),
                        "origin_key": meta.get("origin_key", ""),
                        "filename": meta.get("filename", ""),
                        "distance": 0.0,
                        "pinned": True,
                    })
        except Exception as e:
            logger.warning("Pin chunks lookup failed for %s: %s", collection_name, e)

    # ── 2) Top-K sémantique (dédupliqué des pinned et exclu)
    actual_k = min(top_k, collection.count())
    query_embedding = model.encode([query_text], show_progress_bar=False).tolist()

    excluded_set = set(exclude_origin_keys or [])

    semantic_chunks: List[Dict[str, Any]] = []
    try:
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=actual_k,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        logger.warning("Erreur lors de la requête ChromaDB pour %s: %s. "
                       "Tentative de réindexation...", collection_name, str(e))
        try:
            client.delete_collection(collection_name)
            logger.info("Collection %s supprimée, elle sera réindexée au prochain appel.", collection_name)
        except Exception:
            pass
        # On garde au moins les pinned si on en avait
        return pinned_chunks

    if results and results.get("documents"):
        docs = results["documents"][0]
        metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)
        ids = results.get("ids", [[]])[0] if results.get("ids") else [None] * len(docs)

        for doc_id, doc, meta, dist in zip(ids, docs, metas, distances):
            if doc_id and doc_id in pinned_ids:
                continue  # déjà dans pinned
            if meta.get("origin_key", "") in excluded_set:
                continue  # PJ de la story analysée → injectée en direct, pas via RAG
            semantic_chunks.append({
                "text": doc,
                "source": meta.get("source", ""),
                "origin_key": meta.get("origin_key", ""),
                "filename": meta.get("filename", ""),
                "distance": round(dist, 4),
                "pinned": False,
            })

    return pinned_chunks + semantic_chunks


# ══════════════════════════════════════════════════════════════
#  UTILITAIRE — Vérifie si un epic est déjà indexé
# ══════════════════════════════════════════════════════════════

def is_epic_indexed(epic_key: str) -> bool:
    """Vérifie si une collection existe pour cet epic."""
    client = _get_chroma_client()
    collection_name = epic_key.replace("-", "_").lower()
    try:
        col = client.get_collection(collection_name)
        return col.count() > 0
    except Exception:
        return False
