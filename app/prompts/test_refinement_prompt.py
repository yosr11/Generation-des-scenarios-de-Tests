"""Prompts pour l'assistant IA de refinement des tests manuels."""

from __future__ import annotations

import json
from typing import Any, Dict, List


def build_test_refinement_system_prompt() -> str:
    return """Tu es un assistant QA expert qui aide les testeurs à affiner des cas de test manuels Xray.
Tu reçois un cas de test JSON et une instruction en langage naturel.

Règles impératives :
- Réponds UNIQUEMENT en JSON strict avec les clés "assistant_message" (string, en français) et "test" (objet test complet).
- Conserve le schéma du test : story_id, test_name, objective, description, execution_context, preconditions, scenario_type, priority, labels, étapes, steps.
- Structure préférée : "étapes"[] avec titre, actor (acteur de l'étape), steps[] (sous-étapes atomiques).
- Les acteurs sont associés UNIQUEMENT aux étapes (étapes[].actor), JAMAIS aux sous-étapes (steps[].actor doit rester "").
- Chaque sous-étape a : index, action, data, actor (""), expected_result, revision_po ("").
- Le champ "description" doit lister les titres d'étapes au format : [Acteur] **Verbe** reste du titre (une ligne par étape).
- Ne préfixe PAS les actions des sous-étapes avec [Acteur] — l'acteur apparaît seulement sur l'étape parente.
- Applique uniquement les modifications demandées ; ne réécris pas tout le test sans raison.
- Garde le français pour tout le contenu généré.
- Si l'instruction est ambiguë, fais la modification la plus raisonnable et explique brièvement dans assistant_message."""


def build_test_refinement_user_prompt(
    test: Dict[str, Any],
    user_message: str,
    chat_history: List[Dict[str, str]] | None = None,
    story_context: Dict[str, Any] | None = None,
) -> str:
    history_block = ""
    if chat_history:
        lines = []
        for msg in chat_history[-8:]:
            role = msg.get("role", "user")
            content = (msg.get("content") or "").strip()
            if content:
                lines.append(f"{role.upper()}: {content}")
        if lines:
            history_block = (
                "Historique récent de la conversation :\n" + "\n".join(lines) + "\n\n"
            )

    context_block = ""
    if story_context:
        context_block = (
            "Contexte story (référence uniquement) :\n"
            f"- ID : {story_context.get('story_id', '')}\n"
            f"- Résumé : {story_context.get('summary', '')}\n"
            f"- Acteurs story : {', '.join(story_context.get('actors') or [])}\n\n"
        )

    test_json = json.dumps(test, ensure_ascii=False, indent=2)
    return (
        f"{context_block}"
        f"{history_block}"
        f"Cas de test actuel (JSON) :\n{test_json}\n\n"
        f"Instruction du testeur :\n{user_message.strip()}\n\n"
        "Retourne le JSON avec assistant_message et test (test complet mis à jour)."
    )
