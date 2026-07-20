"""
Orchestrateur LangGraph — Pipeline multi-agents.

Graphe : Enrich → Agent 1 → Agent 2 → Agent 3 → (gap-fill loop) → Agent 5
Chaque nœud appelle les services existants sans les modifier.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph
from app.services.jira_service import enrich_issuelinks_with_description

from app.services.token_tracker import track_agent, track_pipeline
from app.services.pipeline_export_service import (
    collect_story_images,
    build_agent2_input,
    build_evaluation_export,
)
from app.utils.pipeline_cancel import check_pipeline_cancelled, PipelineCancelled, clear_pipeline_cancelled

logger = logging.getLogger(__name__)

def _safe_update_step(story_id: str, agent_name: str, status: str, output: Any = None, error: str = None, progress: int = None):
    try:
        from app.utils.job_manager import update_job_step
        update_job_step(story_id, agent_name, status, output, error, progress)
    except Exception as exc:
        logger.warning(f"Could not update step {agent_name}: {exc}")

# ── Cache RAG legacy tests (session-level) ──
# Évite les appels RAG répétés pour la même story
_legacy_rag_cache: Dict[str, List[Dict[str, Any]]] = {}


# ═══════════════════════════════════════════════════════════════
#  1. STATE — objet partagé qui circule entre tous les nœuds
# ═══════════════════════════════════════════════════════════════

class PipelineState(TypedDict, total=False):
    # ── Entrées ──
    story_id: str
    use_rag: bool
    use_legacy_rag: bool                 # RAG des tests Xray legacy Sopra HR (Agent 2 few-shot)
    model_agent1: str
    model_agent2: str
    model_agent3_quality: str
    model_agent5: str
    coverage_threshold: float
    max_correction_iterations: int
    force_reanalyze: bool
    force_refresh: bool                  # bypass des caches story + RAG epic (refetch Jira + ré-indexation)

    # ── Données accumulées ──
    story: Dict[str, Any]               # Story Jira enrichie
    rag_context: Optional[list]          # Contexte RAG (optionnel)
    legacy_examples: Optional[list]      # Tests legacy similaires (few-shot Agent 2)
    analysis: Optional[Any]              # StoryAnalysisResult (merged final output)
    analysis_dict: Optional[Dict]        # Version dict pour Agent 2
    classification: Optional[Any]        # StoryClassificationResult (classification-only output)
    business_model: Optional[Any]        # BusinessModelingResult (Agent 1.5)
    tests: List[Any]                     # List[ManualTestCase]
    generation_result: Optional[Any]     # ManualTestGenerationResult
    agent2_golden_rule_warnings: List[str]
    agent2_message: Optional[str]
    validation: Optional[Any]            # Agent3ValidationResult
    report: Optional[Any]               # Agent5Report
    classification_result: Optional[Any] # Agent4 — StoryAutomationClassificationResult

    # ── Modèles par agent ──
    model_agent15: str                   # Modèle LLM pour Agent 1.5

    # ── Contrôle ──
    correction_iteration: int
    status: str                          # running | completed | skipped | failed
    errors: List[str]
    duration_ms: int
    token_usage: Optional[Dict[str, Any]]   # consommation tokens par agent


# ═══════════════════════════════════════════════════════════════
#  2. NŒUDS — chaque nœud lit l'état, appelle un service, écrit
# ═══════════════════════════════════════════════════════════════

def node_enrich_story(state: PipelineState) -> dict:
    """Récupère et enrichit la story depuis Jira (avec cache + versioning)."""
    from app.services.jira_service import get_story_byID, get_epic_for_story
    from app.utils.cleaning import clean_story_dict, enrich_story_for_llm, flatten_issuelinks
    from app.repositories.story_repository import get_story_by_id, save_story
    from app.services.epic_service import JIRA_AC_FIELD

    story_id = state["story_id"]
    check_pipeline_cancelled(story_id)
    force_refresh = bool(state.get("force_refresh"))
    
    # "Renforcer l'enrichissement" est activé si la user story n'a pas été traitée avant
    if not get_story_by_id(story_id):
        force_refresh = True
        state["force_refresh"] = True

    _safe_update_step(story_id, "Agent 1", "running", progress=10)
    logger.info(f"[Orchestrator] Enriching story {story_id} (force_refresh={force_refresh})")

    # Vérifier le cache (sauf si force_refresh demande un re-fetch Jira complet)
    db_story = None if force_refresh else get_story_by_id(story_id)
    if db_story and db_story.get("description_clean"):
        if not db_story.get("epic_key"):
            epic_info = get_epic_for_story(story_id)
            if epic_info:
                db_story["epic_key"] = epic_info["key"]
                db_story["epic_summary"] = epic_info["summary"]
                db_story["epic_description"] = epic_info.get("description") or ""
        # Réenregistrer la story existante pour mettre à jour l’historique (created_at)
        save_story(db_story)
        logger.info(f"[Orchestrator] Story {story_id} chargée depuis la base locale")
        return {"story": db_story}

    # Fetch depuis Jira
    result = get_story_byID(story_id)
    if result.get("status") != 200:
        return {
            "status": "failed",
            "errors": [f"Story {story_id} introuvable dans Jira (status={result.get('status')})"],
        }

    fields = result["data"].get("fields", {}) or {}
    flat_links = flatten_issuelinks(fields.get("issuelinks") or [])
    needs_desc = any(not (link.get("description") or "").strip() for link in flat_links)
    if needs_desc:
        flat_links = enrich_issuelinks_with_description(flat_links)

    raw_story = {
        "id": story_id,
        "summary": fields.get("summary") or "",
        "description": fields.get("description") or "",
        "acceptance_criteria_raw": fields.get(JIRA_AC_FIELD) or "",
        "labels": fields.get("labels") or [],
        "components": [c.get("name") for c in (fields.get("components") or [])],
        "issuelinks": flat_links,
        "priority": (fields.get("priority") or {}).get("name"),
        "status": (fields.get("status") or {}).get("name"),
        "fixVersions": [v.get("name") for v in (fields.get("fixVersions") or [])],
        "requirement_status": fields.get("customfield_14422") or [],
        "jira_updated": fields.get("updated") or "",
    }

    cleaned = clean_story_dict(raw_story)
    enriched = enrich_story_for_llm(cleaned)

    epic_info = get_epic_for_story(story_id)
    if epic_info:
        enriched["epic_key"] = epic_info["key"]
        enriched["epic_summary"] = epic_info["summary"]
        enriched["epic_description"] = epic_info.get("description") or ""
    elif db_story and db_story.get("epic_key"):
        enriched["epic_key"] = db_story["epic_key"]
        enriched["epic_summary"] = db_story.get("epic_summary") or ""
        enriched["epic_description"] = db_story.get("epic_description") or ""

    save_story(enriched)
    return {"story": enriched}


def node_build_rag_context(state: PipelineState) -> dict:
    """Construit le contexte RAG (si use_rag=True) — partagé par Agent 1 & Agent 2.

    Réplique la logique de routes_analysis._get_rag_context pour garantir que
    les inputs des agents dans l'orchestrateur soient identiques à ceux des
    endpoints individuels.
    """
    if not state.get("use_rag"):
        return {"rag_context": None}

    check_pipeline_cancelled(state["story_id"])

    from app.services.jira_service import get_epic_for_story
    from app.services.document_collector import collect_documents_for_epic
    from app.services.rag_service import is_epic_indexed, index_documents, retrieve_context, _get_chroma_client

    enriched = state["story"]
    story_id = state["story_id"]
    force_refresh = bool(state.get("force_refresh"))
    epic_key = enriched.get("epic_key", "")

    if not epic_key:
        epic_info = get_epic_for_story(story_id)
        if epic_info:
            epic_key = epic_info["key"]
            enriched["epic_key"] = epic_key
            enriched["epic_summary"] = epic_info["summary"]
            enriched["epic_description"] = epic_info.get("description") or ""
        else:
            logger.warning(f"[Orchestrator] No parent epic for {story_id} → RAG skipped")
            return {"rag_context": None, "story": enriched}
    elif not enriched.get("epic_summary"):
        epic_info = get_epic_for_story(story_id)
        if epic_info:
            enriched["epic_summary"] = epic_info["summary"]
            enriched["epic_description"] = epic_info.get("description") or ""

    logger.info(f"[Orchestrator] Building RAG context for {story_id} (epic={epic_key}, force_refresh={force_refresh})")

    if force_refresh and is_epic_indexed(epic_key):
        collection_name = epic_key.replace("-", "_").lower()
        try:
            _get_chroma_client().delete_collection(collection_name)
            logger.info(f"[Orchestrator] Force refresh: collection RAG {collection_name} supprimée")
        except Exception as exc:
            logger.warning(f"[Orchestrator] Impossible de supprimer la collection {collection_name}: {exc}")

    if not is_epic_indexed(epic_key):
        logger.info(f"[Orchestrator] Indexing epic {epic_key} for RAG (VLM focus={story_id})")
        check_pipeline_cancelled(story_id)
        epic_docs = collect_documents_for_epic(
            epic_key, vlm_focus_story=story_id, cancel_story_id=story_id,
        )
        all_docs = list(epic_docs.get("epic_documents", []))
        for docs in epic_docs.get("documents_by_story", {}).values():
            all_docs.extend(docs)
        if all_docs:
            index_documents(epic_key, all_docs)
        else:
            logger.info(f"[Orchestrator] No documents found for epic {epic_key}")
            return {"rag_context": None, "story": enriched}

    query = f"{enriched.get('summary', '')} {enriched.get('description_clean', '')}"
    try:
        rag_context = retrieve_context(epic_key, query)
    except Exception as e:
        logger.warning(f"[Orchestrator] RAG retrieval failed for {story_id}: {e}")
        rag_context = None

    logger.info(
        f"[Orchestrator] RAG context for {story_id}: "
        f"{len(rag_context) if rag_context else 0} chunks"
    )
    return {"rag_context": rag_context, "story": enriched}


def node_classify_story(state: PipelineState) -> dict:
    """Classification Agent : décide du type de story et prépare le résultat final."""
    from app.services.story_analysis_service import (
        classify_story_with_adaptive_llm,
        merge_story_analysis,
    )
    from app.repositories.analysis_repository import save_analysis
    from app.services.document_collector import collect_story_attachments_only

    story = state["story"]
    story_id = state["story_id"]
    check_pipeline_cancelled(story_id)
    model = state.get("model_agent1", "llama4")
    _safe_update_step(story_id, "Agent 1", "running", progress=15)

    story_attachments = collect_story_attachments_only(story_id)
    if story_attachments:
        logger.info(f"[Orchestrator] Classification Agent: {story_id} has {len(story_attachments)} attachment(s)")

    logger.info(f"[Orchestrator] Classifying {story_id} (model={model})")

    try:
        with track_agent("agent1"):
            classification = classify_story_with_adaptive_llm(
                story=story,
                model_alias=model,
                story_attachments=story_attachments,
            )

        analysis = merge_story_analysis(classification=classification, analysis=None, story=story)
        analysis_dict = analysis.model_dump()
        analysis_dict["model"] = model
        save_analysis(analysis_dict)

        _safe_update_step(story_id, "Agent 1", "completed", output=analysis_dict, progress=25)

        return {
            "classification": classification,
            "analysis": analysis,
            "analysis_dict": analysis_dict,
        }

    except Exception as e:
        logger.error(f"[Orchestrator] Classification Agent failed for {story_id}: {e}")
        _safe_update_step(story_id, "Agent 1", "failed", error=str(e), progress=25)
        return {
            "status": "failed",
            "errors": [f"Classification Agent failed: {e}"],
        }


def node_extract_analysis(state: PipelineState) -> dict:
    """Analysis Agent : extrait les champs fonctionnels uniquement pour les stories fonctionnelles."""
    from app.services.story_analysis_service import (
        extract_story_analysis_with_adaptive_llm,
        merge_story_analysis,
    )
    from app.repositories.analysis_repository import save_analysis
    from app.services.document_collector import collect_story_attachments_only

    story = state["story"]
    story_id = state["story_id"]
    check_pipeline_cancelled(story_id)
    model = state.get("model_agent1", "nova-lite-2")
    classification = state.get("classification")
    _safe_update_step(story_id, "Agent 1", "running", progress=20)

    if classification is None:
        logger.error(f"[Orchestrator] Missing classification for {story_id}")
        return {"status": "failed", "errors": ["Missing classification output"]}

    story_attachments = collect_story_attachments_only(story_id)
    logger.info(f"[Orchestrator] Analysis Agent extracting {story_id} (model={model})")

    try:
        with track_agent("agent1"):
            extracted = extract_story_analysis_with_adaptive_llm(
                story=story,
                model_alias=model,
                story_attachments=story_attachments,
            )

        analysis = merge_story_analysis(
            classification=classification,
            analysis=extracted,
            story=story,
        )
        analysis_dict = analysis.model_dump()
        analysis_dict["model"] = model
        save_analysis(analysis_dict)

        _safe_update_step(story_id, "Agent 1", "completed", output=analysis_dict, progress=25)
        _safe_update_step(story_id, "Agent 1.5", "running", progress=26)

        return {
            "analysis": analysis,
            "analysis_dict": analysis_dict,
        }

    except Exception as e:
        logger.error(f"[Orchestrator] Analysis Agent failed for {story_id}: {e}")
        _safe_update_step(story_id, "Agent 1", "failed", error=str(e), progress=25)
        return {
            "status": "failed",
            "errors": [f"Analysis Agent failed: {e}"],
        }


def node_agent15_business_model(state: PipelineState) -> dict:
    """Agent 1.5 : modélisation des business goals et workflows."""
    from app.services.business_modeling_service import build_business_model
    from app.repositories.business_model_repository import save_business_model

    story_id = state["story_id"]
    analysis_dict = state.get("analysis_dict") or {}
    model = state.get("model_agent15") or state.get("model_agent1", "nova-lite-2")

    check_pipeline_cancelled(story_id)
    _safe_update_step(story_id, "Agent 1.5", "running", progress=27)
    logger.info(f"[Orchestrator] Agent 1.5 modélisation de {story_id} (modèle={model})")

    try:
        with track_agent("agent15"):
            result = build_business_model(analysis=analysis_dict, model_alias=model)

        result_dict = result.model_dump()
        result_dict["model"] = model
        save_business_model(result_dict)

        bm_out = result_dict
        _safe_update_step(story_id, "Agent 1.5", "completed", output=bm_out, progress=30)

        return {"business_model": result}

    except Exception as exc:
        # Agent 1.5 est non-bloquant : en cas d'échec, le pipeline continue sans business model
        logger.error(f"[Orchestrator] Agent 1.5 failed for {story_id}: {exc}")
        _safe_update_step(story_id, "Agent 1.5", "failed", error=str(exc), progress=30)
        return {"business_model": None}


def node_agent2_generate(state: PipelineState) -> dict:
    """Agent 2 : génération de tests manuels."""
    from app.api.manual_test_generation import generate_manual_tests_for_story_data
    from app.repositories.manual_tests_repository import save_manual_tests_snapshot

    story = state["story"]
    analysis_dict = dict(state.get("analysis_dict") or {})
    story_id = state["story_id"]
    check_pipeline_cancelled(story_id)

    # Enrichir analysis_dict avec le business model si disponible
    business_model = state.get("business_model")
    if business_model is not None:
        bm_dict = business_model.model_dump() if hasattr(business_model, "model_dump") else dict(business_model)
        analysis_dict["business_goals"] = bm_dict.get("business_goals", [])
        analysis_dict["business_workflows"] = bm_dict.get("business_workflows", [])
    model = state.get("model_agent2", "nova-lite-2")
    rag_context = state.get("rag_context")
    _safe_update_step(story_id, "Agent 2", "running", progress=35)

    # ── RAG tests legacy Sopra HR (few-shot) ──
    legacy_examples: Optional[list] = state.get("legacy_examples")
    if state.get("use_legacy_rag") and legacy_examples is None:
        try:
            from app.services.legacy_test_rag_service import retrieve_similar
            
            # OPTIMISATION: Caching session-level des résultats RAG
            cache_key = f"{story.get('summary', '')}|||{story.get('description_clean', '')}"
            if cache_key in _legacy_rag_cache:
                legacy_examples = _legacy_rag_cache[cache_key]
                logger.info(f"[Orchestrator] Legacy RAG (CACHED): {len(legacy_examples)} examples for {story_id}")
            else:
                legacy_examples = retrieve_similar(
                    title=story.get("summary", ""),
                    description=story.get("description_clean", ""),
                    k=5,  # ← Réduit de 5 à 3 exemples (économise ~30% tokens)
                )
                _legacy_rag_cache[cache_key] = legacy_examples
                
                if legacy_examples:
                    logger.info(
                        f"[Orchestrator] Legacy RAG: {len(legacy_examples)} examples for {story_id} "
                        f"[{', '.join(e.get('test_id', '?') for e in legacy_examples)}]"
                    )
                else:
                    logger.info(f"[Orchestrator] Legacy RAG: no example >= min_score for {story_id}")
        except Exception as e:
            logger.warning(f"[Orchestrator] Legacy RAG failed for {story_id}: {e}")
            legacy_examples = []

    logger.info(f"[Orchestrator] Agent 2 generating tests for {story_id} (model={model})")

    try:
        check_pipeline_cancelled(story_id)
        with track_agent("agent2"):
            result = generate_manual_tests_for_story_data(
                story=story,
                analysis=analysis_dict,
                model_alias=model,
                rag_context=rag_context,
                legacy_examples=legacy_examples,
            )

        check_pipeline_cancelled(story_id)

        # Persister uniquement si le pipeline n'a pas été annulé
        if result.tests:
            save_manual_tests_snapshot(
                story_id,
                [t.model_dump() for t in result.tests],
                generation_model=model,
            )

        tests_out = [t.model_dump() if hasattr(t, "model_dump") else dict(t) for t in result.tests] if result.tests else []
        _safe_update_step(story_id, "Agent 2", "completed", output=tests_out, progress=50)
        _safe_update_step(story_id, "Agent 3", "running", progress=55)

        return {
            "generation_result": result,
            "tests": list(result.tests),
            "legacy_examples": legacy_examples or [],
            "agent2_golden_rule_warnings": list(getattr(result, "golden_rule_warnings", None) or []),
            "agent2_message": getattr(result, "message", None),
        }

    except PipelineCancelled:
        raise
    except Exception as e:
        logger.error(f"[Orchestrator] Agent 2 failed for {story_id}: {e}")
        _safe_update_step(story_id, "Agent 2", "failed", error=str(e), progress=50)
        return {
            "status": "failed",
            "errors": [f"Agent 2 failed: {e}"],
        }


def node_agent3_validate(state: PipelineState) -> dict:
    """Agent 3 : validation des tests (couverture, doublons, ambiguïtés)."""
    from app.services.agent3_test_validator_service import validate_and_improve_tests
    from app.repositories.validation_repository import save_validation_result

    story_id = state["story_id"]
    check_pipeline_cancelled(story_id)
    analysis = state.get("analysis")
    tests = state.get("tests", [])
    story = state.get("story", {})
    coverage_threshold = state.get("coverage_threshold", 0.70)
    quality_model = state.get("model_agent3_quality", "nova-lite-2")

    testable_points = list(analysis.testable_points) if analysis else []
    story_summary = story.get("summary", "") if isinstance(story, dict) else ""
    _safe_update_step(story_id, "Agent 3", "running", progress=60)

    logger.info(
        f"[Orchestrator] Agent 3 validating {story_id} "
        f"({len(tests)} tests, {len(testable_points)} points, iteration={state.get('correction_iteration', 0)})"
    )

    try:
        with track_agent("agent3"):
            result = validate_and_improve_tests(
                story_id=story_id,
                testable_points=testable_points,
                tests=tests,
                story_summary=story_summary,
                coverage_threshold=coverage_threshold,
                run_llm_ambiguity_detection=True,
                quality_model_alias=quality_model,
            )

        # Persister
        save_validation_result(story_id, result)

        val_out = result.model_dump() if hasattr(result, "model_dump") else dict(result)
        _safe_update_step(story_id, "Agent 3", "completed", output=val_out, progress=75)
        
        _safe_update_step(story_id, "Agent 5", "running", progress=85)

        return {"validation": result}

    except Exception as e:
        logger.error(f"[Orchestrator] Agent 3 failed for {story_id}: {e}")
        _safe_update_step(story_id, "Agent 3", "failed", error=str(e), progress=75)
        return {
            "status": "failed",
            "errors": [f"Agent 3 failed: {e}"],
        }


def node_agent2_gap_fill(state: PipelineState) -> dict:
    """Gap-fill : Agent 2 génère des tests pour les points non couverts, avec feedback Agent 3."""
    from app.services.agent3_correction_loop import run_agent2_gap_fill
    from app.services.agent3_duplicate_service import remove_duplicate_tests
    from app.repositories.manual_tests_repository import save_manual_tests_snapshot

    story_id = state["story_id"]
    check_pipeline_cancelled(story_id)
    story = state.get("story", {})
    analysis_dict = state.get("analysis_dict", {})
    tests = state.get("tests", [])
    validation = state.get("validation")
    model = state.get("model_agent2", "nova-lite-2")
    iteration = state.get("correction_iteration", 0)

    uncovered = validation.report.uncovered_testable_points if validation else []

    # ── Extraire le feedback Agent 3 pour le passer à Agent 2 ──
    dup_pairs = None
    amb_findings = None
    corr_instructions = None
    if validation and validation.report:
        report = validation.report
        if report.duplicate_pairs:
            dup_pairs = [dp.model_dump() for dp in report.duplicate_pairs]
        if report.ambiguity_findings:
            amb_findings = report.ambiguity_findings
        if report.correction_instructions:
            corr_instructions = [ci.model_dump() for ci in report.correction_instructions]

    logger.info(
        f"[Orchestrator] Gap-fill iteration {iteration + 1} for {story_id}: "
        f"{len(uncovered)} uncovered, {len(dup_pairs or [])} dup pairs, "
        f"{len(amb_findings or [])} ambiguities"
    )

    try:
        with track_agent("agent2"):
            gap_result = run_agent2_gap_fill(
                story=story,
                analysis=analysis_dict,
                missing_testable_points=uncovered,
                current_tests=tests,
                rag_context=state.get("rag_context"),
                model_alias=model,
                duplicate_pairs=dup_pairs,
                ambiguity_findings=amb_findings,
                correction_instructions=corr_instructions,
                legacy_examples=state.get("legacy_examples"),
            )

        # Fusionner les nouveaux tests avec les existants
        merged_tests = tests + list(gap_result.tests) if gap_result.tests else tests

        # ── Dédoublonner sémantiquement les tests fusionnés ──
        if len(merged_tests) > 1:
            deduped_tests, dup_result = remove_duplicate_tests(merged_tests, duplicate_threshold=0.80)
            if dup_result.removed_indices:
                logger.info(
                    f"[Orchestrator] Dedup removed {len(dup_result.removed_indices)} duplicate tests "
                    f"({len(merged_tests)} → {len(deduped_tests)})"
                )
            merged_tests = deduped_tests

        # Persister le nouveau snapshot (sauf si annulé entre-temps)
        check_pipeline_cancelled(story_id)
        save_manual_tests_snapshot(
            story_id,
            [t.model_dump() for t in merged_tests],
            generation_model=model,
        )

        logger.info(
            f"[Orchestrator] Gap-fill added {len(gap_result.tests) if gap_result.tests else 0} tests, "
            f"final count after dedup: {len(merged_tests)}"
        )

        return {
            "tests": merged_tests,
            "correction_iteration": iteration + 1,
        }

    except Exception as e:
        logger.error(f"[Orchestrator] Gap-fill failed for {story_id}: {e}")
        # Ne pas bloquer le pipeline — continuer avec les tests actuels
        return {"correction_iteration": iteration + 1}


def node_agent5_report(state: PipelineState) -> dict:
    """Agent 5 : génération du rapport final."""
    from app.services.agent5_report_service import Agent5ReportGeneratorService

    story_id = state["story_id"]
    check_pipeline_cancelled(story_id)
    analysis = state.get("analysis")
    generation_result = state.get("generation_result")
    validation = state.get("validation")
    model = state.get("model_agent5", "nova-lite-2")
    _safe_update_step(story_id, "Agent 5", "running", progress=90)

    logger.info(f"[Orchestrator] Agent 5 generating report for {story_id}")

    if not analysis or not generation_result or not validation:
        logger.warning(f"[Orchestrator] Missing data for Agent 5 report on {story_id}")
        return {"status": "completed"}

    try:
        with track_agent("agent5"):
            service = Agent5ReportGeneratorService(model_name=model)
            report = service.generate_report(
                story_analysis=analysis,
                test_generation=generation_result,
                validation_result=validation,
                correction_iterations=state.get("correction_iteration", 0),
                max_correction_iterations=state.get("max_correction_iterations", 0),
            )
        rep_out = report.model_dump() if hasattr(report, "model_dump") else dict(report)
        _safe_update_step(story_id, "Agent 5", "completed", output=rep_out, progress=100)

        return {
            "report": report,
            "status": "completed",
        }

    except Exception as e:
        logger.error(f"[Orchestrator] Agent 5 failed for {story_id}: {e}")
        _safe_update_step(story_id, "Agent 5", "failed", error=str(e), progress=100)
        return {
            "status": "completed",
            "errors": [f"Agent 5 failed (non-bloquant): {e}"],
        }


# ═══════════════════════════════════════════════════════════════
#  3. ARÊTES CONDITIONNELLES — décisions de routage
# ═══════════════════════════════════════════════════════════════

def route_after_enrich(state: PipelineState) -> str:
    if state.get("status") == "failed":
        return END
    return "classify_story"


def route_after_agent1(state: PipelineState) -> str:
    """Après classification : on ne traite que les stories fonctionnelles."""
    if state.get("status") == "failed":
        return END

    classification = state.get("classification")
    if classification is None:
        return "skip"

    story_type = getattr(classification, "story_type", None) or ""
    if story_type == "invalid_or_too_weak":
        logger.info(f"[Orchestrator] Story {state['story_id']} is invalid_or_too_weak → skipping")
        return "skip"

    if story_type != "functional":
        logger.info(
            f"[Orchestrator] Story {state['story_id']} type='{story_type}' → hors périmètre (fonctionnel uniquement)"
        )
        return "not_functional"

    return "analysis_agent"


def route_after_agent2(state: PipelineState) -> str:
    """Après Agent 2 : si pas de tests générés → END, sinon → Agent 3."""
    if state.get("status") == "failed":
        return END

    gen = state.get("generation_result")
    if not gen or gen.generation_status.value == "not_generated" or not state.get("tests"):
        logger.info(f"[Orchestrator] No tests generated for {state['story_id']} → stopping")
        return "no_tests"
    return "agent3_validate"


def route_after_agent3(state: PipelineState) -> str:
    """Après Agent 3 : VALID → Agent 5, sinon → gap-fill (si itérations restantes et issues actionnables)."""
    if state.get("status") == "failed":
        return END

    next_after_validation = "agent5_report"

    validation = state.get("validation")
    if not validation:
        return next_after_validation

    report = validation.report
    coverage = report.coverage_rate
    iteration = state.get("correction_iteration", 0)
    max_iter = state.get("max_correction_iterations", 2)
    coverage_threshold = state.get("coverage_threshold", 0.70)
    uncovered = report.uncovered_testable_points or []

    duplicates = report.duplicate_pairs or []
    ambiguities = report.ambiguity_findings or []

    # Déclencher le gap-fill si couverture < seuil OU doublons OU ambiguïtés
    has_issues = bool((coverage < coverage_threshold and uncovered) or duplicates or ambiguities)
    if iteration < max_iter and has_issues:
        logger.info(
            f"[Orchestrator] Issues détectées (coverage={coverage:.1%}, uncovered={len(uncovered)}, "
            f"duplicates={len(duplicates)}, ambiguities={len(ambiguities)}) "
            f"→ gap-fill itération {iteration + 1}/{max_iter}"
        )
        return "agent2_gap_fill"

    logger.info(
        f"[Orchestrator] Couverture {coverage:.1%} (seuil={coverage_threshold:.1%}), "
        f"itérations={iteration}/{max_iter} → {next_after_validation}"
    )
    return next_after_validation


# ═══════════════════════════════════════════════════════════════
#  4. NŒUDS TERMINAUX
# ═══════════════════════════════════════════════════════════════

def node_skip(state: PipelineState) -> dict:
    """Story non exploitable → fin avec statut skipped."""
    story_id = state["story_id"]
    _safe_update_step(story_id, "Agent 2", "failed", error="Story non exploitable", progress=100)
    _safe_update_step(story_id, "Agent 3", "failed", error="Story non exploitable")
    _safe_update_step(story_id, "Agent 5", "failed", error="Story non exploitable")
    return {"status": "skipped"}


def node_not_functional(state: PipelineState) -> dict:
    """Story hors périmètre (non fonctionnelle) → court-circuit avec message explicite."""
    story_id = state["story_id"]
    analysis = state.get("analysis")
    story_type = analysis.story_type if analysis else "unknown"
    msg = (
        f"Cette story est de type '{story_type}' et sort du périmètre du pipeline. "
        f"Seules les User Stories fonctionnelles (forme \"En tant que… je veux…\") sont traitées. "
        f"Recommandation : pour une story technique, prévoir des tests d'intégration / unitaires côté développement."
    )
    logger.info(f"[Orchestrator] {story_id} → not_functional ({story_type})")
    
    _safe_update_step(story_id, "Agent 2", "failed", error="Story non fonctionnelle", progress=100)
    _safe_update_step(story_id, "Agent 3", "failed", error="Story non fonctionnelle")
    _safe_update_step(story_id, "Agent 5", "failed", error="Story non fonctionnelle")
    
    return {"status": "skipped", "errors": [msg]}


def node_no_tests(state: PipelineState) -> dict:
    """Aucun test généré → fin avec statut failed."""
    story_id = state["story_id"]
    errors = ["Agent 2 n'a pas pu générer de tests"]
    gen = state.get("generation_result")
    if gen:
        message = (getattr(gen, "message", None) or "").strip()
        if message:
            errors.append(f"Raison : {message}")
        notes = getattr(gen, "notes", None) or []
        for note in notes:
            note_text = (note or "").strip()
            if note_text and note_text not in errors:
                errors.append(note_text)
                
    _safe_update_step(story_id, "Agent 2", "failed", error="\n".join(errors), progress=100)
    _safe_update_step(story_id, "Agent 3", "failed", error="Pas de tests generes")
    _safe_update_step(story_id, "Agent 5", "failed", error="Pas de tests generes")
    
    return {"status": "failed", "errors": errors}


# ═══════════════════════════════════════════════════════════════
#  5. CONSTRUCTION DU GRAPHE
# ═══════════════════════════════════════════════════════════════

def build_pipeline_graph() -> StateGraph:
    """Construit et compile le graphe LangGraph."""

    graph = StateGraph(PipelineState)

    # Ajouter les nœuds
    graph.add_node("enrich_story", node_enrich_story)
    graph.add_node("build_rag_context", node_build_rag_context)
    graph.add_node("classify_story", node_classify_story)
    graph.add_node("analysis_agent", node_extract_analysis)
    graph.add_node("agent2_generate", node_agent2_generate)
    graph.add_node("agent3_validate", node_agent3_validate)
    graph.add_node("agent2_gap_fill", node_agent2_gap_fill)
    graph.add_node("agent15_business_model", node_agent15_business_model)
    graph.add_node("agent5_report", node_agent5_report)
    graph.add_node("skip", node_skip)
    graph.add_node("no_tests", node_no_tests)
    graph.add_node("not_functional", node_not_functional)

    # Point d'entrée
    graph.set_entry_point("enrich_story")

     # Arêtes conditionnelles
    graph.add_conditional_edges("enrich_story", route_after_enrich, {
        "classify_story": "classify_story",   # ← REMPLACER "build_rag_context" par "classify_story"
        END: END,
    })

    

    graph.add_conditional_edges("classify_story", route_after_agent1, {
        "analysis_agent": "analysis_agent",
        "skip": "skip",
        "not_functional": "not_functional",
        END: END,
    })

    graph.add_edge("analysis_agent", "agent15_business_model")
    graph.add_edge("agent15_business_model", "agent2_generate")

    graph.add_conditional_edges("agent2_generate", route_after_agent2, {
        "agent3_validate": "agent3_validate",
        "no_tests": "no_tests",
        END: END,
    })

    graph.add_conditional_edges("agent3_validate", route_after_agent3, {
        "agent5_report": "agent5_report",
        "agent2_gap_fill": "agent2_gap_fill",
        END: END,
    })

    # Après gap-fill → re-validation
    graph.add_edge("agent2_gap_fill", "agent3_validate")

    # Pipeline final : report (Agent 5) → END
    graph.add_edge("agent5_report", END)
    graph.add_edge("skip", END)
    graph.add_edge("no_tests", END)
    graph.add_edge("not_functional", END)

    return graph


# Compiler une seule fois (réutilisable)
_compiled_graph = None


def get_compiled_graph():
    """Retourne le graphe compilé (singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_pipeline_graph().compile()
    return _compiled_graph


# ═══════════════════════════════════════════════════════════════
#  6. API PUBLIQUE
# ═══════════════════════════════════════════════════════════════

def run_pipeline(
    story_id: str,
    *,
    use_rag: bool = False,
    use_legacy_rag: bool = True,
    model_agent1: str = "nova-lite-2",
    model_agent15: str = "nova-lite-2",
    model_agent2: str = "nova-lite-2",
    model_agent3_quality: str = "nova-lite-2",
    model_agent5: str = "nova-lite-2",
    coverage_threshold: float = 0.70,
    max_correction_iterations: int = 2,
    force_reanalyze: bool = True,
    force_refresh: bool = False,
) -> PipelineState:
    """
    Lance le pipeline complet pour une story.

    Returns:
        PipelineState final avec tous les résultats.
    """
    start_time = time.time()

    initial_state: PipelineState = {
        "story_id": story_id,
        "use_rag": use_rag,
        "use_legacy_rag": use_legacy_rag,
        "model_agent1": model_agent1,
        "model_agent15": model_agent15,
        "model_agent2": model_agent2,
        "model_agent3_quality": model_agent3_quality,
        "model_agent5": model_agent5,
        "coverage_threshold": coverage_threshold,
        "max_correction_iterations": max_correction_iterations,
        "force_reanalyze": force_reanalyze,
        "force_refresh": force_refresh,
        "correction_iteration": 0,
        "status": "running",
        "errors": [],
        "tests": [],
    }

    graph = get_compiled_graph()

    logger.info(f"[Orchestrator] ▶ Starting pipeline for {story_id}")

    try:
        # Exécuter le graphe sous un tracker de tokens partagé
        with track_pipeline() as token_usage:
            final_state = graph.invoke(initial_state)
    except PipelineCancelled as exc:
        logger.info(f"[Orchestrator] Pipeline {story_id} annulé")
        clear_pipeline_cancelled(story_id)
        return {
            **initial_state,
            "status": "failed",
            "errors": [str(exc)],
            "duration_ms": int((time.time() - start_time) * 1000),
        }

    duration_ms = int((time.time() - start_time) * 1000)
    final_state["duration_ms"] = duration_ms
    final_state["token_usage"] = token_usage

    # ── Construction du payload d'évaluation (images, RAG, inputs des agents) ──
    analysis        = final_state.get("analysis")
    generation      = final_state.get("generation_result")
    validation      = final_state.get("validation")
    report          = final_state.get("report")
    business_model  = final_state.get("business_model")
    tests           = final_state.get("tests", [])

    images = collect_story_images(story_id)
    agent2_input = build_agent2_input(
        legacy_examples=final_state.get("legacy_examples"),
        rag_context=final_state.get("rag_context"),
    )

    export_source = {
        "story_id": story_id,
        "story": final_state.get("story"),
        "images": images,
        "agent2_input": agent2_input,
        "agent15_business_model": business_model.model_dump() if business_model else None,
        "agent2_tests": [t.model_dump() for t in tests],
        "agent2_golden_rule_warnings": final_state.get("agent2_golden_rule_warnings"),
        "agent2_message": final_state.get("agent2_message"),
        "agent1_analysis": final_state.get("analysis_dict"),
        "agent3_validation": validation.model_dump() if validation else None,
        "agent5_report": report.model_dump() if report else None,
        "legacy_examples": final_state.get("legacy_examples"),
        "rag_context": final_state.get("rag_context"),
        "status": final_state.get("status"),
        "tests_count": len(tests),
        "coverage_rate": validation.report.coverage_rate if validation else None,
        "validation_status": validation.report.validation_status if validation else None,
        "correction_iterations": final_state.get("correction_iteration"),
        "duration_ms": duration_ms,
        "errors": final_state.get("errors"),
        "token_usage": token_usage,
    }

    

    status = final_state.get("status", "completed")
    logger.info(
        f"[Orchestrator] ■ Pipeline finished for {story_id}: "
        f"status={status}, duration={duration_ms}ms, "
        f"tests={len(tests)}, "
        f"iterations={final_state.get('correction_iteration', 0)}"
    )

    return final_state
