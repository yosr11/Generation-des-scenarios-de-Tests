"""
app/repositories/story_repository.py
─────────────────────────────────────
CRUD pour la table stories — PostgreSQL (SQLAlchemy ORM).
Les champs complexes sont stockés en JSONB natif (plus de sérialisation manuelle).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from app.db.postgres import get_sync_session
from app.models.pg_models import Story


def _row_to_dict(obj: Story) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "summary": obj.summary or "",
        "description_clean": obj.description_clean or "",
        "acceptance_criteria_clean": obj.acceptance_criteria_clean or "",
        "labels": obj.labels or [],
        "components": obj.components or [],
        "issuelinks": obj.issuelinks or [],
        "priority": obj.priority or "",
        "status": obj.status or "",
        "story_context_llm": obj.story_context_llm or "",
        "epic_key": obj.epic_key or "",
        "epic_summary": obj.epic_summary or "",
        "epic_description": obj.epic_description or "",
        "jira_updated": obj.jira_updated or "",
        "created_at": str(obj.created_at) if obj.created_at else "",
    }


# ── SAVE (insert or replace) ────────────────────────────────────────────────


def save_story(story: Dict[str, Any]) -> str:
    """
    Upsert de la story. `created_at` est explicitement forcé à "maintenant"
    à CHAQUE appel : sur un `session.merge()`, un attribut jamais assigné sur
    l'objet transitoire n'écrase pas la valeur déjà en base, donc sans ce
    `datetime.now(timezone.utc)` explicite, la date affichée dans l'historique
    restait figée à la date du tout premier traitement de la story.
    """
    session = get_sync_session()
    try:
        obj = Story(
            id=story.get("id", ""),
            summary=story.get("summary", ""),
            description_clean=story.get("description_clean", ""),
            acceptance_criteria_clean=story.get("acceptance_criteria_clean", ""),
            labels=story.get("labels", []),
            components=story.get("components", []),
            issuelinks=story.get("issuelinks", []),
            priority=story.get("priority", ""),
            status=story.get("status", ""),
            story_context_llm=story.get("story_context_llm", ""),
            epic_key=story.get("epic_key", ""),
            epic_summary=story.get("epic_summary", ""),
            epic_description=story.get("epic_description", ""),
            jira_updated=story.get("jira_updated", ""),
            created_at=datetime.now(timezone.utc),
        )
        session.merge(obj)  # INSERT OR UPDATE (upsert via PK)
        session.commit()
        return obj.id
    finally:
        session.close()


def save_stories_bulk(stories: List[Dict[str, Any]]) -> int:
    session = get_sync_session()
    try:
        now = datetime.now(timezone.utc)
        for story in stories:
            obj = Story(
                id=story.get("id", ""),
                summary=story.get("summary", ""),
                description_clean=story.get("description_clean", ""),
                acceptance_criteria_clean=story.get("acceptance_criteria_clean", ""),
                labels=story.get("labels", []),
                components=story.get("components", []),
                issuelinks=story.get("issuelinks", []),
                priority=story.get("priority", ""),
                status=story.get("status", ""),
                story_context_llm=story.get("story_context_llm", ""),
                epic_key=story.get("epic_key", ""),
                epic_summary=story.get("epic_summary", ""),
                epic_description=story.get("epic_description", ""),
                jira_updated=story.get("jira_updated", ""),
                created_at=now,
            )
            session.merge(obj)
        session.commit()
        return len(stories)
    finally:
        session.close()


# ── GET ─────────────────────────────────────────────────────────────────────


def get_story_by_id(story_id: str) -> Optional[Dict[str, Any]]:
    session = get_sync_session()
    try:
        obj = session.get(Story, story_id)
        return _row_to_dict(obj) if obj else None
    finally:
        session.close()


def get_all_stories() -> List[Dict[str, Any]]:
    session = get_sync_session()
    try:
        rows = (
            session.execute(select(Story).order_by(Story.created_at.desc()))
            .scalars()
            .all()
        )
        return [_row_to_dict(r) for r in rows]
    finally:
        session.close()


def get_stories_by_ids(story_ids: List[str]) -> List[Dict[str, Any]]:
    if not story_ids:
        return []
    session = get_sync_session()
    try:
        rows = (
            session.execute(select(Story).where(Story.id.in_(story_ids)))
            .scalars()
            .all()
        )
        return [_row_to_dict(r) for r in rows]
    finally:
        session.close()


def get_stories_by_epic_key(epic_key: str) -> List[Dict[str, Any]]:
    """Stories déjà en base pour un epic donné."""
    if not epic_key:
        return []
    session = get_sync_session()
    try:
        rows = (
            session.execute(
                select(Story)
                .where(Story.epic_key == epic_key.strip().upper())
                .order_by(Story.created_at.desc())
            )
            .scalars()
            .all()
        )
        return [_row_to_dict(r) for r in rows]
    finally:
        session.close()