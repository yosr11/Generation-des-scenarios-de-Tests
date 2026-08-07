"""FastAPI routes pour Agent 5 - Génération de Rapports."""

import logging
import time

from fastapi import APIRouter, HTTPException

from app.models.agent5_report import Agent5ReportResponse, Agent5ReportRequest
from app.repositories.analysis_repository import (
    get_latest_analysis_as_pydantic as fetch_analysis_by_story_id,
)
from app.repositories.manual_tests_repository import (
    get_latest_manual_tests_as_pydantic as fetch_generation_by_story_id,
)
from app.repositories.validation_repository import (
    fetch_validation_by_story_id,
)
from app.services.agent5_report_service import Agent5ReportGeneratorService

router = APIRouter(prefix="/agent5", tags=["Agent5 - Reporting"])
logger = logging.getLogger(__name__)

# Initialize service
_agent5_service = None


def get_agent5_service():
    """Lazy initialization of Agent5 service."""
    global _agent5_service
    if _agent5_service is None:
        _agent5_service = Agent5ReportGeneratorService(model_name="nova-lite-2")
    return _agent5_service


def _fetch_all_agent_data(story_id: str):
    """Charge les résultats des 3 agents depuis la base. Lève HTTPException si manquant."""
    analysis = fetch_analysis_by_story_id(story_id)
    if not analysis:
        raise HTTPException(
            status_code=404, detail=f"Analyse (Agent 1) non trouvée pour {story_id}"
        )

    generation = fetch_generation_by_story_id(story_id)
    if not generation:
        raise HTTPException(
            status_code=404, detail=f"Tests (Agent 3) non trouvés pour {story_id}"
        )

    validation = fetch_validation_by_story_id(story_id)
    if not validation:
        raise HTTPException(
            status_code=404, detail=f"Validation (Agent 4) non trouvée pour {story_id}"
        )

    return analysis, generation, validation


@router.get("/story/{story_id}/report", response_model=Agent5ReportResponse)
def get_stored_report(story_id: str):
    """Retourne le dernier rapport persisté en base (sans appel LLM)."""
    from app.repositories.report_repository import get_latest_report
    from app.models.agent5_report import Agent5Report

    stored = get_latest_report(story_id)
    if not stored or not stored.get("report_data"):
        raise HTTPException(
            status_code=404, detail=f"Aucun rapport trouvé pour {story_id}"
        )
    try:
        report = Agent5Report(**stored["report_data"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rapport invalide : {e}")
    return Agent5ReportResponse(
        status="success",
        report=report,
        report_markdown=None,
        error_message=None,
        generation_duration_ms=0,
    )


@router.post("/story/{story_id}/report", response_model=Agent5ReportResponse)
def generate_story_report(story_id: str, body: Agent5ReportRequest = None):
    """
    Génère un rapport complet pour une user story.

    Récupère les résultats des agents 1-3 depuis la base et synthétise un rapport.
    """
    start_time = time.time()

    # Defaults si pas de body
    output_format = body.output_format if body else "json"

    try:
        logger.info(
            f"[Agent5] Generating report for {story_id} (format={output_format})"
        )

        analysis, generation, validation = _fetch_all_agent_data(story_id)

        service = get_agent5_service()
        report = service.generate_report(
            story_analysis=analysis,
            test_generation=generation,
            validation_result=validation,
        )

        report_md = None
        if output_format == "markdown":
            report_md = service.export_to_markdown(report)

        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"[Agent5] Report generated for {story_id} in {duration_ms}ms: "
            f"status={report.executive_summary.overall_status}, "
            f"coverage={report.coverage_metrics.coverage_rate:.1f}%"
        )

        return Agent5ReportResponse(
            status="success",
            report=report if output_format == "json" else None,
            report_markdown=report_md if output_format == "markdown" else None,
            error_message=None,
            generation_duration_ms=duration_ms,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Agent5] Error generating report for {story_id}: {e}")
        duration_ms = int((time.time() - start_time) * 1000)
        return Agent5ReportResponse(
            status="error",
            report=None,
            report_markdown=None,
            error_message=str(e),
            generation_duration_ms=duration_ms,
        )


@router.get("/story/{story_id}/report/markdown")
def get_story_report_markdown(story_id: str):
    """Retourne le rapport en format Markdown (lisible et formaté)."""
    try:
        analysis, generation, validation = _fetch_all_agent_data(story_id)

        service = get_agent5_service()
        report = service.generate_report(
            story_analysis=analysis,
            test_generation=generation,
            validation_result=validation,
        )

        return {
            "status": "success",
            "story_id": story_id,
            "report_markdown": service.export_to_markdown(report),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Agent5] Error generating markdown for {story_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/story/{story_id}/report/summary")
def get_story_report_summary(story_id: str):
    """Retourne juste le résumé exécutif (executive summary). Utile pour dashboards."""
    try:
        analysis, generation, validation = _fetch_all_agent_data(story_id)

        service = get_agent5_service()
        report = service.generate_report(
            story_analysis=analysis,
            test_generation=generation,
            validation_result=validation,
        )

        return {
            "status": "success",
            "story_id": story_id,
            "overall_status": report.executive_summary.overall_status,
            "key_findings": report.executive_summary.key_findings,
            "next_steps": report.executive_summary.next_steps,
            "coverage_rate": f"{report.coverage_metrics.coverage_rate:.1f}%",
            "validation_status": report.quality_assurance.validation_status,
            "duplicate_count": report.quality_assurance.duplicate_pairs,
            "ambiguity_count": report.quality_assurance.ambiguity_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Agent5] Error generating summary for {story_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-reports")
def generate_batch_reports(story_ids: list[str]):
    """Génère des rapports pour plusieurs stories en batch."""
    results = {
        "total": len(story_ids),
        "succeeded": 0,
        "failed": 0,
        "reports": [],
        "errors": {},
    }

    service = get_agent5_service()

    for story_id in story_ids:
        try:
            analysis = fetch_analysis_by_story_id(story_id)
            generation = fetch_generation_by_story_id(story_id)
            validation = fetch_validation_by_story_id(story_id)

            if not all([analysis, generation, validation]):
                results["errors"][
                    story_id
                ] = "Data missing (analysis/generation/validation)"
                results["failed"] += 1
                continue

            report = service.generate_report(
                story_analysis=analysis,
                test_generation=generation,
                validation_result=validation,
            )

            results["reports"].append(
                {
                    "story_id": story_id,
                    "status": report.executive_summary.overall_status,
                    "coverage": f"{report.coverage_metrics.coverage_rate:.1f}%",
                    "validation": report.quality_assurance.validation_status,
                }
            )
            results["succeeded"] += 1

        except Exception as e:
            results["errors"][story_id] = str(e)
            results["failed"] += 1

    logger.info(f"[Agent5] Batch: {results['succeeded']}/{results['total']} succeeded")
    return results


@router.get("/health")
def agent5_health():
    """Health check pour Agent 5."""
    return {"status": "ok", "agent": "Agent5 - Report Generator"}
