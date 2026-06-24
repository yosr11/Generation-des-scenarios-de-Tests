"""Dernier jeu de tests manuels (Agent 2) par story — pour chargement automatique par Agent 3."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.db.database import get_connection


def save_manual_tests_snapshot(story_id: str, tests: List[Dict[str, Any]], generation_model: str = "") -> int:
    """Sauvegarde un snapshot de tests en remplaçant l'ancien (idempotent)."""
    if not story_id:
        return -1
    conn = get_connection()
    try:
        # Supprimer l'ancien snapshot pour cette story (idempotence)
        conn.execute("DELETE FROM story_manual_tests WHERE story_id = ?", (story_id,))
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


def get_latest_manual_tests_as_pydantic(story_id: str):
    """Retourne ManualTestGenerationResult (objet Pydantic) au lieu de liste de dicts."""
    from app.models.test_manual import ManualTestGenerationResult, ManualTestCase, RecommendedTestStrategy, ManualGenerationStatus
    
    tests_raw = get_latest_manual_tests(story_id)
    if not tests_raw:
        return None
    
    try:
        # Convertir chaque dict en ManualTestCase
        tests = []
        for test_dict in tests_raw:
            try:
                tests.append(ManualTestCase(**test_dict))
            except Exception as e:
                print(f"Error converting test to ManualTestCase: {e}")
                continue
        
        return ManualTestGenerationResult(
            story_id=story_id,
            recommended_test_strategy=RecommendedTestStrategy.MANUAL,
            generation_status=ManualGenerationStatus.GENERATED,
            message=f"{len(tests)} tests générés",
            tests=tests,
            notes=[],
        )
    except Exception as e:
        print(f"Error converting manual tests to Pydantic: {e}")
        return None
