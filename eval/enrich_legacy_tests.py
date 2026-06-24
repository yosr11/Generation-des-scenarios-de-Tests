"""
Enrichit les fichiers JSONL legacy déjà extraits avec les 2 champs manquants :

  - `module_root` recalculé localement (fix du bug du leading '/')
  - `covered_stories` + `metadata.issue_links` récupérés via UN SEUL appel HTTP
    par test (fields=issuelinks uniquement, donc très léger)

Le script :
  - lit chaque `eval/data/legacy_tests/{PROJECT}.jsonl`,
  - écrit le résultat dans `{PROJECT}.enriched.jsonl` (le fichier original
    n'est PAS modifié — sécurité),
  - reprenable via `--resume`,
  - log la progression toutes les 50 tests.

Usage :
    python -m eval.enrich_legacy_tests                  # tous les projets
    python -m eval.enrich_legacy_tests --projects YOUQA
    python -m eval.enrich_legacy_tests --resume
    python -m eval.enrich_legacy_tests --inplace        # remplace le .jsonl original
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Iterable, Optional, Set

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import requests  # noqa: E402

from app.services.jira_service import (  # noqa: E402
    DEFAULT_LEGACY_TEST_PROJECTS,
    JIRA_BASE_URL,
    _extract_covered_stories,
    _parse_issue_links,
    _parse_repo_path,
    _session,
)

DATA_DIR = ROOT / "eval" / "data" / "legacy_tests"


def _fix_module_root(pivot: dict) -> bool:
    """Recalcule module_root depuis module_path. Retourne True si changé."""
    meta = pivot.get("metadata") or {}
    path = meta.get("module_path")
    if not path:
        return False
    old_root = meta.get("module_root")
    new_root = _parse_repo_path(path)["root"]
    if new_root != old_root:
        meta["module_root"] = new_root
        pivot["metadata"] = meta
        return True
    return False


def _fetch_issuelinks(test_key: str, max_retries: int = 3, backoff: float = 2.0) -> dict:
    """
    Récupère UNIQUEMENT le champ issuelinks pour un test (appel léger).
    Retourne {"issuelinks": [...]} ou {"error": True, ...}.
    """
    url = f"{JIRA_BASE_URL}/rest/api/2/issue/{test_key}"
    for attempt in range(1, max_retries + 1):
        try:
            resp = _session.get(url, params={"fields": "issuelinks"}, timeout=20)
        except requests.RequestException as e:
            if attempt == max_retries:
                return {"error": True, "body": str(e)}
            time.sleep(backoff ** attempt)
            continue

        if resp.status_code == 200:
            data = resp.json() or {}
            return {"issuelinks": (data.get("fields") or {}).get("issuelinks") or []}

        if resp.status_code < 500:
            return {"error": True, "status_code": resp.status_code, "body": resp.text[:300]}

        if attempt == max_retries:
            return {"error": True, "status_code": resp.status_code, "body": resp.text[:300]}
        time.sleep(backoff ** attempt)
    return {"error": True, "body": "max retries"}


def enrich_pivot(pivot: dict) -> tuple[bool, Optional[str]]:
    """
    Enrichit un pivot in-place. Retourne (changed, error_msg).
    """
    changed = _fix_module_root(pivot)

    meta = pivot.get("metadata") or {}
    if "issue_links" in meta and "covered_stories" in pivot:
        # Déjà enrichi (cas du --resume)
        return changed, None

    test_id = pivot.get("test_id")
    if not test_id:
        return changed, "missing test_id"

    fetched = _fetch_issuelinks(test_id)
    if fetched.get("error"):
        return changed, fetched.get("body") or "fetch failed"

    links = _parse_issue_links(fetched.get("issuelinks"))
    meta["issue_links"] = links
    pivot["metadata"] = meta
    pivot["covered_stories"] = _extract_covered_stories(links)
    return True, None


def _load_already_done(path: Path) -> Set[str]:
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
                tid = obj.get("test_id")
                if tid:
                    done.add(tid)
            except json.JSONDecodeError:
                continue
    return done


def enrich_project(
    project_key: str,
    src_path: Path,
    dst_path: Path,
    err_path: Path,
    resume: bool,
) -> dict:
    if not src_path.exists():
        print(f"  [SKIP] {src_path} introuvable", flush=True)
        return {"project": project_key, "enriched": 0, "errors": 0, "skipped": True}

    print(f"\n=== {project_key} ===", flush=True)
    print(f"  Source : {src_path}", flush=True)
    print(f"  Output : {dst_path}", flush=True)

    done = _load_already_done(dst_path) if resume else set()
    if done:
        print(f"  Resume : {len(done)} déjà enrichis, skip.", flush=True)
    elif dst_path.exists():
        # Pas de resume : on repart à zéro
        dst_path.unlink()
    if err_path.exists() and not resume:
        err_path.unlink()

    # Compte total pour les logs
    with src_path.open("r", encoding="utf-8") as f:
        total = sum(1 for line in f if line.strip())

    print(f"  Total à traiter : {total}", flush=True)

    enriched = 0
    failed = 0
    t0 = time.time()

    with src_path.open("r", encoding="utf-8") as src, \
         dst_path.open("a", encoding="utf-8") as dst:

        for i, line in enumerate(src, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                pivot = json.loads(line)
            except json.JSONDecodeError:
                failed += 1
                with err_path.open("a", encoding="utf-8") as ef:
                    ef.write(json.dumps({"line": i, "error": "json decode"}) + "\n")
                continue

            test_id = pivot.get("test_id")
            if test_id and test_id in done:
                continue

            _, err = enrich_pivot(pivot)
            if err:
                failed += 1
                with err_path.open("a", encoding="utf-8") as ef:
                    ef.write(json.dumps(
                        {"test_id": test_id, "error": err}, ensure_ascii=False,
                    ) + "\n")
                # On écrit quand même la version partiellement enrichie
                # (module_root est déjà corrigé)

            dst.write(json.dumps(pivot, ensure_ascii=False) + "\n")
            dst.flush()
            enriched += 1

            if i % 50 == 0 or i == total:
                elapsed = time.time() - t0
                rate = enriched / elapsed if elapsed > 0 else 0
                eta = (total - i) / rate if rate > 0 else 0
                print(
                    f"  [{project_key} {i}/{total}] "
                    f"ok={enriched} ko={failed} "
                    f"rate={rate:.1f}/s eta={eta:.0f}s",
                    flush=True,
                )

    return {"project": project_key, "enriched": enriched, "errors": failed}


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--projects",
        nargs="+",
        default=DEFAULT_LEGACY_TEST_PROJECTS,
        help="Projets à enrichir (défaut : %(default)s)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Saute les test_id déjà présents dans le .enriched.jsonl.",
    )
    parser.add_argument(
        "--inplace",
        action="store_true",
        help="Remplace le .jsonl original par sa version enrichie après succès.",
    )
    parser.add_argument(
        "--data-dir",
        default=str(DATA_DIR),
        help=f"Dossier des JSONL (défaut : {DATA_DIR}).",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    data_dir = Path(args.data_dir)
    summary = []
    grand_t0 = time.time()

    for project in args.projects:
        src = data_dir / f"{project}.jsonl"
        dst = data_dir / f"{project}.enriched.jsonl"
        err = data_dir / f"{project}.enrich.errors.jsonl"
        result = enrich_project(project, src, dst, err, resume=args.resume)
        result["src"] = str(src)
        result["dst"] = str(dst)
        summary.append(result)

        if args.inplace and not result.get("skipped") and result["errors"] == 0:
            backup = data_dir / f"{project}.jsonl.bak"
            os.replace(src, backup)
            os.replace(dst, src)
            print(f"  [INPLACE] {src} remplacé (backup -> {backup})", flush=True)

    elapsed = time.time() - grand_t0
    print("\n========== SUMMARY ==========", flush=True)
    for s in summary:
        if s.get("skipped"):
            print(f"  {s['project']:10s}  SKIPPED ({s['src']} introuvable)", flush=True)
        else:
            print(
                f"  {s['project']:10s}  enriched={s['enriched']:>5d}  errors={s['errors']:>3d}",
                flush=True,
            )
    print(f"  Duration : {elapsed:.1f}s ({elapsed/60:.1f} min)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
