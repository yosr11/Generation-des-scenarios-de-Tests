"""
Indexation des tests legacy (format pivot) dans ChromaDB pour le RAG few-shot.

Lit les fichiers `eval/data/legacy_tests/*.enriched.jsonl`, calcule un
embedding (titre + description + étapes condensées) avec
`paraphrase-multilingual-MiniLM-L12-v2`, et insère le tout dans la
collection ChromaDB persistante `legacy_tests`.

Le pivot JSON complet est conservé dans la metadata `pivot_json` pour
pouvoir être ré-injecté tel quel dans le prompt few-shot d'Agent 3.

Usage :
    python -m eval.index_legacy_tests                    # indexe tout
    python -m eval.index_legacy_tests --projects YOUQA
    python -m eval.index_legacy_tests --reset            # vide la collection avant
    python -m eval.index_legacy_tests --batch-size 64
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import chromadb  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

DATA_DIR = ROOT / "eval" / "data" / "legacy_tests"
CHROMA_DIR = ROOT / "app" / "data" / "vector_store"
COLLECTION_NAME = "legacy_tests"
EMBED_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

DEFAULT_PROJECTS = ["YOUQA", "QAGT", "YTINMA", "HRAE2EQA", "PLD4UE2E"]

# Limite raisonnable du texte embeddé : le modèle a une fenêtre de 128 tokens
# (≈ 500 caractères). Au-delà, le contenu est tronqué de toute façon.
MAX_EMBED_CHARS = 1500


def _enriched_path(project: str) -> Path:
    p = DATA_DIR / f"{project}.enriched.jsonl"
    return p if p.exists() else DATA_DIR / f"{project}.jsonl"


def build_embedding_text(pivot: Dict[str, Any]) -> str:
    """
    Construit le texte qui sera transformé en vecteur (option B :
    titre + description + résumé des actions des étapes).

    On exclut volontairement `data` et `expected_result` du vecteur pour
    garder la requête focalisée sur le "scénario" du test, qui est ce
    qu'Agent 3 doit retrouver par similarité.
    """
    parts: List[str] = []

    title = (pivot.get("title") or "").strip()
    if title:
        parts.append(title)

    desc = (pivot.get("description") or "").strip()
    if desc:
        parts.append(desc)

    steps = pivot.get("steps") or []
    if steps:
        step_lines: List[str] = []
        for s in steps:
            idx = s.get("index")
            action = (s.get("action") or "").strip()
            if not action:
                continue
            # Une étape = 1 ligne dense ("1. ...")
            # On retire les éventuels "ETAPE :" / "ACTION(S) :" déjà présents.
            cleaned = action.replace("\n", " ").strip()
            prefix = f"{idx}. " if idx is not None else "- "
            step_lines.append(prefix + cleaned)
        if step_lines:
            parts.append("Étapes : " + " ".join(step_lines))

    text = "\n".join(parts).strip()
    if len(text) > MAX_EMBED_CHARS:
        text = text[:MAX_EMBED_CHARS]
    return text


def build_metadata(pivot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Construit la metadata Chroma. Chroma n'accepte que des scalaires
    (str/int/float/bool), donc on aplatit les listes en chaînes
    séparées par '|' pour conserver la possibilité de filtrer ensuite.
    Le pivot JSON complet est aussi stocké pour la ré-injection dans
    le prompt few-shot.
    """
    meta = pivot.get("metadata") or {}
    covered = pivot.get("covered_stories") or []

    def _join(values: Optional[List[Any]]) -> str:
        if not values:
            return ""
        return "|".join(str(v) for v in values if v is not None)

    return {
        "test_id": pivot.get("test_id") or "",
        "project": pivot.get("project") or "",
        "title": (pivot.get("title") or "")[:300],
        "module_path": (meta.get("module_path") or "")[:300],
        "module_root": meta.get("module_root") or "",
        "test_type": meta.get("test_type") or "",
        "priority": meta.get("priority") or "",
        "status": meta.get("status") or "",
        "steps_count": int(meta.get("steps_count") or 0),
        "epic_link": meta.get("epic_link") or "",
        "labels": _join(meta.get("labels")),
        "components": _join(meta.get("components")),
        "fix_versions": _join(meta.get("fix_versions")),
        "covered_stories": _join(covered),
        "has_covered_story": bool(covered),
        # On sérialise le pivot complet pour pouvoir le ré-injecter
        # tel quel dans le prompt few-shot, sans recharger le JSONL.
        "pivot_json": json.dumps(pivot, ensure_ascii=False),
    }


def iter_pivots(projects: Iterable[str]) -> Iterable[Dict[str, Any]]:
    for project in projects:
        path = _enriched_path(project)
        if not path.exists():
            print(f"  [SKIP] {path} introuvable", flush=True)
            continue
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def index_all(
    projects: List[str],
    batch_size: int,
    reset: bool,
) -> Dict[str, Any]:
    print(f"  Modèle d'embeddings : {EMBED_MODEL_NAME}", flush=True)
    model = SentenceTransformer(EMBED_MODEL_NAME)

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    if reset:
        existing = {c.name for c in client.list_collections()}
        if COLLECTION_NAME in existing:
            client.delete_collection(COLLECTION_NAME)
            print(f"  Collection '{COLLECTION_NAME}' supprimée (reset).", flush=True)

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    print(
        f"  Collection '{COLLECTION_NAME}' prête (count actuel = {collection.count()}).",
        flush=True,
    )

    # On rassemble par batch pour limiter les appels Chroma.
    ids_batch: List[str] = []
    docs_batch: List[str] = []
    metas_batch: List[Dict[str, Any]] = []

    total = 0
    indexed = 0
    skipped_empty = 0
    t0 = time.time()

    def _flush():
        nonlocal indexed
        if not ids_batch:
            return
        embeddings = model.encode(
            docs_batch,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        ).tolist()
        collection.upsert(
            ids=ids_batch,
            documents=docs_batch,
            metadatas=metas_batch,
            embeddings=embeddings,
        )
        indexed += len(ids_batch)
        ids_batch.clear()
        docs_batch.clear()
        metas_batch.clear()

    for pivot in iter_pivots(projects):
        total += 1
        text = build_embedding_text(pivot)
        if not text:
            skipped_empty += 1
            continue
        test_id = pivot.get("test_id")
        if not test_id:
            skipped_empty += 1
            continue
        ids_batch.append(test_id)
        docs_batch.append(text)
        metas_batch.append(build_metadata(pivot))

        if len(ids_batch) >= batch_size:
            _flush()
            if indexed % (batch_size * 5) == 0:
                elapsed = time.time() - t0
                rate = indexed / elapsed if elapsed > 0 else 0
                print(
                    f"  [{indexed} indexed] rate={rate:.1f}/s "
                    f"elapsed={elapsed:.0f}s",
                    flush=True,
                )

    _flush()

    elapsed = time.time() - t0
    final_count = collection.count()
    print("\n========== SUMMARY ==========", flush=True)
    print(f"  Pivots lus           : {total}", flush=True)
    print(f"  Indexés              : {indexed}", flush=True)
    print(f"  Skipped (texte vide) : {skipped_empty}", flush=True)
    print(f"  Collection count     : {final_count}", flush=True)
    print(f"  Durée                : {elapsed:.1f}s ({elapsed/60:.1f} min)", flush=True)

    return {
        "total": total,
        "indexed": indexed,
        "skipped_empty": skipped_empty,
        "collection_count": final_count,
        "duration_sec": elapsed,
    }


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--projects",
        nargs="+",
        default=DEFAULT_PROJECTS,
        help="Projets à indexer (défaut : %(default)s)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Nombre de tests par batch d'embedding (défaut : 64).",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help=f"Vide la collection '{COLLECTION_NAME}' avant indexation.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    index_all(
        projects=args.projects,
        batch_size=args.batch_size,
        reset=args.reset,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
