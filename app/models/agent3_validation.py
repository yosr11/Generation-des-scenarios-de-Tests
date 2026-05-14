"""Modèles Pydantic pour les réponses Agent 3 (validateur pur, sans génération ni LLM)."""

from typing import Annotated, Any, Dict, List, Literal, Union

from pydantic import BaseModel, Field

from app.models.test_manual import ManualTestCase


class DuplicatePairReport(BaseModel):
    """Paire de tests sémantiquement redondants (aucun test n'est supprimé côté Agent 3)."""

    test_index_a: int
    test_index_b: int
    test_name_a: str = ""
    test_name_b: str = ""
    similarity: float


ValidationStatus = Literal["VALID", "PARTIALLY_VALID", "INVALID"]


class AddTestInstruction(BaseModel):
    instruction_type: Literal["add_test"] = "add_test"
    testable_point: str
    rationale: str = ""


class FixObjectiveInstruction(BaseModel):
    instruction_type: Literal["fix_objective"] = "fix_objective"
    test_index: int
    test_name: str = ""
    rationale: str = ""
    original_text: str = ""


class FixStepInstruction(BaseModel):
    instruction_type: Literal["fix_step"] = "fix_step"
    test_index: int
    test_name: str = ""
    step_index: int
    field: str = ""
    rationale: str = ""
    original_text: str = ""


class MergeDuplicatesInstruction(BaseModel):
    instruction_type: Literal["merge_duplicates"] = "merge_duplicates"
    test_index_a: int
    test_index_b: int
    test_name_a: str = ""
    test_name_b: str = ""
    similarity: float = 0.0
    rationale: str = ""


CorrectionInstruction = Annotated[
    Union[AddTestInstruction, FixObjectiveInstruction, FixStepInstruction, MergeDuplicatesInstruction],
    Field(discriminator="instruction_type"),
]


class Agent3ValidationReport(BaseModel):
    """Sortie stricte du validateur (aucune exécution des instructions)."""

    coverage_rate: float
    uncovered_testable_points: List[str] = Field(default_factory=list)
    duplicate_pairs: List[DuplicatePairReport] = Field(default_factory=list)
    ambiguity_findings: List[Dict[str, Any]] = Field(default_factory=list)
    validation_status: ValidationStatus = "INVALID"
    correction_instructions: List[CorrectionInstruction] = Field(default_factory=list)


class Agent3ValidationResult(BaseModel):
    story_id: str
    tests: List[ManualTestCase]
    report: Agent3ValidationReport


class Agent3StoryDashboard(BaseModel):
    """Même charge utile que le rapport, avec identifiant de story (pas de métadonnées Agent 2)."""

    story_id: str
    coverage_rate: float = 0.0
    uncovered_testable_points: List[str] = Field(default_factory=list)
    duplicate_pairs: List[DuplicatePairReport] = Field(default_factory=list)
    ambiguity_findings: List[Dict[str, Any]] = []
    validation_status: ValidationStatus = "INVALID"
    correction_instructions: List[CorrectionInstruction] = Field(default_factory=list)
