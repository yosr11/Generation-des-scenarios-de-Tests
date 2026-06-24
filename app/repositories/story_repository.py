"""
app/repositories/story_repository.py
─────────────────────────────────────
CRUD pour la table stories.
Sérialise/désérialise les champs complexes en JSON.
"""

import json
from typing import Dict, Any, Optional, List
from app.db.database import get_connection


def _serialize(value) -> str:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value) if value is not None else ""


def _deserialize_json(raw: Optional[str], default=None):
    if not raw:
        return default if default is not None else []
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else []


def _row_to_dict(row) -> Dict[str, Any]:
    d = {
        "id":                 row["id"],
        "summary":            row["summary"] or "",
        "description_raw":    row["description_raw"] or "",
        "description_clean":  row["description_clean"] or "",
        "description_llm":    row["description_llm"] or "",
        "acceptance_criteria_raw":   row["acceptance_criteria_raw"] or "",
        "acceptance_criteria_clean": row["acceptance_criteria_clean"] or "",
        "labels":             _deserialize_json(row["labels"]),
        "components":         _deserialize_json(row["components"]),
        "issuelinks":         _deserialize_json(row["issuelinks"]),
        "priority":           row["priority"] or "",
        "status":             row["status"] or "",
        "fixVersions":        _deserialize_json(row["fix_versions"]),
        "requirement_status": _deserialize_json(row["requirement_status"]),
        "references":         _deserialize_json(row["references_json"], default={}),
        "flags":              _deserialize_json(row["flags"], default={}),
        "story_context_llm":  row["story_context_llm"] or "",
        "created_at":         row["created_at"] or "",
    }
    # Colonnes epic (ajoutées après la création initiale de la table)
    try:
        d["epic_key"] = row["epic_key"] or ""
        d["epic_summary"] = row["epic_summary"] or ""
        d["epic_description"] = row["epic_description"] or ""
    except (IndexError, KeyError):
        d["epic_key"] = ""
        d["epic_summary"] = ""
        d["epic_description"] = ""
    # Colonne versioning Jira
    try:
        d["jira_updated"] = row["jira_updated"] or ""
    except (IndexError, KeyError):
        d["jira_updated"] = ""
    return d


# ── SAVE (insert or replace) ────────────────────────────────

def save_story(story: Dict[str, Any]) -> str:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO stories
                (id, summary, description_raw, description_clean, description_llm,
                 acceptance_criteria_raw, acceptance_criteria_clean,
                 labels, components, issuelinks, priority, status,
                 fix_versions, requirement_status, references_json, flags,
                 story_context_llm, epic_key, epic_summary, epic_description, jira_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                story.get("id", ""),
                story.get("summary", ""),
                story.get("description_raw", ""),
                story.get("description_clean", ""),
                story.get("description_llm", ""),
                story.get("acceptance_criteria_raw", ""),
                story.get("acceptance_criteria_clean", ""),
                _serialize(story.get("labels", [])),
                _serialize(story.get("components", [])),
                _serialize(story.get("issuelinks", [])),
                story.get("priority", ""),
                story.get("status", ""),
                _serialize(story.get("fixVersions", [])),
                _serialize(story.get("requirement_status", [])),
                _serialize(story.get("references", {})),
                _serialize(story.get("flags", {})),
                story.get("story_context_llm", ""),
                story.get("epic_key", ""),
                story.get("epic_summary", ""),
                story.get("epic_description", ""),
                story.get("jira_updated", ""),
            ),
        )
        conn.commit()
        return story.get("id", "")
    finally:
        conn.close()


def save_stories_bulk(stories: List[Dict[str, Any]]) -> int:
    conn = get_connection()
    try:
        for story in stories:
            conn.execute(
                """
                INSERT OR REPLACE INTO stories
                    (id, summary, description_raw, description_clean, description_llm,
                     acceptance_criteria_raw, acceptance_criteria_clean,
                     labels, components, issuelinks, priority, status,
                     fix_versions, requirement_status, references_json, flags,
                     story_context_llm, epic_key, epic_summary, epic_description, jira_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    story.get("id", ""),
                    story.get("summary", ""),
                    story.get("description_raw", ""),
                    story.get("description_clean", ""),
                    story.get("description_llm", ""),
                    story.get("acceptance_criteria_raw", ""),
                    story.get("acceptance_criteria_clean", ""),
                    _serialize(story.get("labels", [])),
                    _serialize(story.get("components", [])),
                    _serialize(story.get("issuelinks", [])),
                    story.get("priority", ""),
                    story.get("status", ""),
                    _serialize(story.get("fixVersions", [])),
                    _serialize(story.get("requirement_status", [])),
                    _serialize(story.get("references", {})),
                    _serialize(story.get("flags", {})),
                    story.get("story_context_llm", ""),
                    story.get("epic_key", ""),
                    story.get("epic_summary", ""),
                    story.get("epic_description", ""),
                    story.get("jira_updated", ""),
                ),
            )
        conn.commit()
        return len(stories)
    finally:
        conn.close()


# ── GET ──────────────────────────────────────────────────────

def get_story_by_id(story_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM stories WHERE id = ?", (story_id,)).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def get_all_stories() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM stories ORDER BY created_at DESC").fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_stories_by_ids(story_ids: List[str]) -> List[Dict[str, Any]]:
    if not story_ids:
        return []
    conn = get_connection()
    try:
        placeholders = ",".join("?" for _ in story_ids)
        rows = conn.execute(
            f"SELECT * FROM stories WHERE id IN ({placeholders})",
            story_ids,
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()
