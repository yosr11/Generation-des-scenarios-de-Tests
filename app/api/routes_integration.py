from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import CurrentUser, get_client_ip, get_current_user, get_tester_jira_credentials
from app.db.postgres import get_db
from app.services.audit_service import log_action
from app.services.jira_service import (
    _normalize_priority_for_jira,
    _update_issue_fields,
    add_xray_test_steps,
    create_test_issue,
    create_user_jira_session,
    link_test_to_story_and_related_tests,
    replace_xray_test_steps,
    search_test_issue_by_summary,
)
from app.utils.test_steps_utils import bold_first_word, color_actor_bracket

class IntegrationTestStep(BaseModel):
    action: str = Field(..., description="Action claire à exécuter")
    expected_result: str = Field(..., description="Résultat attendu")
    data: Optional[str] = Field(None, description="Données additionnelles ou contexte")
    actor: Optional[str] = Field(None, description="Acteur du pas de test")


class IntegrationTestCase(BaseModel):
    test_name: str = Field(..., description="Nom du test")
    story_key: Optional[str] = Field(None, description="Clé Jira de la User Story liée")
    objective: str = Field(..., description="Objectif du test")
    scenario_type: Optional[str] = Field(None, description="Type de scénario")
    priority: Optional[str] = Field(None, description="Priorité du test (ex: HIGH, MEDIUM, LOW)")
    preconditions: List[str] = Field(default_factory=list, description="Préconditions du test")
    steps: List[IntegrationTestStep] = Field(default_factory=list)
    etapes: Optional[List[Dict[str, Any]]] = Field(default=None, alias='étapes')

    class Config:
        allow_population_by_field_name = True

   


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
    jira_browse_base_url: Optional[str] = Field(None, description="Base URL Jira pour consulter les tests")
    errors: List[str] = Field(default_factory=list, description="Liste des erreurs rencontrées")


router = APIRouter(tags=["Xray Integration"])


def _truncate_summary(summary: str, max_length: int = 255) -> str:
    """Tronque le summary à la limite Jira (255 caractères)."""
    if len(summary) <= max_length:
        return summary
    return summary[: max_length - 1] + "…"


def _resolve_jira_session(user: CurrentUser):
    if user.is_tester:
        try:
            creds = get_tester_jira_credentials(user)
            return create_user_jira_session(creds.username, creds.password)
        except HTTPException as exc:
            if exc.status_code == 401 and settings.JIRA_USERNAME and settings.JIRA_PASSWORD:
                return create_user_jira_session(settings.JIRA_USERNAME, settings.JIRA_PASSWORD)
            raise

    if settings.JIRA_USERNAME and settings.JIRA_PASSWORD:
        return create_user_jira_session(settings.JIRA_USERNAME, settings.JIRA_PASSWORD)

    raise HTTPException(
        status_code=401,
        detail="Jira session expired. Please log in again.",
    )


def _use_test_jira() -> bool:
    return settings.XRAY_USE_TEST_JIRA


def _jira_browse_base_url(use_test_jira: bool) -> str:
    base_url = settings.JIRA_TEST_URL if use_test_jira else settings.JIRA_BASE_URL
    return f"{base_url.rstrip('/')}/browse"


def _build_description(test_case: IntegrationTestCase) -> str:
    desc = test_case.objective or ""

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
        ] if test_case.steps else []

        desc_steps = build_xray_description(
            {
                "preconditions": test_case.preconditions,
                "étapes": test_case.etapes,
                "steps": sd,
            }
        )
        if desc_steps:
            return desc_steps
    except Exception:
        pass

    return desc


def _build_step_payload(test_case: IntegrationTestCase) -> List[dict]:
    def sanitize(value: Optional[str]) -> str:
        if not value:
            return ""
        t = str(value)
        t = t.replace("•", "-")
        t = t.replace("\u2022", "-")
        t = t.replace("**", "")
        t = t.replace("*", "")
        t = t.replace("__", "")
        t = t.replace("<br>", "\n")
        t = t.replace("<br/>", "\n")
        t = t.replace("<br />", "\n")
        t = t.strip()
        return t

    def normalize_precondition(value: str) -> str:
        value = value.strip()
        lower = value.lower()
        if not value:
            return value
        if lower.startswith("exécuter la précondition suivante"):
            return value
        if value.endswith(":"):
            return f"Exécuter la précondition suivante {value}"
        return f"Exécuter la précondition suivante: {value}"

    payload: List[dict] = []

    for precondition in getattr(test_case, "preconditions", []) or []:
        pre = sanitize(precondition)
        if not pre:
            continue
        action_text = normalize_precondition(pre)
        payload.append({
            "action": f"*ÉTAPE* : {bold_first_word(action_text)}",
            "data": None,
            "result": "none",
        })

    if getattr(test_case, "etapes", None):
        for etape in test_case.etapes:
            etape_dict = etape or {}
            titre = sanitize(etape_dict.get("titre") or "")
            actor = sanitize(etape_dict.get("actor") or "")
            substeps = etape_dict.get("steps") or []
            actions = [sanitize((step or {}).get("action") or "") for step in substeps]
            expecteds = [sanitize((step or {}).get("expected_result") or (step or {}).get("result") or "") for step in substeps]

            action_lines = []
            step_actor = f"{color_actor_bracket(actor)} " if actor else ""
            if titre:
                action_lines.append(f"*ÉTAPE* : {step_actor}{bold_first_word(titre)}")
            if actions:
                action_lines.append("*ACTION(S)* :")
                for action in actions:
                    if action:
                        action_lines.append(f"- {bold_first_word(action)}")

            action_text = "\n".join(line for line in action_lines if line).strip()
            result_text = "\n".join([r for r in expecteds if r]) or "none"

            payload.append({
                "action": action_text,
                "data": "none",
                "result": result_text,
            })
        return payload

    if test_case.steps:
        payload.extend(
            {
                "action": step.action,
                "data": "none",
                "actor": step.actor or "none",
                "result": step.expected_result or "none",
            }
            for step in test_case.steps
        )

    return payload

  

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

            safe_summary = _truncate_summary(test_case.test_name)

            existing = search_test_issue_by_summary(
                project_key=body.project_key,
                summary=safe_summary,
                use_test_jira=use_test_jira,
                session=jira_session,
            )

            if existing:
                logger.info(f"[integrate_tests] Test already exists: {existing}")

                desc = _build_description(test_case)
                step_payload = _build_step_payload(test_case)

                update_fields = {"description": desc}
                normalized_priority = _normalize_priority_for_jira(test_case.priority)
                if normalized_priority:
                    update_fields["priority"] = {"name": normalized_priority}

                update_result = _update_issue_fields(
                    issue_key=existing,
                    fields=update_fields,
                    use_test_jira=use_test_jira,
                    session=jira_session,
                )
                if update_result.get("error"):
                    raise ValueError(
                        f"Update test failed for '{safe_summary}': {update_result.get('message') or update_result.get('body') or update_result.get('raw_body') or update_result.get('error')}"
                    )

                if step_payload:
                    replace_result = replace_xray_test_steps(
                        test_key=existing,
                        steps=step_payload,
                        use_test_jira=use_test_jira,
                        session=jira_session,
                    )
                    if replace_result.get("error"):
                        import json as _json
                        raise ValueError(
                            f"Update test failed for '{safe_summary}': "
                            f"{replace_result.get('message') or replace_result.get('detail') or replace_result.get('body') or replace_result.get('error')}\n"
                            f"Détails: {_json.dumps(replace_result.get('api_errors', replace_result.get('detail', {})), ensure_ascii=False, indent=2)}"
                        )

                # 🔧 AJOUT : relier le test existant à sa story + tests frères
                if test_case.story_key:
                    link_result = link_test_to_story_and_related_tests(
                        test_key=existing,
                        story_key=test_case.story_key,
                        project_key=body.project_key,
                        use_test_jira=use_test_jira,
                        session=jira_session,
                    )
                    if link_result.get("story_link", {}).get("error"):
                        errors.append(
                            f"{safe_summary} (warning): échec du lien vers {test_case.story_key}: "
                            f"{link_result['story_link']}"
                        )
                    for related in link_result.get("related_test_links", []):
                        if related["result"].get("error"):
                            errors.append(
                                f"{safe_summary} (warning): échec du lien vers {related['test']}: "
                                f"{related['result']}"
                            )

                created_keys.append(existing)
                continue

            desc = _build_description(test_case)
            step_payload = _build_step_payload(test_case)

            issue = create_test_issue(
                project_key=body.project_key,
                summary=safe_summary,
                description=desc,
                issue_type="Test",
                steps=step_payload,
                use_test_jira=use_test_jira,
                session=jira_session,
                priority=test_case.priority,
            )

            if issue.get("error"):
                error_detail = (
                    issue.get("message")
                    or issue.get("body")
                    or issue.get("raw_body")
                    or issue.get("error")
                )
                raise ValueError(
                    f"Create test failed for '{safe_summary}': {error_detail}"
                )

            issue_key = issue.get("key")
            if not issue_key:
                raise ValueError(
                    f"Jira did not return issue key for test '{safe_summary}'"
                )

            for warning in issue.get("warnings") or []:
                errors.append(f"{safe_summary} (warning): {warning}")

            logger.info(f"[integrate_tests] Test created with steps: {issue_key}")

           
            if test_case.story_key:
                link_result = link_test_to_story_and_related_tests(
                    test_key=issue_key,
                    story_key=test_case.story_key,
                    project_key=body.project_key,
                    use_test_jira=use_test_jira,
                    session=jira_session,
                )
                if link_result.get("story_link", {}).get("error"):
                    errors.append(
                        f"{safe_summary} (warning): échec du lien vers {test_case.story_key}: "
                        f"{link_result['story_link']}"
                    )
                for related in link_result.get("related_test_links", []):
                    if related["result"].get("error"):
                        errors.append(
                            f"{safe_summary} (warning): échec du lien vers {related['test']}: "
                            f"{related['result']}"
                        )

            created_keys.append(issue_key)

        except Exception as exc:
            logger.error(
                f"[integrate_tests] Error for {test_case.test_name}: {exc}",
                exc_info=True,
            )
            errors.append(f"{test_case.test_name}: {str(exc)}")
            continue

    status = "success"
    if errors:
        status = "partial" if created_keys else "error"

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
        jira_browse_base_url=_jira_browse_base_url(use_test_jira),
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
        safe_summary = _truncate_summary(test_case.test_name)

        logger.info(f"[integrate_test_single] Processing: {safe_summary}")

        existing = search_test_issue_by_summary(
            project_key=body.project_key,
            summary=safe_summary,
            use_test_jira=use_test_jira,
            session=jira_session,
        )

        if existing:
            logger.info(f"[integrate_test_single] Test already exists: {existing}")

            desc = _build_description(test_case)
            step_payload = _build_step_payload(test_case)

            update_fields = {"description": desc}
            normalized_priority = _normalize_priority_for_jira(test_case.priority)
            if normalized_priority:
                update_fields["priority"] = {"name": normalized_priority}

            update_result = _update_issue_fields(
                issue_key=existing,
                fields=update_fields,
                use_test_jira=use_test_jira,
                session=jira_session,
            )
            if update_result.get("error"):
                raise ValueError(
                    f"Update test failed for '{safe_summary}': {update_result.get('message') or update_result.get('body') or update_result.get('raw_body') or update_result.get('error')}"
                )

            if step_payload:
                replace_result = replace_xray_test_steps(
                    test_key=existing,
                    steps=step_payload,
                    use_test_jira=use_test_jira,
                    session=jira_session,
                )
                if replace_result.get("error"):
                    import json as _json
                    raise ValueError(
                        f"Update test failed for '{safe_summary}': "
                        f"{replace_result.get('message') or replace_result.get('detail') or replace_result.get('body') or replace_result.get('error')}\n"
                        f"Détails: {_json.dumps(replace_result.get('api_errors', replace_result.get('detail', {})), ensure_ascii=False, indent=2)}"
                    )
            # 🔧 AJOUT : relier le test existant à sa story + tests frères
            if test_case.story_key:
                link_result = link_test_to_story_and_related_tests(
                    test_key=existing,
                    story_key=test_case.story_key,
                    project_key=body.project_key,
                    use_test_jira=use_test_jira,
                    session=jira_session,
                )
                if link_result.get("story_link", {}).get("error"):
                    errors.append(
                        f"{safe_summary} (warning): échec du lien vers {test_case.story_key}: "
                        f"{link_result['story_link']}"
                    )
                for related in link_result.get("related_test_links", []):
                    if related["result"].get("error"):
                        errors.append(
                            f"{safe_summary} (warning): échec du lien vers {related['test']}: "
                            f"{related['result']}"
                        )

            created_keys.append(existing)

        else:
            desc = _build_description(test_case)
            step_payload = _build_step_payload(test_case)

            issue = create_test_issue(
                project_key=body.project_key,
                summary=safe_summary,
                description=desc,
                issue_type="Test",
                steps=step_payload,
                use_test_jira=use_test_jira,
                session=jira_session,
                priority=test_case.priority,
            )

            if issue.get("error"):
                error_detail = (
                    issue.get("message")
                    or issue.get("body")
                    or issue.get("raw_body")
                    or issue.get("error")
                )
                raise ValueError(
                    f"Create test failed for '{safe_summary}': {error_detail}"
                )

            issue_key = issue.get("key")
            if not issue_key:
                raise ValueError(
                    f"Jira did not return issue key for test '{safe_summary}'"
                )

            for warning in issue.get("warnings") or []:
                errors.append(f"{safe_summary} (warning): {warning}")

            logger.info(f"[integrate_test_single] Test created with steps: {issue_key}")
            logger.info(f"[integrate_test_single] story_key reçu: {test_case.story_key!r}")
            if test_case.story_key:
                link_result = link_test_to_story_and_related_tests(
                    test_key=issue_key,
                    story_key=test_case.story_key,
                    project_key=body.project_key,
                    use_test_jira=use_test_jira,
                    session=jira_session,
                )
                if link_result.get("story_link", {}).get("error"):
                    errors.append(
                        f"{safe_summary} (warning): échec du lien vers {test_case.story_key}: "
                        f"{link_result['story_link']}"
                    )
                for related in link_result.get("related_test_links", []):
                    if related["result"].get("error"):
                        errors.append(
                            f"{safe_summary} (warning): échec du lien vers {related['test']}: "
                            f"{related['result']}"
                        )

            created_keys.append(issue_key)

    except Exception as exc:
        logger.error(f"[integrate_test_single] Error: {exc}", exc_info=True)
        errors.append(str(exc))

    status = "success"
    if errors:
        status = "partial" if created_keys else "error"

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
        jira_browse_base_url=_jira_browse_base_url(use_test_jira),
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

    jira_session = _resolve_jira_session(user)

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
            session=jira_session,
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