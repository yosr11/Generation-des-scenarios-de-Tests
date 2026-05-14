import json


def build_judge_system_prompt() -> str:
    return """
Tu es un juge expert en analyse de user stories Jira.

Compare la user story source et l’analyse produite par un autre LLM.

Règles générales :
- L’évaluation doit être SÉMANTIQUE, pas lexicale.
- Une reformulation correcte ne doit pas être pénalisée si elle conserve le même sens métier.
- Ne considère comme non fidèle qu’un élément qui ajoute une information métier nouvelle, change le sens, ou introduit une contrainte absente de la source.
- Ignore le style rédactionnel, la longueur et la formulation.

Point critique :
- Évalue si l’analyse capture correctement le BESOIN MÉTIER PRINCIPAL.
- Si la story décrit une amélioration, une évolution ou une correction (TO-BE), l’analyse doit refléter ce comportement cible.
- Si l’analyse décrit seulement le fonctionnement actuel (AS-IS) sans capturer l’objectif d’évolution, cela doit être pénalisé en fidélité.
- Si l’analyse conserve ou valide une règle que la story cherche à modifier ou supprimer, cela doit aussi être pénalisé.

Évalue uniquement ces 3 dimensions, de 0 à 100 :

1. fidelity_score
   - L’analyse est-elle sémantiquement fidèle à la story source ?
   - Capture-t-elle correctement l'intention métier principale ?
   - Les reformulations et paraphrases qui conservent le sens métier NE doivent PAS être pénalisées.
   - Les inférences raisonnables et logiques à partir du contexte de la story NE doivent PAS être pénalisées.
   - Pénalise UNIQUEMENT les vraies hallucinations : informations métier inventées qui contredisent ou n'ont aucun lien avec la story source.

2. completeness_score
   - L'analyse capture-t-elle les éléments importants PRÉSENTS dans la story source ?
   - Évalue UNIQUEMENT par rapport au contenu réel de la story source.
   - Si la story source ne mentionne pas d'acteurs explicitement, un champ actors vide ne doit PAS être pénalisé.
   - Si la story source n'a pas de critères d'acceptation écrits, leur absence dans l'analyse ne doit PAS être pénalisée.
   - Si la story est technique (migration, configuration, étude), des champs vides comme actors, business_rules, user_flows sont NORMAUX.
   - Pénalise uniquement les omissions d'éléments clairement présents et importants dans le texte de la story source.

3. coherence_score
   - L’analyse est-elle cohérente en interne ?
   - Pénalise uniquement les contradictions réelles entre les champs.

Retourne UNIQUEMENT un JSON valide avec exactement cette structure :

{
  "fidelity_score": 0,
  "completeness_score": 0,
  "coherence_score": 0,
  "summary": "",
  "final_score": 0.0
}

IMPORTANT : Les clés du JSON doivent être exactement : fidelity_score, completeness_score, coherence_score, summary, final_score.
Ne PAS utiliser "classification_score" ou tout autre nom de clé.

Règles de sortie :
- Pas d’explication hors JSON.
- summary doit être court
- final_score = moyenne simple des 3 scores.
""".strip()

def build_judge_user_prompt(story: dict, analysis: dict) -> str:
    compact_story = {
        "id": story.get("id"),
        "summary": story.get("summary"),
        "description_clean": story.get("description_clean", ""),
        "acceptance_criteria_clean": story.get("acceptance_criteria_clean", ""),
        #"labels": story.get("labels", []),
        #"priority": story.get("priority"),
        #"status": story.get("status"),
    }

    compact_analysis = {
        "actors": analysis.get("actors", []),
        "actions": analysis.get("actions", []),
        "business_rules": analysis.get("business_rules", []),
        "technical_scope": analysis.get("technical_scope", []),
        "testable_points": analysis.get("testable_points", []),
        "user_flows": analysis.get("user_flows", []),
        "acceptance_criteria_explicit": analysis.get("acceptance_criteria_explicit", []),
        "acceptance_criteria_inferred": analysis.get("acceptance_criteria_inferred", []),
        "clarification_questions": analysis.get("clarification_questions", []),
    }

    return f"""
USER STORY SOURCE :
{json.dumps(compact_story, ensure_ascii=False, indent=2)}

ANALYSE PRODUITE PAR LLAMA4 :
{json.dumps(compact_analysis, ensure_ascii=False, indent=2)}

Retourne uniquement le JSON demandé.
""".strip()