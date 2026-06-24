"""
Extraction bulk des tests Xray "legacy" au format pivot.

Itère projet par projet, récupère chaque test via l'API Jira/Xray
(en réutilisant `get_legacy_test_pivot()`), et écrit le résultat en
JSONL incrémental — donc reprenable si la machine plante en cours.

Usage :
    python -m eval.extract_legacy_tests                 # tous les projets par défaut
    python -m eval.extract_legacy_tests --projects YOUQA QAGT
    python -m eval.extract_legacy_tests --limit 50      # limite par projet (debug)
    python -m eval.extract_legacy_tests --no-filter     # désactive "Test Type" = Manual
    python -m eval.extract_legacy_tests --resume        # saute les test_id déjà présents
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Iterable, Optional, Set

# Permettre l'exécution `python eval/extract_legacy_tests.py` (sans -m)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.jira_service import (  # noqa: E402
    DEFAULT_LEGACY_TEST_PROJECTS,
    get_legacy_test_pivot,
    list_project_legacy_tests,
)

OUTPUT_DIR = ROOT / "eval" / "data" / "legacy_tests"


def _load_already_done(path: Path) -> Set[str]:
    """Lit le JSONL existant et retourne l'ensemble des test_id déjà extraits."""
    done: Set[str] = set()
    if not path.exists():
        return done
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            tid = obj.get("test_id")
            if tid:
                done.add(tid)
    return done


def _append_jsonl(path: Path, obj: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _fetch_with_retry(test_key: str, max_retries: int = 3, backoff: float = 2.0) -> dict:
    """Appel `get_legacy_test_pivot` avec retry exponentiel sur erreurs serveur/réseau."""
    last: dict = {}
    for attempt in range(1, max_retries + 1):
        try:
            pivot = get_legacy_test_pivot(test_key)
        except Exception as e:  # noqa: BLE001
            pivot = {"test_id": test_key, "error": True, "body": f"exception: {e}"}

        if not pivot.get("error"):
            return pivot

        last = pivot
        status = pivot.get("status_code", 0)
        # On ne retry que sur 5xx ou erreurs réseau (status=0)
        if status and status < 500:
            return pivot
        if attempt < max_retries:
            time.sleep(backoff ** attempt)
    return last


def extract_project(
    project_key: str,
    output_path: Path,
    error_path: Path,
    limit: Optional[int],
    apply_default_filter: bool,
    extra_jql: str,
    resume: bool,
) -> dict:
    """Extrait tous les tests d'un projet vers `output_path` (JSONL append)."""
    print(f"\n=== {project_key} ===", flush=True)

    listing = list_project_legacy_tests(
        project_key=project_key,
        extra_jql=extra_jql,
        max_results=limit,
        apply_default_filter=apply_default_filter,
    )
    if listing.get("error"):
        print(f"  [ERROR] listing failed: {listing}", flush=True)
        return {"project": project_key, "extracted": 0, "errors": 1}

    tests = listing.get("tests", [])
    total = listing.get("total")
    print(f"  JQL    : {listing.get('jql')}", flush=True)
    print(f"  Total  : {total}  (à traiter : {len(tests)})", flush=True)

    done: Set[str] = _load_already_done(output_path) if resume else set()
    if done:
        print(f"  Resume : {len(done)} déjà présents, skip.", flush=True)

    extracted = 0
    failed = 0
    t0 = time.time()

    for i, t in enumerate(tests, start=1):
        key = t.get("key")
        if not key:
            continue
        if key in done:
            continue

        pivot = _fetch_with_retry(key)

        if pivot.get("error"):
            failed += 1
            _append_jsonl(
                error_path,
                {
                    "project": project_key,
                    "test_id": key,
                    "status_code": pivot.get("status_code"),
                    "body": (pivot.get("body") or "")[:300],
                },
            )
        else:
            _append_jsonl(output_path, pivot)
            extracted += 1

        if i % 25 == 0 or i == len(tests):
            elapsed = time.time() - t0
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(tests) - i) / rate if rate > 0 else 0
            print(
                f"  [{project_key} {i}/{len(tests)}] "
                f"ok={extracted} ko={failed} "
                f"rate={rate:.1f}/s eta={eta:.0f}s",
                flush=True,
            )

    return {"project": project_key, "extracted": extracted, "errors": failed}


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--projects",
        nargs="+",
        default=DEFAULT_LEGACY_TEST_PROJECTS,
        help="Liste des project keys à extraire (défaut : %(default)s)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limite le nombre de tests par projet (utile en debug).",
    )
    parser.add_argument(
        "--no-filter",
        action="store_true",
        help='Désactive le filtre par défaut `"Test Type" = Manual`.',
    )
    parser.add_argument(
        "--extra-jql",
        default="",
        help="JQL supplémentaire (ex: 'status != Obsolete').",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Saute les test_id déjà présents dans le JSONL de sortie.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help=f"Dossier de sortie (défaut : {OUTPUT_DIR}).",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = []
    grand_t0 = time.time()

    for project in args.projects:
        output_path = out_dir / f"{project}.jsonl"
        error_path = out_dir / f"{project}.errors.jsonl"
        result = extract_project(
            project_key=project,
            output_path=output_path,
            error_path=error_path,
            limit=args.limit,
            apply_default_filter=not args.no_filter,
            extra_jql=args.extra_jql,
            resume=args.resume,
        )
        result["output"] = str(output_path)
        summary.append(result)

    total_extracted = sum(s["extracted"] for s in summary)
    total_errors = sum(s["errors"] for s in summary)
    elapsed = time.time() - grand_t0

    print("\n========== SUMMARY ==========", flush=True)
    for s in summary:
        print(
            f"  {s['project']:10s}  extracted={s['extracted']:>5d}  "
            f"errors={s['errors']:>3d}  -> {s['output']}",
            flush=True,
        )
    print(f"  TOTAL    extracted={total_extracted}  errors={total_errors}", flush=True)
    print(f"  Duration : {elapsed:.1f}s ({elapsed/60:.1f} min)", flush=True)

    summary_path = out_dir / "summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "projects": summary,
                "total_extracted": total_extracted,
                "total_errors": total_errors,
                "duration_sec": elapsed,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"  Summary written to {summary_path}", flush=True)

    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
