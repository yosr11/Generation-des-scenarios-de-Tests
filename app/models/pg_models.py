"""Modèles PostgreSQL : utilisateurs, logs d'audit, runs de pipeline et tables métier."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.postgres import Base

# Type JSON portable : JSONB natif sur PostgreSQL, JSON classique (TEXT) sur SQLite.
# Permet aux tests d'utiliser une base SQLite temporaire sans erreur de compilation DDL.
PortableJSONB = JSONB().with_variant(JSON(), "sqlite")

# ── Modèles Auth / Admin ─────────────────────────────────────────────────────


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", "role", name="uq_users_email_role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="tester")
    # Admin registers a tester by their Jira username (no password stored)
    jira_username: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_identifier: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PipelineRun(Base):
    """Trace chaque lancement de pipeline."""

    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    story_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    launched_by: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running")
    # Options used
    use_rag: Mapped[bool] = mapped_column(Boolean, default=True)
    use_legacy_rag: Mapped[bool] = mapped_column(Boolean, default=False)
    run_agent4: Mapped[bool] = mapped_column(Boolean, default=True)
    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Result summary
    tests_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ── Modèles métier (migrés depuis SQLite) ────────────────────────────────────


class Story(Base):
    """Stories Jira nettoyées et enrichies."""

    __tablename__ = "stories"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_clean: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_llm: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    acceptance_criteria_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    acceptance_criteria_clean: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    labels: Mapped[Optional[list]] = mapped_column(
        PortableJSONB, nullable=True, default=list
    )
    components: Mapped[Optional[list]] = mapped_column(
        PortableJSONB, nullable=True, default=list
    )
    issuelinks: Mapped[Optional[list]] = mapped_column(
        PortableJSONB, nullable=True, default=list
    )
    priority: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fix_versions: Mapped[Optional[list]] = mapped_column(
        PortableJSONB, nullable=True, default=list
    )
    requirement_status: Mapped[Optional[dict]] = mapped_column(
        PortableJSONB, nullable=True, default=dict
    )
    references_json: Mapped[Optional[dict]] = mapped_column(
        PortableJSONB, nullable=True, default=dict
    )
    flags: Mapped[Optional[dict]] = mapped_column(
        PortableJSONB, nullable=True, default=dict
    )
    story_context_llm: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    epic_key: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    epic_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    epic_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    jira_updated: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class StoryAnalysis(Base):
    """Résultats d'analyse LLM par story (Agent 1)."""

    __tablename__ = "story_analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    story_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    story_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    story_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    recommended_test_type: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    actors: Mapped[Optional[list]] = mapped_column(
        PortableJSONB, nullable=True, default=list
    )
    actions: Mapped[Optional[list]] = mapped_column(
        PortableJSONB, nullable=True, default=list
    )
    business_rules: Mapped[Optional[list]] = mapped_column(
        PortableJSONB, nullable=True, default=list
    )
    technical_scope: Mapped[Optional[list]] = mapped_column(
        PortableJSONB, nullable=True, default=list
    )
    testable_points: Mapped[Optional[list]] = mapped_column(
        PortableJSONB, nullable=True, default=list
    )
    acceptance_criteria_explicit: Mapped[Optional[list]] = mapped_column(
        PortableJSONB, nullable=True, default=list
    )
    acceptance_criteria_inferred: Mapped[Optional[list]] = mapped_column(
        PortableJSONB, nullable=True, default=list
    )
    clarification_questions: Mapped[Optional[list]] = mapped_column(
        PortableJSONB, nullable=True, default=list
    )
    analysis_reason: Mapped[Optional[list]] = mapped_column(
        PortableJSONB, nullable=True, default=list
    )
    user_flows: Mapped[Optional[list]] = mapped_column(
        PortableJSONB, nullable=True, default=list
    )
    resolved_from_references: Mapped[Optional[list]] = mapped_column(
        PortableJSONB, nullable=True, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class StoryManualTests(Base):
    """Dernier snapshot de tests manuels générés par l'Agent 2."""

    __tablename__ = "story_manual_tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    story_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tests_json: Mapped[list] = mapped_column(
        PortableJSONB, nullable=False, default=list
    )
    generation_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Agent3Validation(Base):
    """Résultats de validation Agent 3 par story."""

    __tablename__ = "agent3_validations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    story_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    coverage_rate: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, default=0.0
    )
    uncovered_testable_points: Mapped[Optional[list]] = mapped_column(
        PortableJSONB, nullable=True, default=list
    )
    duplicate_pairs: Mapped[Optional[list]] = mapped_column(
        PortableJSONB, nullable=True, default=list
    )
    ambiguity_findings: Mapped[Optional[list]] = mapped_column(
        PortableJSONB, nullable=True, default=list
    )
    validation_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    llm_quality_feedback: Mapped[Optional[dict]] = mapped_column(
        PortableJSONB, nullable=True
    )
    llm_quality_model_alias: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    correction_instructions: Mapped[Optional[list]] = mapped_column(
        PortableJSONB, nullable=True, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AutomationClassification(Base):
    """Classifications d'automatisation par test (Agent 4)."""

    __tablename__ = "automation_classifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    story_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    test_name: Mapped[str] = mapped_column(Text, nullable=False)
    classification: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[str] = mapped_column(String(50), nullable=False)
    raison: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    po_feedback: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class StoryBusinessModel(Base):
    """Business models générés par l'Agent 1.5."""

    __tablename__ = "story_business_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    story_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    business_goals: Mapped[Optional[list]] = mapped_column(
        PortableJSONB, nullable=True, default=list
    )
    business_workflows: Mapped[Optional[list]] = mapped_column(
        PortableJSONB, nullable=True, default=list
    )
    modeling_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class GeneratedScenario(Base):
    """Scénarios de test générés par l'Agent 2 (mode scénarios)."""

    __tablename__ = "generated_scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    story_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scenario_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    priority: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    preconditions: Mapped[Optional[list]] = mapped_column(
        PortableJSONB, nullable=True, default=list
    )
    steps: Mapped[Optional[list]] = mapped_column(
        PortableJSONB, nullable=True, default=list
    )
    expected_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_ustype: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )