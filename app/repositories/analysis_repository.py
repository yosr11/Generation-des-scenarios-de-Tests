"""
app/repositories/analysis_repository.py
────────────────────────────────────────
CRUD pour la table story_analysis (résultats LLM).
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
    return {
        "id":                          row["id"],
        "story_id":                    row["story_id"],
        "model":                       row["model"] or "",
        "story_type":                  row["story_type"] or "",
        "exploitability":              row["exploitability"] or "",
        "recommended_test_type":       row["recommended_test_type"] or "",
        "actors":                      _deserialize_json(row["actors"]),
        "actions":                     _deserialize_json(row["actions"]),
        "business_rules":              _deserialize_json(row["business_rules"]),
        "technical_scope":             _deserialize_json(row["technical_scope"]),
        "testable_points":             _deserialize_json(row["testable_points"]),
        "acceptance_criteria_explicit": _deserialize_json(row["acceptance_criteria_explicit"]),
        "acceptance_criteria_inferred": _deserialize_json(row["acceptance_criteria_inferred"]),
        "clarification_questions":     _deserialize_json(row["clarification_questions"]),
        "analysis_reason":             _deserialize_json(row["analysis_reason"]),
        "created_at":                  row["created_at"] or "",
    }


# ── SAVE ─────────────────────────────────────────────────────

def save_analysis(analysis: Dict[str, Any]) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO story_analysis
                (story_id, model, story_type, exploitability, recommended_test_type,
                 actors, actions, business_rules, technical_scope, testable_points,
                 acceptance_criteria_explicit, acceptance_criteria_inferred,
                 clarification_questions, analysis_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                analysis.get("story_id", ""),
                analysis.get("model", ""),
                analysis.get("story_type", ""),
                analysis.get("exploitability", ""),
                analysis.get("recommended_test_type", ""),
                _serialize(analysis.get("actors", [])),
                _serialize(analysis.get("actions", [])),
                _serialize(analysis.get("business_rules", [])),
                _serialize(analysis.get("technical_scope", [])),
                _serialize(analysis.get("testable_points", [])),
                _serialize(analysis.get("acceptance_criteria_explicit", [])),
                _serialize(analysis.get("acceptance_criteria_inferred", [])),
                _serialize(analysis.get("clarification_questions", [])),
                _serialize(analysis.get("analysis_reason", [])),
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def save_analyses_bulk(analyses: List[Dict[str, Any]]) -> int:
    conn = get_connection()
    try:
        for a in analyses:
            conn.execute(
                """
                INSERT INTO story_analysis
                    (story_id, model, story_type, exploitability, recommended_test_type,
                     actors, actions, business_rules, technical_scope, testable_points,
                     acceptance_criteria_explicit, acceptance_criteria_inferred,
                     clarification_questions, analysis_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    a.get("story_id", ""),
                    a.get("model", ""),
                    a.get("story_type", ""),
                    a.get("exploitability", ""),
                    a.get("recommended_test_type", ""),
                    _serialize(a.get("actors", [])),
                    _serialize(a.get("actions", [])),
                    _serialize(a.get("business_rules", [])),
                    _serialize(a.get("technical_scope", [])),
                    _serialize(a.get("testable_points", [])),
                    _serialize(a.get("acceptance_criteria_explicit", [])),
                    _serialize(a.get("acceptance_criteria_inferred", [])),
                    _serialize(a.get("clarification_questions", [])),
                    _serialize(a.get("analysis_reason", [])),
                ),
            )
        conn.commit()
        return len(analyses)
    finally:
        conn.close()


# ── GET ──────────────────────────────────────────────────────

def get_analyses_by_story(story_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM story_analysis WHERE story_id = ? ORDER BY created_at DESC",
            (story_id,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_latest_analysis(story_id: str, model: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        if model:
            row = conn.execute(
                "SELECT * FROM story_analysis WHERE story_id = ? AND model = ? ORDER BY created_at DESC LIMIT 1",
                (story_id, model),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM story_analysis WHERE story_id = ? ORDER BY created_at DESC LIMIT 1",
                (story_id,),
            ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()
