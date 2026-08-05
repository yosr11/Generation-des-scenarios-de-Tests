import json
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

from eval.DeepEval.data_preparation import load_eval_stories
from eval.DeepEval.metrics import build_metric_suite


def load_existing_results(output_json_path: Path) -> List[Dict[str, Any]]:
    if not output_json_path.exists():
        return []
    try:
        with output_json_path.open(encoding="utf-8") as handle:
            existing = json.load(handle)
        return existing.get("results", [])
    except (json.JSONDecodeError, KeyError):
        print(
            f"  [WARN] Fichier {output_json_path} illisible ou corrompu, on repart de zéro."
        )
        return []


def story_is_complete(story_result: Dict[str, Any]) -> bool:
    return all(
        key in story_result
        for key in ["agent1", "agent2", "agent3_qa_quality", "agent4", "agent5"]
    )


def save_progress(
    results: List[Dict[str, Any]],
    output_json_path: Path,
    input_json_path: str,
) -> None:
    summary = build_global_summary(results)
    output = {
        "meta": {"input_file": str(input_json_path), "case_count": len(results)},
        "summary": summary,
        "results": results,
    }
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    with output_json_path.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)


def run_evaluation(
    input_json_path: str | Path,
    output_json_path: str | Path,
    max_cases: int | None = None,
    force_restart: bool = False,
) -> Dict[str, Any]:
    input_json_path = Path(input_json_path)
    output_json_path = Path(output_json_path)

    stories = load_eval_stories(input_json_path)
    if max_cases is not None:
        stories = stories[:max_cases]

    results: List[Dict[str, Any]] = []
    already_done_ids: set = set()

    if not force_restart:
        existing_results = load_existing_results(output_json_path)
        for r in existing_results:
            if story_is_complete(r):
                results.append(r)
                already_done_ids.add(r["story_id"])

        if already_done_ids:
            print(
                f"[REPRISE] {len(already_done_ids)} story(ies) déjà évaluée(s), on les saute : "
                f"{sorted(already_done_ids)}"
            )

    stories_to_run = [
        s for s in stories if s.get("story_id", "unknown") not in already_done_ids
    ]

    if not stories_to_run:
        print("Toutes les stories demandées sont déjà évaluées. Rien à faire.")
        summary = build_global_summary(results)
        print_summary(results, summary)
        return {
            "meta": {"input_file": str(input_json_path), "case_count": len(results)},
            "summary": summary,
            "results": results,
        }

    metrics = build_metric_suite()

    for story in stories_to_run:
        story_id = story.get("story_id", "unknown")

        agent1_out = story.get("agent1", {}).get("output", {})
        agent2_out = story.get("agent2", {}).get("output", {})
        agent3_out = story.get("agent3", {}).get("output", {})
        agent4_input = story.get("agent4", {}).get("input", {})
        agent4_out = story.get("agent4", {}).get("output", {})
        agent5_out = story.get("agent5", {}).get("output", {})

        story_result: Dict[str, Any] = {"story_id": story_id}

        try:
            agent1_score = metrics["agent1"].score(agent1_out)
            agent1_score["score"] = round(agent1_score["score"] * 100, 1)

            agent2_score = metrics["agent2"].score(agent1_out, agent2_out)
            agent2_score["score"] = round(agent2_score["score"] * 100, 1)

            agent3_qa_quality_score = metrics["agent3"].qa_quality(agent3_out)
            agent3_qa_quality_score["score"] = round(agent3_qa_quality_score["score"] * 100, 1)

            agent3_coverage = metrics["agent3"].coverage_from_agent4(agent4_out)
            agent3_coverage["coverage_rate"] = round(
                agent3_coverage["coverage_rate"] * 100, 1
            )

            agent4_score = metrics["agent4"].score(agent4_input, agent4_out)
            agent4_score["score"] = round(agent4_score["score"] * 100, 1)

            agent5_score = metrics["agent5"].score(agent4_out, agent5_out)
            agent5_score["score"] = round(agent5_score["score"] * 100, 1)

            story_result.update(
                {
                    "agent1": agent1_score,
                    "agent2": agent2_score,
                    "agent3_qa_quality": agent3_qa_quality_score,
                    "agent3_coverage": agent3_coverage,
                    "agent4": agent4_score,
                    "agent5": agent5_score,
                }
            )
        except Exception as e:
            print(f"\n[ERREUR] Échec sur la story {story_id} : {e}")
            if len(story_result) > 1:
                results.append(story_result)
            save_progress(results, output_json_path, str(input_json_path))
            raise

        results.append(story_result)
        save_progress(results, output_json_path, str(input_json_path))

    summary = build_global_summary(results)

    output = {
        "meta": {"input_file": str(input_json_path), "case_count": len(results)},
        "summary": summary,
        "results": results,
    }

    print_summary(results, summary)
    return output


def build_global_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calcule des statistiques globales sur tout le run : moyennes par agent
    et les pires stories, pour suivre l'évolution du pipeline dans le temps."""
    agent_keys = ["agent1", "agent2", "agent3_qa_quality", "agent4", "agent5"]
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
            "taux_sous_0_7": (
                round(sum(1 for s in scores if s < 70) / len(scores), 2)
                if scores
                else None
            ),
            "pires_stories": worst,
        }

    coverages = [r["agent3_coverage"]["coverage_rate"] for r in results]
    summary["couverture_moyenne_tests"] = (
        round(mean(coverages), 3) if coverages else None
    )

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
        for agent_key in [
            "agent1",
            "agent2",
            "agent3_qa_quality",
            "agent4",
            "agent5",
        ]:
            data = r.get(agent_key, {})
            score = data.get("score")
            if score is not None:
                flag = "⚠️ " if score < 70 else "✅ "
                print(f"  {flag}{agent_key}: score={score}")
                for issue in data.get("issues", []):
                    print(f"      - [{issue['severity']}] {issue['message']}")
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    input_json = base_dir / "evalAgents.json"
    output_json = base_dir / "evaluation_results.json"
    try:
        run_evaluation(input_json, output_json, max_cases=None)
        print(f"Évaluation terminée : {output_json}")
    except Exception:
        print(
            "Le script s'est arrêté avant la fin. Relance-le pour reprendre là où il s'est arrêté."
        )
