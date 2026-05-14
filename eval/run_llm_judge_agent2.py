import argparse
from .judge_runner_agent2 import evaluate_dataset


def main():
    parser = argparse.ArgumentParser(description="Évaluation LLM-as-Judge des tests manuels (Agent 2)")
    parser.add_argument("--stories", required=True, help="Fichier contenant stories + analyses (ex: agent1 results)")
    parser.add_argument("--tests", required=True, help="Fichier contenant les tests générés par l'Agent 2")
    parser.add_argument("--output", required=True, help="Chemin du JSON de sortie")
    parser.add_argument("--model", default="llama4", help="Alias du modèle juge (ex: llama4, gptoss120b)")
    parser.add_argument("--runs", type=int, default=1, help="Nombre de runs par story")

    args = parser.parse_args()

    result = evaluate_dataset(
        output_json_path=args.output,
        model_alias=args.model,
        num_runs=args.runs,
        stories_json_path=args.stories,
        tests_json_path=args.tests,
    )

    print("\n=== SUMMARY AGENT 2 (Tests Manuels) ===")
    print(f"count: {result['summary']['count']}")
    print(f"avg_fidelity_score: {result['summary']['avg_fidelity_score']}")
    print(f"avg_coverage_score: {result['summary']['avg_coverage_score']}")
    print(f"avg_writing_quality_score: {result['summary']['avg_writing_quality_score']}")
    print(f"avg_structure_score: {result['summary']['avg_structure_score']}")
    print(f"avg_relevance_score: {result['summary']['avg_relevance_score']}")
    print(f"avg_final_score: {result['summary']['avg_final_score']}")
    print(f"stories_without_critical_error_count: {result['summary']['stories_without_critical_error_count']}")
    print(f"stories_without_critical_error_percent: {result['summary']['stories_without_critical_error_percent']}")


if __name__ == "__main__":
    main()
