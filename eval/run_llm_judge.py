import argparse
from unittest import result
from .judge_runner import evaluate_dataset


def main():
    parser = argparse.ArgumentParser(description="Évaluation LLM-as-Judge sur fichier JSON (batch)")
    parser.add_argument("--input", required=True, help="Chemin du JSON d'entrée")
    parser.add_argument("--output", required=True, help="Chemin du JSON de sortie")
    parser.add_argument("--model", default="qwen3",
                        help="Alias du modèle juge (Groq: qwen3, gptoss120b, llama4 | GitHub Models: gpt-4.1, gpt-4.1-mini, gpt-4o)")
    parser.add_argument("--runs", type=int, default=1, help="Nombre de runs par story")

    args = parser.parse_args()

    result = evaluate_dataset(
        input_json_path=args.input,
        output_json_path=args.output,
        model_alias=args.model,
        num_runs=args.runs
    )

    print("\n=== SUMMARY ===")
    print(f"count: {result['summary']['count']}")
    print(f"avg_fidelity_score: {result['summary']['avg_fidelity_score']}")
    print(f"avg_coherence_score: {result['summary']['avg_coherence_score']}")
    print(f"avg_completeness_score: {result['summary']['avg_completeness_score']}")
    print(f"avg_final_score: {result['summary']['avg_final_score']}")
    print(f"stories_without_critical_error_count: {result['summary']['stories_without_critical_error_count']}")
    print(f"stories_without_critical_error_percent: {result['summary']['stories_without_critical_error_percent']}")


if __name__ == "__main__":
    main()