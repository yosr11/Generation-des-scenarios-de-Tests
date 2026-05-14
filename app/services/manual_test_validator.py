from typing import List
from app.models.test_manual import ManualTestGenerationResult


FORBIDDEN_ACTION_STARTS = ["vérifier", "verifier"]
FORBIDDEN_OBJECTIVE_STARTS = ["vérifier", "verifier"]


def validate_manual_generation_result(result: ManualTestGenerationResult) -> List[str]:
    """
    Validation structurelle uniquement — checks fiables sans faux positifs.
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
            else:
                lowered_objective = test.objective.strip().lower()
                for forbidden in FORBIDDEN_OBJECTIVE_STARTS:
                    if lowered_objective.startswith(forbidden):
                        errors.append(
                            f"[{test.story_id}] objective commence par '{forbidden}'."
                        )

            if len(test.steps) == 0:
                errors.append(f"[{test.story_id}] aucun step généré.")

            if len(test.steps) > 15:
                errors.append(f"[{test.story_id}] plus de 15 étapes générées.")

            for step in test.steps:
                action = step.action.strip()
                expected = step.expected_result.strip()

                if not action:
                    errors.append(f"[{test.story_id}] step {step.index}: action vide.")
                else:
                    lowered = action.lower()
                    for forbidden in FORBIDDEN_ACTION_STARTS:
                        if lowered.startswith(forbidden):
                            errors.append(
                                f"[{test.story_id}] step {step.index}: l'action commence par '{forbidden}'."
                            )

                if not expected:
                    errors.append(f"[{test.story_id}] step {step.index}: expected_result vide.")

    return errors
