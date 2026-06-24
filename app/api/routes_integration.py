from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.jira_service import (
    add_xray_test_steps,
    create_test_issue,
    search_test_issue_by_summary,
)


class IntegrationTestStep(BaseModel):
    action: str = Field(..., description="Action claire à exécuter")
    expected_result: str = Field(..., description="Résultat attendu")
    data: Optional[str] = Field(None, description="Données additionnelles ou contexte")
    actor: Optional[str] = Field(None, description="Acteur du pas de test")


class IntegrationTestCase(BaseModel):
    test_name: str = Field(..., description="Nom du test")
    objective: str = Field(..., description="Objectif du test")
    scenario_type: Optional[str] = Field(None, description="Type de scénario")
    steps: List[IntegrationTestStep] = Field(default_factory=list)


class IntegrateTestsRequest(BaseModel):
    project_key: str = Field("YOUQA", description="Clé du projet Jira")
    tests: List[IntegrationTestCase] = Field(..., description="Liste des tests à intégrer")
    coverage_rate: Optional[float] = Field(None, ge=0, le=1, description="Taux de couverture validé")
    duplicate_count: Optional[int] = Field(0, ge=0, description="Nombre de doublons détectés")
    ambiguity_count: Optional[int] = Field(0, ge=0, description="Nombre d'ambiguïtés détectées")


class IntegrateTestSingleRequest(BaseModel):
    project_key: str = Field("YOUQA", description="Clé du projet Jira")
    test: IntegrationTestCase = Field(..., description="Test à intégrer")


class IntegrateTestsResponse(BaseModel):
    status: str = Field(..., description="success, partial or error")
    created_count: int = Field(0, description="Nombre de tests créés avec succès")
    created_keys: List[str] = Field(default_factory=list, description="Clés Jira des tests créés")
    errors: List[str] = Field(default_factory=list, description="Liste des erreurs rencontrées")


router = APIRouter(tags=["Xray Integration"])


def _build_description(test_case: IntegrationTestCase) -> str:
    """
    Construit une description lisible.
    Les vraies steps Xray sont envoyées séparément dans customfield_14404.
    """
    desc = test_case.objective or ""

    if test_case.steps:
        try:
            from app.utils.test_steps_utils import build_xray_description

            sd = [
                {
                    "action": step.action,
                    "data": step.data or "",
                    "actor": step.actor or "",
                    "expected_result": step.expected_result,
                }
                for step in test_case.steps
            ]

            desc_steps = build_xray_description({"steps": sd})
            if desc_steps:
                desc = desc_steps

        except Exception:
            pass

    return desc


def _build_step_payload(test_case: IntegrationTestCase) -> List[dict]:
    """
    Format interne envoyé à jira_service.py.
    jira_service.py convertira ensuite vers le format Xray exact.
    """
    return [
        {
            "action": step.action,
            "data": step.data or "",
            "actor": step.actor or "",
            "result": step.expected_result,
        }
        for step in test_case.steps
    ]


@router.post("/integrate-tests", response_model=IntegrateTestsResponse)
def integrate_tests(body: IntegrateTestsRequest):
    """
    Intègre plusieurs tests manuels générés dans Jira/Xray TEST.

    Correction importante :
    - Les steps sont envoyées directement pendant la création du Test.
    - On ne fait plus un deuxième appel add_xray_test_steps après création.
    """
    import logging

    logger = logging.getLogger(__name__)

    if not body.tests:
        raise HTTPException(
            status_code=400,
            detail="Aucun test fourni pour l'intégration.",
        )

    created_keys: List[str] = []
    errors: List[str] = []

    logger.info(
        f"[integrate_tests] Début intégration: {len(body.tests)} tests dans {body.project_key}"
    )

    for test_case in body.tests:
        try:
            logger.info(f"[integrate_tests] Processing: {test_case.test_name}")

            existing = search_test_issue_by_summary(
                project_key=body.project_key,
                summary=test_case.test_name,
                use_test_jira=True,
            )

            if existing:
                logger.info(f"[integrate_tests] Test already exists: {existing}")
                created_keys.append(existing)
                continue

            desc = _build_description(test_case)
            step_payload = _build_step_payload(test_case)

            issue = create_test_issue(
                project_key=body.project_key,
                summary=test_case.test_name,
                description=desc,
                issue_type="Test",
                steps=step_payload,
                use_test_jira=True,
            )

            if issue.get("error"):
                error_detail = (
                    issue.get("message")
                    or issue.get("body")
                    or issue.get("raw_body")
                    or issue.get("error")
                )
                raise ValueError(
                    f"Create test failed for '{test_case.test_name}': {error_detail}"
                )

            issue_key = issue.get("key")
            if not issue_key:
                raise ValueError(
                    f"Jira did not return issue key for test '{test_case.test_name}'"
                )

            logger.info(f"[integrate_tests] Test created with steps: {issue_key}")
            created_keys.append(issue_key)

        except Exception as exc:
            logger.error(
                f"[integrate_tests] Error for {test_case.test_name}: {exc}",
                exc_info=True,
            )
            errors.append(f"{test_case.test_name}: {str(exc)}")
            continue

    status = "success" if not errors else "partial"

    return IntegrateTestsResponse(
        status=status,
        created_count=len(created_keys),
        created_keys=created_keys,
        errors=errors,
    )


@router.post("/integrate-test", response_model=IntegrateTestsResponse)
def integrate_test_single(body: IntegrateTestSingleRequest):
    """
    Intègre un seul test manuel dans Jira/Xray TEST.

    Correction importante :
    - Les steps sont envoyées directement dans create_test_issue().
    - Pas de deuxième update après création.
    """
    import logging

    logger = logging.getLogger(__name__)

    created_keys: List[str] = []
    errors: List[str] = []

    try:
        test_case = body.test

        logger.info(f"[integrate_test_single] Processing: {test_case.test_name}")

        existing = search_test_issue_by_summary(
            project_key=body.project_key,
            summary=test_case.test_name,
            use_test_jira=True,
        )

        if existing:
            logger.info(f"[integrate_test_single] Test already exists: {existing}")
            created_keys.append(existing)

        else:
            desc = _build_description(test_case)
            step_payload = _build_step_payload(test_case)

            issue = create_test_issue(
                project_key=body.project_key,
                summary=test_case.test_name,
                description=desc,
                issue_type="Test",
                steps=step_payload,
                use_test_jira=True,
            )

            if issue.get("error"):
                error_detail = (
                    issue.get("message")
                    or issue.get("body")
                    or issue.get("raw_body")
                    or issue.get("error")
                )
                raise ValueError(
                    f"Create test failed for '{test_case.test_name}': {error_detail}"
                )

            issue_key = issue.get("key")
            if not issue_key:
                raise ValueError(
                    f"Jira did not return issue key for test '{test_case.test_name}'"
                )

            logger.info(f"[integrate_test_single] Test created with steps: {issue_key}")
            created_keys.append(issue_key)

    except Exception as exc:
        logger.error(f"[integrate_test_single] Error: {exc}", exc_info=True)
        errors.append(str(exc))

    status = "success" if not errors else "partial"

    return IntegrateTestsResponse(
        status=status,
        created_count=len(created_keys),
        created_keys=created_keys,
        errors=errors,
    )


class AddStepRequest(BaseModel):
    action: str = Field(...)
    expected_result: str = Field(...)
    data: Optional[str] = Field(None)
    actor: Optional[str] = Field(None)


@router.post("/tests/{test_key}/add-step")
def add_step_to_test(test_key: str, body: AddStepRequest):
    """
    Ajoute une step à un test Xray existant.

    Attention :
    Si Jira retourne "User does not have permission to browse or edit",
    cet endpoint ne pourra pas fonctionner sans permission Edit.
    L'intégration principale évite ce problème en créant les steps directement.
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        step_payload = [
            {
                "action": body.action,
                "data": body.data or "",
                "actor": body.actor or "",
                "result": body.expected_result,
            }
        ]

        res = add_xray_test_steps(
            test_key=test_key,
            steps=step_payload,
            use_test_jira=True,
        )

        if res.get("error"):
            return {
                "error": True,
                "detail": res.get("message")
                or res.get("fallback_error")
                or str(res),
            }

        return {"ok": True, "result": res}

    except Exception as exc:
        logger.error(
            f"[add_step_to_test] Error adding step to {test_key}: {exc}",
            exc_info=True,
        )
        return {"error": True, "detail": str(exc)}
