"""
Métriques déterministes d'évaluation du pipeline multi-agents.
Version corrigée : comparaison sémantique (au lieu de mot-à-mot) et
pondération des erreurs selon leur gravité (au lieu d'un poids fixe).
"""

from enum import Enum
from typing import Any, Dict, List

from eval.DeepEval.semantic_similarity import best_semantic_match


# Seuil de similarité sémantique en dessous duquel on considère qu'un
# testable_point n'est "rattaché" à rien. À ajuster via calibration_tests.py
SEMANTIC_ORPHAN_THRESHOLD = 0.40


class Severity(Enum):
    """Gravité d'une erreur détectée -> poids retiré au score final."""
    CRITIQUE = 0.30   # ex: aucun test généré, aucune étape
    MAJEUR = 0.15     # ex: verbe interdit, point non couvert
    MINEUR = 0.05     # ex: champ optionnel manquant (priority, label...)


def compute_score(issues: List[Dict[str, str]]) -> float:
    """Calcule un score entre 0 et 1 à partir d'une liste d'issues,
    chacune ayant une sévérité. Remplace l'ancien 'score -= 0.2 * len(issues)'."""
    penalty = sum(Severity[issue["severity"]].value for issue in issues)
    return round(max(0.0, 1.0 - penalty), 3)


def _issue(message: str, severity: str) -> Dict[str, str]:
    return {"message": message, "severity": severity}


# ---------------------------------------------------------------------------
# AGENT 1 — Complétude structurelle de l'extraction
# ---------------------------------------------------------------------------
class Agent1Metrics:
    """Vérifie que l'extraction (actors/actions/testable_points/business_rules)
    est structurellement complète."""

    def score(self, agent1_output: Dict[str, Any]) -> Dict[str, Any]:
        issues: List[Dict[str, str]] = []

        actors = agent1_output.get("actors", [])
        actions = agent1_output.get("actions", [])
        testable_points = agent1_output.get("testable_points", [])
        business_rules = agent1_output.get("business_rules", [])
        acceptance_explicit = agent1_output.get("acceptance_criteria_explicit", [])
        story_type = agent1_output.get("story_type", "")

        if len(testable_points) == 0:
            issues.append(_issue("aucun testable_point extrait", "CRITIQUE"))

        if story_type == "functional" and len(actors) == 0 and len(actions) == 0:
            issues.append(_issue(
                "story_type=functional mais aucun actor/action extrait", "CRITIQUE"
            ))

        if len(business_rules) == 0 and len(acceptance_explicit) > 0:
            issues.append(_issue(
                "acceptance_criteria_explicit non vide mais business_rules vide "
                "(règle métier potentiellement perdue)", "MAJEUR"
            ))

        # Chaque testable_point devrait se rattacher SÉMANTIQUEMENT à au moins
        # une action ou une règle métier -> détection de points "orphelins".
        # On compare le SENS des phrases, pas les mots qui les composent.
        context_sentences = actions + business_rules
        if context_sentences:
            orphan_points = []
            for tp in testable_points:
                score, _ = best_semantic_match(tp, context_sentences)
                if score < SEMANTIC_ORPHAN_THRESHOLD:
                    orphan_points.append(tp)

            if testable_points and len(orphan_points) / len(testable_points) > 0.5:
                issues.append(_issue(
                    f"{len(orphan_points)}/{len(testable_points)} testable_points "
                    "sémantiquement déconnectés de toute action/règle métier",
                    "MAJEUR",
                ))

        return {"score": compute_score(issues), "issues": issues}


# ---------------------------------------------------------------------------
# AGENT 1.5 — Cohérence du business model avec agent1
# ---------------------------------------------------------------------------
class Agent15Metrics:
    def score(self, agent1_output: Dict[str, Any], agent15_output: Dict[str, Any]) -> Dict[str, Any]:
        issues: List[Dict[str, str]] = []

        goals = agent15_output.get("business_goals", [])
        workflows = agent15_output.get("business_workflows", [])

        if not goals:
            issues.append(_issue("aucun business_goal produit", "CRITIQUE"))
        if not workflows:
            issues.append(_issue("aucun business_workflow produit", "CRITIQUE"))

        goal_ids = {g.get("id") for g in goals}
        linked_ids = {w.get("linked_goal_id") for w in workflows if w.get("linked_goal_id")}

        orphan_workflows = linked_ids - goal_ids
        orphan_goals = goal_ids - linked_ids

        if orphan_workflows:
            issues.append(_issue(
                f"workflows référençant un goal_id inexistant: {sorted(orphan_workflows)}",
                "CRITIQUE",
            ))
        if orphan_goals:
            issues.append(_issue(
                f"goals jamais utilisés par un workflow: {sorted(orphan_goals)}",
                "MINEUR",
            ))

        # Les acteurs cités dans les goals doivent venir d'agent1 (comparaison
        # sémantique car les libellés peuvent varier légèrement, ex: "RH de
        # proximité" vs "RH proximité")
        agent1_actors = agent1_output.get("actors", [])
        for g in goals:
            for actor in g.get("actors", []):
                if agent1_actors:
                    score, _ = best_semantic_match(actor, agent1_actors)
                    if score < 0.6:
                        issues.append(_issue(
                            f"goal '{g.get('id')}' introduit un actor '{actor}' "
                            "absent d'agent1", "MAJEUR",
                        ))

        for w in workflows:
            if not w.get("steps"):
                issues.append(_issue(
                    f"workflow '{w.get('id')}' n'a aucune étape (steps vide)", "CRITIQUE",
                ))
            if not w.get("success_criteria"):
                issues.append(_issue(
                    f"workflow '{w.get('id')}' n'a aucun success_criteria", "MAJEUR",
                ))

        return {"score": compute_score(issues), "issues": issues}


# ---------------------------------------------------------------------------
# AGENT 2 — Qualité rédactionnelle des tests + couverture (via agent3)
# ---------------------------------------------------------------------------
class Agent2Metrics:
    def qa_quality(self, agent2_output: Dict[str, Any]) -> Dict[str, Any]:
        issues: List[Dict[str, str]] = []
        tests = agent2_output.get("tests", [])

        if not tests:
            return {"score": 0.0, "issues": [_issue("aucun test généré", "CRITIQUE")]}

        for t in tests:
            name = t.get("test_name", "unknown")
            

            

            if not t.get("scenario_type"):
                issues.append(_issue(f"{name}: scenario_type manquant", "MINEUR"))
            if not t.get("priority"):
                issues.append(_issue(f"{name}: priority manquante", "MINEUR"))

            steps = t.get("steps", [])
            if not steps:
                issues.append(_issue(f"{name}: aucune étape (steps vide)", "CRITIQUE"))
                continue

            for step in steps:
                if isinstance(step, dict):
                    idx = step.get("index", "?")
                    action = step.get("action", "")
                    expected = step.get("expected_result", "")
                elif isinstance(step, str):
                    idx = "?"
                    action = step
                    expected = ""
                else:
                    idx = "?"
                    action = ""
                    expected = ""

                if not action:
                    issues.append(_issue(f"step {idx}: action manquante", "MAJEUR"))

                if not expected:
                    issues.append(_issue(f"step {idx}: expected_result manquant", "MAJEUR"))

        return {"score": compute_score(issues), "issues": issues}

    def coverage_from_agent3(self, agent3_output: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "coverage_rate": agent3_output.get("coverage_rate", 0.0),
            "missing_tests_count": len(agent3_output.get("uncovered_testable_points", [])),
            "missing_tests": agent3_output.get("uncovered_testable_points", []),
            "duplicate_count": len(agent3_output.get("duplicate_pairs", [])),
            "validation_status": agent3_output.get("validation_status", "UNKNOWN"),
        }


# ---------------------------------------------------------------------------
# AGENT 3 — Justesse interne de la validation
# ---------------------------------------------------------------------------
class Agent3Metrics:
    def score(self, agent3_input: Dict[str, Any], agent3_output: Dict[str, Any]) -> Dict[str, Any]:
        issues: List[Dict[str, str]] = []

        testable_points = agent3_input.get("testable_points", [])
        uncovered = agent3_output.get("uncovered_testable_points", [])
        coverage_rate = agent3_output.get("coverage_rate", 0.0)

        for point in uncovered:
            if point not in testable_points:
                issues.append(_issue(
                    f"uncovered_testable_points contient un point absent de l'input: "
                    f"'{point[:60]}...'", "CRITIQUE",
                ))

        if testable_points:
            expected_covered = len(testable_points) - len(uncovered)
            expected_rate = round(expected_covered / len(testable_points), 4)
            if abs(expected_rate - coverage_rate) > 0.02:
                issues.append(_issue(
                    f"coverage_rate incohérent: déclaré={coverage_rate}, "
                    f"calculé={expected_rate}", "CRITIQUE",
                ))

       

        validation_status = agent3_output.get("validation_status", "")
        has_ambiguities = len(agent3_output.get("ambiguity_findings", [])) > 0
        has_uncovered = len(uncovered) > 0
        if validation_status == "VALID" and (has_ambiguities or has_uncovered):
            issues.append(_issue(
                "validation_status=VALID alors que des ambiguïtés ou des points "
                "non couverts existent", "CRITIQUE",
            ))

        return {"score": compute_score(issues), "issues": issues}


# ---------------------------------------------------------------------------
# AGENT 5 — Fidélité du rapport final aux chiffres d'agent3
# ---------------------------------------------------------------------------
class Agent5Metrics:
    def score(self, agent3_output: Dict[str, Any], agent5_output: Dict[str, Any]) -> Dict[str, Any]:
        issues: List[Dict[str, str]] = []

        agent3_coverage_pct = round(agent3_output.get("coverage_rate", 0.0) * 100, 1)
        agent5_coverage_pct = agent5_output.get("coverage_metrics", {}).get("coverage_rate")

        if agent5_coverage_pct is not None and abs(agent3_coverage_pct - agent5_coverage_pct) > 1.0:
            issues.append(_issue(
                f"coverage_rate divergent: agent3={agent3_coverage_pct}%, "
                f"agent5={agent5_coverage_pct}%", "CRITIQUE",
            ))

        agent3_ambiguity_count = len(agent3_output.get("ambiguity_findings", []))
        agent5_ambiguity_count = agent5_output.get("quality_assurance", {}).get("ambiguity_count")
        if agent5_ambiguity_count is not None and agent3_ambiguity_count != agent5_ambiguity_count:
            issues.append(_issue(
                f"ambiguity_count divergent: agent3={agent3_ambiguity_count}, "
                f"agent5={agent5_ambiguity_count}", "MAJEUR",
            ))

        agent3_dup = len(agent3_output.get("duplicate_pairs", []))
        agent5_dup = agent5_output.get("quality_assurance", {}).get("duplicate_pairs")
        if agent5_dup is not None and agent3_dup != agent5_dup:
            issues.append(_issue(
                f"duplicate_pairs divergent: agent3={agent3_dup}, agent5={agent5_dup}", "MAJEUR",
            ))

        agent3_uncovered = set(agent3_output.get("uncovered_testable_points", []))
        agent5_uncovered = set(agent5_output.get("coverage_metrics", {}).get("uncovered_points", []))
        if agent3_uncovered != agent5_uncovered:
            issues.append(_issue("uncovered_points divergents entre agent3 et agent5", "CRITIQUE"))

        overall_status = agent5_output.get("executive_summary", {}).get("overall_status")
        recommendations = agent5_output.get("recommendations", [])
        if overall_status not in ("VALID", None) and not recommendations:
            issues.append(_issue(
                f"overall_status={overall_status} mais aucune recommendation fournie", "MAJEUR",
            ))

        return {"score": compute_score(issues), "issues": issues}


def build_metric_suite() -> Dict[str, Any]:
    return {
        "agent1": Agent1Metrics(),
        "agent1_5": Agent15Metrics(),
        "agent2": Agent2Metrics(),
        "agent3": Agent3Metrics(),
        "agent5": Agent5Metrics(),
    }