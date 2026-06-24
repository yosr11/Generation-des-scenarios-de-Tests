"""
Repository pour les classifications d'automatisation (Agent 4).

Stocke le dernier snapshot par story (les classifications sont remplacées
à chaque run du pipeline) et permet au PO de mettre à jour le `po_feedback`
d'une classification individuelle.
"""

import json
from typing import Any, Dict, List, Optional

from app.db.database import get_connection
from app.models.automation_classification import (
    AutomationDecision,
    ConfidenceLevel,
    PoFeedback,
    StoryAutomationClassificationResult,
    TestAutomationClassification,
)


def save_classifications(result: StoryAutomationClassificationResult) -> None:
    """Remplace les classifications existantes pour la story."""
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM automation_classifications WHERE story_id = ?",
            (result.story_id,),
        )
        for c in result.classifications:
            conn.execute(
                """
                INSERT INTO automation_classifications
                    (story_id, test_name, classification, confidence, raison,
                     po_feedback, model, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.story_id,
                    c.test_name,
                    c.classification.value,
                    c.confidence.value,
                    c.raison,
                    c.po_feedback.value,
                    result.model,
                    c.error,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def get_classifications(story_id: str) -> Optional[StoryAutomationClassificationResult]:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT test_name, classification, confidence, raison,
                   po_feedback, model, error
              FROM automation_classifications
             WHERE story_id = ?
             ORDER BY id ASC
            """,
            (story_id,),
        )
        rows = cur.fetchall()
        if not rows:
            return None
        items: List[TestAutomationClassification] = []
        model = ""
        for r in rows:
            model = r["model"] or model
            items.append(
                TestAutomationClassification(
                    test_name=r["test_name"] or "",
                    classification=AutomationDecision(r["classification"]),
                    confidence=ConfidenceLevel(r["confidence"]),
                    raison=r["raison"] or "",
                    po_feedback=PoFeedback(r["po_feedback"] or "pending"),
                    error=r["error"],
                )
            )
        return StoryAutomationClassificationResult(
            story_id=story_id,
            model=model,
            classifications=items,
        )
    finally:
        conn.close()


def update_po_feedback(story_id: str, test_name: str, feedback: PoFeedback) -> bool:
    """Met à jour le retour du PO sur une classification. Retourne True si une ligne touchée."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            UPDATE automation_classifications
               SET po_feedback = ?
             WHERE story_id = ? AND test_name = ?
            """,
            (feedback.value, story_id, test_name),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
