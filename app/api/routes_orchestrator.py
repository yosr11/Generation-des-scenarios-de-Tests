"""
Routes FastAPI pour l'orchestrateur LangGraph.

Expose le pipeline complet : story → Agent 1 → Agent 2 → Agent 3 (+ gap-fill) → Agent 5.
"""

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, HTMLResponse
from pydantic import BaseModel, Field

from app.services.agent_orchestrator import run_pipeline, PipelineState
from app.services.agent5_report_service import Agent5ReportGeneratorService
from app.services.epic_service import get_stories_by_epic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orchestrator", tags=["Orchestrator — Full Pipeline"])


# ═══════════════════════════════════════════════════════════════
#  Modèles de requête / réponse
# ═══════════════════════════════════════════════════════════════

class PipelineRequest(BaseModel):
    """Paramètres optionnels pour le pipeline."""

    model_config = {"protected_namespaces": ()}

    use_rag: bool = Field(default=False, description="Activer le RAG ChromaDB")
    use_legacy_rag: bool = Field(default=True, description="Activer le RAG des tests Xray legacy Sopra HR (few-shot Agent 2)")
    model_agent1: str = Field(default="qwen3", description="Modèle LLM pour Agent 1 (analyse). Options: qwen3, llama4, gptoss, gptoss120b, qwen3.6, nova-lite-2")
    model_agent2: str = Field(default="llama4", description="Modèle LLM pour Agent 2 (génération)")
    model_agent3_quality: str = Field(default="llama4", description="Modèle LLM pour Agent 3 (qualité)")
    model_agent5: str = Field(default="qwen3", description="Modèle LLM pour Agent 5 (rapport)")
    model_agent4: str = Field(default="qwen3", description="Modèle LLM pour Agent 4 (classifieur auto/manuel)")
    coverage_threshold: float = Field(default=0.70, ge=0.0, le=1.0, description="Seuil de couverture")
    max_correction_iterations: int = Field(default=2, ge=0, le=5, description="Max itérations gap-fill")
    force_refresh: bool = Field(
        default=False,
        description=(
            "Bypass des caches : re-fetch story depuis Jira et ré-indexation des documents "
            "de l'epic (utile après ajout de nouveaux mockups / activation du VLM)."
        ),
    )
    run_agent4: bool = Field(default=False, description="Activer la classification Agent 4 (AUTO/MANUEL)")


class PipelineStoryResult(BaseModel):
    """Résultat du pipeline pour une story."""

    story_id: str
    status: str                  # completed | skipped | failed
    story_type: Optional[str] = None
    tests_count: int = 0
    coverage_rate: Optional[float] = None
    validation_status: Optional[str] = None
    correction_iterations: int = 0
    report_status: Optional[str] = None
    duration_ms: int = 0
    errors: List[str] = []
    report_markdown: Optional[str] = None

    # ── Sorties détaillées par agent ──
    agent1_analysis: Optional[dict] = Field(default=None, description="Sortie Agent 1 (analyse)")
    agent2_tests: Optional[List[dict]] = Field(default=None, description="Sortie Agent 2 (tests générés)")
    agent2_golden_rule_warnings: Optional[List[str]] = Field(
        default=None,
        description="Avertissements golden rules non bloquants (Agent 2)",
    )
    agent2_message: Optional[str] = Field(default=None, description="Message Agent 2")
    agent3_validation: Optional[dict] = Field(default=None, description="Sortie Agent 3 (validation/couverture)")
    agent4_classification: Optional[dict] = Field(default=None, description="Sortie Agent 4 (classification AUTO/MANUEL)")
    agent5_report: Optional[dict] = Field(default=None, description="Sortie Agent 5 (rapport final)")

    # ── Métriques de consommation LLM ──
    token_usage: Optional[dict] = Field(default=None, description="Tokens consommés par agent et par modèle")

    # ── Traçabilité RAG tests legacy (few-shot Agent 2) ──
    legacy_examples: Optional[List[dict]] = Field(
        default=None,
        description="Tests Xray legacy injectés en few-shot à Agent 2 (id, score, titre, pivot complet).",
    )


class EpicPipelineResult(BaseModel):
    """Résultat du pipeline pour un epic entier."""

    epic_key: str
    total_stories: int
    completed: int
    skipped: int
    failed: int
    results: List[PipelineStoryResult]
    total_duration_ms: int


# ═══════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════

def _dump(obj: Any) -> Optional[Any]:
    """Convertit un objet Pydantic / dataclass / dict en dict sérialisable."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(mode="json")
        except Exception:
            try:
                return obj.model_dump()
            except Exception:
                pass
    if hasattr(obj, "dict"):
        try:
            return obj.dict()
        except Exception:
            pass
    if isinstance(obj, dict):
        return obj
    return None


def _state_to_result(state: PipelineState, include_markdown: bool = False) -> PipelineStoryResult:
    """Convertit le PipelineState final en réponse API."""
    analysis = state.get("analysis")
    validation = state.get("validation")
    report = state.get("report")
    classification = state.get("classification_result")
    tests = state.get("tests", []) or []

    result = PipelineStoryResult(
        story_id=state.get("story_id", ""),
        status=state.get("status", "failed"),
        story_type=analysis.story_type if analysis else None,
        tests_count=len(tests),
        coverage_rate=validation.report.coverage_rate if validation else None,
        validation_status=validation.report.validation_status if validation else None,
        correction_iterations=state.get("correction_iteration", 0),
        report_status=report.executive_summary.overall_status if report else None,
        duration_ms=state.get("duration_ms", 0),
        errors=state.get("errors", []),
        agent1_analysis=_dump(analysis),
        agent2_tests=[d for d in (_dump(t) for t in tests) if d is not None] or None,
        agent2_golden_rule_warnings=state.get("agent2_golden_rule_warnings") or None,
        agent2_message=state.get("agent2_message"),
        agent3_validation=_dump(validation),
        agent4_classification=_dump(classification),
        agent5_report=_dump(report),
        token_usage=state.get("token_usage"),
        legacy_examples=state.get("legacy_examples") or None,
    )

    if include_markdown and report:
        try:
            service = Agent5ReportGeneratorService(model_name=state.get("model_agent5", "qwen3"))
            result.report_markdown = service.export_to_markdown(report)
        except Exception:
            pass

    return result


# ═══════════════════════════════════════════════════════════════
#  Routes
# ═══════════════════════════════════════════════════════════════

@router.post(
    "/run/{story_id}",
    response_model=PipelineStoryResult,
    summary="Pipeline complet pour une story (Agent 1 → 2 → 3 → 4)",
)
def run_story_pipeline(story_id: str, body: PipelineRequest = None):
    """
    Lance le pipeline complet :
    1. Enrichit la story depuis Jira
    2. Agent 1 : analyse
    3. Agent 2 : génération de tests
    4. Agent 3 : validation (+ boucle corrective gap-fill si couverture insuffisante)
    5. Agent 5 : rapport final
    """
    params = body or PipelineRequest()

    logger.info(f"[Route] Pipeline started for {story_id}")

    try:
        final_state = run_pipeline(
            story_id=story_id,
            use_rag=params.use_rag,
            use_legacy_rag=params.use_legacy_rag,
            model_agent1=params.model_agent1,
            model_agent2=params.model_agent2,
            model_agent3_quality=params.model_agent3_quality,
            model_agent5=params.model_agent5,
            model_agent4=params.model_agent4,
            coverage_threshold=params.coverage_threshold,
            max_correction_iterations=params.max_correction_iterations,
            force_refresh=params.force_refresh,
            run_agent4=params.run_agent4,
        )

        return _state_to_result(final_state, include_markdown=False)

    except Exception as e:
        logger.error(f"[Route] Pipeline error for {story_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")


@router.post(
    "/run/{story_id}/markdown",
    response_model=PipelineStoryResult,
    summary="Pipeline complet + rapport Markdown",
)
def run_story_pipeline_with_markdown(story_id: str, body: PipelineRequest = None):
    """Même pipeline que /run/{story_id} mais inclut le rapport Markdown dans la réponse."""
    params = body or PipelineRequest()

    try:
        final_state = run_pipeline(
            story_id=story_id,
            use_rag=params.use_rag,
            use_legacy_rag=params.use_legacy_rag,
            model_agent1=params.model_agent1,
            model_agent2=params.model_agent2,
            model_agent3_quality=params.model_agent3_quality,
            model_agent5=params.model_agent5,
            model_agent4=params.model_agent4,
            coverage_threshold=params.coverage_threshold,
            max_correction_iterations=params.max_correction_iterations,
            force_refresh=params.force_refresh,
            run_agent4=params.run_agent4,
        )

        return _state_to_result(final_state, include_markdown=True)

    except Exception as e:
        logger.error(f"[Route] Pipeline error for {story_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")


@router.post(
    "/run/{story_id}/report.md",
    response_class=PlainTextResponse,
    summary="Pipeline complet → rapport Markdown brut (text/markdown)",
)
def run_story_pipeline_report_md(story_id: str, body: PipelineRequest = None):
    """Renvoie uniquement le rapport en Markdown brut (header `text/markdown`).

    Pratique pour copier-coller le rapport ou l'afficher dans un viewer Markdown,
    sans les caractères `\n` échappés d'une réponse JSON.
    """
    params = body or PipelineRequest()
    try:
        final_state = run_pipeline(
            story_id=story_id,
            use_rag=params.use_rag,
            use_legacy_rag=params.use_legacy_rag,
            model_agent1=params.model_agent1,
            model_agent2=params.model_agent2,
            model_agent3_quality=params.model_agent3_quality,
            model_agent5=params.model_agent5,
            model_agent4=params.model_agent4,
            coverage_threshold=params.coverage_threshold,
            max_correction_iterations=params.max_correction_iterations,
            force_refresh=params.force_refresh,
            run_agent4=params.run_agent4,
        )
        report = final_state.get("report")
        if not report:
            raise HTTPException(status_code=500, detail="Aucun rapport généré")
        service = Agent5ReportGeneratorService(model_name=params.model_agent5)
        md = service.export_to_markdown(report)
        return PlainTextResponse(content=md, media_type="text/markdown; charset=utf-8")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Route] Pipeline error for {story_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")


@router.post(
    "/run/{story_id}/report.html",
    response_class=HTMLResponse,
    summary="Pipeline complet → rapport rendu en HTML",
)
def run_story_pipeline_report_html(story_id: str, body: PipelineRequest = None):
    """Rendu HTML du rapport Markdown — affichable directement dans un navigateur."""
    params = body or PipelineRequest()
    try:
        final_state = run_pipeline(
            story_id=story_id,
            use_rag=params.use_rag,
            use_legacy_rag=params.use_legacy_rag,
            model_agent1=params.model_agent1,
            model_agent2=params.model_agent2,
            model_agent3_quality=params.model_agent3_quality,
            model_agent5=params.model_agent5,
            model_agent4=params.model_agent4,
            coverage_threshold=params.coverage_threshold,
            max_correction_iterations=params.max_correction_iterations,
            force_refresh=params.force_refresh,
            run_agent4=params.run_agent4,
        )
        report = final_state.get("report")
        if not report:
            raise HTTPException(status_code=500, detail="Aucun rapport généré")
        service = Agent5ReportGeneratorService(model_name=params.model_agent5)
        md = service.export_to_markdown(report)

        try:
            import markdown as md_lib  # type: ignore
            body_html = md_lib.markdown(md, extensions=["tables", "fenced_code"])
        except ImportError:
            # Fallback minimal si la lib markdown n'est pas installée
            from html import escape
            body_html = f"<pre>{escape(md)}</pre>"

        html = f"""<!doctype html>
<html lang=\"fr\">
<head>
<meta charset=\"utf-8\">
<title>Rapport QA — {story_id}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 920px;
         margin: 2rem auto; padding: 0 1rem; color: #24292f; line-height: 1.55; }}
  h1, h2, h3 {{ border-bottom: 1px solid #d0d7de; padding-bottom: .3rem; }}
  code {{ background: #f6f8fa; padding: .15em .4em; border-radius: 4px; }}
  pre {{ background: #f6f8fa; padding: 1rem; border-radius: 6px; overflow-x: auto; }}
  table {{ border-collapse: collapse; margin: 1rem 0; }}
  th, td {{ border: 1px solid #d0d7de; padding: .4rem .8rem; text-align: left; }}
  th {{ background: #f6f8fa; }}
  blockquote {{ color: #57606a; border-left: 4px solid #d0d7de; padding: 0 1rem; margin: 0; }}
</style>
</head>
<body>
{body_html}
</body>
</html>"""
        return HTMLResponse(content=html)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Route] Pipeline error for {story_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")




@router.post(
    "/run/epic/{epic_key}",
    response_model=EpicPipelineResult,
    summary="Pipeline complet pour toutes les stories d'un epic",
)
def run_epic_pipeline(epic_key: str, body: PipelineRequest = None):
    """
    Lance le pipeline pour chaque story de l'epic.
    Les stories sont traitées séquentiellement.
    """
    import time

    params = body or PipelineRequest()
    start_time = time.time()

    stories = get_stories_by_epic(epic_key)
    if not stories:
        raise HTTPException(status_code=404, detail=f"Aucune story trouvée pour l'epic {epic_key}")

    results: List[PipelineStoryResult] = []
    completed = 0
    skipped = 0
    failed = 0

    for story_data in stories:
        sid = story_data.get("key") or story_data.get("id", "")
        if not sid:
            continue

        logger.info(f"[Route] Epic pipeline: processing {sid} ({len(results) + 1}/{len(stories)})")

        try:
            final_state = run_pipeline(
                story_id=sid,
                use_rag=params.use_rag,
                use_legacy_rag=params.use_legacy_rag,
                model_agent1=params.model_agent1,
                model_agent2=params.model_agent2,
                model_agent3_quality=params.model_agent3_quality,
                model_agent5=params.model_agent5,
                model_agent4=params.model_agent4,
                coverage_threshold=params.coverage_threshold,
                max_correction_iterations=params.max_correction_iterations,
                force_refresh=params.force_refresh,
                run_agent4=params.run_agent4,
            )

            result = _state_to_result(final_state)
            results.append(result)

            if result.status == "completed":
                completed += 1
            elif result.status == "skipped":
                skipped += 1
            else:
                failed += 1

        except Exception as e:
            logger.error(f"[Route] Epic pipeline error for {sid}: {e}")
            results.append(PipelineStoryResult(
                story_id=sid,
                status="failed",
                errors=[str(e)],
            ))
            failed += 1

    total_duration = int((time.time() - start_time) * 1000)

    return EpicPipelineResult(
        epic_key=epic_key,
        total_stories=len(results),
        completed=completed,
        skipped=skipped,
        failed=failed,
        results=results,
        total_duration_ms=total_duration,
    )
