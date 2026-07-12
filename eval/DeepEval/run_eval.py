import json
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

from eval.DeepEval.data_preparation import load_eval_stories
from eval.DeepEval.metrics import build_metric_suite


def run_evaluation(
    input_json_path: str | Path,
    output_json_path: str | Path,
    max_cases: int | None = None,
) -> Dict[str, Any]:
    stories = load_eval_stories(input_json_path)
    if max_cases is not None:
        stories = stories[:max_cases]

    metrics = build_metric_suite()
    results: List[Dict[str, Any]] = []

    for story in stories:
        story_id = story.get("story_id", "unknown")

        agent1_out = story.get("agent1", {}).get("output", {})
        agent15_out = story.get("agent1_5", {}).get("output", {})
        agent2_out = story.get("agent2", {}).get("output", {})
        agent3_input = story.get("agent3", {}).get("input", {})
        agent3_out = story.get("agent3", {}).get("output", {})
        agent5_out = story.get("agent5", {}).get("output", {})

        results.append({
            "story_id": story_id,
            "agent1": metrics["agent1"].score(agent1_out),
            "agent1_5": metrics["agent1_5"].score(agent1_out, agent15_out),
            "agent2_qa_quality": metrics["agent2"].qa_quality(agent2_out),
            "agent2_coverage": metrics["agent2"].coverage_from_agent3(agent3_out),
            "agent3": metrics["agent3"].score(agent3_input, agent3_out),
            "agent5": metrics["agent5"].score(agent3_out, agent5_out),
        })

    summary = build_global_summary(results)

    output = {
        "meta": {"input_file": str(input_json_path), "case_count": len(results)},
        "summary": summary,
        "results": results,
    }

    output_path = Path(output_json_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)

    print_summary(results, summary)
    return output


def build_global_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calcule des statistiques globales sur tout le run : moyennes par agent
    et les pires stories, pour suivre l'évolution du pipeline dans le temps."""
    agent_keys = ["agent1", "agent1_5", "agent2_qa_quality", "agent3", "agent5"]
    summary: Dict[str, Any] = {}

    for key in agent_keys:
        scores = [r[key]["score"] for r in results if key in r]
        worst = sorted(
            [(r["story_id"], r[key]["score"]) for r in results if key in r],
            key=lambda x: x[1],
        )[:3]
        summary[key] = {
            "score_moyen": round(mean(scores), 3) if scores else None,
            "score_min": round(min(scores), 3) if scores else None,
            "score_max": round(max(scores), 3) if scores else None,
            "taux_sous_0_7": round(sum(1 for s in scores if s < 0.7) / len(scores), 2) if scores else None,
            "pires_stories": worst,
        }

    coverages = [r["agent2_coverage"]["coverage_rate"] for r in results]
    summary["couverture_moyenne_tests"] = round(mean(coverages), 3) if coverages else None

    return summary


def print_summary(results: List[Dict[str, Any]], summary: Dict[str, Any]) -> None:
    print(f"\n{'='*70}")
    print(f"VUE D'ENSEMBLE — {len(results)} stories évaluées")
    print(f"{'='*70}")
    for agent_key, stats in summary.items():
        if not isinstance(stats, dict):
            continue
        print(f"\n{agent_key}:")
        print(f"  score moyen  : {stats['score_moyen']}")
        print(f"  score min/max: {stats['score_min']} / {stats['score_max']}")
        print(f"  % sous 0.7   : {stats['taux_sous_0_7']}")
        print(f"  pires stories: {stats['pires_stories']}")

    print(f"\n{'='*70}")
    print("DÉTAIL PAR STORY")
    print(f"{'='*70}")
    for r in results:
        print(f"\n[{r['story_id']}]")
        for agent_key in ["agent1", "agent1_5", "agent2_qa_quality", "agent3", "agent5"]:
            data = r.get(agent_key, {})
            score = data.get("score")
            if score is not None:
                flag = "⚠️ " if score < 0.7 else "✅ "
                print(f"  {flag}{agent_key}: score={score}")
                for issue in data.get("issues", []):
                    print(f"      - [{issue['severity']}] {issue['message']}")
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    input_json = base_dir / "evalAgents.json"
    output_json = base_dir / "evaluation_results.json"
    run_evaluation(input_json, output_json, max_cases=None)
    print(f"Évaluation terminée : {output_json}")