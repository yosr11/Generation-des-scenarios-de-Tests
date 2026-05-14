
# app/api/routes_analysis.py

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any

from app.services.jira_service import get_story_byID, get_epic_for_story
from app.utils.cleaning import clean_story_dict, enrich_story_for_llm
from app.services.story_analysis_service import analyze_story_with_groq, StoryAnalysisError
from app.services.llm_client import GROQ_MODELS
from app.repositories.story_repository import get_story_by_id, save_story
from app.repositories.analysis_repository import save_analysis
from app.services.epic_service import JIRA_AC_FIELD, get_stories_by_epic_detailed
from app.services.document_collector import collect_documents_for_epic
from app.services.rag_service import index_documents, retrieve_context, is_epic_indexed
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["Story_Analysis"])


def _flatten_issuelinks(raw_links: list) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for link in raw_links:
        link_type = (link.get("type") or {}).get("name", "")
        for direction in ("inwardIssue", "outwardIssue"):
            target = link.get(direction)
            if target:
                out.append({
                    "type": link_type,
                    "direction": direction.replace("Issue", ""),
                    "key": target.get("key", ""),
                    "summary": (target.get("fields") or {}).get("summary", ""),
                    "status": ((target.get("fields") or {}).get("status") or {}).get("name", ""),
                })
    return out


def _get_enriched_story(issue_key: str) -> Dict[str, Any]:
    db_story = get_story_by_id(issue_key)
    if db_story and db_story.get("description_clean"):
        # S'assurer que l'epic info est toujours présente
        if not db_story.get("epic_key"):
            epic_info = get_epic_for_story(issue_key)
            if epic_info:
                db_story["epic_key"] = epic_info["key"]
                db_story["epic_summary"] = epic_info["summary"]
                db_story["epic_description"] = epic_info.get("description") or ""
                save_story(db_story)
        return db_story

    result = get_story_byID(issue_key)

    if result["status"] == 404:
        raise HTTPException(status_code=404, detail=f"Story {issue_key} introuvable")
    if result["status"] != 200:
        raise HTTPException(status_code=result["status"], detail=result.get("error", "Erreur Jira"))

    fields = result["data"].get("fields", {}) or {}

    raw_story = {
        "id": issue_key,
        "summary": fields.get("summary") or "",
        "description": fields.get("description") or "",
        "acceptance_criteria_raw": fields.get(JIRA_AC_FIELD) or "",
        "labels": fields.get("labels") or [],
        "components": [c.get("name") for c in (fields.get("components") or [])],
        "issuelinks": _flatten_issuelinks(fields.get("issuelinks") or []),
        "priority": (fields.get("priority") or {}).get("name"),
        "status": (fields.get("status") or {}).get("name"),
        "fixVersions": [v.get("name") for v in (fields.get("fixVersions") or [])],
        "requirement_status": fields.get("customfield_14422") or [],
    }

    cleaned = clean_story_dict(raw_story)
    enriched = enrich_story_for_llm(cleaned)

    epic_info = get_epic_for_story(issue_key)
    if epic_info:
        enriched["epic_key"] = epic_info["key"]
        enriched["epic_summary"] = epic_info["summary"]
        enriched["epic_description"] = epic_info.get("description") or ""

    save_story(enriched)
    return enriched


def _build_response(enriched, model_alias, model_name, provider, analysis):
    # Sauvegarder l'analyse en base
    try:
        analysis_dict = analysis.model_dump()
        analysis_dict["model"] = model_alias
        save_analysis(analysis_dict)
        logger.info("Analyse sauvegardée pour %s (modèle: %s)", analysis_dict.get("story_id"), model_alias)
    except Exception as e:
        logger.warning("Echec sauvegarde analyse pour %s : %s", enriched.get("id", ""), e)

    return {
        "model_alias": model_alias,
        "provider": provider,
        "model_name": model_name,
        "epic": {
            "key":     enriched.get("epic_key", ""),
            "summary": enriched.get("epic_summary", ""),
        } if enriched.get("epic_key") else None,
        "story": {
            "id":                        enriched.get("id", ""),
            "summary":                   enriched.get("summary", ""),
            "description_clean":         enriched.get("description_clean", ""),
            "acceptance_criteria_clean":  enriched.get("acceptance_criteria_clean", ""),
            "labels":                    enriched.get("labels", []),
            "priority":                  enriched.get("priority", ""),
            "status":                    enriched.get("status", ""),
        },
        "analysis": analysis.model_dump(),
    }


ALLOWED_MODELS = list(GROQ_MODELS.keys())


def _get_rag_context(enriched: Dict[str, Any]) -> list | None:
    """
    Trouve l'epic parent de la story, indexe ses documents
    s'ils ne le sont pas encore, puis retourne le contexte RAG.
    """
    epic_key = enriched.get("epic_key", "")

    # Fallback : chercher l'epic parent si absent
    if not epic_key:
        story_id = enriched.get("id", "")
        logger.info("epic_key absent pour %s, tentative de récupération ...", story_id)
        epic_info = get_epic_for_story(story_id)
        if epic_info:
            epic_key = epic_info["key"]
            enriched["epic_key"] = epic_key
            enriched["epic_summary"] = epic_info["summary"]
            enriched["epic_description"] = epic_info.get("description") or ""
        else:
            logger.warning("Pas d'epic parent trouvé pour %s, RAG ignoré", story_id)
            return None

    logger.info("RAG activé pour %s (epic: %s)", enriched.get("id"), epic_key)

    # Indexer si pas déjà fait
    if not is_epic_indexed(epic_key):
        logger.info("Indexation RAG de l'epic %s ...", epic_key)
        epic_docs = collect_documents_for_epic(epic_key)
        all_docs = list(epic_docs.get("epic_documents", []))
        for docs in epic_docs.get("documents_by_story", {}).values():
            all_docs.extend(docs)
        if all_docs:
            index_documents(epic_key, all_docs)
        else:
            logger.info("Aucun document trouvé pour l'epic %s", epic_key)
            return None

    query = f"{enriched.get('summary', '')} {enriched.get('description_clean', '')}"
    return retrieve_context(epic_key, query)


# ══════════════════════════════════════════════════════════════
#  ROUTE EPIC : analyser toutes les stories d'une fonctionnalité
# ══════════════════════════════════════════════════════════════

@router.get("/epic/{epic_key}")
def analyze_epic_stories(
    epic_key: str,
    model_alias: str = Query(
        "qwen3",
        description="Model alias. Allowed: qwen3, gptoss, llama4"
    ),
    use_rag: bool = Query(
        False,
        description="Activer le RAG : collecte les documents de l'epic, "
                    "les indexe dans ChromaDB, et injecte le contexte pertinent "
                    "dans chaque analyse."
    ),
):
    """
    Analyse toutes les User Stories d'un Epic.
    Entrée  : clé de l'epic (ex: NUXEPM-345)
    Sortie  : liste des stories analysées par le LLM

    Si use_rag=true :
      1. Collecte les documents (PJ, tickets liés) de l'epic
      2. Indexe les documents dans ChromaDB
      3. Pour chaque story, recherche les passages pertinents
         et les injecte dans le prompt
    """
    if model_alias not in ALLOWED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model_alias '{model_alias}'. Allowed values: {ALLOWED_MODELS}"
        )

    # 1) Récupérer les stories brutes de l'epic
    raw_stories = get_stories_by_epic_detailed(epic_key)
    if raw_stories is None:
        raise HTTPException(status_code=502, detail="Erreur lors de la communication avec Jira")
    if not raw_stories:
        raise HTTPException(status_code=404, detail=f"Aucune story trouvée pour l'epic {epic_key}")

    # 2) RAG : collecte + indexation (si activé)
    rag_info = None
    if use_rag:
        epic_docs = collect_documents_for_epic(epic_key)
        all_docs = list(epic_docs.get("epic_documents", []))
        for docs in epic_docs.get("documents_by_story", {}).values():
            all_docs.extend(docs)

        if all_docs:
            rag_info = index_documents(epic_key, all_docs)

    model_name = GROQ_MODELS[model_alias]
    results = []
    errors = []
    skipped = []

    def _analyze_raw_story(raw: Dict[str, Any]) -> Dict[str, Any]:
        story_id = raw.get("id", "")
        cleaned = clean_story_dict(raw)
        enriched = enrich_story_for_llm(cleaned)
        enriched["epic_key"] = epic_key

        # Filtrer les stories sans description après nettoyage
        description = (enriched.get("description_clean") or "").strip()
        if not description:
            return {"story_id": story_id, "skipped": True}

        # RAG retrieval pour cette story
        rag_context = None
        if use_rag and rag_info and rag_info.get("total_chunks", 0) > 0:
            query = f"{enriched.get('summary', '')} {enriched.get('description_clean', '')}"
            rag_context = retrieve_context(epic_key, query)

        analysis = analyze_story_with_groq(
            story=enriched,
            model_alias=model_alias,
            rag_context=rag_context,
        )
        return {
            "story_id": story_id,
            "result": _build_response(enriched, model_alias, model_name, "groq", analysis),
            "rag_chunks_used": len(rag_context) if rag_context else 0,
        }

    for raw in raw_stories:
        story_id = raw.get("id", "")
        try:
            outcome = _analyze_raw_story(raw)
            if outcome.get("skipped"):
                logger.info("Story %s ignorée : pas de description après nettoyage", story_id)
                skipped.append({"story_id": story_id, "reason": "Pas de description"})
            else:
                results.append(outcome["result"])
        except (StoryAnalysisError, ConnectionError, TimeoutError) as e:
            errors.append({"story_id": story_id, "error": str(e)})
        except Exception as e:
            errors.append({"story_id": story_id, "error": f"Unexpected: {str(e)}"})

    response = {
        "epic_key": epic_key,
        "model_alias": model_alias,
        "model_name": model_name,
        "total_stories": len(raw_stories),
        "analyzed": len(results),
        "skipped_no_description": len(skipped),
        "failed": len(errors),
        "results": results,
        "skipped": skipped,
        "errors": errors,
    }

    if rag_info:
        response["rag"] = rag_info

    return response


# ══════════════════════════════════════════════════════════════
#  ROUTE GÉNÉRIQUE (paramètre model_alias)
# ══════════════════════════════════════════════════════════════

@router.get("/{issue_key}")
def analyze_story(
    issue_key: str,
    model_alias: str = Query(
        "qwen3",
        description="Model alias. Allowed: qwen3, gptoss, llama4"
    ),
    use_rag: bool = Query(
        False,
        description="Activer le RAG : indexe les documents de l'epic parent "
                    "et injecte le contexte pertinent dans l'analyse."
    ),
):
    if model_alias not in ALLOWED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model_alias '{model_alias}'. Allowed values: {ALLOWED_MODELS}"
        )
    enriched = _get_enriched_story(issue_key)

    description = (enriched.get("description_clean") or enriched.get("description") or "").strip()
    if not description:
        raise HTTPException(
            status_code=422,
            detail=f"Story {issue_key} ignorée : pas de description. Contactez le PO pour enrichir la story."
        )

    rag_context = _get_rag_context(enriched) if use_rag else None

    try:
        analysis = analyze_story_with_groq(
            story=enriched, model_alias=model_alias, rag_context=rag_context,
        )
        model_name = GROQ_MODELS[model_alias]
    except (StoryAnalysisError, ConnectionError, TimeoutError) as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected analysis error: {str(e)}")
    return _build_response(enriched, model_alias, model_name, "groq", analysis)


# ══════════════════════════════════════════════════════════════
#  ROUTES DÉDIÉES GROQ
# ══════════════════════════════════════════════════════════════

@router.get("/qwen3/{issue_key}")
def analyze_story_qwen3(issue_key: str, use_rag: bool = Query(False)):
    enriched = _get_enriched_story(issue_key)
    description = (enriched.get("description_clean") or enriched.get("description") or "").strip()
    if not description:
        raise HTTPException(
            status_code=422,
            detail=f"Story {issue_key} ignorée : pas de description. Contactez le PO pour enrichir la story."
        )
    rag_context = _get_rag_context(enriched) if use_rag else None
    try:
        analysis = analyze_story_with_groq(story=enriched, model_alias="qwen3", rag_context=rag_context)
    except (StoryAnalysisError, ConnectionError, TimeoutError) as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected analysis error: {str(e)}")
    return _build_response(enriched, "qwen3", GROQ_MODELS["qwen3"], "groq", analysis)


@router.get("/gptoss/{issue_key}")
def analyze_story_gptoss(issue_key: str, use_rag: bool = Query(False)):
    enriched = _get_enriched_story(issue_key)
    description = (enriched.get("description_clean") or enriched.get("description") or "").strip()
    if not description:
        raise HTTPException(
            status_code=422,
            detail=f"Story {issue_key} ignorée : pas de description. Contactez le PO pour enrichir la story."
        )
    rag_context = _get_rag_context(enriched) if use_rag else None
    try:
        analysis = analyze_story_with_groq(story=enriched, model_alias="gptoss", rag_context=rag_context)
    except (StoryAnalysisError, ConnectionError, TimeoutError) as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected analysis error: {str(e)}")
    return _build_response(enriched, "gptoss", GROQ_MODELS["gptoss"], "groq", analysis)


@router.get("/llama4/{issue_key}")
def analyze_story_llama4(issue_key: str, use_rag: bool = Query(False)):
    enriched = _get_enriched_story(issue_key)

    # ✅ NE PLUS bloquer ici si la description est vide
    # Le service analyze_story_with_groq gère ce cas
    rag_context = _get_rag_context(enriched) if use_rag else None

    try:
        analysis = analyze_story_with_groq(
            story=enriched,
            model_alias="llama4",
            rag_context=rag_context
        )
    except (StoryAnalysisError, ConnectionError, TimeoutError) as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected analysis error: {str(e)}"
        )

    return _build_response(
        enriched,
        "llama4",
        GROQ_MODELS["llama4"],
        "groq",
        analysis
    )