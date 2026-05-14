import json
from pathlib import Path
from statistics import mean
from typing import Any

from .judge_prompt import build_judge_system_prompt, build_judge_user_prompt
from app.services.llm_client import call_groq, call_groq_json_schema


def load_json(path: str) -> Any:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def safe_json_loads(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Réponse JSON invalide du juge LLM : {e}\nContenu reçu:\n{text}")


def get_judge_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "fidelity_score": {"type": "integer"},
            "completeness_score": {"type": "integer"},
            "coherence_score": {"type": "integer"},
            "summary": {"type": "string"},
            "final_score": {"type": "number"}
        },
        "required": [
            "fidelity_score",
            "completeness_score",
            "coherence_score",
            "summary",
            "final_score"
        ],
        "additionalProperties": False
    }

def get_verdict(final_score):
    if final_score >= 85:
        return "GOOD"
    elif final_score >= 70:
        return "PARTIAL"
    else:
        return "BAD"
    
def normalize_judge_result(raw: dict) -> dict:
    fidelity = int(raw.get("fidelity_score", 0))
    # Fallback: si le modèle retourne classification_score au lieu de completeness_score
    completeness = int(raw.get("completeness_score", raw.get("classification_score", 0)))
    coherence = int(raw.get("coherence_score", 0))

    final_score = round((fidelity + completeness + coherence) / 3, 2)

    has_critical_error = (
        fidelity < 70
        or coherence < 70
        or completeness < 70
    )
    verdict = get_verdict(final_score)

    return {
        "fidelity_score": fidelity,
        "completeness_score": completeness,
        "coherence_score": coherence,
        "final_score": float(raw.get("final_score", final_score)),
        "absence_critical_error": not has_critical_error,
        "verdict": verdict
    }


  
    
def judge_once(story: dict, analysis: dict, model_alias: str = "qwen3", max_retries: int = 3) -> dict:
    system_prompt = build_judge_system_prompt()
    user_prompt = build_judge_user_prompt(story, analysis)

    for attempt in range(max_retries):
        try:
            # GPT OSS 120B -> JSON schema
            if model_alias == "gptoss120b":
                raw_text = call_groq_json_schema(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema=get_judge_schema(),
                    model_alias=model_alias,
                    temperature=0.0,
                    max_tokens=1000,
                )
            else:
                # Qwen3 ou autre -> JSON object
                raw_text = call_groq(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model_alias=model_alias,
                    temperature=0.0,
                    max_tokens=1000,
                )

            raw_json = safe_json_loads(raw_text)
            return normalize_judge_result(raw_json)
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  [Retry {attempt + 1}/{max_retries}] Erreur juge : {type(e).__name__}")
            else:
                raise


def evaluate_dataset(
    input_json_path: str,
    output_json_path: str,
    model_alias: str = "qwen3",
    num_runs: int = 1
) -> dict:
    data = load_json(input_json_path)

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and "results" in data:
        items = data["results"]
    elif isinstance(data, dict) and "stories" in data:
        items = data["stories"]
    else:
        raise ValueError("Format JSON non supporté. Attendu : liste ou dict avec clé 'results' ou 'stories'.")

    # ── Reprise sur interruption ──
    evaluated = []
    already_done = set()
    output_path = Path(output_json_path)
    if output_path.exists():
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))
            evaluated = existing.get("results", [])
            already_done = {r["story"]["id"] for r in evaluated if "story" in r}
            print(f"[REPRISE] {len(already_done)} stories déjà jugées, on reprend à partir de la suivante.")
        except Exception:
            evaluated = []
            already_done = set()

    total_items = len(items)

    for idx, item in enumerate(items, start=1):
        if "story" not in item or "analysis" not in item:
            raise ValueError(f"Élément index {idx} invalide : il doit contenir 'story' et 'analysis'.")

        story = item["story"]
        analysis = item["analysis"]
        story_id = story.get("id", f"item_{idx}")

        # Skip les stories déjà jugées
        if story_id in already_done:
            print(f"[{idx}/{total_items}] {story_id} | DÉJÀ JUGÉ — skip")
            continue

        try:
            judge_result = judge_once(
                story=story,
                analysis=analysis,
                model_alias=model_alias
            )
        except Exception as e:
            print(f"[{idx}/{total_items}] {story_id} | ERREUR FATALE : {e}")
            _save_partial(output_json_path, evaluated, model_alias, num_runs)
            continue

        evaluated_item = {
            "story": story,
            "analysis": analysis,
            "judge": judge_result
        }
        evaluated.append(evaluated_item)

        print(
        f"[{idx}/{total_items}] {story_id} | "
        f"fidélité={judge_result['fidelity_score']} | "
        f"verdict={judge_result['verdict']} | "
        f"cohérence={judge_result['coherence_score']} | "
        f"complétude={judge_result['completeness_score']} | "
        f"absence_erreur_critique={'oui' if judge_result['absence_critical_error'] else 'non'}"
)

        # Sauvegarde incrémentale toutes les 5 stories
        if len(evaluated) % 5 == 0:
            _save_partial(output_json_path, evaluated, model_alias, num_runs)

    summary = build_summary(evaluated)

    output = {
        "meta": {
            "judge_model_alias": model_alias,
            "num_runs": num_runs,
            "count": len(evaluated)
        },
        "summary": summary,
        "results": evaluated
    }

    save_json(output_json_path, output)
    return output


def _save_partial(output_json_path, evaluated, model_alias, num_runs):
    """Sauvegarde intermédiaire pour ne pas perdre le travail."""
    summary = build_summary(evaluated)
    output = {
        "meta": {"judge_model_alias": model_alias, "num_runs": num_runs, "count": len(evaluated)},
        "summary": summary,
        "results": evaluated
    }
    save_json(output_json_path, output)


def build_summary(results: list[dict]) -> dict:
    if not results:
        return {
            "count": 0,
            "avg_fidelity_score": 0,
            "avg_coherence_score": 0,
            "avg_completeness_score": 0,
            "avg_final_score": 0,
            "stories_without_critical_error_count": 0,
            "stories_without_critical_error_percent": 0,
        }

    count = len(results)

    avg_fidelity = round(mean(r["judge"]["fidelity_score"] for r in results), 2)
    avg_coherence = round(mean(r["judge"]["coherence_score"] for r in results), 2)
    avg_completeness = round(mean(r["judge"]["completeness_score"] for r in results), 2)
    avg_final = round(mean(r["judge"]["final_score"] for r in results), 2)

    no_critical_count = sum(
        1 for r in results if r["judge"].get("absence_critical_error", False)
    )
    no_critical_percent = round((no_critical_count / count) * 100, 2)

    return {
        "count": count,
        "avg_fidelity_score": avg_fidelity,
        "avg_coherence_score": avg_coherence,
        "avg_completeness_score": avg_completeness,
        "avg_final_score": avg_final,
        "stories_without_critical_error_count": no_critical_count,
        "stories_without_critical_error_percent": no_critical_percent,
    }