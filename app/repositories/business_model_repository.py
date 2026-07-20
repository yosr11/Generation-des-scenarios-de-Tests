"""
app/repositories/business_model_repository.py
───────────────────────────────────────────────
CRUD pour la table story_business_models (résultats Agent 1.5) — PostgreSQL (SQLAlchemy ORM).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from app.db.postgres import get_sync_session
from app.models.pg_models import StoryBusinessModel

logger = logging.getLogger(__name__)


# ─── SAVE ────────────────────────────────────────────────────────────────────

def save_business_model(result_dict: Dict[str, Any]) -> int:
    """
    Persiste un BusinessModelingResult (sous forme dict) dans story_business_models.

    Returns:
        id de la ligne insérée (>0), ou -1 en cas d'erreur.
    """
    session = get_sync_session()
    story_id = result_dict.get("story_id", "")
    try:
        obj = StoryBusinessModel(
            story_id=story_id,
            model=result_dict.get("model", ""),
            business_goals=result_dict.get("business_goals", []),
            business_workflows=result_dict.get("business_workflows", []),
            modeling_notes=result_dict.get("modeling_notes", "") or "",
        )
        session.add(obj)
        session.commit()
        session.refresh(obj)
        logger.info("[BM Repo] Business model sauvegardé pour %s (id=%s)", story_id, obj.id)
        return obj.id
    except Exception as exc:
        logger.error("[BM Repo] Erreur lors de la sauvegarde : %s", exc, exc_info=True)
        session.rollback()
        return -1
    finally:
        session.close()


# ─── GET LATEST ──────────────────────────────────────────────────────────────

def get_latest_business_model(story_id: str, model: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retourne le dernier business model persisté pour une story.

    Args:
        story_id : identifiant Jira de la story.
        model    : filtre optionnel sur l'alias modèle.

    Returns:
        Dict ou None si absent.
    """
    session = get_sync_session()
    try:
        stmt = select(StoryBusinessModel).where(StoryBusinessModel.story_id == story_id)
        if model:
            stmt = stmt.where(StoryBusinessModel.model == model)
        stmt = stmt.order_by(StoryBusinessModel.created_at.desc()).limit(1)
        obj = session.execute(stmt).scalar_one_or_none()
        return _row_to_dict(obj) if obj else None
    except Exception as exc:
        logger.error("[BM Repo] Erreur lors de la lecture pour %s: %s", story_id, exc, exc_info=True)
        return None
    finally:
        session.close()


# ─── LIST ────────────────────────────────────────────────────────────────────

def list_business_models(story_id: str) -> List[Dict[str, Any]]:
    """Retourne l'historique complet des business models pour une story."""
    session = get_sync_session()
    try:
        rows = session.execute(
            select(StoryBusinessModel)
            .where(StoryBusinessModel.story_id == story_id)
            .order_by(StoryBusinessModel.created_at.desc())
        ).scalars().all()
        return [_row_to_dict(r) for r in rows]
    except Exception as exc:
        logger.error("[BM Repo] Erreur listing pour %s: %s", story_id, exc, exc_info=True)
        return []
    finally:
        session.close()


# ─── Helper ──────────────────────────────────────────────────────────────────

def _row_to_dict(obj: StoryBusinessModel) -> Dict[str, Any]:
    return {
        "id":                 obj.id,
        "story_id":           obj.story_id,
        "model":              obj.model or "",
        "business_goals":     obj.business_goals or [],
        "business_workflows": obj.business_workflows or [],
        "modeling_notes":     obj.modeling_notes or "",
        "created_at":         str(obj.created_at) if obj.created_at else "",
    }
