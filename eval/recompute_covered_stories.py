"""
Recalcule `covered_stories` dans les fichiers `.enriched.jsonl` existants
à partir du champ `metadata.issue_links` déjà présent.

Aucun appel HTTP : on relit juste les fichiers, on applique la nouvelle
règle (`_extract_covered_stories`), on réécrit le fichier en place.

Usage :
    python -m eval.recompute_covered_stories
    python -m eval.recompute_covered_stories --projects YOUQA QAGT
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Iterable, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.jira_service import (  # noqa: E402
    DEFAULT_LEGACY_TEST_PROJECTS,
    _extract_covered_stories,
)

DATA_DIR = ROOT / "eval" / "data" / "legacy_tests"


def recompute_file(path: Path) -> dict:
    """Réécrit `path` avec covered_stories recalculé. Retourne stats."""
    if not path.exists():
        return {"path": str(path), "skipped": True, "reason": "introuvable"}

    total = 0
    changed = 0
    with_story = 0
    no_links = 0

    tmp_fd, tmp_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent),
    )
    tmp_path = Path(tmp_name)

    try:
        with path.open("r", encoding="utf-8") as src, \
             tmp_path.open("w", encoding="utf-8") as dst:
            for line in src:
                line = line.strip()
                if not line:
                    continue
                pivot = json.loads(line)
                total += 1

                links = (pivot.get("metadata") or {}).get("issue_links") or {}
                if not links.get("outward") and not links.get("inward"):
                    no_links += 1

                new_covered = _extract_covered_stories(links)
                old_covered = pivot.get("covered_stories") or []
                if new_covered != old_covered:
                    changed += 1
                pivot["covered_stories"] = new_covered
                if new_covered:
                    with_story += 1

                dst.write(json.dumps(pivot, ensure_ascii=False) + "\n")
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    finally:
        # On ferme le descripteur (mkstemp en ouvre un)
        import os
        os.close(tmp_fd)

    # Remplacement atomique
    tmp_path.replace(path)

    return {
        "path": str(path),
        "total": total,
        "changed": changed,
        "with_story": with_story,
        "no_links": no_links,
    }


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--projects",
        nargs="+",
        default=DEFAULT_LEGACY_TEST_PROJECTS,
        help="Projets à traiter (défaut : %(default)s)",
    )
    parser.add_argument(
        "--data-dir",
        default=str(DATA_DIR),
        help=f"Dossier des JSONL (défaut : {DATA_DIR}).",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    data_dir = Path(args.data_dir)
    results = []
    for project in args.projects:
        # On prend .enriched.jsonl en priorité, sinon .jsonl
        for name in (f"{project}.enriched.jsonl", f"{project}.jsonl"):
            path = data_dir / name
            if path.exists():
                print(f"\n=== {project} ({name}) ===", flush=True)
                res = recompute_file(path)
                results.append({"project": project, **res})
                if not res.get("skipped"):
                    pct = 100 * res["with_story"] / res["total"] if res["total"] else 0
                    print(
                        f"  total={res['total']}  "
                        f"changed={res['changed']}  "
                        f"with_story={res['with_story']} ({pct:.1f}%)  "
                        f"no_links={res['no_links']}",
                        flush=True,
                    )
                break
        else:
            print(f"\n=== {project} : aucun fichier trouvé, SKIP ===", flush=True)

    print("\n========== SUMMARY ==========", flush=True)
    for r in results:
        if r.get("skipped"):
            continue
        pct = 100 * r["with_story"] / r["total"] if r["total"] else 0
        print(
            f"  {r['project']:10s}  total={r['total']:>5d}  "
            f"with_story={r['with_story']:>5d} ({pct:5.1f}%)  "
            f"changed={r['changed']:>5d}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
