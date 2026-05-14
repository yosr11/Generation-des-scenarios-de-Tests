# eval/testable_points_coverage_eval.py
"""
Évaluation de la couverture des testable_points de l'Agent 1
par les tests générés par l'Agent 2.

Utilise la similarité cosinus sur des embeddings (sentence-transformers)
pour déterminer si chaque testable_point est couvert par au moins un step de test.

Usage :
    py -m eval.testable_points_coverage_eval --input eval/agent2_output.json
"""

import json
import argparse
import numpy as np
from sentence_transformers import SentenceTransformer

# ── Modèle d'embeddings multilingue ──
_model = None


def get_model() -> SentenceTransformer:
    """Charge le modèle une seule fois (lazy loading)."""
    global _model
    if _model is None:
        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _model


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Similarité cosinus entre deux vecteurs."""
    dot = np.dot(vec_a, vec_b)
    norm = np.linalg.norm(vec_a) * np.linalg.norm(vec_b)
    if norm == 0:
        return 0.0
    return float(dot / norm)


def check_coverage(testable_points: list[str], tests: list[dict], threshold: float = 0.5) -> dict:
    """
    Vérifie si chaque testable_point est couvert par au moins un test.
    
    Pour chaque testable_point, compare avec (via cosine similarity sur embeddings) :
    - objective de chaque test
    - expected_result de chaque step
    - action de chaque step
    
    Retourne le détail de couverture.
    """
    model = get_model()

    # Collecter tous les textes candidats des tests
    candidates = []  # (text, test_name)
    for test in tests:
        obj = test.get("objective", "")
        if obj:
            candidates.append((obj, test.get("test_name", "")))
        for step in test.get("steps", []):
            er = step.get("expected_result", "")
            if er:
                candidates.append((er, test.get("test_name", "")))
            action = step.get("action", "")
            if action:
                candidates.append((action, test.get("test_name", "")))

    if not candidates:
        return {
            "total_testable_points": len(testable_points),
            "covered": 0,
            "not_covered": len(testable_points),
            "coverage_rate_percent": 0.0,
            "details": [],
        }

    # Encoder tous les textes en une seule passe pour la performance
    tp_embeddings = model.encode(testable_points, normalize_embeddings=True)
    candidate_texts = [c[0] for c in candidates]
    candidate_embeddings = model.encode(candidate_texts, normalize_embeddings=True)

    coverage_details = []
    for i, tp in enumerate(testable_points):
        best_score = 0.0
        best_match = ""
        best_test = ""

        for j, (cand_text, cand_test_name) in enumerate(candidates):
            score = cosine_similarity(tp_embeddings[i], candidate_embeddings[j])
            if score > best_score:
                best_score = score
                best_match = cand_text[:80]
                best_test = cand_test_name

        covered = best_score >= threshold
        coverage_details.append({
            "testable_point": tp,
            "covered": covered,
            "best_score": round(best_score, 3),
            "best_match": best_match,
            "matched_test": best_test,
        })

    covered_count = sum(1 for c in coverage_details if c["covered"])
    total = len(testable_points)
    coverage_rate = round(covered_count / total * 100, 2) if total > 0 else 100.0

    return {
        "total_testable_points": total,
        "covered": covered_count,
        "not_covered": total - covered_count,
        "coverage_rate_percent": coverage_rate,
        "details": coverage_details,
    }


def evaluate_file(input_path: str, threshold: float = 0.5

                  ) -> dict:
    """Évalue la couverture des testable_points pour toutes les stories."""
    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    results_list = data.get("results", data if isinstance(data, list) else [])

    story_results = []
    total_tp = 0
    total_covered = 0
    stories_with_full_coverage = 0

    for item in results_list:
        story_id = item.get("story_id", "?")
        analysis = item.get("analysis", {})
        testable_points = analysis.get("testable_points", [])
        tests_data = item.get("tests", {})
        tests = tests_data.get("tests", []) if isinstance(tests_data, dict) else tests_data

        if not testable_points:
            story_results.append({
                "story_id": story_id,
                "status": "no_testable_points",
                "coverage": None,
            })
            continue

        if not tests:
            story_results.append({
                "story_id": story_id,
                "status": "no_tests",
                "coverage": {
                    "total_testable_points": len(testable_points),
                    "covered": 0,
                    "not_covered": len(testable_points),
                    "coverage_rate_percent": 0.0,
                    "details": [],
                },
            })
            total_tp += len(testable_points)
            continue

        coverage = check_coverage(testable_points, tests, threshold)
        total_tp += coverage["total_testable_points"]
        total_covered += coverage["covered"]

        if coverage["coverage_rate_percent"] == 100.0:
            stories_with_full_coverage += 1

        story_results.append({
            "story_id": story_id,
            "status": "evaluated",
            "coverage": coverage,
        })

    stories_evaluated = sum(1 for s in story_results if s["status"] == "evaluated")
    global_coverage = round(total_covered / total_tp * 100, 2) if total_tp > 0 else 0.0

    summary = {
        "total_stories": len(results_list),
        "stories_evaluated": stories_evaluated,
        "stories_no_testable_points": sum(1 for s in story_results if s["status"] == "no_testable_points"),
        "stories_no_tests": sum(1 for s in story_results if s["status"] == "no_tests"),
        "stories_with_full_coverage": stories_with_full_coverage,
        "total_testable_points": total_tp,
        "total_covered": total_covered,
        "total_not_covered": total_tp - total_covered,
        "global_coverage_rate_percent": global_coverage,
        "threshold_used": threshold,
    }

    return {
        "summary": summary,
        "details": story_results,
    }


def main():
    parser = argparse.ArgumentParser(description="Couverture des testable_points par les tests Agent 2")
    parser.add_argument("--input", required=True, help="Fichier JSON Agent 2 (agent2_output.json)")
    parser.add_argument("--output", help="Fichier JSON de sortie (optionnel)")
    parser.add_argument("--threshold", type=float, default=0.5,
                        help="Seuil de similarité cosinus pour considérer un point couvert (défaut: 0.5)")
    args = parser.parse_args()

    result = evaluate_file(args.input, args.threshold)
    summary = result["summary"]

    print("\n==== COUVERTURE DES TESTABLE POINTS — RÉSUMÉ ====")
    print(f"Stories évaluées           : {summary['stories_evaluated']}")
    print(f"Stories sans testable pts  : {summary['stories_no_testable_points']}")
    print(f"Stories sans tests         : {summary['stories_no_tests']}")
    print(f"Stories couverture 100%    : {summary['stories_with_full_coverage']}/{summary['stories_evaluated']}")
    print(f"Total testable points      : {summary['total_testable_points']}")
    print(f"Couverts                   : {summary['total_covered']}")
    print(f"Non couverts               : {summary['total_not_covered']}")
    print(f"Taux de couverture global  : {summary['global_coverage_rate_percent']}%")
    print(f"Seuil de similarité        : {summary['threshold_used']}")

    print("\n==== DÉTAIL PAR STORY ====")
    for sr in result["details"]:
        if sr["status"] == "no_testable_points":
            print(f"  {sr['story_id']:30s} | Pas de testable_points")
            continue
        if sr["status"] == "no_tests":
            print(f"  {sr['story_id']:30s} | Pas de tests générés — 0% couverture")
            continue

        cov = sr["coverage"]
        status = "✓ 100%" if cov["coverage_rate_percent"] == 100 else f"⚠ {cov['coverage_rate_percent']}%"
        print(f"  {sr['story_id']:30s} | {cov['covered']}/{cov['total_testable_points']} couverts | {status}")

        # Afficher les points non couverts
        for d in cov["details"]:
            if not d["covered"]:
                print(f"    ✗ NON COUVERT (score={d['best_score']}) : {d['testable_point'][:80]}")
            else:
                print(f"    ✓ couvert     (score={d['best_score']}) : {d['testable_point'][:80]}")
                print(f"      → match: {d['best_match']}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\nRésultats sauvegardés dans {args.output}")


if __name__ == "__main__":
    main()
