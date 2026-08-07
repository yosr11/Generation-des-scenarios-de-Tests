"""Persistance des rapports finaux Agent 5."""

from typing import Any, Dict, Optional

from sqlalchemy import select

from app.db.postgres import get_sync_session
from app.models.pg_models import Report


def save_report(report_data: Dict[str, Any]) -> int:
    """Enregistre un rapport complet et retourne son identifiant."""
    session = get_sync_session()
    try:
        obj = Report(
            story_id=report_data.get("story_id", ""),
            report_title=report_data.get("report_title"),
            report_version=report_data.get("report_version"),
            generated_timestamp=report_data.get("generated_timestamp"),
            report_data=report_data,
        )
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj.id
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_latest_report(story_id: str) -> Optional[Dict[str, Any]]:
    """Retourne le dernier rapport enregistré pour une story."""
    session = get_sync_session()
    try:
        obj = (
            session.execute(
                select(Report)
                .where(Report.story_id == story_id)
                .order_by(Report.created_at.desc(), Report.id.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        if obj is None:
            return None
        return {
            "id": obj.id,
            "story_id": obj.story_id,
            "report_title": obj.report_title,
            "report_version": obj.report_version,
            "generated_timestamp": obj.generated_timestamp,
            "report_data": obj.report_data,
            "created_at": str(obj.created_at) if obj.created_at else "",
        }
    finally:
        session.close()