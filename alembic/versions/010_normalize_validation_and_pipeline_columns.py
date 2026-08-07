"""Normalize validation table and pipeline test output names.

Revision ID: 010_normalize_schema
Revises: 009_create_reports
Create Date: 2026-08-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "010_normalize_schema"
down_revision: Union[str, None] = "009_create_reports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector, table_name: str) -> bool:
    return inspector.has_table(table_name)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Keep Agent 4 validation as the single validation table.
    if _table_exists(inspector, "agent3_validations"):
        indexes = inspector.get_indexes("agent3_validations")
        for index in indexes:
            op.drop_index(index["name"], table_name="agent3_validations")
        op.drop_table("agent3_validations")

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "agent4_validations") and not _table_exists(
        inspector, "validation_story"
    ):
        op.rename_table("agent4_validations", "validation_story")
        inspector = sa.inspect(bind)
        for index in inspector.get_indexes("validation_story"):
            if index["name"] == "ix_agent4_validations_story_id":
                op.execute(
                    sa.text(
                        "ALTER INDEX ix_agent4_validations_story_id "
                        "RENAME TO ix_validation_story_story_id"
                    )
                )
                break

    inspector = sa.inspect(bind)
    pipeline_columns = {
        column["name"] for column in inspector.get_columns("pipeline_runs")
    }
    if "agent2_tests" in pipeline_columns and "agent3_tests" not in pipeline_columns:
        op.alter_column(
            "pipeline_runs",
            "agent2_tests",
            new_column_name="agent3_tests",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    pipeline_columns = {
        column["name"] for column in inspector.get_columns("pipeline_runs")
    }
    if "agent3_tests" in pipeline_columns and "agent2_tests" not in pipeline_columns:
        op.alter_column(
            "pipeline_runs",
            "agent3_tests",
            new_column_name="agent2_tests",
        )

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "validation_story") and not _table_exists(
        inspector, "agent4_validations"
    ):
        op.rename_table("validation_story", "agent4_validations")
