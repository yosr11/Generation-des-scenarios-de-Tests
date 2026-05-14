"""Dernier jeu de tests manuels (Agent 2) par story — pour chargement automatique par Agent 3."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.db.database import get_connection


def save_manual_tests_snapshot(story_id: str, tests: List[Dict[str, Any]], generation_model: str = "") -> int:
    if not story_id:
        return -1
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO story_manual_tests (story_id, tests_json, generation_model)
            VALUES (?, ?, ?)
            """,
            (story_id, json.dumps(tests, ensure_ascii=False), generation_model or ""),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def get_latest_manual_tests(story_id: str) -> Optional[List[Dict[str, Any]]]:
    """Retourne la liste des tests (dicts ManualTestCase) du dernier enregistrement, ou None."""
    if not story_id:
        return None
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT tests_json FROM story_manual_tests
            WHERE story_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (story_id,),
        ).fetchone()
        if not row or not row["tests_json"]:
            return None
        data = json.loads(row["tests_json"])
        if isinstance(data, list):
            return data
        return None
    finally:
        conn.close()
