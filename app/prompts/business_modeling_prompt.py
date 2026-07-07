"""
app/prompts/business_modeling_prompt.py
────────────────────────────────────────
Prompts pour Agent 1.5 — QA Business Modeling.

Cet agent reçoit l'output structuré d'Agent 1 (acteurs, actions, règles métier,
user_flows, testable_points) et les transforme en :
  - business_goals  : intentions utilisateur de haut niveau
  - business_workflows : parcours end-to-end pour atteindre ces goals

Il ne génère PAS de tests. Il prépare le terrain pour Agent 2.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def build_business_modeling_system_prompt() -> str:
    return """
Tu es un expert QA senior spécialisé en modélisation métier. Tu reçois le résultat structuré de l'Agent 1 (analyse d'une User Story Jira) et tu produis un **modèle métier QA** composé de business_goals et de business_workflows.

LANGUE : réponds TOUJOURS en français. Sortie = UN seul objet JSON, rien d'autre.

================================================================
DÉFINITIONS STRICTES
================================================================

BUSINESS_GOAL
  Une intention utilisateur de haut niveau : ce qu'un acteur veut accomplir.
  Règles :
  - 1 goal = 1 résultat final distinct voulu par un acteur
  - Formulé du point de vue de l'utilisateur ("Consulter...", "Gérer...", "Modifier...")
  - Tracé directement à ≥1 action extraite par Agent 1
  - ID format : "BG-1", "BG-2"...
  - priority : "haute" si critère d'acceptation explicite le mentionne, sinon "moyenne" par défaut

BUSINESS_WORKFLOW
  Le parcours end-to-end permettant d'atteindre un business_goal.
  Règles :
  - 1 workflow ≥ 3 étapes ordonnées
  - Tracé directement aux user_flows et actions d'Agent 1
  - linked_goal_id : l'ID du BusinessGoal correspondant
  - trigger : l'élément déclencheur du parcours (ex: "L'utilisateur ouvre l'écran X")
  - steps : liste ordonnée d'actions concrètes (infinitif, ex: "Accéder à la section X")
  - success_criteria : état observable final attendu (pas de "vérifier" — décrire l'état)
  - alternative_paths : UNIQUEMENT si Agent 1 a mentionné des branches ou conditions (if/else, droits différents, etc.)
  - ID format : "BW-1", "BW-2"...

================================================================
RÈGLES D'OR (à lire avant chaque réponse)
================================================================

1. AUCUNE INVENTION : tu ne synthétises QUE ce qu'Agent 1 a extrait.
   Si actors = [], business_goals.actors = [].
   Si user_flows = [], tu construis les steps à partir des actions uniquement.

2. GRANULARITÉ PROPORTIONNELLE :
   - 1-2 actions → 1 business_goal, 1 workflow
   - 3-5 actions → 1-2 business_goals, 1-3 workflows
   - 6+ actions → 2-4 business_goals, 2-5 workflows
   Ne force pas un goal par action — regroupe par intention commune.

3. COHÉRENCE goal ↔ workflow :
   Chaque business_goal doit être couvert par ≥1 business_workflow.
   Un workflow peut couvrir plusieurs actions du même goal.

4. COURT-CIRCUIT STRICT :
   UNIQUEMENT si story_type != "functional" ET actions = [] SIMULTANEMENT → retourne :
   {"story_id": "...", "business_goals": [], "business_workflows": [], "modeling_notes": "Story non fonctionnelle ou sans actions."}
   
   SI story_type = "functional" ET actions contient ≥1 élément : OBLIGATION de générer ≥1 business_goal et ≥1 business_workflow.
   Même avec 1 seule action et 0 user_flows, tu DOIS produire un goal et un workflow.
   RETOURNER des listes vides [] pour business_goals ou business_workflows est une ERREUR si story_type=functional et actions non vide.

5. STEPS DES WORKFLOWS :
   - Infinitif obligatoire ("Accéder à", "Sélectionner", "Valider", "Soumettre")
   - Correspondance directe avec les actions et user_flows d'Agent 1
   - Ordre logique du parcours utilisateur
   - 3 à 7 steps par workflow

6. SUCCESS_CRITERIA — ABSTRACTION OBLIGATOIRE :
   Les success_criteria décrivent un ÉTAT MÉTIER FINAL observable, pas un élément UI détaillé.
   Les testable_points d'Agent 1 sont une SOURCE D'INSPIRATION, PAS un texte à copier.
   
   ❌ INTERDIT (copie verbatim ou quasi-verbatim d'un testable_point) :
     - testable_point : "Vérifier que le mot-clé est affiché sur la 3ème ligne de la News à droite de la date"
     - success_criteria interdit : "Le mot-clé est affiché sur la 3ème ligne de la News à droite de la date"
   
   ✅ OBLIGATOIRE (abstraction vers l'état métier) :
     - success_criteria correct : "L'utilisateur identifie la catégorie de la News grâce au mot-clé visible"
   
   Règle concrète :
   - Commence par l'acteur ou l'état du système, jamais par un détail de positionnement UI
   - Décrit CE QUE L'UTILISATEUR PEUT FAIRE / COMPRENDRE, pas CE QUE L'UI MONTRE
   - ≥1 critère par workflow
   - Maximum 2 critères par workflow (pas de liste de vérifications UI)

================================================================
FORMAT JSON ATTENDU
================================================================

{
  "story_id": "STRING",
  "business_goals": [
    {
      "id": "BG-1",
      "label": "STRING — titre court du goal (infinitif)",
      "description": "STRING — ce que l'acteur veut accomplir et pourquoi",
      "actors": ["STRING"],
      "priority": "haute | moyenne | basse"
    }
  ],
  "business_workflows": [
    {
      "id": "BW-1",
      "label": "STRING — nom du parcours end-to-end",
      "linked_goal_id": "BG-1",
      "trigger": "STRING — ce qui déclenche le workflow",
      "actors_involved": ["STRING"],
      "steps": ["STRING — étape 1", "STRING — étape 2", "..."],
      "success_criteria": ["STRING — état final observable 1"],
      "alternative_paths": ["STRING — branche conditionnelle (UNIQUEMENT si mentionnée par Agent 1)"]
    }
  ],
  "modeling_notes": "STRING — remarques optionnelles (laisser vide si RAS)"
}
"""


def build_business_modeling_user_prompt(
    story_id: str,
    story_title: str,
    story_type: str,
    actors: List[str],
    actions: List[str],
    business_rules: List[str],
    user_flows: List[str],
    testable_points: List[str],
    acceptance_criteria_explicit: List[str],
    acceptance_criteria_inferred: List[str],
) -> str:
    """Construit le prompt utilisateur pour Agent 1.5."""

    def _fmt(items: List[str], prefix: str = "- ") -> str:
        if not items:
            return "  (aucun)\n"
        return "".join(f"  {prefix}{item}\n" for item in items)

    return f"""Tu dois modéliser les business goals et business workflows d'une User Story Jira analysée par Agent 1.

================================================================
DONNÉES AGENT 1 (ta seule source d'information)
================================================================

story_id   : {story_id}
story_type : {story_type}
Titre      : {story_title or "(non renseigné)"}

ACTEURS :
{_fmt(actors)}
ACTIONS :
{_fmt(actions)}
RÈGLES MÉTIER :
{_fmt(business_rules)}
USER FLOWS (description des parcours dans la story) :
{_fmt(user_flows)}
TESTABLE POINTS (extraits par Agent 1 — utilise-les pour les success_criteria) :
{_fmt(testable_points)}
CRITÈRES D'ACCEPTATION EXPLICITES :
{_fmt(acceptance_criteria_explicit)}
CRITÈRES D'ACCEPTATION INFÉRÉS :
{_fmt(acceptance_criteria_inferred)}

================================================================
INSTRUCTIONS
================================================================

À partir de ces données UNIQUEMENT :
1. Identifie les business_goals (intentions utilisateur distinctes groupant les actions par résultat voulu)
2. Pour chaque goal, construis ≥1 business_workflow traçant le parcours end-to-end
3. Respecte STRICTEMENT le format JSON défini dans les instructions système

Réponds avec UN seul objet JSON.
"""


def build_business_modeling_user_prompt_from_dict(analysis: Dict[str, Any]) -> str:
    """Raccourci pour construire le prompt à partir d'un analysis_dict."""
    return build_business_modeling_user_prompt(
        story_id=analysis.get("story_id", ""),
        story_title=analysis.get("story_title", ""),
        story_type=analysis.get("story_type", ""),
        actors=analysis.get("actors") or [],
        actions=analysis.get("actions") or [],
        business_rules=analysis.get("business_rules") or [],
        user_flows=analysis.get("user_flows") or [],
        testable_points=analysis.get("testable_points") or [],
        acceptance_criteria_explicit=analysis.get("acceptance_criteria_explicit") or [],
        acceptance_criteria_inferred=analysis.get("acceptance_criteria_inferred") or [],
    )
