# app/models/analysis.py
from typing import List, Literal
from pydantic import BaseModel, Field, field_validator

StoryType = Literal[
    "functional",
    "technical",
    "poc_or_study",
    "documentation",
    "invalid_or_too_weak",
]


class StoryClassificationResult(BaseModel):
    story_id: str = Field(..., description="Jira issue key / story id")
    story_title: str = Field("", description="Title / summary of the story")
    story_type: StoryType = Field(..., description="Main type of the story")
    analysis_reason: List[str] = Field(
        default_factory=list,
        description="Short reasons explaining the classification decision",
    )


class StoryAnalysisResult(BaseModel):
    story_id: str = Field(..., description="Jira issue key / story id")
    story_title: str = Field("", description="Title / summary of the story")

    story_type: StoryType = Field(
        ...,
        description="Main type of the story",
    )

    actors: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)

    business_rules: List[str] = Field(
        default_factory=list,
        description="Business rules explicitly or strongly implied by the story",
    )

    technical_scope: List[str] = Field(
        default_factory=list,
        description="Technical scope / technical concerns if the story is technical",
    )

    testable_points: List[str] = Field(
        default_factory=list,
        description="Concrete points that can be tested or validated",
    )

    user_flows: List[str] = Field(
        default_factory=list,
        description="Step-by-step user flows extracted from the story description",
    )

    acceptance_criteria_explicit: List[str] = Field(
        default_factory=list,
        description="Acceptance criteria explicitly present in the story text",
    )

    acceptance_criteria_inferred: List[str] = Field(
        default_factory=list,
        description="Acceptance criteria inferred from the story when explicit AC are missing",
    )

    clarification_questions: List[str] = Field(
        default_factory=list,
        description="Questions to ask if the story is ambiguous or missing details",
    )

    analysis_reason: List[str] = Field(
        default_factory=list,
        description="Short reasons explaining the classification decision",
    )

    resolved_from_references: List[str] = Field(
        default_factory=list,
        description="Ticket keys whose content was fetched and injected (reference resolution)",
    )

    @field_validator(
        "analysis_reason",
        "actors",
        "actions",
        "business_rules",
        "technical_scope",
        "testable_points",
        "acceptance_criteria_explicit",
        "acceptance_criteria_inferred",
        "clarification_questions",
        mode="before",
    )
    @classmethod
    def _coerce_to_list(cls, v):
        if isinstance(v, str):
            return [v]
        return v
