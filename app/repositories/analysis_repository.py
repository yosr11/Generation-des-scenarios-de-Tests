"""
app/repositories/analysis_repository.py
────────────────────────────────────────
CRUD pour la table story_analysis (résultats LLM).
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
        "id":                          row["id"],
        "story_id":                    row["story_id"],
        "model":                       row["model"] or "",
        "story_title":                 row["story_title"] or "",
        "story_type":                  row["story_type"] or "",
        "actors":                      _deserialize_json(row["actors"]),
        "actions":                     _deserialize_json(row["actions"]),
        "business_rules":              _deserialize_json(row["business_rules"]),
        "technical_scope":             _deserialize_json(row["technical_scope"]),
        "testable_points":             _deserialize_json(row["testable_points"]),
        "acceptance_criteria_explicit": _deserialize_json(row["acceptance_criteria_explicit"]),
        "acceptance_criteria_inferred": _deserialize_json(row["acceptance_criteria_inferred"]),
        "clarification_questions":     _deserialize_json(row["clarification_questions"]),
        "analysis_reason":             _deserialize_json(row["analysis_reason"]),
        "user_flows":                  _deserialize_json(row["user_flows"]),
        "resolved_from_references":    _deserialize_json(row["resolved_from_references"]),
        "created_at":                  row["created_at"] or "",
    }


# ── SAVE ─────────────────────────────────────────────────────

def save_analysis(analysis: Dict[str, Any]) -> int:
    import logging
    logger = logging.getLogger(__name__)
    
    conn = get_connection()
    try:
        story_id = analysis.get("story_id", "")
        logger.info(f"[SAVE] Saving analysis for {story_id} with keys: {list(analysis.keys())}")
        
        cur = conn.execute(
            """
            INSERT INTO story_analysis
                (story_id, model, story_title, story_type,
                 actors, actions, business_rules, technical_scope, testable_points,
                 acceptance_criteria_explicit, acceptance_criteria_inferred,
                 clarification_questions, analysis_reason,
                 user_flows, resolved_from_references)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                story_id,
                analysis.get("model", ""),
                analysis.get("story_title", ""),
                analysis.get("story_type", ""),
                _serialize(analysis.get("actors", [])),
                _serialize(analysis.get("actions", [])),
                _serialize(analysis.get("business_rules", [])),
                _serialize(analysis.get("technical_scope", [])),
                _serialize(analysis.get("testable_points", [])),
                _serialize(analysis.get("acceptance_criteria_explicit", [])),
                _serialize(analysis.get("acceptance_criteria_inferred", [])),
                _serialize(analysis.get("clarification_questions", [])),
                _serialize(analysis.get("analysis_reason", [])),
                _serialize(analysis.get("user_flows", [])),
                _serialize(analysis.get("resolved_from_references", [])),
            ),
        )
        conn.commit()
        logger.info(f"[SAVE] Analysis saved for {story_id} with rowid={cur.lastrowid}")
        return cur.lastrowid
    except Exception as e:
        logger.error(f"[SAVE] Error saving analysis: {e}", exc_info=True)
        return -1
    finally:
        conn.close()


def save_analyses_bulk(analyses: List[Dict[str, Any]]) -> int:
    conn = get_connection()
    try:
        for a in analyses:
            conn.execute(
                """
                INSERT INTO story_analysis
                    (story_id, model, story_title, story_type,
                     actors, actions, business_rules, technical_scope, testable_points,
                     acceptance_criteria_explicit, acceptance_criteria_inferred,
                     clarification_questions, analysis_reason,
                     user_flows, resolved_from_references)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    a.get("story_id", ""),
                    a.get("model", ""),
                    a.get("story_title", ""),
                    a.get("story_type", ""),
                    _serialize(a.get("actors", [])),
                    _serialize(a.get("actions", [])),
                    _serialize(a.get("business_rules", [])),
                    _serialize(a.get("technical_scope", [])),
                    _serialize(a.get("testable_points", [])),
                    _serialize(a.get("acceptance_criteria_explicit", [])),
                    _serialize(a.get("acceptance_criteria_inferred", [])),
                    _serialize(a.get("clarification_questions", [])),
                    _serialize(a.get("analysis_reason", [])),
                    _serialize(a.get("user_flows", [])),
                    _serialize(a.get("resolved_from_references", [])),
                ),
            )
        conn.commit()
        return len(analyses)
    finally:
        conn.close()


# ── GET ──────────────────────────────────────────────────────

def get_analyses_by_story(story_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM story_analysis WHERE story_id = ? ORDER BY created_at DESC",
            (story_id,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_latest_analysis(story_id: str, model: Optional[str] = None) -> Optional[Dict[str, Any]]:
    import logging
    logger = logging.getLogger(__name__)
    
    conn = get_connection()
    try:
        if model:
            logger.info(f"[FETCH] Getting analysis for {story_id} with model={model}")
            row = conn.execute(
                "SELECT * FROM story_analysis WHERE story_id = ? AND model = ? ORDER BY created_at DESC LIMIT 1",
                (story_id, model),
            ).fetchone()
        else:
            logger.info(f"[FETCH] Getting latest analysis for {story_id}")
            row = conn.execute(
                "SELECT * FROM story_analysis WHERE story_id = ? ORDER BY created_at DESC LIMIT 1",
                (story_id,),
            ).fetchone()
        
        if not row:
            logger.warning(f"[FETCH] No analysis found for {story_id}")
            return None
        
        result = _row_to_dict(row)
        logger.info(f"[FETCH] Analysis found for {story_id}")
        return result
    except Exception as e:
        logger.error(f"[FETCH] Error getting analysis for {story_id}: {e}", exc_info=True)
        return None
    finally:
        conn.close()


def debug_analysis_in_db(story_id: str):
    """Fonction de diagnostic : affiche exactement ce qui est en base pour une story."""
    import logging
    logger = logging.getLogger(__name__)
    
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM story_analysis WHERE story_id = ? ORDER BY created_at DESC",
            (story_id,),
        ).fetchall()
        
        logger.info(f"[DEBUG] Found {len(rows)} analysis records for {story_id}")
        for i, row in enumerate(rows):
            logger.info(f"[DEBUG] Record {i}: {dict(row)}")
        
        return len(rows)
    except Exception as e:
        logger.error(f"[DEBUG] Error checking DB for {story_id}: {e}", exc_info=True)
        return -1
    finally:
        conn.close()


def get_latest_analysis_as_pydantic(story_id: str, model: Optional[str] = None):
    """Retourne StoryAnalysisResult (objet Pydantic) au lieu de dict."""
    from app.models.analysis import StoryAnalysisResult
    import logging
    logger = logging.getLogger(__name__)
    
    data = get_latest_analysis(story_id, model)
    if not data:
        logger.warning(f"[Agent5] No analysis data found in DB for {story_id}")
        return None
    
    logger.info(f"[Agent5] Analysis data found for {story_id}: keys={list(data.keys())}")
    
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
        logger.info(f"[Agent5] Successfully converted analysis to Pydantic for {story_id}")
        return result
    except Exception as e:
        logger.error(f"[Agent5] Error converting analysis to Pydantic for {story_id}: {e}", exc_info=True)
        return None
def fetch_analysis_by_story_id(story_id: str) -> Optional[Dict[str, Any]]:
    return get_latest_analysis(story_id)