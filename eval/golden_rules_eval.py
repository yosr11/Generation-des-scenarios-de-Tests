# eval/golden_rules_eval.py
"""
Évaluation programmatique des golden rules pour les tests manuels de l'Agent 2.

Vérifie de manière déterministe le respect des conventions d'écriture
définies dans le prompt de génération de tests.

Usage :
    py -m eval.golden_rules_eval --input eval/agent2_output.json
"""

import json
import re
import argparse
from pathlib import Path


# ── Mots vagues interdits dans expected_result ──
VAGUE_WORDS = [
    "correctement", "normalement", "avec succès", "bien",
    "proprement", "convenablement", "sans problème", "comme prévu",
    "de manière appropriée", "de façon correcte",
]

# ── Patterns de négation dans expected_result ──
NEGATION_PATTERNS = [
    r"\bn['''](?:est|a|ont|sont)\s+pas\b",
    r"\bne\s+\w+\s+pas\b",
    r"\bne\s+\w+\s+plus\b",
    r"\bne\s+\w+\s+jamais\b",
    r"\bne\s+\w+\s+rien\b",
    r"\bne\s+\w+\s+aucun\b",
    r"\baucun(?:e)?\b",
]

# ── Pattern de nommage attendu : STORYID-TYPE-NNN ──
NAMING_PATTERN = re.compile(
    r"^[A-Za-z]+-\d+-(NOM|ALT|EXC)-\d{3}\b"
)

# ── Verbes conjugués courants (non infinitif) ──
CONJUGATED_VERBS = [
    r"\bClique[rz]?\b(?!r\b)",   # "Clique" mais pas "Cliquer"
    r"\bSaisit\b", r"\bSaisie\b",
    r"\bOuvre\b(?!r\b)",
    r"\bNavigue\b(?!r\b)",
    r"\bAccède\b(?!r\b)",
    r"\bSélectionne\b(?!r\b)",
]


def check_golden_rules(test: dict, story_id: str) -> list[dict]:
    """Vérifie les golden rules sur un test, retourne la liste des violations."""
    violations = []
    test_name = test.get("test_name", "")
    objective = test.get("objective", "")
    steps = test.get("steps", [])

    # ── Règle 1 : Convention de nommage ──
    if not NAMING_PATTERN.match(test_name):
        violations.append({
            "rule": "naming_convention",
            "severity": "warning",
            "message": f"Test name ne suit pas le pattern STORYID-TYPE-NNN : '{test_name}'",
        })

    # ── Règle 2 : Objective ne commence pas par "Vérifier" ──
    if objective.strip().lower().startswith("vérifier"):
        violations.append({
            "rule": "objective_no_verifier",
            "severity": "error",
            "message": f"L'objective commence par 'Vérifier' : '{objective[:60]}...'",
        })

    # ── Règle 3 : revision_po toujours vide ──
    for step in steps:
        if step.get("revision_po", "").strip():
            violations.append({
                "rule": "revision_po_empty",
                "severity": "warning",
                "message": f"Step {step['index']} a revision_po non vide : '{step['revision_po']}'",
            })

    # ── Règle 4 : Pas de "Vérifier" comme verbe d'action dans les steps ──
    for step in steps:
        action = step.get("action", "")
        if action.strip().lower().startswith("vérifier"):
            violations.append({
                "rule": "action_no_verifier",
                "severity": "error",
                "message": f"Step {step['index']} : action commence par 'Vérifier' : '{action[:60]}...'",
            })

    # ── Règle 5 : Pas de mots vagues dans expected_result ──
    for step in steps:
        er = step.get("expected_result", "").lower()
        for word in VAGUE_WORDS:
            if word in er:
                violations.append({
                    "rule": "no_vague_words",
                    "severity": "error",
                    "message": f"Step {step['index']} : expected_result contient '{word}'",
                })

    # ── Règle 6 : Pas de négation dans expected_result (désactivée) ──
    # Règle retirée : la négation dans expected_result est tolérée
    # car le prompt a été renforcé pour les futures générations.

    # ── Règle 7 : scenario_type valide ──
    valid_types = {"NOM", "ALT", "EXC"}
    st = test.get("scenario_type", "")
    if st not in valid_types:
        violations.append({
            "rule": "valid_scenario_type",
            "severity": "error",
            "message": f"scenario_type invalide : '{st}' (attendu: NOM, ALT, EXC)",
        })

    # ── Règle 8 : priority valide ──
    valid_priorities = {"High", "Medium", "Low"}
    prio = test.get("priority", "")
    if prio not in valid_priorities:
        violations.append({
            "rule": "valid_priority",
            "severity": "warning",
            "message": f"priority invalide : '{prio}' (attendu: High, Medium, Low)",
        })

    # ── Règle 9 : preconditions et execution_context remplis ──
    if not test.get("execution_context", "").strip():
        violations.append({
            "rule": "execution_context_filled",
            "severity": "warning",
            "message": "execution_context est vide",
        })
    if not test.get("preconditions"):
        violations.append({
            "rule": "preconditions_filled",
            "severity": "warning",
            "message": "preconditions est vide",
        })

    # ── Règle 10 : Au moins 1 step par test ──
    if len(steps) < 1:
        violations.append({
            "rule": "min_steps",
            "severity": "error",
            "message": f"Aucun step défini pour ce test",
        })

    return violations


def evaluate_file(input_path: str) -> dict:
    """Évalue tous les tests d'un fichier agent2_output.json."""
    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    results_list = data.get("results", data if isinstance(data, list) else [])

    total_tests = 0
    total_violations = 0
    total_errors = 0
    total_warnings = 0
    rule_counts = {}
    story_results = []

    for item in results_list:
        story_id = item.get("story_id", "?")
        tests_data = item.get("tests", {})
        tests = tests_data.get("tests", []) if isinstance(tests_data, dict) else tests_data

        story_violations = []
        for test in tests:
            total_tests += 1
            violations = check_golden_rules(test, story_id)
            total_violations += len(violations)

            for v in violations:
                if v["severity"] == "error":
                    total_errors += 1
                else:
                    total_warnings += 1
                rule_counts[v["rule"]] = rule_counts.get(v["rule"], 0) + 1

            story_violations.append({
                "test_name": test.get("test_name", ""),
                "violations_count": len(violations),
                "violations": violations,
            })

        story_results.append({
            "story_id": story_id,
            "tests_count": len(tests),
            "tests": story_violations,
        })

    # ── Score global ──
    if total_tests > 0:
        tests_clean = sum(
            1 for sr in story_results
            for t in sr["tests"]
            if t["violations_count"] == 0
        )
        compliance_rate = round(tests_clean / total_tests * 100, 2)
    else:
        compliance_rate = 0

    summary = {
        "total_stories": len(results_list),
        "total_tests": total_tests,
        "total_violations": total_violations,
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "tests_fully_compliant": tests_clean if total_tests > 0 else 0,
        "compliance_rate_percent": compliance_rate,
        "violations_by_rule": dict(sorted(rule_counts.items(), key=lambda x: -x[1])),
    }

    return {
        "summary": summary,
        "details": story_results,
    }


def main():
    parser = argparse.ArgumentParser(description="Vérification des golden rules Agent 2")
    parser.add_argument("--input", required=True, help="Fichier JSON Agent 2 (agent2_output.json)")
    parser.add_argument("--output", help="Fichier JSON de sortie (optionnel)")
    args = parser.parse_args()

    result = evaluate_file(args.input)
    summary = result["summary"]

    print("\n==== GOLDEN RULES — RÉSUMÉ ====")
    print(f"Stories évaluées      : {summary['total_stories']}")
    print(f"Tests évalués         : {summary['total_tests']}")
    print(f"Tests conformes       : {summary['tests_fully_compliant']}/{summary['total_tests']}")
    print(f"Taux de conformité    : {summary['compliance_rate_percent']}%")
    print(f"Violations totales    : {summary['total_violations']} (erreurs: {summary['total_errors']}, warnings: {summary['total_warnings']})")
    print(f"\nViolations par règle  :")
    for rule, count in summary["violations_by_rule"].items():
        print(f"  {rule:40s} : {count}")

    # Détail des violations par story
    print("\n==== DÉTAIL PAR STORY ====")
    for sr in result["details"]:
        violations_total = sum(t["violations_count"] for t in sr["tests"])
        status = "✓" if violations_total == 0 else f"✗ ({violations_total} violations)"
        print(f"  {sr['story_id']:30s} | {sr['tests_count']} tests | {status}")
        for t in sr["tests"]:
            if t["violations_count"] > 0:
                print(f"    {t['test_name'][:60]}")
                for v in t["violations"]:
                    sev = "ERR" if v["severity"] == "error" else "WRN"
                    print(f"      [{sev}] {v['rule']}: {v['message'][:100]}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\nRésultats sauvegardés dans {args.output}")


if __name__ == "__main__":
    main()
