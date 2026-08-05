"""
Métriques LLM-judge (GEval) pour évaluer la fidélité sémantique du pipeline.
Contrairement à metrics.py (déterministe, gratuit), ces métriques appellent
un LLM et doivent être utilisées de façon ciblée (pas sur tout le dataset
à chaque run, pour limiter coût et temps).

Le juge LLM utilisé est GitHub Models (gpt-4.1) via le wrapper
GitHubModelsLLM, au lieu d'OpenAI par défaut.

Historique des changements :
- agent1_faithfulness et agent1_hallucination restent séparées (granularité
  du reporting préférée à la fusion : on veut pouvoir distinguer un problème
  de traçabilité d'un problème d'invention pure)
- agent3_functional_relevance retirée (redondante avec independent_coverage)
- agent2_hallucination ajoutée (lacune identifiée : agent1.5 pouvait
  inventer des règles métier dans ses workflows sans que rien ne le détecte)
- seuils différenciés selon la gravité : 0.85 pour tout ce qui touche à
  l'exactitude factuelle/hallucination, 0.7 pour le reste (style, logique)
- télémétrie DeepEval désactivée (os.environ) pour éviter les erreurs
  PostHog bruyantes dans les environnements avec proxy/certificat
  self-signed (voir aussi run_geval_evaluation.py)
"""

import os

# Doit être défini AVANT le premier import de deepeval, sinon la
# télémétrie est déjà initialisée et l'opt-out n'a aucun effet.
os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "YES"

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams

#from eval.DeepEval.github_models_llm import GitHubModelsLLM
from eval.DeepEval.groq_llm import GroqLLM

# ---------------------------------------------------------------------------
# Juge LLM partagé par toutes les métriques (une seule instance)
# ---------------------------------------------------------------------------
#judge_model = GitHubModelsLLM(model_alias="gpt-4.1")
judge = GroqLLM("gptoss120b")


# ---------------------------------------------------------------------------
# AGENT 1 — Faithfulness (traçabilité des éléments extraits)
# ---------------------------------------------------------------------------
def agent1_faithfulness_metric(threshold: float = 0.85) -> GEval:
    """Les actors/actions/testable_points viennent-ils réellement de la story ?"""
    return GEval(
        name="Agent1 Faithfulness",
        criteria=(
            "You are given the original Jira user story (input) and the extracted "
            "actors, actions, and testable_points (actual_output). "
            "For each element in the output, check if it is directly traceable to "
            "explicit text or clear logical implication in the input story. "
            "Score 1.0 if every extracted element is clearly grounded in the source text. "
            "Score close to 0.0 if many elements have no clear basis in the input. "
            "Do not penalize reasonable paraphrasing or synthesis of explicit content — "
            "only penalize elements that are not supported at all by the input."
        ),
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=threshold,
        model=judge,
    )


# ---------------------------------------------------------------------------
# AGENT 1 — Hallucination check (invention de règles/contraintes/comportements)
# ---------------------------------------------------------------------------
def agent1_hallucination_metric(threshold: float = 0.85) -> GEval:
    """L'agent n'invente-t-il pas d'éléments (règles métier, contraintes, comportements) ?"""
    return GEval(
        name="Agent1 Hallucination Check",
        criteria=(
            "You are given the original Jira user story (input) and agent1's full analysis "
            "output including business_rules, acceptance_criteria, and clarification_questions "
            "(actual_output). "
            "Identify any fabricated detail: a business rule, constraint, numeric value, or "
            "behavior stated in the output that is NOT present, implied, or reasonably inferable "
            "from the input story or its attached images/descriptions. "
            "Score 1.0 if there is no fabrication. Score low (below 0.3) if the output invents "
            "significant business logic not supported by the input."
        ),
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=threshold,
        model=judge,
    )


# ---------------------------------------------------------------------------
# AGENT 1 — Exactitude factuelle stricte (valeurs, dates, règles précises)
# ---------------------------------------------------------------------------
def agent1_factual_accuracy_metric(threshold: float = 0.85) -> GEval:
    """Les valeurs numériques, dates, seuils et règles métier précises extraites
    sont-elles exactement fidèles à la story (pas juste "globalement cohérentes") ?"""
    return GEval(
        name="Agent1 Factual Accuracy",
        criteria=(
            "You are given the original Jira story (input) and agent1's extracted "
            "business_rules, acceptance_criteria_explicit, and testable_points "
            "(actual_output). "
            "Check every specific fact stated in the output — numeric values, dates, "
            "thresholds, named fields, exact conditions — against the input. "
            "Flag any discrepancy: a wrong number, a wrong date, a misstated condition, "
            "or a rule that reverses/contradicts what the story actually says. "
            "Score 1.0 if all specific facts are exactly accurate. Score very low if "
            "any numeric value, date, or precise condition is wrong or contradicted."
        ),
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=threshold,
        model=judge,
    )


# ---------------------------------------------------------------------------
# AGENT 1.5 — Hallucination des règles métier dans le business model
# Lacune comblée : la vérification déterministe (Agent2Metrics) ne
# détectait que les acteurs inventés, pas les règles métier inventées
# dans les success_criteria / steps / business_goals.
# ---------------------------------------------------------------------------
def agent2_hallucination_metric(threshold: float = 0.85) -> GEval:
    """agent1.5 invente-t-il des règles métier, contraintes ou comportements
    absents de l'analyse d'agent1 dans ses business_goals/business_workflows ?"""
    return GEval(
        name="Agent1.5 Business Rule Hallucination",
        criteria=(
            "You are given agent1's analysis (input) with its business_rules, "
            "testable_points, and actors, and the business model produced by agent1.5 "
            "(actual_output) with its business_goals and business_workflows including "
            "steps and success_criteria. "
            "Identify any business rule, constraint, condition, or behavior described "
            "in a business_goal, workflow step, or success_criteria that is NOT present, "
            "implied, or reasonably derivable from agent1's business_rules or "
            "testable_points. "
            "Do not penalize reasonable elaboration of an existing rule into concrete "
            "steps — only penalize genuinely new business logic that agent1 never stated. "
            "Score 1.0 if no fabricated business rule is found. Score low (below 0.3) if "
            "the business model introduces significant unfounded business logic."
        ),
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=threshold,
        model=judge,
    )


# ---------------------------------------------------------------------------
# BUSINESS WORKFLOW QUALITY — logique du workflow, cohérence des étapes métier
# ---------------------------------------------------------------------------
def business_workflow_quality_metric(threshold: float = 0.7) -> GEval:
    """Le workflow métier est-il logique ? Les étapes sont-elles cohérentes ?"""
    return GEval(
        name="Business Workflow Quality",
        criteria=(
            "You are given agent1's story analysis (input) and the business_workflows "
            "produced downstream (actual_output), each with a trigger, steps, actors_involved, "
            "and success_criteria. "
            "Evaluate whether: "
            "(1) each workflow's steps follow a logical, plausible sequence a real user would "
            "perform, with no missing critical step or nonsensical ordering; "
            "(2) the actors_involved match the actions described in the steps; "
            "(3) the success_criteria are a coherent, verifiable consequence of the steps; "
            "(4) the workflow stays consistent with the business rules and testable_points "
            "from agent1's analysis. "
            "Score 1.0 if workflows are logically sound and business-coherent. "
            "Score low if steps are illogical, contradictory, or disconnected from the "
            "underlying business rules."
        ),
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=threshold,
        model=judge,
    )


# ---------------------------------------------------------------------------
# AGENT 2 — Conformité des tests aux workflows métier (agent1.5)
# ---------------------------------------------------------------------------
def agent3_workflow_compliance_metric(threshold: float = 0.7) -> GEval:
    """Les tests respectent-ils les workflows métier définis par agent1.5,
    ou s'en écartent-ils (étapes différentes, ordre différent, acteurs différents) ?"""
    return GEval(
        name="Agent3 Workflow Compliance",
        criteria=(
            "You are given the business_workflows produced by agent1.5, each with "
            "steps, actors_involved, and success_criteria (input), and the test cases "
            "generated afterward (actual_output). "
            "Check whether the test steps follow the same logical sequence, the same "
            "actors, and validate the same success_criteria as the corresponding "
            "business workflow. Flag any test that contradicts, skips a critical step "
            "of, or diverges significantly from its source workflow. "
            "Score 1.0 if tests are faithful implementations of the workflows. "
            "Score low if tests diverge from or ignore the defined workflows."
        ),
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=threshold,
        model=judge,
    )


# ---------------------------------------------------------------------------
# COUVERTURE SÉMANTIQUE INDÉPENDANTE — story -> tests (sans passer par agent4)
# Reste la seule vérification comparant directement story brute <-> tests,
# après retrait d'agent3_functional_relevance qui faisait doublon.
# ---------------------------------------------------------------------------
def independent_coverage_metric(threshold: float = 0.7) -> GEval:
    """Juge indépendant de la couverture : ne fait pas confiance au coverage_rate
    déclaré par agent4, ré-évalue depuis zéro à partir de la story et des tests."""
    return GEval(
        name="Independent Story-to-Tests Coverage",
        criteria=(
            "You are given the original Jira user story with its explicit acceptance "
            "criteria and description (input), and the full set of generated test "
            "cases (actual_output). "
            "Independently identify every distinct functional requirement, business "
            "rule, edge case, or acceptance criterion explicitly stated in the story. "
            "Then check whether each one is covered by at least one test case. "
            "Score 1.0 if all explicit requirements are covered. Score proportionally "
            "lower for each requirement that has no corresponding test. "
            "Pay special attention to edge cases, error scenarios, and accessibility "
            "or permission-related rules, which are often forgotten."
        ),
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=threshold,
        model=judge,
    )


# ---------------------------------------------------------------------------
# AGENT 5 — Fidélité et exhaustivité du rapport (au-delà des chiffres)
# ---------------------------------------------------------------------------
def agent5_fidelity_metric(threshold: float = 0.7) -> GEval:
    """Le rapport final résume-t-il fidèlement TOUTES les erreurs/risques
    identifiés en amont (agent4), sans en omettre ni en minimiser certains ?"""
    return GEval(
        name="Agent5 Report Fidelity",
        criteria=(
            "You are given agent4's full validation output including "
            "ambiguity_findings, uncovered_testable_points, and duplicate_pairs "
            "(input), and agent5's final report with its executive_summary, "
            "quality_assurance issues, and recommendations (actual_output). "
            "Check whether the report accurately and completely reflects every "
            "significant issue found by agent4: no ambiguity or coverage gap should "
            "be silently dropped, downplayed, or contradicted in the final report. "
            "Also check that recommendations are specific and actionable, not generic "
            "boilerplate disconnected from the actual issues found. "
            "Score 1.0 if the report is fully faithful and its recommendations are "
            "specific to the real issues. Score low if issues are omitted, "
            "downplayed, or if recommendations are generic/disconnected."
        ),
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=threshold,
        model=judge,
    )


# ---------------------------------------------------------------------------
# STYLE / LISIBILITÉ — nommage, structure, clarté des tests
# ---------------------------------------------------------------------------
def test_style_readability_metric(threshold: float = 0.7) -> GEval:
    """Qualité rédactionnelle indépendante des règles déterministes déjà
    vérifiées (verbe interdit) : nommage clair, lisibilité, structure standard."""
    return GEval(
        name="Test Style & Readability",
        criteria=(
            "You are given a set of generated test cases (actual_output). "
            "Evaluate their writing quality: "
            "(1) test_name is specific and descriptive, not generic ('Test 1', "
            "'Vérification générale'); "
            "(2) each step's action is a single, unambiguous, executable instruction; "
            "(3) expected_result is specific and observable, not vague ('ça marche', "
            "'affichage correct' without detail); "
            "(4) overall structure follows a standard QA test format (clear "
            "preconditions, sequential steps, verifiable outcomes). "
            "Score 1.0 if tests are clearly and professionally written. Score low if "
            "names/steps/results are vague, generic, or poorly structured."
        ),
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=threshold,
        model=judge,
    )