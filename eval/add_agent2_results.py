# eval/add_agent2_results.py
"""
Ajoute de nouveaux résultats Agent 2 dans agent2_output.json.

Usage :
    py eval/add_agent2_results.py --input new_results.json
    py eval/add_agent2_results.py --input new_results.json --output eval/agent2_output.json

Le fichier new_results.json peut contenir :
  - Une liste d'objets (chaque objet = 1 story)
  - Un objet avec une clé "results" contenant une liste
  - Un seul objet (1 story)

Chaque objet peut avoir l'un de ces formats :

FORMAT A (standard - déjà structuré) :
{
  "story_id": "...",
  "story_summary": "...",
  "story_type": "...",
  "analysis": { ... },
  "tests": { ... }
}

FORMAT B (pipeline brut - story + analysis séparés) :
{
  "story": { "id": "...", "summary": "...", ... },
  "analysis": { "story_type": "...", ... },
  "tests": { "tests": [...], ... }
}

FORMAT C (2 fichiers séparés) :
    py eval/add_agent2_results.py --analyses agent1_results.json --tests agent2_raw.json
"""

import json
import argparse
import sys
from pathlib import Path


AGENT2_OUTPUT = Path(__file__).parent / "agent2_output.json"

STANDARD_KEYS = ["story_id", "story_summary", "story_type", "analysis", "tests"]


def load_json(path: str) -> any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: any):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_analysis(analysis: dict) -> dict:
    """Normalise un objet analysis au format standard."""
    return {
        "id": analysis.get("id"),
        "story_id": analysis.get("story_id", ""),
        "model": analysis.get("model", "llama4"),
        "story_type": analysis.get("story_type", ""),
        "actors": analysis.get("actors", []),
        "actions": analysis.get("actions", []),
        "business_rules": analysis.get("business_rules", []),
        "technical_scope": analysis.get("technical_scope", []),
        "testable_points": analysis.get("testable_points", []),
        "acceptance_criteria_explicit": analysis.get("acceptance_criteria_explicit", []),
        "acceptance_criteria_inferred": analysis.get("acceptance_criteria_inferred", []),
        "clarification_questions": analysis.get("clarification_questions", []),
        "analysis_reason": analysis.get("analysis_reason", []),
        "created_at": analysis.get("created_at", ""),
    }


def normalize_tests(tests_data: dict) -> dict:
    """Normalise un objet tests au format standard."""
    if isinstance(tests_data, list):
        # C'est directement une liste de tests
        return {
            "story_id": tests_data[0].get("story_id", "") if tests_data else "",
            "recommended_test_strategy": "manual",
            "generation_status": "generated",
            "message": "",
            "tests": tests_data,
            "notes": [],
        }
    return {
        "story_id": tests_data.get("story_id", ""),
        "recommended_test_strategy": tests_data.get("recommended_test_strategy", "manual"),
        "generation_status": tests_data.get("generation_status", "generated"),
        "message": tests_data.get("message", ""),
        "tests": tests_data.get("tests", []),
        "notes": tests_data.get("notes", []),
    }


def normalize_entry(raw: dict) -> dict:
    """Convertit n'importe quel format en format standard."""

    # FORMAT A : déjà standard
    if all(k in raw for k in ["story_id", "analysis", "tests"]):
        return {
            "story_id": raw["story_id"],
            "story_summary": raw.get("story_summary", ""),
            "story_type": raw.get("story_type", raw.get("analysis", {}).get("story_type", "")),
            "analysis": normalize_analysis(raw["analysis"]),
            "tests": normalize_tests(raw["tests"]),
        }

    # FORMAT B : story + analysis + tests (pipeline brut)
    if "story" in raw and "analysis" in raw:
        story = raw["story"]
        analysis = raw["analysis"]
        tests_data = raw.get("tests", {"tests": [], "generation_status": "generated"})
        story_id = story.get("id", analysis.get("story_id", ""))

        return {
            "story_id": story_id,
            "story_summary": story.get("summary", ""),
            "story_type": analysis.get("story_type", ""),
            "analysis": normalize_analysis({**analysis, "story_id": story_id}),
            "tests": normalize_tests({**tests_data, "story_id": story_id} if isinstance(tests_data, dict) else tests_data),
        }

    raise ValueError(f"Format non reconnu. Clés trouvées : {list(raw.keys())}")


def extract_items(data) -> list:
    """Extrait la liste d'items d'un fichier JSON quel que soit le format."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ["results", "stories", "items"]:
            if key in data:
                return data[key]
        # Objet unique
        return [data]
    raise ValueError("Format JSON non supporté")


def merge_from_two_files(analyses_path: str, tests_path: str) -> list:
    """Fusionne un fichier d'analyses et un fichier de tests par story_id."""
    analyses_data = load_json(analyses_path)
    tests_data = load_json(tests_path)

    analyses_items = extract_items(analyses_data)
    tests_items = extract_items(tests_data)

    # Index analyses par story_id
    analysis_index = {}
    for item in analyses_items:
        if "story" in item:
            sid = item["story"].get("id", "")
            analysis_index[sid] = {
                "story": item["story"],
                "analysis": item.get("analysis", {}),
            }
        elif "story_id" in item:
            sid = item["story_id"]
            analysis_index[sid] = {"story": {}, "analysis": item}

    # Index tests par story_id
    tests_index = {}
    for item in tests_items:
        sid = item.get("story_id", "")
        if not sid and "tests" in item and isinstance(item["tests"], list) and item["tests"]:
            sid = item["tests"][0].get("story_id", "")
        tests_index[sid] = item

    # Fusionner
    merged = []
    for sid in analysis_index:
        entry = {
            **analysis_index[sid],
            "tests": tests_index.get(sid, {"tests": [], "generation_status": "not_found"}),
        }
        merged.append(normalize_entry(entry))

    return merged


def main():
    parser = argparse.ArgumentParser(description="Ajouter des résultats Agent 2")
    parser.add_argument("--input", help="Fichier JSON avec les nouveaux résultats")
    parser.add_argument("--analyses", help="Fichier analyses (format pipeline)")
    parser.add_argument("--tests", help="Fichier tests (format pipeline)")
    parser.add_argument("--output", default=str(AGENT2_OUTPUT), help="Fichier de sortie")
    parser.add_argument("--dry-run", action="store_true", help="Afficher sans sauvegarder")
    args = parser.parse_args()

    if not args.input and not (args.analyses and args.tests):
        parser.error("Fournir --input OU (--analyses + --tests)")

    # Charger fichier existant
    output_path = Path(args.output)
    if output_path.exists():
        existing = load_json(str(output_path))
    else:
        existing = {
            "epic_key": "",
            "analysis_model": "llama4",
            "generation_model": "qwen3",
            "total_stories": 0,
            "generated": 0,
            "skipped": 0,
            "failed": 0,
            "results": [],
            "skipped_details": [],
        }

    existing_ids = {r["story_id"] for r in existing["results"]}

    # Charger nouveaux résultats
    if args.input:
        raw_data = load_json(args.input)
        raw_items = extract_items(raw_data)
        new_items = [normalize_entry(item) for item in raw_items]
    else:
        new_items = merge_from_two_files(args.analyses, args.tests)

    # Filtrer doublons
    added = []
    skipped_duplicates = []
    for item in new_items:
        if item["story_id"] in existing_ids:
            skipped_duplicates.append(item["story_id"])
        else:
            added.append(item)
            existing_ids.add(item["story_id"])

    # Résumé
    print(f"\n=== AJOUT DE RÉSULTATS AGENT 2 ===")
    print(f"Entrées existantes    : {len(existing['results'])}")
    print(f"Nouvelles entrées     : {len(new_items)}")
    print(f"Doublons ignorés      : {len(skipped_duplicates)} {skipped_duplicates if skipped_duplicates else ''}")
    print(f"Entrées ajoutées      : {len(added)}")

    if added:
        print(f"\nNouvelles stories :")
        for item in added:
            tests_count = len(item["tests"].get("tests", []))
            print(f"  + {item['story_id']:30s} | {item['story_type']:20s} | {tests_count} tests")

    if args.dry_run:
        print("\n[DRY RUN] Aucune modification sauvegardée.")
        return

    # Sauvegarder
    existing["results"].extend(added)
    existing["generated"] = len([
        r for r in existing["results"]
        if isinstance(r.get("tests"), dict) and r["tests"].get("generation_status") == "generated"
    ])
    existing["total_stories"] = max(existing.get("total_stories", 0), len(existing["results"]))

    save_json(str(output_path), existing)
    print(f"\nTotal résultats       : {len(existing['results'])}")
    print(f"Sauvegardé dans       : {output_path}")


if __name__ == "__main__":
    main()
