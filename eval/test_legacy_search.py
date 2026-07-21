"""Petit script de test interactif pour la collection legacy_tests."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import chromadb  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

CHROMA_DIR = ROOT / "app" / "data" / "vector_store"
MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
OUT_LOG = ROOT / "eval" / "data" / "legacy_tests" / "_search_test.log"


def _log(msg: str, fh) -> None:
    print(msg, flush=True)
    fh.write(msg + "\n")
    fh.flush()


def main():
    queries = sys.argv[1:] or [
        "valider une demande de conge par le manager",
        "envoyer une question RH",
        "embauche d'un nouveau collaborateur",
    ]

    with OUT_LOG.open("w", encoding="utf-8") as fh:
        model = SentenceTransformer(MODEL)
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        col = client.get_collection("legacy_tests")
        _log(f"Collection count : {col.count()}\n", fh)

        for q in queries:
            _log(f"=== Q : {q!r} ===", fh)
            emb = model.encode([q], normalize_embeddings=True).tolist()
            res = col.query(query_embeddings=emb, n_results=5)
            for dist, meta in zip(res["distances"][0], res["metadatas"][0]):
                sim = 1 - dist
                _log(f"  [{sim:.3f}] {meta.get('project')} {meta.get('test_id')}", fh)
                _log(f"          {meta.get('title','')[:120]}", fh)
                mp = meta.get("module_path") or ""
                if mp:
                    _log(f"          module: {mp[:100]}", fh)
            _log("", fh)


if __name__ == "__main__":
    main()
