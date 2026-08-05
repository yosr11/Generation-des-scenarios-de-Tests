"""Affiche la moyenne par métrique pour les fichiers d'évaluation.

Usage:
  python eval/DeepEval/print_metric_averages.py
"""
import json
from pathlib import Path
from statistics import mean

BASE = Path(__file__).resolve().parent
GEVAL_FILE = BASE / "geval_evaluation_results.json"
DETER_FILE = BASE / "evaluation_results.json"


def load_json(path: Path):
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def mean_or_none(values):
    return round(mean(values), 3) if values else None


def normalize_and_percent(val):
    # If val looks like 0-1, convert to 0-100
    if val is None:
        return None
    try:
        v = float(val)
    except Exception:
        return None
    if v <= 1.0:
        return round(v * 100, 2)
    return round(v, 2)


def print_geval_averages(data):
    print("\nGEval averages:")
    results = data.get("results", [])
    if not results:
        print("  (no GEval results)")
        return
    # collect metric names from first result
    metric_names = []
    first = results[0]
    for k in first.keys():
        if k == "story_id":
            continue
        metric_names.append(k)

    for name in metric_names:
        scores = [r.get(name, {}).get("score") for r in results if name in r and r.get(name) is not None]
        # filter None
        scores = [s for s in scores if s is not None]
        avg = mean_or_none(scores)
        avg_pct = normalize_and_percent(avg)
        print(f"  {name}: moyenne={'{:.3f}'.format(avg) if avg is not None else 'N/A'} -> {avg_pct if avg_pct is not None else 'N/A'} %")


def print_deterministic_averages(data):
    print("\nDeterministic runner averages:")
    results = data.get("results", [])
    if not results:
        print("  (no deterministic results)")
        return
    # agent keys
    agent_keys = ["agent1", "agent2", "agent3_qa_quality", "agent4", "agent5"]
    for key in agent_keys:
        scores = []
        for r in results:
            v = r.get(key)
            if not v:
                continue
            if isinstance(v, dict):
                s = v.get("score") or v.get("coverage_rate")
            else:
                s = None
            if s is not None:
                scores.append(s)
        avg = mean_or_none(scores)
        avg_pct = normalize_and_percent(avg)
        print(f"  {key}: moyenne={'{:.3f}'.format(avg) if avg is not None else 'N/A'} -> {avg_pct if avg_pct is not None else 'N/A'} %")


if __name__ == "__main__":
    geval = load_json(GEVAL_FILE)
    deter = load_json(DETER_FILE)

    if geval:
        print_geval_averages(geval)
    else:
        print("GEval file not found.")

    if deter:
        print_deterministic_averages(deter)
    else:
        print("Deterministic evaluation file not found.")
