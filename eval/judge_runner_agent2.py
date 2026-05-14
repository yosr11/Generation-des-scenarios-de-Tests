import json
from pathlib import Path
from statistics import mean
from typing import Any

from .judge_prompt_agent2 import build_agent2_judge_system_prompt, build_agent2_judge_user_prompt
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
            "coverage_score": {"type": "integer"},
            "writing_quality_score": {"type": "integer"},
            "structure_score": {"type": "integer"},
            "relevance_score": {"type": "integer"},
            "summary": {"type": "string"},
            "final_score": {"type": "number"}
        },
        "required": [
            "fidelity_score",
            "coverage_score",
            "writing_quality_score",
            "structure_score",
            "relevance_score",
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
    coverage = int(raw.get("coverage_score", 0))
    writing = int(raw.get("writing_quality_score", 0))
    structure = int(raw.get("structure_score", 0))
    relevance = int(raw.get("relevance_score", 0))

    final_score = round((fidelity + coverage + writing + structure + relevance) / 5, 2)

    has_critical_error = (
        fidelity < 70
        or coverage < 70
        or writing < 70
    )
    verdict = get_verdict(final_score)

    return {
        "fidelity_score": fidelity,
        "coverage_score": coverage,
        "writing_quality_score": writing,
        "structure_score": structure,
        "relevance_score": relevance,
        "final_score": float(raw.get("final_score", final_score)),
        "absence_critical_error": not has_critical_error,
        "verdict": verdict
    }


def judge_once(story: dict, analysis: dict, tests: list, model_alias: str = "qwen3", max_retries: int = 3) -> dict:
    system_prompt = build_agent2_judge_system_prompt()
    user_prompt = build_agent2_judge_user_prompt(story, analysis, tests)

    for attempt in range(max_retries):
        try:
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


def _load_items_separate(stories_path: str, tests_path: str) -> list:
    """
    Charge stories+analyses depuis un fichier et tests depuis un autre,
    puis fusionne par story_id.
    """
    stories_data = load_json(stories_path)
    tests_data = load_json(tests_path)

    # Extraire les items story+analysis
    if isinstance(stories_data, dict) and "results" in stories_data:
        story_items = stories_data["results"]
    elif isinstance(stories_data, list):
        story_items = stories_data
    else:
        raise ValueError("Format stories JSON non supporté.")

    # Construire un index story_id → {story, analysis}
    story_index = {}
    for item in story_items:
        story = item.get("story", {})
        sid = story.get("id", "")
        if sid:
            story_index[sid] = {
                "story": story,
                "analysis": item.get("analysis", {}),
            }

    # Extraire les tests
    if isinstance(tests_data, dict) and "results" in tests_data:
        test_items = tests_data["results"]
    elif isinstance(tests_data, list):
        test_items = tests_data
    else:
        raise ValueError("Format tests JSON non supporté.")

    # Fusionner : chaque test_item doit avoir story_id pour matcher
    items = []
    for t_item in test_items:
        # Trouver le story_id dans les tests
        sid = t_item.get("story_id", "")
        if not sid:
            # Chercher dans les tests individuels
            tests_list = t_item.get("tests", [])
            if tests_list and isinstance(tests_list, list):
                sid = tests_list[0].get("story_id", "")
            if not sid:
                sid = t_item.get("story", {}).get("id", "")

        if sid not in story_index:
            print(f"  [WARN] Story {sid} non trouvée dans le fichier stories — ignorée")
            continue

        matched = story_index[sid]
        # Les tests peuvent être dans t_item["tests"]["tests"] (ManualTestGenerationResult)
        # ou directement dans t_item["tests"] (liste)
        raw_tests = t_item.get("tests", [])
        if isinstance(raw_tests, dict):
            tests = raw_tests.get("tests", [])
        else:
            tests = raw_tests

        items.append({
            "story": matched["story"],
            "analysis": matched["analysis"],
            "tests": tests,
        })

    print(f"[MERGE] {len(items)} stories fusionnées (stories: {len(story_index)}, tests: {len(test_items)})")
    return items


def evaluate_dataset(
    output_json_path: str,
    model_alias: str = "qwen3",
    num_runs: int = 1,
    stories_json_path: str = None,
    tests_json_path: str = None,
) -> dict:
    items = _load_items_separate(stories_json_path, tests_json_path)

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
        if "story" not in item or "analysis" not in item or "tests" not in item:
            raise ValueError(f"Élément index {idx} invalide : il doit contenir 'story', 'analysis' et 'tests'.")

        story = item["story"]
        analysis = item["analysis"]
        tests = item["tests"]
        story_id = story.get("id", f"item_{idx}")

        if story_id in already_done:
            print(f"[{idx}/{total_items}] {story_id} | DÉJÀ JUGÉ — skip")
            continue

        try:
            judge_result = judge_once(
                story=story,
                analysis=analysis,
                tests=tests,
                model_alias=model_alias
            )
        except Exception as e:
            print(f"[{idx}/{total_items}] {story_id} | ERREUR FATALE : {e}")
            _save_partial(output_json_path, evaluated, model_alias, num_runs)
            continue

        evaluated_item = {
            "story": story,
            "analysis": analysis,
            "tests": tests,
            "judge": judge_result
        }
        evaluated.append(evaluated_item)

        print(
            f"[{idx}/{total_items}] {story_id} | "
            f"fidélité={judge_result['fidelity_score']} | "
            f"couverture={judge_result['coverage_score']} | "
            f"rédaction={judge_result['writing_quality_score']} | "
            f"structure={judge_result['structure_score']} | "
            f"pertinence={judge_result['relevance_score']} | "
            f"verdict={judge_result['verdict']}"
        )

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
            "avg_coverage_score": 0,
            "avg_writing_quality_score": 0,
            "avg_structure_score": 0,
            "avg_relevance_score": 0,
            "avg_final_score": 0,
            "stories_without_critical_error_count": 0,
            "stories_without_critical_error_percent": 0,
        }

    count = len(results)

    avg_fidelity = round(mean(r["judge"]["fidelity_score"] for r in results), 2)
    avg_coverage = round(mean(r["judge"]["coverage_score"] for r in results), 2)
    avg_writing = round(mean(r["judge"]["writing_quality_score"] for r in results), 2)
    avg_structure = round(mean(r["judge"]["structure_score"] for r in results), 2)
    avg_relevance = round(mean(r["judge"]["relevance_score"] for r in results), 2)
    avg_final = round(mean(r["judge"]["final_score"] for r in results), 2)

    no_critical_count = sum(
        1 for r in results if r["judge"].get("absence_critical_error", False)
    )
    no_critical_percent = round((no_critical_count / count) * 100, 2)

    return {
        "count": count,
        "avg_fidelity_score": avg_fidelity,
        "avg_coverage_score": avg_coverage,
        "avg_writing_quality_score": avg_writing,
        "avg_structure_score": avg_structure,
        "avg_relevance_score": avg_relevance,
        "avg_final_score": avg_final,
        "stories_without_critical_error_count": no_critical_count,
        "stories_without_critical_error_percent": no_critical_percent,
    }
