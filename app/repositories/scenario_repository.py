"""
app/repositories/scenario_repository.py
────────────────────────────────────────
CRUD pour la table generated_scenarios.
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
        "id":              row["id"],
        "story_id":        row["story_id"],
        "title":           row["title"] or "",
        "type":            row["type"] or "",
        "priority":        row["priority"] or "",
        "preconditions":   _deserialize_json(row["preconditions"]),
        "steps":           _deserialize_json(row["steps"]),
        "expected_result": row["expected_result"] or "",
        "source_ustype":   row["source_ustype"] or "",
        "model":           row["model"] or "",
        "created_at":      row["created_at"] or "",
    }


# ── SAVE ─────────────────────────────────────────────────────

def save_scenario(scenario: Dict[str, Any]) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO generated_scenarios
                (story_id, title, type, priority, preconditions,
                 steps, expected_result, source_ustype, model)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scenario.get("source_story", ""),
                scenario.get("title", ""),
                scenario.get("type", ""),
                scenario.get("priority", ""),
                _serialize(scenario.get("preconditions", [])),
                _serialize(scenario.get("steps", [])),
                scenario.get("expected_result", ""),
                scenario.get("source_ustype", ""),
                scenario.get("model", ""),
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def save_scenarios_bulk(scenarios: List[Dict[str, Any]], model: str = "") -> int:
    conn = get_connection()
    try:
        for s in scenarios:
            conn.execute(
                """
                INSERT INTO generated_scenarios
                    (story_id, title, type, priority, preconditions,
                     steps, expected_result, source_ustype, model)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    s.get("source_story", ""),
                    s.get("title", ""),
                    s.get("type", ""),
                    s.get("priority", ""),
                    _serialize(s.get("preconditions", [])),
                    _serialize(s.get("steps", [])),
                    s.get("expected_result", ""),
                    s.get("source_ustype", ""),
                    model or s.get("model", ""),
                ),
            )
        conn.commit()
        return len(scenarios)
    finally:
        conn.close()


# ── GET ──────────────────────────────────────────────────────

def get_scenarios_by_story(story_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM generated_scenarios WHERE story_id = ? ORDER BY created_at DESC",
            (story_id,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_all_scenarios() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM generated_scenarios ORDER BY created_at DESC").fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()
