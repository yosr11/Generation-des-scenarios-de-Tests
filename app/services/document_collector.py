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
from typing import Any, Dict, List, Optional

import requests
import urllib3
from dotenv import load_dotenv

from app.utils.document_loader import extract_text_from_bytes
from app.utils.cleaning import clean_text

load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "https://hra-jira.ptx.fr.sopra").rstrip("/")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_PASSWORD = os.getenv("JIRA_PASSWORD")
JIRA_EPIC_LINK_FIELD = os.getenv("JIRA_EPIC_LINK_FIELD", "customfield_12402")

# Taille max d'un fichier à télécharger (10 Mo)
MAX_FILE_SIZE = 10 * 1024 * 1024

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
    Retourne une liste de dicts {source, origin_key, filename, text}.
    """
    documents: List[Dict[str, Any]] = []

    # 1) PJ de la story elle-même
    story_attachments = _get_attachments(issue_key)
    for att in story_attachments:
        text = _download_and_extract(att)
        if text:
            documents.append({
                "source": "attachment",
                "origin_key": issue_key,
                "filename": att.get("filename", ""),
                "text": text,
            })

    # 2) PJ de l'epic parent
    epic_key = _get_epic_key(issue_key)
    if epic_key:
        epic_attachments = _get_attachments(epic_key)
        for att in epic_attachments:
            text = _download_and_extract(att)
            if text:
                documents.append({
                    "source": "epic_attachment",
                    "origin_key": epic_key,
                    "filename": att.get("filename", ""),
                    "text": text,
                })

    # 3) Tickets liés : description + PJ
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
            text = _download_and_extract(att)
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


def collect_documents_for_epic(epic_key: str) -> Dict[str, Any]:
    """
    Collecte les documents pour TOUTES les stories d'un epic.
    Déduplique : les PJ de l'epic et les PJ/descriptions partagées
    ne sont récupérées qu'une seule fois.

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

    # 1) PJ de l'epic lui-même (une seule fois)
    epic_documents: List[Dict[str, Any]] = []
    epic_attachments = _get_attachments(epic_key)
    for att in epic_attachments:
        text = _download_and_extract(att)
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

        # PJ de la story
        story_attachments = _get_attachments(story_key)
        for att in story_attachments:
            fname = att.get("filename", "")
            dedup_key = f"{story_key}_{fname}"
            if dedup_key not in seen_filenames:
                seen_filenames.add(dedup_key)
                text = _download_and_extract(att)
                if text:
                    story_docs.append({
                        "source": "attachment",
                        "origin_key": story_key,
                        "filename": fname,
                        "text": text,
                    })

        # Tickets liés (description + PJ), dédupliqués globalement
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
                    text = _download_and_extract(att)
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
        "(epic: %d, stories: %d)",
        epic_key,
        len(stories),
        total_docs,
        len(epic_documents),
        total_docs - len(epic_documents),
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


def _download_and_extract(attachment: Dict[str, Any]) -> Optional[str]:
    """Télécharge une PJ et extrait le texte."""
    content_url = attachment.get("content")
    filename = attachment.get("filename", "")
    size = attachment.get("size", 0)

    if not content_url:
        return None

    # Skip les fichiers trop gros ou les images
    if size > MAX_FILE_SIZE:
        logger.info("Skip %s (trop volumineux : %d octets)", filename, size)
        return None

    if filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".ico")):
        return None

    try:
        resp = _session.get(content_url, timeout=None)
        if resp.status_code != 200:
            return None
        return extract_text_from_bytes(resp.content, filename)
    except requests.RequestException as e:
        logger.warning("Erreur téléchargement %s : %s", filename, e)
        return None


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
