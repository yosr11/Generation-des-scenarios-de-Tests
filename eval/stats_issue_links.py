"""
Stats rapides sur les types de liens (issue_links) présents dans les
fichiers enrichis. Aide à choisir quels types compter comme
"couverture de User Story" pour `covered_stories`.

Usage :
    python -m eval.stats_issue_links
    python -m eval.stats_issue_links --projects YOUQA
    python -m eval.stats_issue_links --top 30
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable, Optional

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "eval" / "data" / "legacy_tests"

DEFAULT_PROJECTS = ["YOUQA", "QAGT", "YTINMA", "HRAE2EQA", "PLD4UE2E"]

# Préfixes de projets que l'on considère comme "User Stories" (NUXEPM, YOU, etc.)
# Les liens vers d'autres tests (YOUQA-..., QAGT-..., HRAE2EQA-...) NE sont PAS
# des stories — on les sépare pour clarifier.
TEST_PROJECT_PREFIXES = {"YOUQA", "QAGT", "YTINMA", "HRAE2EQA", "PLD4UE2E"}


def _project_of(key: str) -> str:
    return key.split("-", 1)[0] if "-" in key else key


def _enriched_path(project: str) -> Path:
    enriched = DATA_DIR / f"{project}.enriched.jsonl"
    if enriched.exists():
        return enriched
    return DATA_DIR / f"{project}.jsonl"


def analyze(projects: Iterable[str], top: int) -> None:
    type_counter: Counter[str] = Counter()
    direction_counter: Counter[str] = Counter()
    type_target_kind: dict[str, Counter[str]] = {}
    # Échantillon : pour chaque type, garder 3 exemples (test_id, direction, target_key, target_summary)
    samples: dict[str, list[tuple[str, str, str, str]]] = {}

    total_tests = 0
    tests_with_links = 0
    tests_with_story_link = 0

    for project in projects:
        path = _enriched_path(project)
        if not path.exists():
            print(f"  [SKIP] {path} introuvable", flush=True)
            continue
        print(f"  Lecture {path}", flush=True)

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    pivot = json.loads(line)
                except json.JSONDecodeError:
                    continue
                total_tests += 1
                test_id = pivot.get("test_id", "?")
                meta = pivot.get("metadata") or {}
                links = meta.get("issue_links") or {}

                has_any = False
                has_story = False
                for direction_grp in ("outward", "inward"):
                    for lk in links.get(direction_grp, []):
                        has_any = True
                        t = lk.get("type") or ""
                        d = lk.get("direction") or ""
                        target_key = lk.get("key") or ""
                        target_proj = _project_of(target_key)
                        kind = (
                            "TEST" if target_proj in TEST_PROJECT_PREFIXES else "STORY"
                        )
                        if kind == "STORY":
                            has_story = True

                        type_counter[t] += 1
                        direction_counter[f"{t} / {d}"] += 1
                        type_target_kind.setdefault(t, Counter())[kind] += 1
                        if t not in samples:
                            samples[t] = []
                        if len(samples[t]) < 3:
                            samples[t].append(
                                (
                                    test_id,
                                    d,
                                    target_key,
                                    (lk.get("summary") or "")[:80],
                                ),
                            )

                if has_any:
                    tests_with_links += 1
                if has_story:
                    tests_with_story_link += 1

    print("\n========== GLOBAL ==========")
    print(f"  Tests analysés       : {total_tests}")
    print(
        f"  Tests avec >=1 lien  : {tests_with_links} "
        f"({100*tests_with_links/total_tests:.1f}%)"
    )
    print(
        f"  Tests reliés à STORY : {tests_with_story_link} "
        f"({100*tests_with_story_link/total_tests:.1f}%)"
    )

    print(f"\n========== TOP {top} TYPES (toutes directions) ==========")
    print(f"  {'TYPE':<25s} {'count':>7s}  {'-> STORY':>9s}  {'-> TEST':>9s}")
    for t, c in type_counter.most_common(top):
        kinds = type_target_kind.get(t, Counter())
        print(
            f"  {t:<25s} {c:>7d}  {kinds.get('STORY', 0):>9d}  {kinds.get('TEST', 0):>9d}"
        )

    print(f"\n========== TOP {top} (TYPE / DIRECTION) ==========")
    for td, c in direction_counter.most_common(top):
        print(f"  {td:<55s} {c:>7d}")

    print("\n========== EXEMPLES PAR TYPE ==========")
    for t in sorted(type_counter, key=lambda x: -type_counter[x])[:top]:
        print(f"\n  -- {t}  (total={type_counter[t]}) --")
        for tid, d, k, s in samples.get(t, []):
            print(f"     {tid}  --[{d}]-->  {k}    {s!r}")


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projects", nargs="+", default=DEFAULT_PROJECTS)
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args(list(argv) if argv is not None else None)
    analyze(args.projects, args.top)
    return 0


if __name__ == "__main__":
    sys.exit(main())
