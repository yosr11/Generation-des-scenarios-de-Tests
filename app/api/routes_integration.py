from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import CurrentUser, get_client_ip, get_current_user, get_tester_jira_credentials
from app.db.postgres import get_db
from app.services.audit_service import log_action
from app.services.jira_service import (
    add_xray_test_steps,
    create_test_issue,
    create_user_jira_session,
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


def _resolve_jira_session(user: CurrentUser):
    if user.is_tester:
        creds = get_tester_jira_credentials(user)
        return create_user_jira_session(creds.username, creds.password)
    return None


def _use_test_jira() -> bool:
    """Keep Xray integration on the same Jira instance as auth/project selection."""
    return settings.JIRA_BASE_URL.rstrip("/") == settings.JIRA_TEST_URL.rstrip("/")


def _build_description(test_case: IntegrationTestCase) -> str:
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
async def integrate_tests(
    body: IntegrateTestsRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import logging

    logger = logging.getLogger(__name__)

    if not body.tests:
        raise HTTPException(
            status_code=400,
            detail="Aucun test fourni pour l'intégration.",
        )

    jira_session = _resolve_jira_session(user)
    use_test_jira = _use_test_jira()
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
                use_test_jira=use_test_jira,
                session=jira_session,
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
                use_test_jira=use_test_jira,
                session=jira_session,
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

    await log_action(
        db,
        user_identifier=user.email or user.jira_username or user.user_id,
        role=user.role,
        action="integrate_tests",
        resource=body.project_key,
        details=f"created={len(created_keys)}, errors={len(errors)}",
        ip_address=get_client_ip(request),
    )

    return IntegrateTestsResponse(
        status=status,
        created_count=len(created_keys),
        created_keys=created_keys,
        errors=errors,
    )


@router.post("/integrate-test", response_model=IntegrateTestsResponse)
async def integrate_test_single(
    body: IntegrateTestSingleRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import logging

    logger = logging.getLogger(__name__)

    jira_session = _resolve_jira_session(user)
    use_test_jira = _use_test_jira()
    created_keys: List[str] = []
    errors: List[str] = []

    try:
        test_case = body.test

        logger.info(f"[integrate_test_single] Processing: {test_case.test_name}")

        existing = search_test_issue_by_summary(
            project_key=body.project_key,
            summary=test_case.test_name,
            use_test_jira=use_test_jira,
            session=jira_session,
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
                use_test_jira=use_test_jira,
                session=jira_session,
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

    await log_action(
        db,
        user_identifier=user.email or user.jira_username or user.user_id,
        role=user.role,
        action="integrate_test",
        resource=f"{body.project_key}/{body.test.test_name}",
        details=f"keys={created_keys}",
        ip_address=get_client_ip(request),
    )

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
def add_step_to_test(
    test_key: str,
    body: AddStepRequest,
    user: CurrentUser = Depends(get_current_user),
):
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
            use_test_jira=_use_test_jira(),
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
