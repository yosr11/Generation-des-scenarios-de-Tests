# app/api/routes_documents.py
"""
Routes pour la collecte de documents liés à une story ou un epic.
Permet de visualiser ce que le RAG aura comme contexte.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.services.document_collector import collect_documents_for_story, collect_documents_for_epic
from app.services.rag_service import index_documents, is_epic_indexed

router = APIRouter(prefix="/documents", tags=["Document_Collection"])


@router.get("/attachment/{issue_key}/{attachment_id}")
def get_story_attachment(issue_key: str, attachment_id: str):
    """
    Proxy authentifié vers une pièce jointe Jira (affichage image dans le frontend).
    """
    from app.services.document_collector import _get_attachments, _session

    sid = issue_key.strip().upper()
    attachments = _get_attachments(sid)
    att = next((a for a in attachments if str(a.get("id")) == str(attachment_id)), None)
    if not att or not att.get("content"):
        raise HTTPException(status_code=404, detail="Pièce jointe introuvable")

    try:
        resp = _session.get(att["content"], timeout=30)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur téléchargement Jira: {exc}") from exc

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Impossible de récupérer la pièce jointe")

    media_type = att.get("mimeType") or "application/octet-stream"
    return Response(content=resp.content, media_type=media_type)


@router.get("/{issue_key}")
def get_documents_for_story(issue_key: str):
    """
    Collecte tous les documents liés à une story Jira :
    - PJ de la story
    - PJ de l'epic parent
    - Descriptions et PJ des tickets liés

    Retourne la liste des documents avec leur texte extrait.
    """
    documents = collect_documents_for_story(issue_key)

    if not documents:
        return {
            "issue_key": issue_key,
            "total_documents": 0,
            "message": "Aucun document trouvé pour cette story",
            "documents": [],
        }

    # Résumé par source
    by_source = {}
    for doc in documents:
        src = doc["source"]
        by_source[src] = by_source.get(src, 0) + 1

    # Tronquer le texte pour la lisibilité dans la réponse API
    docs_preview = []
    for doc in documents:
        text = doc["text"]
        docs_preview.append({
            "source": doc["source"],
            "origin_key": doc["origin_key"],
            "filename": doc["filename"],
            "text_length": len(text),
            "text_preview": text[:500] + "..." if len(text) > 500 else text,
            "text_full": text,
        })

    return {
        "issue_key": issue_key,
        "total_documents": len(documents),
        "by_source": by_source,
        "documents": docs_preview,
    }


@router.get("/epic/{epic_key}")
def get_documents_for_epic(epic_key: str):
    """
    Collecte tous les documents liés à un epic entier :
    - PJ de l'epic
    - PJ de chaque story
    - Descriptions et PJ des tickets liés (dédupliqués)

    Utile pour indexer tout le contexte d'un epic dans le RAG.
    """
    result = collect_documents_for_epic(epic_key)

    if result["total_documents"] == 0:
        return {
            "epic_key": epic_key,
            "total_stories": result["total_stories"],
            "total_documents": 0,
            "message": "Aucun document trouvé pour cet epic",
        }

    # Construire un résumé
    all_docs = list(result["epic_documents"])
    for story_key, docs in result["documents_by_story"].items():
        all_docs.extend(docs)

    by_source = {}
    for doc in all_docs:
        src = doc["source"]
        by_source[src] = by_source.get(src, 0) + 1

    # Preview de chaque document
    docs_preview = []
    for doc in all_docs:
        text = doc["text"]
        docs_preview.append({
            "source": doc["source"],
            "origin_key": doc["origin_key"],
            "filename": doc["filename"],
            "text_length": len(text),
            "text_preview": text[:500] + "..." if len(text) > 500 else text,
        })

    return {
        "epic_key": epic_key,
        "total_stories": result["total_stories"],
        "total_documents": result["total_documents"],
        "by_source": by_source,
        "stories_with_docs": list(result["documents_by_story"].keys()),
        "documents": docs_preview,
    }


@router.post("/index/{epic_key}")
def index_epic_documents(epic_key: str):
    """
    Pré-indexe les documents d'un epic dans ChromaDB.

    Appeler cette route AVANT l'analyse avec RAG pour éviter
    l'attente lors de l'analyse. Une fois indexé, les analyses
    avec use_rag=true seront quasi-instantanées (quelques secondes).

    Si l'epic est déjà indexé, retourne l'info sans ré-indexer.
    Ajouter ?force=true pour forcer la ré-indexation.
    """
    from fastapi import Query

    return _do_index(epic_key, force=False)


@router.post("/index/{epic_key}/force")
def reindex_epic_documents(epic_key: str):
    """
    Force la ré-indexation des documents d'un epic dans ChromaDB,
    même s'il est déjà indexé.
    """
    return _do_index(epic_key, force=True)


def _do_index(epic_key: str, force: bool) -> dict:
    if not force and is_epic_indexed(epic_key):
        return {
            "epic_key": epic_key,
            "status": "already_indexed",
            "message": "L'epic est déjà indexé. Utilisez /index/{epic_key}/force pour ré-indexer.",
        }

    # 1) Collecte
    epic_docs = collect_documents_for_epic(epic_key)
    all_docs = list(epic_docs.get("epic_documents", []))
    for docs in epic_docs.get("documents_by_story", {}).values():
        all_docs.extend(docs)

    if not all_docs:
        return {
            "epic_key": epic_key,
            "status": "no_documents",
            "message": "Aucun document trouvé pour cet epic",
            "total_stories": epic_docs.get("total_stories", 0),
        }

    # 2) Indexation
    rag_info = index_documents(epic_key, all_docs)

    return {
        "epic_key": epic_key,
        "status": "indexed",
        "total_stories": epic_docs.get("total_stories", 0),
        "total_documents": len(all_docs),
        "total_chunks": rag_info.get("total_chunks", 0),
    }
