"""Dernier jeu de tests manuels (Agent 2) par story — PostgreSQL (SQLAlchemy ORM)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select

from app.db.postgres import get_sync_session
from app.models.pg_models import StoryManualTests


def save_manual_tests_snapshot(story_id: str, tests: List[Dict[str, Any]], generation_model: str = "") -> int:
    """Sauvegarde un snapshot de tests en remplaçant l'ancien (idempotent)."""
    if not story_id:
        return -1
    session = get_sync_session()
    try:
        # Supprimer l'ancien snapshot (idempotence)
        existing = session.execute(
            select(StoryManualTests).where(StoryManualTests.story_id == story_id)
        ).scalars().all()
        for row in existing:
            session.delete(row)

        obj = StoryManualTests(
            story_id=story_id,
            tests_json=tests,  # JSONB natif — pas de json.dumps()
            generation_model=generation_model or "",
        )
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj.id
    finally:
        session.close()


def get_latest_manual_tests(story_id: str) -> Optional[List[Dict[str, Any]]]:
    """Retourne la liste des tests du dernier enregistrement, ou None."""
    if not story_id:
        return None
    session = get_sync_session()
    try:
        obj = session.execute(
            select(StoryManualTests)
            .where(StoryManualTests.story_id == story_id)
            .order_by(StoryManualTests.id.desc())
            .limit(1)
        ).scalar_one_or_none()
        if not obj or not obj.tests_json:
            return None
        data = obj.tests_json  # Déjà désérialisé par SQLAlchemy/JSONB
        return data if isinstance(data, list) else None
    finally:
        session.close()


def get_latest_manual_tests_as_pydantic(story_id: str):
    """Retourne ManualTestGenerationResult (objet Pydantic) au lieu de liste de dicts."""
    from app.models.test_manual import (
        ManualGenerationStatus,
        ManualTestCase,
        ManualTestGenerationResult,
        RecommendedTestStrategy,
    )

    tests_raw = get_latest_manual_tests(story_id)
    if not tests_raw:
        return None

    try:
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
