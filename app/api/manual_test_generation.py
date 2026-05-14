import os
import logging
import httpx
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query

from app.models.test_manual import ManualTestGenerationResult
from app.services.manual_test_generator import ManualTestGeneratorService
from app.services.llm_client import GROQ_MODELS, ALL_MODELS, build_llm_client
from app.repositories.story_repository import get_story_by_id
from app.repositories.analysis_repository import get_latest_analysis
from app.services.rag_service import retrieve_context, is_epic_indexed
from app.services.document_collector import collect_documents_for_epic
from app.services.rag_service import index_documents
from app.services.epic_service import get_stories_by_epic_detailed
from app.utils.cleaning import clean_story_dict, enrich_story_for_llm
from app.services.story_analysis_service import analyze_story_with_groq, StoryAnalysisError, _is_reference_only_description
from app.repositories.story_repository import save_story
from app.repositories.analysis_repository import save_analysis
from app.repositories.manual_tests_repository import save_manual_tests_snapshot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/manual-tests", tags=["Manual Test Generation"])

ALLOWED_MODELS = list(ALL_MODELS.keys())


def generate_manual_tests_for_story_data(
    story: Dict[str, Any],
    analysis: Dict[str, Any],
    model_alias: str,
    use_rag: bool,
) -> ManualTestGenerationResult:
    """
    Génère les tests Agent 2 à partir d'une story et d'une analyse déjà chargées (pas d'accès HTTP).
    Réutilisé par POST /manual-tests/generate/{story_id} et par Agent 3 (dashboard).
    """
    story_id = story.get("id", "")

    description = (story.get("description_clean") or "").strip()
    if not description:
        return ManualTestGenerationResult(
            story_id=story_id,
            recommended_test_strategy="needs_refinement",
            generation_status="not_generated",
            message="Description vide. Impossible de générer des tests. Contacter le PO pour compléter la story.",
            tests=[],
            notes=["Action requise : demander au PO de renseigner la description de la story avant de relancer la génération."],
        )

    story_type = (analysis.get("story_type") or "").strip().lower()
    if _is_reference_only_description(description) and story_type == "invalid_or_too_weak":
        return ManualTestGenerationResult(
            story_id=story_id,
            recommended_test_strategy="needs_refinement",
            generation_status="not_generated",
            message=f"Description insuffisante (référence seule : \"{description[:80]}\"). "
                    "L'analyse n'a pas pu résoudre le contenu. Contacter le PO.",
            tests=[],
            notes=[
                "La description ne contient qu'une référence à un autre ticket.",
                "L'Agent 1 n'a pas pu résoudre le contenu depuis Jira.",
                "Action requise : enrichir la description de la story avec le contenu fonctionnel.",
            ],
        )

    if story_type == "invalid_or_too_weak":
        return ManualTestGenerationResult(
            story_id=story_id,
            recommended_test_strategy="needs_refinement",
            generation_status="not_generated",
            message="Story trop faible ou invalide pour générer des tests. Contacter le PO.",
            tests=[],
            notes=["Action requise : la story doit être complétée ou reformulée par le PO."],
        )

    rag_context = _get_rag_context(story) if use_rag else None
    llm_client, model_name = build_llm_client(model_alias)
    service = ManualTestGeneratorService(llm_client=llm_client, model_name=model_name)
    result = service.generate(story=story, analysis=analysis, rag_context=rag_context)
    if result.tests and story_id:
        save_manual_tests_snapshot(
            story_id,
            [t.model_dump() for t in result.tests],
            generation_model=model_alias,
        )
    return result


def _build_groq_client():
    """Crée un client Groq SDK (compatible chat.completions.create)."""
    from groq import Groq
    transport = httpx.HTTPTransport(verify=False)
    return Groq(
        api_key=os.getenv("GROQ_API_KEY"),
        http_client=httpx.Client(transport=transport, timeout=60.0),
    )


def _get_rag_context(enriched: dict) -> list | None:
    """Récupère le contexte RAG pour la story (indexe l'epic si nécessaire)."""
    epic_key = enriched.get("epic_key", "")
    if not epic_key:
        return None

    if not is_epic_indexed(epic_key):
        epic_docs = collect_documents_for_epic(epic_key)
        all_docs = list(epic_docs.get("epic_documents", []))
        for docs in epic_docs.get("documents_by_story", {}).values():
            all_docs.extend(docs)
        if all_docs:
            index_documents(epic_key, all_docs)
        else:
            return None

    query = f"{enriched.get('summary', '')} {enriched.get('description_clean', '')}"
    return retrieve_context(epic_key, query)


@router.post("/generate/{story_id}", response_model=ManualTestGenerationResult)
def generate_manual_tests(
    story_id: str,
    model_alias: str = Query("llama4", description=f"Model alias. Allowed: {list(ALL_MODELS.keys())}"),
    use_rag: bool = Query(True, description="Injecter le contexte RAG dans la génération"),
):
    if model_alias not in ALLOWED_MODELS:
        raise HTTPException(status_code=400, detail=f"Model alias invalide '{model_alias}'. Allowed: {ALLOWED_MODELS}")

    story = get_story_by_id(story_id)
    if not story:
        raise HTTPException(status_code=404, detail=f"Story introuvable en base : {story_id}. Lancez d'abord l'analyse via /analysis/{story_id}.")

    analysis = get_latest_analysis(story_id)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Aucune analyse trouvée pour {story_id}. Lancez d'abord l'analyse via /analysis/{story_id}.")

    return generate_manual_tests_for_story_data(story, analysis, model_alias, use_rag)


# ══════════════════════════════════════════════════════════════
#  ROUTE EPIC : générer les tests pour toutes les stories d'un epic
# ══════════════════════════════════════════════════════════════

@router.post("/generate/epic/{epic_key}")
def generate_manual_tests_for_epic(
    epic_key: str,
    analysis_model: str = Query("llama4", description=f"Modèle pour l'Agent 1 (analyse). Allowed: {list(GROQ_MODELS.keys())}"),
    generation_model: str = Query("deepseek", description=f"Modèle pour l'Agent 2 (génération tests). Allowed: {list(ALL_MODELS.keys())}"),
    use_rag: bool = Query(True, description="Injecter le contexte RAG dans la génération"),
):
    """
    Pipeline complet pour un Epic :
      1. Récupère toutes les stories de l'epic depuis Jira
      2. Pour chaque story : nettoie → analyse (Agent 1, llama4) → génère les tests (Agent 2, qwen3)
      3. Retourne un résumé global avec tous les résultats
    """
    if analysis_model not in ALLOWED_MODELS:
        raise HTTPException(status_code=400, detail=f"Model alias invalide '{analysis_model}'. Allowed: {ALLOWED_MODELS}")
    if generation_model not in ALL_MODELS:
        raise HTTPException(status_code=400, detail=f"Model alias invalide '{generation_model}'. Allowed: {list(ALL_MODELS.keys())}")

    # 1) Récupérer les stories brutes de l'epic
    raw_stories = get_stories_by_epic_detailed(epic_key)
    if raw_stories is None:
        raise HTTPException(status_code=502, detail="Erreur lors de la communication avec Jira")
    if not raw_stories:
        raise HTTPException(status_code=404, detail=f"Aucune story trouvée pour l'epic {epic_key}")

    # 2) RAG : collecte + indexation (si activé)
    if use_rag and not is_epic_indexed(epic_key):
        epic_docs = collect_documents_for_epic(epic_key)
        all_docs = list(epic_docs.get("epic_documents", []))
        for docs in epic_docs.get("documents_by_story", {}).values():
            all_docs.extend(docs)
        if all_docs:
            index_documents(epic_key, all_docs)

    analysis_model_name = GROQ_MODELS[analysis_model]
    llm_client, generation_model_name = build_llm_client(generation_model)
    service = ManualTestGeneratorService(llm_client=llm_client, model_name=generation_model_name)

    results: List[Dict[str, Any]] = []
    skipped: List[Dict[str, str]] = []
    errors: List[Dict[str, str]] = []

    for raw in raw_stories:
        story_id = raw.get("id", "")
        try:
            # Nettoyage + enrichissement
            cleaned = clean_story_dict(raw)
            enriched = enrich_story_for_llm(cleaned)
            enriched["epic_key"] = epic_key
            save_story(enriched)

            # Filtrer les stories sans description
            description = (enriched.get("description_clean") or "").strip()
            if not description:
                skipped.append({"story_id": story_id, "reason": "Pas de description"})
                continue

            # Filtrer les stories avec description = référence seule
            # (la résolution automatique sera tentée par l'Agent 1)
            if _is_reference_only_description(description):
                logger.info(f"Story {story_id} : description = référence seule, résolution via Agent 1")

            # Agent 1 : Analyse — réutiliser si déjà faite, sinon analyser
            existing_analysis = get_latest_analysis(story_id)
            if existing_analysis:
                logger.info(f"Story {story_id} : analyse existante trouvée en base, skip Agent 1")
                analysis_dict = existing_analysis
            else:
                try:
                    analysis = analyze_story_with_groq(story=enriched, model_alias=analysis_model)
                    analysis_dict = analysis.model_dump()
                    analysis_dict["model"] = analysis_model
                    save_analysis(analysis_dict)
                except (StoryAnalysisError, Exception) as e:
                    errors.append({"story_id": story_id, "step": "analysis", "error": str(e)})
                    continue

            # Filtrer les stories invalides
            story_type = (analysis_dict.get("story_type") or "").strip().lower()
            if story_type == "invalid_or_too_weak":
                skipped.append({"story_id": story_id, "reason": "Story invalide ou trop faible"})
                continue

            # Contexte RAG
            rag_context = None
            if use_rag and is_epic_indexed(epic_key):
                query = f"{enriched.get('summary', '')} {enriched.get('description_clean', '')}"
                rag_context = retrieve_context(epic_key, query)

            # Agent 2 : Génération des tests
            test_result = service.generate(story=enriched, analysis=analysis_dict, rag_context=rag_context)
            if test_result.tests and story_id:
                save_manual_tests_snapshot(
                    story_id,
                    [t.model_dump() for t in test_result.tests],
                    generation_model=generation_model,
                )

            results.append({
                "story_id": story_id,
                "story_summary": enriched.get("summary", ""),
                "story_type": story_type,
                "analysis": analysis_dict,
                "tests": test_result.model_dump(),
            })

        except Exception as e:
            errors.append({"story_id": story_id, "step": "generation", "error": str(e)})

    return {
        "epic_key": epic_key,
        "analysis_model": analysis_model,
        "generation_model": generation_model,
        "analysis_model_name": analysis_model_name,
        "generation_model_name": generation_model_name,
        "total_stories": len(raw_stories),
        "generated": len(results),
        "skipped": len(skipped),
        "failed": len(errors),
        "results": results,
        "skipped_details": skipped,
        "errors": errors,
    }