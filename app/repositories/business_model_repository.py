"""
app/repositories/business_model_repository.py
───────────────────────────────────────────────
CRUD pour la table story_business_models (résultats Agent 1.5).
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.db.database import get_connection

logger = logging.getLogger(__name__)


# ─── Helpers de sérialisation ───────────────────────────────────────────────

def _to_json(value: Any) -> str:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value) if value is not None else ""


def _from_json(raw: Optional[str], default=None) -> Any:
    if not raw:
        return default if default is not None else []
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else []


def _row_to_dict(row) -> Dict[str, Any]:
    return {
        "id":                row["id"],
        "story_id":          row["story_id"],
        "model":             row["model"] or "",
        "business_goals":    _from_json(row["business_goals"], default=[]),
        "business_workflows": _from_json(row["business_workflows"], default=[]),
        "modeling_notes":    row["modeling_notes"] or "",
        "created_at":        row["created_at"] or "",
    }


# ─── SAVE ────────────────────────────────────────────────────────────────────

def save_business_model(result_dict: Dict[str, Any]) -> int:
    """
    Persiste un BusinessModelingResult (sous forme dict) dans story_business_models.

    Returns:
        rowid de la ligne insérée (>0), ou -1 en cas d'erreur.
    """
    conn = get_connection()
    try:
        story_id = result_dict.get("story_id", "")
        cur = conn.execute(
            """
            INSERT INTO story_business_models
                (story_id, model, business_goals, business_workflows, modeling_notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                story_id,
                result_dict.get("model", ""),
                _to_json(result_dict.get("business_goals", [])),
                _to_json(result_dict.get("business_workflows", [])),
                result_dict.get("modeling_notes", "") or "",
            ),
        )
        conn.commit()
        logger.info(f"[BM Repo] Business model sauvegardé pour {story_id} (rowid={cur.lastrowid})")
        return cur.lastrowid
    except Exception as exc:
        logger.error(f"[BM Repo] Erreur lors de la sauvegarde : {exc}", exc_info=True)
        return -1
    finally:
        conn.close()


# ─── GET LATEST ──────────────────────────────────────────────────────────────

def get_latest_business_model(
    story_id: str,
    model: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Retourne le dernier business model persisté pour une story.

    Args:
        story_id : identifiant Jira de la story.
        model    : filtre optionnel sur l'alias modèle.

    Returns:
        Dict ou None si absent.
    """
    conn = get_connection()
    try:
        if model:
            row = conn.execute(
                """
                SELECT * FROM story_business_models
                WHERE story_id = ? AND model = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (story_id, model),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT * FROM story_business_models
                WHERE story_id = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (story_id,),
            ).fetchone()

        return _row_to_dict(row) if row else None
    except Exception as exc:
        logger.error(f"[BM Repo] Erreur lors de la lecture pour {story_id}: {exc}", exc_info=True)
        return None
    finally:
        conn.close()


# ─── LIST ────────────────────────────────────────────────────────────────────

def list_business_models(story_id: str) -> List[Dict[str, Any]]:
    """Retourne l'historique complet des business models pour une story."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM story_business_models WHERE story_id = ? ORDER BY created_at DESC",
            (story_id,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    except Exception as exc:
        logger.error(f"[BM Repo] Erreur listing pour {story_id}: {exc}", exc_info=True)
        return []
    finally:
        conn.close()
