import re
from typing import Any, List, Tuple, Union

from app.models.test_manual import ManualTestGenerationResult


FORBIDDEN_ACTION_STARTS = ["vérifier", "verifier"]
FORBIDDEN_OBJECTIVE_STARTS = ["vérifier", "verifier"]

# Seuils de granularité — utilisés pour les avertissements QA (non bloquants).
MIN_ACTION_WORDS = 3
MIN_STEPS_PER_TEST = 1

_WORD_RE = re.compile(r"\b[\wÀ-ÿ'’-]+\b", re.UNICODE)


def _count_words(text: str) -> int:
    return len(_WORD_RE.findall(text or ""))


def _step_field(step: Any, field: str, default: str = "") -> str:
    if isinstance(step, dict):
        return (step.get(field) or default).strip()
    return (getattr(step, field, default) or default).strip()


def _step_index(step: Any) -> int:
    if isinstance(step, dict):
        return int(step.get("index") or 0)
    return int(getattr(step, "index", 0) or 0)


def collect_step_golden_rule_warnings(
    story_id: str,
    etape_idx: int | None,
    step: Any,
) -> List[str]:
    """Avertissements golden rules non bloquants pour une action de test."""
    warnings: List[str] = []
    action = _step_field(step, "action")
    data_field = _step_field(step, "data")
    step_label = (
        f"ÉTAPE {etape_idx} step {_step_index(step)}"
        if etape_idx
        else f"step {_step_index(step)}"
    )

    if action:
        lowered = action.lower()
        for forbidden in FORBIDDEN_ACTION_STARTS:
            if lowered.startswith(forbidden):
                warnings.append(
                    f"[{story_id}] {step_label} : l'action commence par « {forbidden} » "
                    "(préférer un verbe d'action : Cliquer, Saisir, Consulter, Valider…)."
                )
        if _count_words(action) < MIN_ACTION_WORDS:
            warnings.append(
                f"[{story_id}] {step_label} : action « {action} » courte "
                f"(recommandé : min {MIN_ACTION_WORDS} mots — verbe + objet + complément)."
            )

    if not data_field:
        warnings.append(
            f"[{story_id}] {step_label} : champ data vide (à compléter par le QA : acteur, contexte ou données)."
        )

    return warnings


def collect_test_golden_rule_warnings(test: Union[dict, Any]) -> List[Tuple[str, List[str]]]:
    """
    Retourne les avertissements par step sous forme (label, messages).
    Accepte un dict (UI/API) ou un ManualTestCase Pydantic.
    """
    if isinstance(test, dict):
        story_id = (test.get("story_id") or "").strip()
        objective = (test.get("objective") or "").strip()
        etapes = test.get("étapes") or []
        steps = test.get("steps") or []
    else:
        story_id = (getattr(test, "story_id", "") or "").strip()
        objective = (getattr(test, "objective", "") or "").strip()
        etapes = getattr(test, "étapes", None) or []
        steps = getattr(test, "steps", None) or []

    per_step: List[Tuple[str, List[str]]] = []

    if objective:
        lowered_objective = objective.lower()
        for forbidden in FORBIDDEN_OBJECTIVE_STARTS:
            if lowered_objective.startswith(forbidden):
                per_step.append((
                    "objective",
                    [
                        f"[{story_id}] objective commence par « {forbidden} » "
                        "(préférer un verbe d'action à l'infinitif)."
                    ],
                ))

    if etapes:
        for etape_idx, etape in enumerate(etapes, 1):
            if isinstance(etape, dict):
                etape_steps = etape.get("steps") or []
            else:
                etape_steps = getattr(etape, "steps", None) or []
            for step in etape_steps:
                label = f"ÉTAPE {etape_idx} step {_step_index(step)}"
                msgs = collect_step_golden_rule_warnings(story_id, etape_idx, step)
                if msgs:
                    per_step.append((label, msgs))
    else:
        for step in steps:
            label = f"step {_step_index(step)}"
            msgs = collect_step_golden_rule_warnings(story_id, None, step)
            if msgs:
                per_step.append((label, msgs))

    return per_step


def collect_golden_rule_warnings(result: ManualTestGenerationResult) -> List[str]:
    """Agrège tous les avertissements golden rules (non bloquants)."""
    warnings: List[str] = []
    if result.generation_status != "generated" or not result.tests:
        return warnings

    for test in result.tests:
        for _label, msgs in collect_test_golden_rule_warnings(test):
            warnings.extend(msgs)
    return warnings


def validate_manual_generation_result(result: ManualTestGenerationResult) -> List[str]:
    """
    Validation structurelle bloquante uniquement.
    Les golden rules (data vide, action courte, verbe « vérifier »…) sont des avertissements QA.
    """
    errors: List[str] = []

    if result.generation_status == "generated":
        if not result.tests:
            errors.append("Le statut est 'generated' mais aucun test n'a été produit.")

        for test in result.tests:
            if not test.test_name.strip():
                errors.append(f"[{test.story_id}] test_name vide.")

            if not test.objective.strip():
                errors.append(f"[{test.story_id}] objective vide.")

            etapes = getattr(test, "étapes", None) or []
            if etapes:
                if len(etapes) < MIN_STEPS_PER_TEST:
                    errors.append(
                        f"[{test.story_id}] test '{test.test_name.strip()}' a seulement "
                        f"{len(etapes)} étape(s) — minimum attendu : {MIN_STEPS_PER_TEST}."
                    )
                if len(etapes) > 10:
                    errors.append(f"[{test.story_id}] plus de 10 étapes générées.")

                for etape_idx, etape in enumerate(etapes, 1):
                    titre = _extract_etape_field(etape, "titre")
                    if not titre:
                        errors.append(f"[{test.story_id}] ÉTAPE {etape_idx}: titre vide.")

                    if isinstance(etape, dict):
                        etape_steps = etape.get("steps", [])
                    else:
                        etape_steps = getattr(etape, "steps", [])

                    if not etape_steps:
                        errors.append(f"[{test.story_id}] ÉTAPE {etape_idx}: aucun step.")

                    for step in etape_steps:
                        _validate_step_structure(test.story_id, etape_idx, step, errors)
            else:
                if len(test.steps) == 0:
                    errors.append(f"[{test.story_id}] aucun step généré.")
                elif len(test.steps) < MIN_STEPS_PER_TEST:
                    errors.append(
                        f"[{test.story_id}] test '{test.test_name.strip()}' a seulement "
                        f"{len(test.steps)} étape(s) — minimum attendu : {MIN_STEPS_PER_TEST}."
                    )

                if len(test.steps) > 15:
                    errors.append(f"[{test.story_id}] plus de 15 étapes générées.")

                for step in test.steps:
                    _validate_step_structure(test.story_id, None, step, errors)

    return errors


def _validate_step_structure(
    story_id: str,
    etape_idx: int | None,
    step: Any,
    errors: List[str],
) -> None:
    """Valide uniquement les champs structurels obligatoires d'un step."""
    action = _step_field(step, "action")
    expected = _step_field(step, "expected_result")
    step_label = (
        f"ÉTAPE {etape_idx} step {_step_index(step)}"
        if etape_idx
        else f"step {_step_index(step)}"
    )

    if not action:
        errors.append(f"[{story_id}] {step_label}: action vide.")
    if not expected:
        errors.append(f"[{story_id}] {step_label}: expected_result vide.")


def _extract_etape_field(etape, field_name: str, default: str = "") -> str:
    """Extrait un champ d'un objet étape (dict ou Pydantic)."""
    if isinstance(etape, dict):
        return (etape.get(field_name) or default).strip()
    return (getattr(etape, field_name, default) or default).strip()
