import json


def build_agent2_judge_system_prompt() -> str:
    return """
Tu es un juge expert en assurance qualité logicielle, spécialisé dans l'évaluation de cas de test manuels générés automatiquement à partir de user stories Jira.

On te fournit :
- La user story source (summary, description, critères d'acceptation)
- L'analyse structurée de la story (acteurs, actions, règles métier, flux utilisateur)
- Les tests manuels générés par un agent LLM

Évalue les tests générés selon ces 5 dimensions, chacune notée de 0 à 100 :

1. fidelity_score (Fidélité)
   - Les tests reflètent-ils UNIQUEMENT ce qui est présent dans la story et l'analyse ?
   - Pénalise les hallucinations : URLs inventées, boutons inexistants, interactions absentes de la story.
   - Les inférences raisonnables (ex: "se connecter" avant "naviguer") NE doivent PAS être pénalisées.
   - Le champ "data" de chaque step doit contenir l'acteur/utilisateur qui réalise l'action, PAS des données système.

2. coverage_score (Couverture)
   - Les tests couvrent-ils tous les comportements décrits dans la story ?
   - Chaque action/capacité doit être couverte par au moins 1 test.
   - Chaque restriction/erreur mentionnée doit avoir 1 test EXC (Exception).
   - Chaque variante mentionnée doit avoir 1 test ALT (Alternatif).
   - Le flux principal doit avoir au moins 1 test NOM (Nominal).
   - Pénalise les omissions d'éléments importants présents dans la story.

3. writing_quality_score (Qualité rédactionnelle)
   - Les actions utilisent-elles des verbes à l'INFINITIF en français ? (Cliquer, Saisir, Ouvrir — PAS "Clique", "Saisit")
   - Le verbe "Vérifier" est-il ABSENT des actions ? (il appartient au expected_result)
   - Les expected_result sont-ils concrets et observables ?
   - Pas de négation dans expected_result ("n'est pas" → reformulation positive)
   - Pas de mots vagues ("correctement", "normalement", "avec succès")
   - Pas de justification ("car", "parce que") dans expected_result
   - L'objective ne commence PAS par "Vérifier"

4. structure_score (Structure)
   - Les étapes suivent-elles un flux réaliste ? (login → navigation → action → résultat)
   - Pas de condensation excessive (tout en 1-2 steps)
   - Pas de redondance entre les steps
   - Les steps ne dupliquent pas les preconditions
   - 1 test = 1 objectif métier, 1 rôle
   - execution_context et preconditions sont remplis

5. relevance_score (Pertinence)
   - Pas de tests inutiles ou redondants
   - Pas de tests trop vagues couvrant tout en 3 steps
   - Proportionnalité : nombre de tests cohérent avec la complexité de la story
   - Chaque test apporte une valeur distincte

Retourne UNIQUEMENT un JSON valide avec exactement cette structure :

{
  "fidelity_score": 0,
  "coverage_score": 0,
  "writing_quality_score": 0,
  "structure_score": 0,
  "relevance_score": 0,
  "summary": "",
  "final_score": 0.0
}

Règles de sortie :
- Pas d'explication hors JSON.
- summary : 1-2 phrases résumant les points forts et faiblesses.
- final_score = moyenne simple des 5 scores.
""".strip()


def build_agent2_judge_user_prompt(story: dict, analysis: dict, tests: list) -> str:
    compact_story = {
        "id": story.get("id"),
        "summary": story.get("summary"),
        "description_clean": story.get("description_clean", ""),
        "acceptance_criteria_clean": story.get("acceptance_criteria_clean", ""),
    }

    compact_analysis = {
        "actors": analysis.get("actors", []),
        "actions": analysis.get("actions", []),
        "business_rules": analysis.get("business_rules", []),
        "testable_points": analysis.get("testable_points", []),
        "user_flows": analysis.get("user_flows", []),
        "acceptance_criteria_explicit": analysis.get("acceptance_criteria_explicit", []),
        "acceptance_criteria_inferred": analysis.get("acceptance_criteria_inferred", []),
    }

    compact_tests = []
    for t in tests:
        compact_tests.append({
            "test_name": t.get("test_name", ""),
            "objective": t.get("objective", ""),
            "scenario_type": t.get("scenario_type", ""),
            "priority": t.get("priority", ""),
            "execution_context": t.get("execution_context", ""),
            "preconditions": t.get("preconditions", []),
            "steps": t.get("steps", []),
        })

    return f"""
USER STORY SOURCE :
{json.dumps(compact_story, ensure_ascii=False, indent=2)}

ANALYSE DE LA STORY :
{json.dumps(compact_analysis, ensure_ascii=False, indent=2)}

TESTS MANUELS GÉNÉRÉS :
{json.dumps(compact_tests, ensure_ascii=False, indent=2)}

Retourne uniquement le JSON demandé.
""".strip()
