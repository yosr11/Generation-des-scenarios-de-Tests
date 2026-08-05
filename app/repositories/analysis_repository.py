"""
app/repositories/analysis_repository.py
────────────────────────────────────────
CRUD pour la table story_analysis — PostgreSQL (SQLAlchemy ORM).
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from app.db.postgres import get_sync_session
from app.models.pg_models import StoryAnalysis

logger = logging.getLogger(__name__)


def _row_to_dict(obj: StoryAnalysis) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "story_id": obj.story_id,
        "model": obj.model or "",
        "story_title": obj.story_title or "",
        "story_type": obj.story_type or "",
        "actors": obj.actors or [],
        "actions": obj.actions or [],
        "business_rules": obj.business_rules or [],
        "technical_scope": obj.technical_scope or [],
        "testable_points": obj.testable_points or [],
        "acceptance_criteria_explicit": obj.acceptance_criteria_explicit or [],
        "acceptance_criteria_inferred": obj.acceptance_criteria_inferred or [],
        "clarification_questions": obj.clarification_questions or [],
        "analysis_reason": obj.analysis_reason or [],
        "user_flows": obj.user_flows or [],
        "resolved_from_references": obj.resolved_from_references or [],
        "created_at": str(obj.created_at) if obj.created_at else "",
    }


# ── SAVE ────────────────────────────────────────────────────────────────────


def save_analysis(analysis: Dict[str, Any]) -> int:
    session = get_sync_session()
    story_id = analysis.get("story_id", "")
    logger.info("[SAVE] Saving analysis for %s", story_id)
    try:
        obj = StoryAnalysis(
            story_id=story_id,
            model=analysis.get("model", ""),
            story_title=analysis.get("story_title", ""),
            story_type=analysis.get("story_type", ""),
            actors=analysis.get("actors", []),
            actions=analysis.get("actions", []),
            business_rules=analysis.get("business_rules", []),
            technical_scope=analysis.get("technical_scope", []),
            testable_points=analysis.get("testable_points", []),
            acceptance_criteria_explicit=analysis.get(
                "acceptance_criteria_explicit", []
            ),
            acceptance_criteria_inferred=analysis.get(
                "acceptance_criteria_inferred", []
            ),
            clarification_questions=analysis.get("clarification_questions", []),
            analysis_reason=analysis.get("analysis_reason", []),
            user_flows=analysis.get("user_flows", []),
            resolved_from_references=analysis.get("resolved_from_references", []),
        )
        session.add(obj)
        session.commit()
        session.refresh(obj)
        logger.info("[SAVE] Analysis saved for %s (id=%s)", story_id, obj.id)
        return obj.id
    except Exception as e:
        logger.error("[SAVE] Error saving analysis: %s", e, exc_info=True)
        session.rollback()
        return -1
    finally:
        session.close()


def save_analyses_bulk(analyses: List[Dict[str, Any]]) -> int:
    session = get_sync_session()
    try:
        for a in analyses:
            obj = StoryAnalysis(
                story_id=a.get("story_id", ""),
                model=a.get("model", ""),
                story_title=a.get("story_title", ""),
                story_type=a.get("story_type", ""),
                actors=a.get("actors", []),
                actions=a.get("actions", []),
                business_rules=a.get("business_rules", []),
                technical_scope=a.get("technical_scope", []),
                testable_points=a.get("testable_points", []),
                acceptance_criteria_explicit=a.get("acceptance_criteria_explicit", []),
                acceptance_criteria_inferred=a.get("acceptance_criteria_inferred", []),
                clarification_questions=a.get("clarification_questions", []),
                analysis_reason=a.get("analysis_reason", []),
                user_flows=a.get("user_flows", []),
                resolved_from_references=a.get("resolved_from_references", []),
            )
            session.add(obj)
        session.commit()
        return len(analyses)
    finally:
        session.close()


# ── GET ─────────────────────────────────────────────────────────────────────


def get_analyses_by_story(story_id: str) -> List[Dict[str, Any]]:
    session = get_sync_session()
    try:
        rows = (
            session.execute(
                select(StoryAnalysis)
                .where(StoryAnalysis.story_id == story_id)
                .order_by(StoryAnalysis.created_at.desc())
            )
            .scalars()
            .all()
        )
        return [_row_to_dict(r) for r in rows]
    finally:
        session.close()


def get_latest_analysis(
    story_id: str, model: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    session = get_sync_session()
    try:
        stmt = select(StoryAnalysis).where(StoryAnalysis.story_id == story_id)
        if model:
            stmt = stmt.where(StoryAnalysis.model == model)
        stmt = stmt.order_by(StoryAnalysis.created_at.desc()).limit(1)
        obj = session.execute(stmt).scalar_one_or_none()
        if not obj:
            logger.warning("[FETCH] No analysis found for %s", story_id)
            return None
        return _row_to_dict(obj)
    except Exception as e:
        logger.error(
            "[FETCH] Error getting analysis for %s: %s", story_id, e, exc_info=True
        )
        return None
    finally:
        session.close()


def debug_analysis_in_db(story_id: str) -> int:
    """Fonction de diagnostic : affiche les enregistrements en base pour une story."""
    session = get_sync_session()
    try:
        rows = (
            session.execute(
                select(StoryAnalysis)
                .where(StoryAnalysis.story_id == story_id)
                .order_by(StoryAnalysis.created_at.desc())
            )
            .scalars()
            .all()
        )
        logger.info("[DEBUG] Found %d analysis records for %s", len(rows), story_id)
        for i, obj in enumerate(rows):
            logger.info("[DEBUG] Record %d: id=%s model=%s", i, obj.id, obj.model)
        return len(rows)
    except Exception as e:
        logger.error("[DEBUG] Error checking DB for %s: %s", story_id, e, exc_info=True)
        return -1
    finally:
        session.close()


def get_latest_analysis_as_pydantic(story_id: str, model: Optional[str] = None):
    """Retourne StoryAnalysisResult (objet Pydantic) au lieu de dict."""
    from app.models.analysis import StoryAnalysisResult

    data = get_latest_analysis(story_id, model)
    if not data:
        logger.warning("[Agent5] No analysis data found in DB for %s", story_id)
        return None

    logger.info(
        "[Agent5] Analysis data found for %s: keys=%s", story_id, list(data.keys())
    )
    try:
        result = StoryAnalysisResult(
            story_id=data.get("story_id", story_id),
            story_title=data.get("story_title", story_id),
            story_type=data.get("story_type", "functional"),
            actors=data.get("actors", []),
            actions=data.get("actions", []),
            business_rules=data.get("business_rules", []),
            technical_scope=data.get("technical_scope", []),
            testable_points=data.get("testable_points", []),
            user_flows=data.get("user_flows", []),
            acceptance_criteria_explicit=data.get("acceptance_criteria_explicit", []),
            acceptance_criteria_inferred=data.get("acceptance_criteria_inferred", []),
            clarification_questions=data.get("clarification_questions", []),
            analysis_reason=data.get("analysis_reason", []),
            resolved_from_references=data.get("resolved_from_references", []),
        )
        logger.info(
            "[Agent5] Successfully converted analysis to Pydantic for %s", story_id
        )
        return result
    except Exception as e:
        logger.error(
            "[Agent5] Error converting analysis to Pydantic for %s: %s",
            story_id,
            e,
            exc_info=True,
        )
        return None


def fetch_analysis_by_story_id(story_id: str) -> Optional[Dict[str, Any]]:
    return get_latest_analysis(story_id)
