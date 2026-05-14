from typing import Dict, Any, Tuple


def decide_manual_test_strategy(story: Dict[str, Any], analysis: Dict[str, Any]) -> Tuple[str, str]:
    """
    Retourne :
    - strategy: manual | automated | needs_refinement
    - reason: explication textuelle
    """

    story_type = (analysis.get("story_type") or "").strip()
    exploitability = (analysis.get("exploitability") or "").strip()
    description = (story.get("description_clean") or "").strip()
    ac_explicit = analysis.get("acceptance_criteria_explicit") or []
    actions = analysis.get("actions") or []
    testable_points = analysis.get("testable_points") or []

    # Stories trop faibles ou documentaires
    if story_type in ["documentation", "poc_or_study", "invalid_or_too_weak"]:
        return "needs_refinement", "La story n'est pas suffisamment exploitable pour générer un test manuel."

    # Stories techniques : on ne traite pas maintenant
    if story_type == "technical":
        return "automated", "Cette story semble plutôt adaptée à un traitement automatisé ou technique."

    # Low exploitability -> pas de génération fiable
    if exploitability == "low":
        return "needs_refinement", "La story est trop peu exploitable pour une génération manuelle fiable."

    # Pas de description + pas d'AC + peu d'actions
    if not description and not ac_explicit and len(actions) == 0:
        return "needs_refinement", "La story ne contient pas assez d'informations pour générer un test manuel."

    # Fonctionnelle exploitable
    if story_type == "functional" and exploitability in ["high", "medium"]:
        if description or ac_explicit or testable_points:
            return "manual", "La story est adaptée à la génération d'un test manuel."
        return "needs_refinement", "La story fonctionnelle manque encore d'informations pour une génération fiable."

    # Non fonctionnelle : hors scope manuel pour cette version
    if story_type == "non_functional":
        return "automated", "Cette story relève plutôt d'une vérification non fonctionnelle ou automatisée."

    return "needs_refinement", "Cas non couvert ou informations insuffisantes."