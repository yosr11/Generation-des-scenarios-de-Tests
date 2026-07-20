"""Ajout des 6 tables métier dans PostgreSQL (migration depuis SQLite).

Revision ID: 003_add_business_tables
Revises: 002_add_user_fields_and_pipeline_runs
Create Date: 2026-07-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "003_add_business_tables"
down_revision: Union[str, None] = "002_add_user_fields_and_pipeline_runs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── stories ──────────────────────────────────────────────────────────────
    op.create_table(
        "stories",
        sa.Column("id", sa.String(100), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("description_raw", sa.Text(), nullable=True),
        sa.Column("description_clean", sa.Text(), nullable=True),
        sa.Column("description_llm", sa.Text(), nullable=True),
        sa.Column("acceptance_criteria_raw", sa.Text(), nullable=True),
        sa.Column("acceptance_criteria_clean", sa.Text(), nullable=True),
        sa.Column("labels", JSONB(), nullable=True),
        sa.Column("components", JSONB(), nullable=True),
        sa.Column("issuelinks", JSONB(), nullable=True),
        sa.Column("priority", sa.String(50), nullable=True),
        sa.Column("status", sa.String(100), nullable=True),
        sa.Column("fix_versions", JSONB(), nullable=True),
        sa.Column("requirement_status", JSONB(), nullable=True),
        sa.Column("references_json", JSONB(), nullable=True),
        sa.Column("flags", JSONB(), nullable=True),
        sa.Column("story_context_llm", sa.Text(), nullable=True),
        sa.Column("epic_key", sa.String(100), nullable=True),
        sa.Column("epic_summary", sa.Text(), nullable=True),
        sa.Column("epic_description", sa.Text(), nullable=True),
        sa.Column("jira_updated", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stories_epic_key", "stories", ["epic_key"], unique=False)

    # ── story_analysis ────────────────────────────────────────────────────────
    op.create_table(
        "story_analysis",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("story_id", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("story_title", sa.Text(), nullable=True),
        sa.Column("story_type", sa.String(100), nullable=True),
        sa.Column("recommended_test_type", sa.String(100), nullable=True),
        sa.Column("actors", JSONB(), nullable=True),
        sa.Column("actions", JSONB(), nullable=True),
        sa.Column("business_rules", JSONB(), nullable=True),
        sa.Column("technical_scope", JSONB(), nullable=True),
        sa.Column("testable_points", JSONB(), nullable=True),
        sa.Column("acceptance_criteria_explicit", JSONB(), nullable=True),
        sa.Column("acceptance_criteria_inferred", JSONB(), nullable=True),
        sa.Column("clarification_questions", JSONB(), nullable=True),
        sa.Column("analysis_reason", JSONB(), nullable=True),
        sa.Column("user_flows", JSONB(), nullable=True),
        sa.Column("resolved_from_references", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_story_analysis_story_id", "story_analysis", ["story_id"], unique=False)

    # ── story_manual_tests ───────────────────────────────────────────────────
    op.create_table(
        "story_manual_tests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("story_id", sa.String(100), nullable=False),
        sa.Column("tests_json", JSONB(), nullable=False),
        sa.Column("generation_model", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_story_manual_tests_story_id", "story_manual_tests", ["story_id"], unique=False)

    # ── agent3_validations ───────────────────────────────────────────────────
    op.create_table(
        "agent3_validations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("story_id", sa.String(100), nullable=False),
        sa.Column("coverage_rate", sa.Float(), nullable=True),
        sa.Column("uncovered_testable_points", JSONB(), nullable=True),
        sa.Column("duplicate_pairs", JSONB(), nullable=True),
        sa.Column("ambiguity_findings", JSONB(), nullable=True),
        sa.Column("validation_status", sa.String(50), nullable=True),
        sa.Column("llm_quality_feedback", JSONB(), nullable=True),
        sa.Column("llm_quality_model_alias", sa.String(100), nullable=True),
        sa.Column("correction_instructions", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent3_validations_story_id", "agent3_validations", ["story_id"], unique=False)

    # ── automation_classifications ───────────────────────────────────────────
    op.create_table(
        "automation_classifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("story_id", sa.String(100), nullable=False),
        sa.Column("test_name", sa.Text(), nullable=False),
        sa.Column("classification", sa.String(50), nullable=False),
        sa.Column("confidence", sa.String(50), nullable=False),
        sa.Column("raison", sa.Text(), nullable=True),
        sa.Column("po_feedback", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_automation_classifications_story_id", "automation_classifications", ["story_id"], unique=False)

    # ── story_business_models ────────────────────────────────────────────────
    op.create_table(
        "story_business_models",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("story_id", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("business_goals", JSONB(), nullable=True),
        sa.Column("business_workflows", JSONB(), nullable=True),
        sa.Column("modeling_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_story_business_models_story_id", "story_business_models", ["story_id"], unique=False)

    # ── generated_scenarios ──────────────────────────────────────────────────
    op.create_table(
        "generated_scenarios",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("story_id", sa.String(100), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("scenario_type", sa.String(100), nullable=True),
        sa.Column("priority", sa.String(50), nullable=True),
        sa.Column("preconditions", JSONB(), nullable=True),
        sa.Column("steps", JSONB(), nullable=True),
        sa.Column("expected_result", sa.Text(), nullable=True),
        sa.Column("source_ustype", sa.String(100), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_generated_scenarios_story_id", "generated_scenarios", ["story_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_generated_scenarios_story_id", table_name="generated_scenarios")
    op.drop_table("generated_scenarios")

    op.drop_index("ix_story_business_models_story_id", table_name="story_business_models")
    op.drop_table("story_business_models")


    op.drop_index("ix_automation_classifications_story_id", table_name="automation_classifications")
    op.drop_table("automation_classifications")

    op.drop_index("ix_agent3_validations_story_id", table_name="agent3_validations")
    op.drop_table("agent3_validations")

    op.drop_index("ix_story_manual_tests_story_id", table_name="story_manual_tests")
    op.drop_table("story_manual_tests")

    op.drop_index("ix_story_analysis_story_id", table_name="story_analysis")
    op.drop_table("story_analysis")

    op.drop_index("ix_stories_epic_key", table_name="stories")
    op.drop_table("stories")
