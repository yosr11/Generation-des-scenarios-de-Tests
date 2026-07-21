from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class ManualGenerationStatus(str, Enum):
    GENERATED = "generated"
    NOT_GENERATED = "not_generated"


class RecommendedTestStrategy(str, Enum):
    MANUAL = "manual"
    AUTOMATED = "automated"
    NEEDS_REFINEMENT = "needs_refinement"


class ScenarioType(str, Enum):
    NOM = "NOM"
    ALT = "ALT"
    EXC = "EXC"


class PriorityLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class ManualTestStep(BaseModel):
    index: int = Field(..., description="Numéro de l'étape")
    action: str = Field(
        ..., description="Action claire, testable, formulée avec un verbe à l'infinitif"
    )
    data: Optional[str] = Field(
        default="", description="Données de l'étape ou acteur effectuant l'action"
    )
    actor: Optional[str] = Field(
        default="",
        description="L'acteur qui réalise cette action (ex: Collaborateur, Manager RH)",
    )
    expected_result: str = Field(..., description="Résultat attendu clair et mesurable")
    revision_po: Optional[str] = Field(
        default="",
        description="Commentaire du Product Owner sur la pertinence du test (vide par défaut)",
    )


class ManualTestEtape(BaseModel):
    """Une étape du test, contenant des actions groupées d'un acteur"""

    titre: str = Field(
        ..., description="Titre général de l'étape (ex: 'Accéder à l'application')"
    )
    actor: Optional[str] = Field(
        default="", description="L'acteur qui exécute cette étape"
    )
    steps: List[ManualTestStep] = Field(
        default_factory=list, description="Actions détaillées de cette étape"
    )


class ManualTestCase(BaseModel):
    story_id: str
    test_name: str
    objective: str
    description: Optional[str] = Field(
        default="", description="Résumé des actions et du scénario du test"
    )
    execution_context: Optional[str] = ""
    preconditions: List[str] = []
    scenario_type: ScenarioType = ScenarioType.NOM
    priority: PriorityLevel = PriorityLevel.MEDIUM
    labels: List[str] = []
    étapes: List[ManualTestEtape] = Field(
        default_factory=list, description="Étapes groupées du test"
    )
    steps: List[ManualTestStep] = []  # Garder pour compatibilité


class ManualTestGenerationResult(BaseModel):
    story_id: str
    recommended_test_strategy: RecommendedTestStrategy
    generation_status: ManualGenerationStatus
    message: str
    tests: List[ManualTestCase] = []
    notes: List[str] = []
    golden_rule_warnings: List[str] = Field(
        default_factory=list,
        description="Avertissements golden rules non bloquants (complétion QA recommandée)",
    )
