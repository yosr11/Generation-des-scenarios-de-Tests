"""
Runner dédié aux métriques LLM-judge (GEval). À lancer séparément du
run_evaluation.py déterministe, car plus lent et coûteux en tokens.

Métriques couvertes (9 au total) :
  - agent1_faithfulness
  - agent1_hallucination
  - agent1_factual_accuracy
  - agent2_hallucination     (nouveau : règles métier inventées par agent1.5)
  - business_workflow_quality
  - agent3_workflow_compliance
  - independent_coverage      (agent3_functional_relevance retirée, doublon)
  - agent5_fidelity
  - test_style_readability

SYSTÈME DE REPRISE (checkpoint) :
- Après chaque story évaluée, le résultat est sauvegardé immédiatement
  dans le fichier de sortie (pas seulement à la fin du script).
- Au démarrage, le script relit ce fichier et saute les stories déjà
  évaluées avec succès.
- Si le quota GitHub Models est épuisé (rate-limit qui bloque tout),
  tu peux simplement relancer le script le lendemain : il reprendra
  exactement là où il s'est arrêté, sans refaire les stories déjà faites.

Pour forcer une ré-évaluation complète depuis zéro, supprime le fichier
de sortie avant de relancer, ou utilise force_restart=True.

RÉSUMÉ / MOYENNES :
- À la fin d'un run complet (ou en cas d'interruption), la moyenne de
  chaque métrique sur toutes les stories traitées jusque-là est affichée.
- Pour ré-afficher ce résumé à tout moment sans relancer d'évaluation,
  lance : python run_geval_evaluation.py --summary-only
"""

import os

# Doit être défini AVANT le premier import de deepeval (au cas où ce
# fichier serait le point d'entrée exécuté avant geval_metrics.py).
os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "YES"

import json
import sys
import time
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

from deepeval.test_case import LLMTestCase

from eval.DeepEval.data_preparation import load_eval_stories, serialize_payload
from eval.DeepEval.geval_metrics import (
    agent1_faithfulness_metric,
    agent1_hallucination_metric,
    agent1_factual_accuracy_metric,
    agent2_hallucination_metric,
    business_workflow_quality_metric,
    agent3_workflow_compliance_metric,
    independent_coverage_metric,
    agent5_fidelity_metric,
    test_style_readability_metric,
)

# ---------------------------------------------------------------------------
# Réglages anti rate-limit
# ---------------------------------------------------------------------------
PAUSE_BETWEEN_METRICS_SEC = 3  # pause entre chaque métrique (appel LLM)
PAUSE_BETWEEN_STORIES_SEC = 8  # pause entre chaque story

METRIC_NAMES = [
    "agent1_faithfulness",
    "agent1_hallucination",
    "agent1_factual_accuracy",
    "agent2_hallucination",
    "business_workflow_quality",
    "agent3_workflow_compliance",
    "independent_coverage",
    "agent5_fidelity",
    "test_style_readability",
]


def build_metrics() -> Dict[str, Any]:
    return {
        "agent1_faithfulness": agent1_faithfulness_metric(),
        "agent1_hallucination": agent1_hallucination_metric(),
        "agent1_factual_accuracy": agent1_factual_accuracy_metric(),
        "agent2_hallucination": agent2_hallucination_metric(),
        "business_workflow_quality": business_workflow_quality_metric(),
        "agent3_workflow_compliance": agent3_workflow_compliance_metric(),
        "independent_coverage": independent_coverage_metric(),
        "agent5_fidelity": agent5_fidelity_metric(),
        "test_style_readability": test_style_readability_metric(),
    }


def load_existing_results(output_json_path: Path) -> List[Dict[str, Any]]:
    """Relit les résultats déjà sauvegardés d'un run précédent, s'ils existent."""
    if not output_json_path.exists():
        return []
    try:
        with output_json_path.open(encoding="utf-8") as f:
            existing = json.load(f)
        return existing.get("results", [])
    except (json.JSONDecodeError, KeyError):
        print(
            f"  [WARN] Fichier {output_json_path} illisible ou corrompu, on repart de zéro."
        )
        return []


def story_is_complete(story_result: Dict[str, Any]) -> bool:
    """Une story est considérée complète si toutes les métriques ont un score."""
    return all(name in story_result for name in METRIC_NAMES)


def save_progress(
    results: List[Dict[str, Any]], output_json_path: Path, input_json_path: str
) -> None:
    """Sauvegarde immédiate de l'état actuel (utilisée après chaque story)."""
    summary = build_geval_summary(results, METRIC_NAMES)
    output = {
        "meta": {"input_file": str(input_json_path), "case_count": len(results)},
        "summary": summary,
        "results": results,
    }
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    with output_json_path.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)


def run_geval_evaluation(
    input_json_path: str | Path,
    output_json_path: str | Path,
    max_cases: int | None = None,
    force_restart: bool = False,
) -> Dict[str, Any]:
    output_json_path = Path(output_json_path)

    stories = load_eval_stories(input_json_path)
    if max_cases is not None:
        stories = stories[:max_cases]

    # ── Reprise : on charge les résultats existants ─────────────────────
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
        summary = build_geval_summary(results, METRIC_NAMES)
        print_geval_summary(results, summary, METRIC_NAMES)
        return {
            "meta": {"input_file": str(input_json_path), "case_count": len(results)},
            "summary": summary,
            "results": results,
        }

    metrics = build_metrics()

    for story_idx, story in enumerate(stories_to_run):
        story_id = story.get("story_id", "unknown")
        print(
            f"\nÉvaluation GEval — {story_id}... "
            f"({story_idx + 1}/{len(stories_to_run)} restantes)"
        )

        agent1_input = story.get("agent1", {}).get("input", {})
        agent1_output = story.get("agent1", {}).get("output", {})
        agent2_output = story.get("agent2", {}).get("output", {})
        agent3_output = story.get("agent3", {}).get("output", {})
        agent4_output = story.get("agent4", {}).get("output", {})
        agent5_output = story.get("agent5", {}).get("output", {})

        agent1_input_str = serialize_payload(agent1_input)
        agent1_extraction_str = serialize_payload(
            {
                "actors": agent1_output.get("actors", []),
                "actions": agent1_output.get("actions", []),
                "testable_points": agent1_output.get("testable_points", []),
            }
        )
        agent1_full_output_str = serialize_payload(agent1_output)
        agent1_facts_str = serialize_payload(
            {
                "business_rules": agent1_output.get("business_rules", []),
                "acceptance_criteria_explicit": agent1_output.get(
                    "acceptance_criteria_explicit", []
                ),
                "testable_points": agent1_output.get("testable_points", []),
            }
        )
        agent2_str = serialize_payload(agent2_output)
        agent3_tests_str = serialize_payload(agent3_output.get("tests", []))
        agent4_str = serialize_payload(
            {
                "ambiguity_findings": agent4_output.get("ambiguity_findings", []),
                "uncovered_testable_points": agent4_output.get(
                    "uncovered_testable_points", []
                ),
                "duplicate_pairs": agent4_output.get("duplicate_pairs", []),
            }
        )
        agent5_str = serialize_payload(agent5_output)

        test_cases = {
            "agent1_faithfulness": LLMTestCase(
                input=agent1_input_str,
                actual_output=agent1_extraction_str,
            ),
            "agent1_hallucination": LLMTestCase(
                input=agent1_input_str,
                actual_output=agent1_full_output_str,
            ),
            "agent1_factual_accuracy": LLMTestCase(
                input=agent1_input_str,
                actual_output=agent1_facts_str,
            ),
            "agent2_hallucination": LLMTestCase(
                input=agent1_full_output_str,
                actual_output=agent2_str,
            ),
            "business_workflow_quality": LLMTestCase(
                input=agent1_full_output_str,
                actual_output=agent2_str,
            ),
            "agent3_workflow_compliance": LLMTestCase(
                input=agent2_str,
                actual_output=agent3_tests_str,
            ),
            "independent_coverage": LLMTestCase(
                input=agent1_input_str,
                actual_output=agent3_tests_str,
            ),
            "agent5_fidelity": LLMTestCase(
                input=agent4_str,
                actual_output=agent5_str,
            ),
            "test_style_readability": LLMTestCase(
                input="",
                actual_output=agent3_tests_str,
            ),
        }

        story_result: Dict[str, Any] = {"story_id": story_id}

        try:
            for idx, metric_name in enumerate(METRIC_NAMES):
                metric = metrics[metric_name]
                tc = test_cases[metric_name]

                print(f"  → {metric_name}...")
                metric.measure(tc)
                story_result[metric_name] = {
                    "score": round(metric.score * 100, 1),
                    "passed": metric.is_successful(),
                    "reason": metric.reason,
                }

                if idx < len(METRIC_NAMES) - 1:
                    time.sleep(PAUSE_BETWEEN_METRICS_SEC)

        except Exception as e:
            # Quota épuisé ou autre erreur bloquante : on sauvegarde ce qui
            # a déjà été calculé pour cette story (même partiel) puis on
            # sauvegarde la progression globale et on arrête proprement.
            print(f"\n[ERREUR] Échec sur la story {story_id} : {e}")
            print(
                "[INFO] Progression sauvegardée. Relance le script plus tard pour reprendre."
            )
            if len(story_result) > 1:  # au moins une métrique a été calculée
                results.append(story_result)
            save_progress(results, output_json_path, str(input_json_path))

            # On affiche quand même la moyenne par métrique sur ce qui a
            # été calculé jusqu'ici, pour ne pas perdre cette information
            # en cas d'interruption (rate-limit, coupure réseau, etc.).
            partial_summary = build_geval_summary(results, METRIC_NAMES)
            print_geval_summary(results, partial_summary, METRIC_NAMES)

            raise

        results.append(story_result)

        # ── Sauvegarde immédiate après chaque story complète ────────────
        save_progress(results, output_json_path, str(input_json_path))
        print(
            f"  [OK] Story {story_id} sauvegardée ({len(results)} story(ies) au total)."
        )

        if story_idx < len(stories_to_run) - 1:
            print(
                f"  ... pause de {PAUSE_BETWEEN_STORIES_SEC}s avant la story suivante ..."
            )
            time.sleep(PAUSE_BETWEEN_STORIES_SEC)

    summary = build_geval_summary(results, METRIC_NAMES)
    output = {
        "meta": {"input_file": str(input_json_path), "case_count": len(results)},
        "summary": summary,
        "results": results,
    }

    print_geval_summary(results, summary, METRIC_NAMES)
    return output


def build_geval_summary(
    results: List[Dict[str, Any]], metric_names: List[str]
) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    for name in metric_names:
        scores = [r[name]["score"] for r in results if name in r]
        worst = sorted(
            [(r["story_id"], r[name]["score"]) for r in results if name in r],
            key=lambda x: x[1],
        )[:3]
        summary[name] = {
            "score_moyen": round(mean(scores), 3) if scores else None,
            "taux_sous_seuil": (
                round(sum(1 for s in scores if s < 70) / len(scores), 2)
                if scores
                else None
            ),
            "pires_stories": worst,
        }
    return summary


def print_geval_summary(
    results: List[Dict[str, Any]], summary: Dict[str, Any], metric_names: List[str]
) -> None:
    print(f"\n{'='*70}")
    print(f"MOYENNE PAR MÉTRIQUE — {len(results)} stories évaluées")
    print(f"{'='*70}")
    print(f"{'Métrique':<32}{'Moyenne':>10}{'%< seuil':>12}")
    print(f"{'-'*70}")
    for name in metric_names:
        stats = summary.get(name, {})
        moy = stats.get("score_moyen")
        seuil = stats.get("taux_sous_seuil")
        moy_str = f"{moy:.1f}" if moy is not None else "N/A"
        seuil_str = f"{seuil * 100:.0f}%" if seuil is not None else "N/A"
        print(f"{name:<32}{moy_str:>10}{seuil_str:>12}")
    print(f"{'-'*70}")

    print(f"\nPires stories par métrique :")
    for name in metric_names:
        stats = summary.get(name, {})
        worst = stats.get("pires_stories", [])
        if worst:
            print(f"  {name}: {worst}")

    print(f"\n{'='*70}\nDÉTAIL PAR STORY\n{'='*70}")
    for r in results:
        print(f"\n[{r['story_id']}]")
        for name in metric_names:
            if name not in r:
                continue
            d = r[name]
            flag = "⚠️ " if not d["passed"] else "✅ "
            print(f"  {flag}{name}: {d['score']}")
    print(f"\n{'='*70}\n")


def print_summary_only(output_json_path: str | Path) -> None:
    """Réaffiche le résumé (moyenne par métrique) depuis un fichier déjà
    sauvegardé, sans relancer aucune évaluation. Pratique pour consulter
    l'état d'avancement à tout moment, y compris après une interruption."""
    output_json_path = Path(output_json_path)
    if not output_json_path.exists():
        print(f"Aucun fichier trouvé : {output_json_path}")
        return
    with output_json_path.open(encoding="utf-8") as f:
        data = json.load(f)
    results = data.get("results", [])
    if not results:
        print(f"Le fichier {output_json_path} ne contient aucun résultat.")
        return
    summary = build_geval_summary(results, METRIC_NAMES)
    print_geval_summary(results, summary, METRIC_NAMES)


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    input_json = base_dir / "evalAgents.json"
    output_json = base_dir / "geval_evaluation_results.json"

    if "--summary-only" in sys.argv:
        print_summary_only(output_json)
    else:
        try:
            run_geval_evaluation(input_json, output_json, max_cases=None)
            print(f"Évaluation GEval terminée : {output_json}")
        except Exception:
            print(
                "Le script s'est arrêté avant la fin. Relance-le pour reprendre là où il s'est arrêté."
            )