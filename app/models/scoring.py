# app/models/scoring.py
from pydantic import BaseModel, Field
from typing import List, Literal


class CoverageDetail(BaseModel):
    total_testable_elements: int = 0
    covered_elements: int = 0
    uncovered_elements: List[str] = Field(default_factory=list)
    coverage_score: float = 0.0


class QualityDetail(BaseModel):
    total_scenarios: int = 0
    well_structured: int = 0
    vague_or_incomplete: List[str] = Field(default_factory=list)
    quality_score: float = 0.0


class ScoringResult(BaseModel):
    story_id: str
    coverage: CoverageDetail = Field(default_factory=CoverageDetail)
    quality: QualityDetail = Field(default_factory=QualityDetail)
    overall_score: float = 0.0
    grade: Literal["A", "B", "C", "D", "F"] = "F"
    risks: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    scoring_reason: str = ""
