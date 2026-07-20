"""
Repository pour les classifications d'automatisation (Agent 4) — PostgreSQL (SQLAlchemy ORM).

Stocke le dernier snapshot par story (les classifications sont remplacées
à chaque run du pipeline) et permet au PO de mettre à jour le `po_feedback`
d'une classification individuelle.
"""

from typing import List, Optional

from sqlalchemy import select

from app.db.postgres import get_sync_session
from app.models.automation_classification import (
    AutomationDecision,
    ConfidenceLevel,
    PoFeedback,
    StoryAutomationClassificationResult,
    TestAutomationClassification,
)
from app.models.pg_models import AutomationClassification


def save_classifications(result: StoryAutomationClassificationResult) -> None:
    """Remplace les classifications existantes pour la story."""
    session = get_sync_session()
    try:
        # Supprimer les anciennes classifications
        existing = session.execute(
            select(AutomationClassification).where(
                AutomationClassification.story_id == result.story_id
            )
        ).scalars().all()
        for row in existing:
            session.delete(row)

        # Insérer les nouvelles
        for c in result.classifications:
            obj = AutomationClassification(
                story_id=result.story_id,
                test_name=c.test_name,
                classification=c.classification.value,
                confidence=c.confidence.value,
                raison=c.raison,
                po_feedback=c.po_feedback.value,
                model=result.model,
                error=c.error,
            )
            session.add(obj)
        session.commit()
    finally:
        session.close()


def get_classifications(story_id: str) -> Optional[StoryAutomationClassificationResult]:
    session = get_sync_session()
    try:
        rows = session.execute(
            select(AutomationClassification)
            .where(AutomationClassification.story_id == story_id)
            .order_by(AutomationClassification.id.asc())
        ).scalars().all()

        if not rows:
            return None

        items: List[TestAutomationClassification] = []
        model = ""
        for r in rows:
            model = r.model or model
            items.append(
                TestAutomationClassification(
                    test_name=r.test_name or "",
                    classification=AutomationDecision(r.classification),
                    confidence=ConfidenceLevel(r.confidence),
                    raison=r.raison or "",
                    po_feedback=PoFeedback(r.po_feedback or "pending"),
                    error=r.error,
                )
            )
        return StoryAutomationClassificationResult(
            story_id=story_id,
            model=model,
            classifications=items,
        )
    finally:
        session.close()


def update_po_feedback(story_id: str, test_name: str, feedback: PoFeedback) -> bool:
    """Met à jour le retour du PO sur une classification. Retourne True si une ligne touchée."""
    session = get_sync_session()
    try:
        obj = session.execute(
            select(AutomationClassification).where(
                AutomationClassification.story_id == story_id,
                AutomationClassification.test_name == test_name,
            )
        ).scalar_one_or_none()
        if not obj:
            return False
        obj.po_feedback = feedback.value
        session.commit()
        return True
    finally:
        session.close()
