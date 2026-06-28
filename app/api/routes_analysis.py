
# app/api/routes_analysis.py

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any

from app.services.jira_service import get_story_byID, get_epic_for_story
from app.utils.cleaning import clean_story_dict, enrich_story_for_llm, flatten_issuelinks
from app.services.story_analysis_service import analyze_story_with_groq, StoryAnalysisError
from app.services.llm_client import GROQ_MODELS
from app.repositories.story_repository import get_story_by_id, save_story
from app.repositories.analysis_repository import save_analysis
from app.services.epic_service import JIRA_AC_FIELD, get_stories_by_epic_detailed
from app.services.document_collector import collect_documents_for_epic, collect_documents_for_story
from app.services.rag_service import index_documents, retrieve_context, is_epic_indexed, _get_chroma_client
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["Story_Analysis"])


def _get_enriched_story(issue_key: str, force_refresh: bool = False) -> Dict[str, Any]:
    db_story = None if force_refresh else get_story_by_id(issue_key)

    # Vérifier si la story en cache est périmée (versioning Jira)
    need_refresh = False
    if db_story and db_story.get("description_clean"):
        try:
            jira_data = get_story_byID(issue_key)
            if jira_data.get("status") == 200:
                jira_updated = (jira_data["data"].get("fields") or {}).get("updated", "")
                cached_updated = db_story.get("jira_updated", "")
                if jira_updated and jira_updated != cached_updated:
                    logger.info(
                        "Story %s modifiée dans Jira (cached=%s, jira=%s) → re-fetch",
                        issue_key, cached_updated, jira_updated,
                    )
                    need_refresh = True
                else:
                    # Pas de changement, utiliser le cache
                    if not db_story.get("epic_key"):
                        epic_info = get_epic_for_story(issue_key)
                        if epic_info:
                            db_story["epic_key"] = epic_info["key"]
                            db_story["epic_summary"] = epic_info["summary"]
                            db_story["epic_description"] = epic_info.get("description") or ""
                            save_story(db_story)
                    return db_story
        except Exception:
            # Jira inaccessible → utiliser le cache
            if not db_story.get("epic_key"):
                epic_info = get_epic_for_story(issue_key)
                if epic_info:
                    db_story["epic_key"] = epic_info["key"]
                    db_story["epic_summary"] = epic_info["summary"]
                    db_story["epic_description"] = epic_info.get("description") or ""
                    save_story(db_story)
            return db_story

    if not need_refresh and not db_story:
        pass  # fall through to Jira fetch below

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
        "issuelinks": flatten_issuelinks(fields.get("issuelinks") or []),
        "priority": (fields.get("priority") or {}).get("name"),
        "status": (fields.get("status") or {}).get("name"),
        "fixVersions": [v.get("name") for v in (fields.get("fixVersions") or [])],
        "requirement_status": fields.get("customfield_14422") or [],
        "jira_updated": fields.get("updated") or "",
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
        
        logger.info(f"[SAVE] Attempting to save analysis for {analysis_dict.get('story_id')}")
        logger.info(f"[SAVE] Analysis dict keys: {list(analysis_dict.keys())}")
        
        rowid = save_analysis(analysis_dict)
        
        if rowid > 0:
            logger.info(f"✅ Analyse sauvegardée pour {analysis_dict.get('story_id')} (modèle: {model_alias}, rowid: {rowid})")
        else:
            logger.error(f"❌ Echec sauvegarde analyse pour {analysis_dict.get('story_id')} (rowid: {rowid})")
            
    except Exception as e:
        logger.error(f"❌ EXCEPTION lors sauvegarde analyse pour {enriched.get('id', '')}: {e}", exc_info=True)

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


def _get_story_attachments(story_id: str) -> list:
    """
    Récupère DIRECTEMENT les pièces jointes de la story (PDF → texte,
    images → OCR+VLM), sans passer par le RAG. Ces documents font partie
    intégrante de la spec et seront injectés en direct dans le prompt
    d'Agent 1.

    Retourne la liste des dicts {source, origin_key, filename, text}
    correspondant aux PJ directement attachées à la story (filtre :
    source == 'attachment' et origin_key == story_id).
    """
    try:
        docs = collect_documents_for_story(story_id)
    except Exception as exc:
        print(f"[ATTACH] Erreur lors de la collecte des PJ de {story_id}: {exc}", flush=True)
        return []

    # Filtrer : on ne garde que les PJ directement attachées à la story
    # (pas l'epic, pas les linked, pas les autres stories)
    story_only = [
        d for d in docs
        if d.get("source") == "attachment" and d.get("origin_key") == story_id
    ]
    print(f"[ATTACH] {story_id} : {len(story_only)} pièce(s) jointe(s) directe(s)", flush=True)
    for d in story_only:
        is_image = "[Image jointe :" in d.get("text", "")
        kind = "image (OCR+VLM)" if is_image else "doc"
        print(f"[ATTACH]   - {d.get('filename')} [{kind}, {len(d.get('text',''))} chars]", flush=True)
    return story_only


def _get_rag_context(enriched: Dict[str, Any], force_refresh: bool = False) -> list | None:
    """
    Trouve l'epic parent de la story, indexe ses documents
    s'ils ne le sont pas encore, puis retourne le contexte RAG.
    Si force_refresh=True : supprime la collection RAG existante et
    ré-indexe avec VLM scopé sur la story analysée.
    """
    epic_key = enriched.get("epic_key", "")
    story_id = enriched.get("id", "")

    # Fallback : chercher l'epic parent si absent
    if not epic_key:
        print(f"[RAG] epic_key absent pour {story_id}, tentative de récupération ...", flush=True)
        epic_info = get_epic_for_story(story_id)
        if epic_info:
            epic_key = epic_info["key"]
            enriched["epic_key"] = epic_key
            enriched["epic_summary"] = epic_info["summary"]
            enriched["epic_description"] = epic_info.get("description") or ""
        else:
            print(f"[RAG] Pas d'epic parent trouvé pour {story_id}, RAG ignoré", flush=True)
            return None

    print(f"[RAG] activé pour {story_id} (epic: {epic_key}, force_refresh={force_refresh})", flush=True)

    # Force refresh : drop la collection RAG existante
    if force_refresh and is_epic_indexed(epic_key):
        collection_name = epic_key.replace("-", "_").lower()
        try:
            _get_chroma_client().delete_collection(collection_name)
            print(f"[RAG] Force refresh: collection {collection_name} supprimée", flush=True)
        except Exception as exc:
            print(f"[RAG] Impossible de supprimer la collection {collection_name}: {exc}", flush=True)

    # Indexer si pas déjà fait (ou si on vient de la supprimer)
    if not is_epic_indexed(epic_key):
        print(f"[RAG] Indexation de l'epic {epic_key} (VLM focus={story_id}) ...", flush=True)
        epic_docs = collect_documents_for_epic(epic_key, vlm_focus_story=story_id)
        all_docs = list(epic_docs.get("epic_documents", []))
        for docs in epic_docs.get("documents_by_story", {}).values():
            all_docs.extend(docs)

        # Compter combien de docs sont des descriptions d'images (OCR+VLM)
        image_docs = [d for d in all_docs if "[Image jointe :" in d.get("text", "")]
        print(f"[RAG] Documents collectés : {len(all_docs)} (dont {len(image_docs)} descriptions d'images)", flush=True)
        for img_doc in image_docs:
            print(f"[RAG]   - image: {img_doc.get('filename')} (origin={img_doc.get('origin_key')}, {len(img_doc.get('text',''))} chars)", flush=True)

        if all_docs:
            index_documents(epic_key, all_docs)
        else:
            print(f"[RAG] Aucun document trouvé pour l'epic {epic_key}", flush=True)
            return None

    query = f"{enriched.get('summary', '')} {enriched.get('description_clean', '')}"
    # Les PJ de la story sont injectées en DIRECT comme spec (via _get_story_attachments),
    # pas via le RAG → on les exclut du top-K sémantique pour ne pas dupliquer.
    rag_context = retrieve_context(epic_key, query, exclude_origin_keys=[story_id])

    # Logging : confirmer ce qui arrive dans le contexte RAG (sans les PJ de la story)
    if rag_context:
        print(f"[RAG→Agent1] {story_id} : {len(rag_context)} chunks RAG (hors PJ story) récupérés", flush=True)
        origins = {}
        for c in rag_context:
            ok = c.get("origin_key", "?")
            origins[ok] = origins.get(ok, 0) + 1
        print(f"[RAG→Agent1] {story_id} : origines = {origins}", flush=True)
    else:
        print(f"[RAG→Agent1] {story_id} : aucun contexte RAG retourné", flush=True)

    return rag_context


# ══════════════════════════════════════════════════════════════
#  ROUTE EPIC : analyser toutes les stories d'une fonctionnalité
# ══════════════════════════════════════════════════════════════

@router.get("/epic/{epic_key}")
def analyze_epic_stories(
    epic_key: str,
    model_alias: str = Query(
        "llama4",
        description="Model alias. Allowed: qwen3, gptoss, llama4"
    ),
    use_rag: bool = Query(
        False,
        description="Activer le RAG : collecte les documents de l'epic, "
                    "les indexe dans ChromaDB, et injecte le contexte pertinent "
                    "dans chaque analyse. Inclut : PJ de l'epic + PJ de chaque story "
                    "de l'epic + descriptions et PJ des tickets liés. Les images de "
                    "chaque story passent par OCR+VLM (uniquement pour la story en cours "
                    "d'analyse afin de maîtriser le coût)."
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

        # Attachments directs de la story (images + pièces jointes + issuelinks descriptions)
        story_attachments = _get_story_attachments(story_id)

        analysis = analyze_story_with_groq(
            story=enriched,
            model_alias=model_alias,
            rag_context=rag_context,
            story_attachments=story_attachments,
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
        "llama4",
        description="Model alias. Allowed: qwen3, gptoss, llama4"
    ),
    use_rag: bool = Query(
        False,
        description="Activer le RAG : indexe tous les documents liés à l'epic parent "
                    "(PJ de l'epic + PJ de chaque story de l'epic, y compris la story analysée, "
                    "+ descriptions et PJ des tickets liés) et injecte le contexte pertinent "
                    "dans l'analyse. Les images de la story analysée passent par OCR+VLM."
    ),
    force_refresh: bool = Query(
        False,
        description="Forcer le rafraîchissement : re-fetch Jira (ignore le cache story) "
                    "+ supprime et ré-indexe la collection RAG de l'epic (re-passe par OCR+VLM "
                    "sur les images de la story)."
    ),
):
    if model_alias not in ALLOWED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model_alias '{model_alias}'. Allowed values: {ALLOWED_MODELS}"
        )
    enriched = _get_enriched_story(issue_key, force_refresh=force_refresh)

    # Les PJ de la story sont TOUJOURS injectées en direct (spec), indépendamment de use_rag
    story_attachments = _get_story_attachments(issue_key)
    rag_context = _get_rag_context(enriched, force_refresh=force_refresh) if use_rag else None

    try:
        analysis = analyze_story_with_groq(
            story=enriched, model_alias=model_alias,
            rag_context=rag_context, story_attachments=story_attachments,
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
def analyze_story_qwen3(issue_key: str, use_rag: bool = Query(False), force_refresh: bool = Query(False)):
    enriched = _get_enriched_story(issue_key, force_refresh=force_refresh)
    story_attachments = _get_story_attachments(issue_key)
    rag_context = _get_rag_context(enriched, force_refresh=force_refresh) if use_rag else None
    try:
        analysis = analyze_story_with_groq(
            story=enriched, model_alias="qwen3",
            rag_context=rag_context, story_attachments=story_attachments,
        )
    except (StoryAnalysisError, ConnectionError, TimeoutError) as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected analysis error: {str(e)}")
    return _build_response(enriched, "qwen3", GROQ_MODELS["qwen3"], "groq", analysis)


@router.get("/gptoss/{issue_key}")
def analyze_story_gptoss(issue_key: str, use_rag: bool = Query(False), force_refresh: bool = Query(False)):
    enriched = _get_enriched_story(issue_key, force_refresh=force_refresh)
    story_attachments = _get_story_attachments(issue_key)
    rag_context = _get_rag_context(enriched, force_refresh=force_refresh) if use_rag else None
    try:
        analysis = analyze_story_with_groq(
            story=enriched, model_alias="gptoss",
            rag_context=rag_context, story_attachments=story_attachments,
        )
    except (StoryAnalysisError, ConnectionError, TimeoutError) as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected analysis error: {str(e)}")
    return _build_response(enriched, "gptoss", GROQ_MODELS["gptoss"], "groq", analysis)


@router.get("/llama4/{issue_key}")
def analyze_story_llama4(issue_key: str, use_rag: bool = Query(False), force_refresh: bool = Query(False)):
    enriched = _get_enriched_story(issue_key, force_refresh=force_refresh)
    story_attachments = _get_story_attachments(issue_key)
    rag_context = _get_rag_context(enriched, force_refresh=force_refresh) if use_rag else None

    try:
        analysis = analyze_story_with_groq(
            story=enriched,
            model_alias="llama4",
            rag_context=rag_context,
            story_attachments=story_attachments,
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
