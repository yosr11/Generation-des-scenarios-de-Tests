"""
app/services/document_collector.py
───────────────────────────────────
Collecte les documents liés à une story Jira pour le RAG :
  1. Pièces jointes (PJ) de la story
  2. Pièces jointes de l'epic parent
  3. Descriptions des tickets liés (issuelinks)
  4. PJ des tickets liés

Chaque document collecté est retourné sous forme de dict :
  {
    "source": "attachment" | "linked_issue" | "epic_attachment",
    "origin_key": "NUXEPM-404",
    "filename": "SFD_Conges.pdf",
    "text": "... contenu extrait ...",
  }
"""

import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

import requests
import urllib3
from dotenv import load_dotenv

from app.utils.document_loader import extract_text_from_bytes
from app.utils.cleaning import clean_text
from app.services.vision_client import describe_image, ocr_only

load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "https://hra-jira.ptx.fr.sopra").rstrip("/")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_PASSWORD = os.getenv("JIRA_PASSWORD")
JIRA_EPIC_LINK_FIELD = os.getenv("JIRA_EPIC_LINK_FIELD", "customfield_12402")

# Taille max d'un fichier à télécharger (10 Mo)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Workers pour le téléchargement + extraction parallèle des PJ d'un epic.
# 4 = bon compromis : 4× plus rapide qu'en séquentiel sans saturer la rate-limit Groq vision.
ATTACHMENT_WORKERS = int(os.getenv("ATTACHMENT_WORKERS", "4"))
# Limite du nombre d'images traitées par VLM par story (réduit les coûts)
MAX_VLM_IMAGES_PER_STORY = int(os.getenv("MAX_VLM_IMAGES_PER_STORY", "9999"))

_session = requests.Session()
_session.auth = (JIRA_USERNAME, JIRA_PASSWORD)
_session.verify = False
_session.headers.update({"Accept": "application/json"})


# ══════════════════════════════════════════════════════════════
#  API PUBLIQUE
# ══════════════════════════════════════════════════════════════

def collect_documents_for_story(issue_key: str) -> List[Dict[str, Any]]:
    """
    Collecte tous les documents liés à une story Jira.
    Le VLM (images) n'est appliqué qu'aux PJ de la story elle-même.
    Retourne une liste de dicts {source, origin_key, filename, text}.
    """
    documents: List[Dict[str, Any]] = []

    # 1) PJ de la story elle-même — VLM activé seulement sur les N premières images
    story_attachments = _get_attachments(issue_key)
    vlm_count = 0
    for att in story_attachments:
        fname = att.get("filename", "") or ""
        name_lower = fname.lower()
        is_image = name_lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"))

        text = None
        if is_image:
            if vlm_count < MAX_VLM_IMAGES_PER_STORY:
                text = _download_and_extract(att, vlm_enabled=True)
                if text:
                    vlm_count += 1
            else:
                # fallback local OCR (no VLM call)
                try:
                    resp = _session.get(att.get("content"), timeout=None)
                    if resp.status_code == 200:
                        text = ocr_only(resp.content, fname)
                except Exception:
                    text = None
        else:
            # Non-images : normal extraction (pdf/docx/text)
            text = _download_and_extract(att, vlm_enabled=False)

        if text:
            documents.append({
                "source": "attachment",
                "origin_key": issue_key,
                "filename": fname,
                "text": text,
            })

    # 2) PJ de l'epic parent — VLM désactivé (mockups souvent génériques, coût élevé)
    epic_key = _get_epic_key(issue_key)
    if epic_key:
        epic_attachments = _get_attachments(epic_key)
        for att in epic_attachments:
            text = _download_and_extract(att, vlm_enabled=False)
            if text:
                documents.append({
                    "source": "epic_attachment",
                    "origin_key": epic_key,
                    "filename": att.get("filename", ""),
                    "text": text,
                })

    # 3) Tickets liés : description + PJ — VLM désactivé
    linked_keys = _get_linked_issue_keys(issue_key)
    for linked_key in linked_keys:
        # Description du ticket lié (nettoyée du wiki markup)
        desc = _get_issue_description(linked_key)
        if desc and len(desc.strip()) > 20:
            cleaned_desc = clean_text(desc)
            documents.append({
                "source": "linked_issue",
                "origin_key": linked_key,
                "filename": f"{linked_key}_description",
                "text": cleaned_desc,
            })

        # PJ du ticket lié
        linked_attachments = _get_attachments(linked_key)
        for att in linked_attachments:
            text = _download_and_extract(att, vlm_enabled=False)
            if text:
                documents.append({
                    "source": "linked_attachment",
                    "origin_key": linked_key,
                    "filename": att.get("filename", ""),
                    "text": text,
                })

    logger.info(
        "Collecte documents pour %s : %d documents récupérés "
        "(story: %d, epic: %d, linked: %d)",
        issue_key,
        len(documents),
        len(story_attachments),
        len(_get_attachments(epic_key)) if epic_key else 0,
        len(linked_keys),
    )

    return documents


def collect_documents_for_epic(
    epic_key: str,
    *,
    vlm_focus_story: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Collecte les documents pour TOUTES les stories d'un epic.
    Déduplique : les PJ de l'epic et les PJ/descriptions partagées
    ne sont récupérées qu'une seule fois.

    `vlm_focus_story` : si fourni, le VLM (extraction d'images) n'est appliqué
    QUE sur les pièces jointes de cette story. Toutes les autres images
    (epic, autres stories, tickets liés) sont ignorées pour limiter le coût.

    Retourne :
      {
        "epic_key": "NUXEPM-345",
        "total_stories": 12,
        "total_documents": 45,
        "documents_by_story": { "NUXEPM-404": [...], ... },
        "epic_documents": [...],
      }
    """
    from app.services.epic_service import get_stories_by_epic

    stories = get_stories_by_epic(epic_key)
    if not stories:
        return {
            "epic_key": epic_key,
            "total_stories": 0,
            "total_documents": 0,
            "documents_by_story": {},
            "epic_documents": [],
        }

    # 1) PJ de l'epic lui-même (une seule fois) — VLM désactivé
    epic_documents: List[Dict[str, Any]] = []
    epic_attachments = _get_attachments(epic_key)
    for att in epic_attachments:
        text = _download_and_extract(att, vlm_enabled=False)
        if text:
            epic_documents.append({
                "source": "epic_attachment",
                "origin_key": epic_key,
                "filename": att.get("filename", ""),
                "text": text,
            })

    # 2) Pour chaque story : PJ + tickets liés (avec dédoublonnage)
    seen_filenames: set = {d["filename"] for d in epic_documents}
    seen_linked_keys: set = set()
    documents_by_story: Dict[str, List[Dict[str, Any]]] = {}

    for story in stories:
        story_key = story.get("id", "")
        story_docs: List[Dict[str, Any]] = []
        is_focus = (vlm_focus_story is not None and story_key == vlm_focus_story)

        # PJ de la story — VLM activé uniquement si c'est la story en focus,
        # et limité à MAX_VLM_IMAGES_PER_STORY par story. Sinon on tente l'OCR local.
        story_attachments = _get_attachments(story_key)
        vlm_count = 0
        for att in story_attachments:
            fname = att.get("filename", "") or ""
            dedup_key = f"{story_key}_{fname}"
            if dedup_key not in seen_filenames:
                seen_filenames.add(dedup_key)
                name_lower = fname.lower()
                is_image = name_lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"))

                text = None
                if is_image and is_focus and vlm_count < MAX_VLM_IMAGES_PER_STORY:
                    text = _download_and_extract(att, vlm_enabled=True)
                    if text:
                        vlm_count += 1
                elif is_image:
                    try:
                        resp = _session.get(att.get("content"), timeout=None)
                        if resp.status_code == 200:
                            text = ocr_only(resp.content, fname)
                    except Exception:
                        text = None
                else:
                    text = _download_and_extract(att, vlm_enabled=False)

                if text:
                    story_docs.append({
                        "source": "attachment",
                        "origin_key": story_key,
                        "filename": fname,
                        "text": text,
                    })

        # Tickets liés (description + PJ), dédupliqués globalement — VLM désactivé
        linked_keys = _get_linked_issue_keys(story_key)
        for linked_key in linked_keys:
            if linked_key in seen_linked_keys:
                continue
            seen_linked_keys.add(linked_key)

            desc = _get_issue_description(linked_key)
            if desc and len(desc.strip()) > 20:
                cleaned_desc = clean_text(desc)
                story_docs.append({
                    "source": "linked_issue",
                    "origin_key": linked_key,
                    "filename": f"{linked_key}_description",
                    "text": cleaned_desc,
                })

            linked_attachments = _get_attachments(linked_key)
            for att in linked_attachments:
                fname = att.get("filename", "")
                dedup_key = f"{linked_key}_{fname}"
                if dedup_key not in seen_filenames:
                    seen_filenames.add(dedup_key)
                    text = _download_and_extract(att, vlm_enabled=False)
                    if text:
                        story_docs.append({
                            "source": "linked_attachment",
                            "origin_key": linked_key,
                            "filename": fname,
                            "text": text,
                        })

        if story_docs:
            documents_by_story[story_key] = story_docs

    total_docs = len(epic_documents) + sum(
        len(docs) for docs in documents_by_story.values()
    )

    logger.info(
        "Collecte epic %s : %d stories, %d documents total "
        "(epic: %d, stories: %d, vlm_focus=%s)",
        epic_key,
        len(stories),
        total_docs,
        len(epic_documents),
        total_docs - len(epic_documents),
        vlm_focus_story or "aucune",
    )

    return {
        "epic_key": epic_key,
        "total_stories": len(stories),
        "total_documents": total_docs,
        "documents_by_story": documents_by_story,
        "epic_documents": epic_documents,
    }


# ══════════════════════════════════════════════════════════════
#  FONCTIONS INTERNES
# ══════════════════════════════════════════════════════════════

def _get_attachments(issue_key: str) -> List[Dict[str, Any]]:
    """Récupère la liste des PJ d'un ticket Jira."""
    url = f"{JIRA_BASE_URL}/rest/api/2/issue/{issue_key}"
    try:
        resp = _session.get(url, params={"fields": "attachment"}, timeout=20)
        if resp.status_code != 200:
            return []
        fields = resp.json().get("fields", {}) or {}
        return fields.get("attachment", []) or []
    except requests.RequestException as e:
        logger.warning("Erreur récupération PJ de %s : %s", issue_key, e)
        return []


def _download_and_extract(
    attachment: Dict[str, Any],
    *,
    vlm_enabled: bool = False,
) -> Optional[str]:
    """Télécharge une PJ et extrait le texte.

    Les images bitmap ne sont envoyées au VLM Groq que si `vlm_enabled=True`.
    Par défaut on les ignore pour limiter le coût/latence : on n'active le VLM
    que sur les PJ de la story actuellement analysée.
    """
    content_url = attachment.get("content")
    filename = attachment.get("filename", "")
    size = attachment.get("size", 0)

    if not content_url:
        return None

    if size > MAX_FILE_SIZE:
        logger.info("Skip %s (trop volumineux : %d octets)", filename, size)
        return None

    name_lower = filename.lower()
    # Formats vectoriels / icônes non gérés par le VLM (et peu utiles pour la spec)
    if name_lower.endswith((".svg", ".ico")):
        return None

    is_image = name_lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"))
    if is_image and not vlm_enabled:
        logger.debug("Skip image %s (VLM désactivé pour cette source)", filename)
        return None

    try:
        resp = _session.get(content_url, timeout=None)
        if resp.status_code != 200:
            return None
    except requests.RequestException as e:
        logger.warning("Erreur téléchargement %s : %s", filename, e)
        return None

    if is_image:
        return describe_image(resp.content, filename)

    # PDF / DOCX / texte brut
    return extract_text_from_bytes(resp.content, filename)


def _get_epic_key(issue_key: str) -> Optional[str]:
    """Récupère la clé de l'epic parent d'une story."""
    url = f"{JIRA_BASE_URL}/rest/api/2/issue/{issue_key}"
    try:
        resp = _session.get(
            url,
            params={"fields": f"{JIRA_EPIC_LINK_FIELD},parent"},
            timeout=20,
        )
        if resp.status_code != 200:
            return None
        fields = resp.json().get("fields", {}) or {}
        epic_key = fields.get(JIRA_EPIC_LINK_FIELD)
        if not epic_key:
            parent = fields.get("parent") or {}
            if (parent.get("fields", {}) or {}).get("issuetype", {}).get("name") == "Epic":
                epic_key = parent.get("key")
        return epic_key
    except requests.RequestException:
        return None


def _get_linked_issue_keys(issue_key: str) -> List[str]:
    """Récupère les clés des tickets liés à une story."""
    url = f"{JIRA_BASE_URL}/rest/api/2/issue/{issue_key}"
    try:
        resp = _session.get(url, params={"fields": "issuelinks"}, timeout=20)
        if resp.status_code != 200:
            return []
        fields = resp.json().get("fields", {}) or {}
        issuelinks = fields.get("issuelinks", []) or []

        keys = []
        for link in issuelinks:
            for direction in ("inwardIssue", "outwardIssue"):
                target = link.get(direction)
                if target and target.get("key"):
                    keys.append(target["key"])
        return keys
    except requests.RequestException:
        return []


def _get_issue_description(issue_key: str) -> Optional[str]:
    """Récupère la description brute d'un ticket."""
    url = f"{JIRA_BASE_URL}/rest/api/2/issue/{issue_key}"
    try:
        resp = _session.get(url, params={"fields": "description"}, timeout=20)
        if resp.status_code != 200:
            return None
        fields = resp.json().get("fields", {}) or {}
        return fields.get("description")
    except requests.RequestException:
        return None
