"""
Modèles Pydantic pour l'Agent 4 — Classifieur d'automatisation.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class AutomationDecision(str, Enum):
    AUTOMATISER = "AUTOMATISER"
    MANUEL = "MANUEL"


class ConfidenceLevel(str, Enum):
    HAUTE = "HAUTE"
    MOYENNE = "MOYENNE"
    FAIBLE = "FAIBLE"


class PoFeedback(str, Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"


class TestAutomationClassification(BaseModel):
    test_name: str
    classification: AutomationDecision
    confidence: ConfidenceLevel = ConfidenceLevel.MOYENNE
    raison: str = ""
    po_feedback: PoFeedback = PoFeedback.PENDING
    error: Optional[str] = None


class StoryAutomationClassificationResult(BaseModel):
    story_id: str
    model: str = ""
    classifications: List[TestAutomationClassification] = Field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.classifications)

    @property
    def to_automate(self) -> int:
        return sum(1 for c in self.classifications if c.classification == AutomationDecision.AUTOMATISER)

    @property
    def to_manual(self) -> int:
        return self.total - self.to_automate
