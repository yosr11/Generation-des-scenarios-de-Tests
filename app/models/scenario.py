# app/models/scenario.py
from pydantic import BaseModel, Field
from typing import List, Literal


class ScenarioStep(BaseModel):
    step: str
    type: Literal["given", "when", "then"]


class TestScenario(BaseModel):
    title: str
    type: Literal["smoke", "nominal", "edge_case", "negative", "regression"] = "nominal"
    priority: Literal["high", "medium", "low"] = "medium"
    preconditions: List[str] = Field(default_factory=list)
    steps: List[ScenarioStep] = Field(default_factory=list)
    expected_result: str = ""
    traced_to: List[str] = Field(default_factory=list)


class ScenarioGenerationResult(BaseModel):
    story_id: str
    scenarios: List[TestScenario] = Field(default_factory=list)
    generation_notes: str = ""
