"""
Repository pour sauvegarder/récupérer résultats de validation Agent 3.
"""

import json
from typing import Dict, Any, Optional
from app.db.database import get_connection
from app.models.agent3_validation import Agent3ValidationResult, Agent3ValidationReport


def _serialize_json(value) -> str:
    """Sérialise dict/list en JSON."""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value) if value is not None else ""


def _deserialize_json(raw: Optional[str], default=None):
    """Désérialise JSON en dict/list."""
    if not raw:
        return default if default is not None else {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else {}


def save_validation_result(
    story_id: str,
    validation_result: Agent3ValidationResult,
) -> bool:
    """
    Sauvegarde les résultats de validation Agent 3 en base.
    
    Args:
        story_id: ID de la story
        validation_result: Résultat de validation
    
    Returns:
        True si sauvegardé, False sinon
    """
    try:
        conn = get_connection()
        report = validation_result.report
        
        # Sérialiser les listes complexes
        uncovered_points_json = _serialize_json(report.uncovered_testable_points)
        duplicate_pairs_json = _serialize_json(
            [p.model_dump() for p in report.duplicate_pairs] if report.duplicate_pairs else []
        )
        ambiguity_findings_json = _serialize_json(
            [a for a in report.ambiguity_findings] if report.ambiguity_findings else []
        )
        
        # Sérialiser LLM feedback
        llm_feedback_json = ""
        if report.llm_quality_feedback:
            llm_feedback_json = _serialize_json(report.llm_quality_feedback.model_dump())
        
        # Sérialiser correction_instructions
        correction_instructions_json = ""
        if report.correction_instructions:
            correction_instructions_json = _serialize_json(
                [ci.model_dump() if hasattr(ci, "model_dump") else ci for ci in report.correction_instructions]
            )
        
        # Supprimer l'ancien puis insérer (idempotent par story_id)
        conn.execute(
            "DELETE FROM agent3_validations WHERE story_id = ?",
            (story_id,),
        )
        conn.execute(
            """
            INSERT INTO agent3_validations (
                story_id,
                coverage_rate,
                uncovered_testable_points,
                duplicate_pairs,
                ambiguity_findings,
                validation_status,
                llm_quality_feedback,
                llm_quality_model_alias,
                correction_instructions,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                story_id,
                report.coverage_rate,
                uncovered_points_json,
                duplicate_pairs_json,
                ambiguity_findings_json,
                report.validation_status,
                llm_feedback_json,
                report.llm_quality_model_alias or "",
                correction_instructions_json,
            ),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving validation result: {e}")
        return False


def fetch_validation_by_story_id(story_id: str) -> Optional[Agent3ValidationResult]:
    """
    Récupère les résultats de validation pour une story.
    
    Args:
        story_id: ID de la story
    
    Returns:
        Agent3ValidationResult ou None
    """
    try:
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM agent3_validations WHERE story_id = ? ORDER BY created_at DESC LIMIT 1",
            (story_id,),
        ).fetchone()
        
        if not row:
            return None
        
        # Désérialiser les champs JSON
        uncovered_points = _deserialize_json(row["uncovered_testable_points"], [])
        duplicate_pairs_raw = _deserialize_json(row["duplicate_pairs"], [])
        ambiguity_findings = _deserialize_json(row["ambiguity_findings"], [])
        llm_feedback_raw = _deserialize_json(row["llm_quality_feedback"], None)
        
        # Reconstruire les modèles
        from app.models.agent3_validation import (
            DuplicatePairReport,
            LLMQualityFeedback,
        )
        
        duplicate_pairs = []
        for dup in duplicate_pairs_raw:
            try:
                duplicate_pairs.append(DuplicatePairReport(**dup))
            except Exception:
                pass
        
        llm_quality_feedback = None
        if llm_feedback_raw:
            try:
                llm_quality_feedback = LLMQualityFeedback(**llm_feedback_raw)
            except Exception:
                pass
        
        # Récupérer les tests associés et les convertir en ManualTestCase
        from app.repositories.manual_tests_repository import get_latest_manual_tests
        from app.models.test_manual import ManualTestCase
        tests_raw = get_latest_manual_tests(story_id)
        tests = []
        if tests_raw:
            for t in tests_raw:
                try:
                    tests.append(ManualTestCase(**t))
                except Exception:
                    pass
        
        # Construire le rapport
        report = Agent3ValidationReport(
            coverage_rate=row["coverage_rate"] or 0.0,
            uncovered_testable_points=uncovered_points,
            duplicate_pairs=duplicate_pairs,
            ambiguity_findings=ambiguity_findings,
            validation_status=row["validation_status"] or "UNKNOWN",
            correction_instructions=[],
            llm_quality_feedback=llm_quality_feedback,
            llm_quality_model_alias=row["llm_quality_model_alias"],
        )
        
        result = Agent3ValidationResult(
            story_id=story_id,
            tests=tests,
            report=report,
        )
        
        return result
    
    except Exception as e:
        print(f"Error fetching validation result: {e}")
        return None


def delete_validation_by_story_id(story_id: str) -> bool:
    """Supprime les résultats de validation pour une story."""
    try:
        conn = get_connection()
        conn.execute("DELETE FROM agent3_validations WHERE story_id = ?", (story_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting validation result: {e}")
        return False
