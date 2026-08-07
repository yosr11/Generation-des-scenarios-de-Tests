"""
Repository pour sauvegarder/récupérer résultats de validation Agent 4 — PostgreSQL (SQLAlchemy ORM).
"""

from typing import Optional

from sqlalchemy import select

from app.db.postgres import get_sync_session
from app.models.agent4_validation import Agent4ValidationReport, Agent4ValidationResult
from app.models.pg_models import Agent4Validation


def save_validation_result(
    story_id: str, validation_result: Agent4ValidationResult
) -> bool:
    """
    Sauvegarde les résultats de validation Agent 4 en base (idempotent par story_id).
    """
    try:
        session = get_sync_session()
        report = validation_result.report

        # Supprimer l'ancien enregistrement pour cette story
        existing = (
            session.execute(
                select(Agent4Validation).where(Agent4Validation.story_id == story_id)
            )
            .scalars()
            .all()
        )
        for row in existing:
            session.delete(row)

        # Sérialiser les objets Pydantic en dicts pour JSONB
        duplicate_pairs = (
            [p.model_dump() for p in report.duplicate_pairs]
            if report.duplicate_pairs
            else []
        )
        llm_quality_feedback = (
            report.llm_quality_feedback.model_dump()
            if report.llm_quality_feedback
            else None
        )

        obj = Agent4Validation(
            story_id=story_id,
            coverage_rate=report.coverage_rate,
            uncovered_testable_points=report.uncovered_testable_points or [],
            duplicate_pairs=duplicate_pairs,
            ambiguity_findings=report.ambiguity_findings or [],
            validation_status=report.validation_status,
            llm_quality_feedback=llm_quality_feedback,
        )
        session.add(obj)
        session.commit()
        return True
    except Exception as e:
        print(f"Error saving validation result: {e}")
        return False
    finally:
        session.close()


def fetch_validation_by_story_id(story_id: str) -> Optional[Agent4ValidationResult]:
    """Récupère les résultats de validation pour une story."""
    try:
        session = get_sync_session()
        obj = session.execute(
            select(Agent4Validation)
            .where(Agent4Validation.story_id == story_id)
            .order_by(Agent4Validation.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        if not obj:
            return None

        # Reconstruire les modèles Pydantic
        from app.models.agent4_validation import DuplicatePairReport, LLMQualityFeedback

        duplicate_pairs = []
        for dup in obj.duplicate_pairs or []:
            try:
                duplicate_pairs.append(DuplicatePairReport(**dup))
            except Exception:
                pass

        llm_quality_feedback = None
        if obj.llm_quality_feedback:
            try:
                llm_quality_feedback = LLMQualityFeedback(**obj.llm_quality_feedback)
            except Exception:
                pass

        # Récupérer les tests associés
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

        report = Agent4ValidationReport(
            coverage_rate=obj.coverage_rate or 0.0,
            uncovered_testable_points=obj.uncovered_testable_points or [],
            duplicate_pairs=duplicate_pairs,
            ambiguity_findings=obj.ambiguity_findings or [],
            validation_status=obj.validation_status or "UNKNOWN",
            llm_quality_feedback=llm_quality_feedback,
        )

        return Agent4ValidationResult(story_id=story_id, tests=tests, report=report)

    except Exception as e:
        print(f"Error fetching validation result: {e}")
        return None
    finally:
        session.close()


def delete_validation_by_story_id(story_id: str) -> bool:
    """Supprime les résultats de validation pour une story."""
    try:
        session = get_sync_session()
        rows = (
            session.execute(
                select(Agent4Validation).where(Agent4Validation.story_id == story_id)
            )
            .scalars()
            .all()
        )
        for row in rows:
            session.delete(row)
        session.commit()
        return True
    except Exception as e:
        print(f"Error deleting validation result: {e}")
        return False
    finally:
        session.close()
