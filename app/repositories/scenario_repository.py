"""
app/repositories/scenario_repository.py
────────────────────────────────────────
CRUD pour la table generated_scenarios — PostgreSQL (SQLAlchemy ORM).
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import select

from app.db.postgres import get_sync_session
from app.models.pg_models import GeneratedScenario


def _row_to_dict(obj: GeneratedScenario) -> Dict[str, Any]:
    return {
        "id":              obj.id,
        "story_id":        obj.story_id,
        "title":           obj.title or "",
        "type":            obj.scenario_type or "",
        "priority":        obj.priority or "",
        "preconditions":   obj.preconditions or [],
        "steps":           obj.steps or [],
        "expected_result": obj.expected_result or "",
        "source_ustype":   obj.source_ustype or "",
        "model":           obj.model or "",
        "created_at":      str(obj.created_at) if obj.created_at else "",
    }


# ── SAVE ─────────────────────────────────────────────────────────────────────

def save_scenario(scenario: Dict[str, Any]) -> int:
    session = get_sync_session()
    try:
        obj = GeneratedScenario(
            story_id=scenario.get("source_story", ""),
            title=scenario.get("title", ""),
            scenario_type=scenario.get("type", ""),
            priority=scenario.get("priority", ""),
            preconditions=scenario.get("preconditions", []),
            steps=scenario.get("steps", []),
            expected_result=scenario.get("expected_result", ""),
            source_ustype=scenario.get("source_ustype", ""),
            model=scenario.get("model", ""),
        )
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj.id
    finally:
        session.close()


def save_scenarios_bulk(scenarios: List[Dict[str, Any]], model: str = "") -> int:
    session = get_sync_session()
    try:
        for s in scenarios:
            obj = GeneratedScenario(
                story_id=s.get("source_story", ""),
                title=s.get("title", ""),
                scenario_type=s.get("type", ""),
                priority=s.get("priority", ""),
                preconditions=s.get("preconditions", []),
                steps=s.get("steps", []),
                expected_result=s.get("expected_result", ""),
                source_ustype=s.get("source_ustype", ""),
                model=model or s.get("model", ""),
            )
            session.add(obj)
        session.commit()
        return len(scenarios)
    finally:
        session.close()


# ── GET ───────────────────────────────────────────────────────────────────────

def get_scenarios_by_story(story_id: str) -> List[Dict[str, Any]]:
    session = get_sync_session()
    try:
        rows = session.execute(
            select(GeneratedScenario)
            .where(GeneratedScenario.story_id == story_id)
            .order_by(GeneratedScenario.created_at.desc())
        ).scalars().all()
        return [_row_to_dict(r) for r in rows]
    finally:
        session.close()


def get_all_scenarios() -> List[Dict[str, Any]]:
    session = get_sync_session()
    try:
        rows = session.execute(
            select(GeneratedScenario).order_by(GeneratedScenario.created_at.desc())
        ).scalars().all()
        return [_row_to_dict(r) for r in rows]
    finally:
        session.close()
