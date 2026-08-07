"""Slim down pipeline_runs: drop RAG options, error message and result JSON copies.

Revision ID: 011_slim_pipeline_runs
Revises: 010_normalize_schema
Create Date: 2026-08-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "011_slim_pipeline_runs"
down_revision: Union[str, None] = "010_normalize_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_DROP_COLUMNS = (
    "use_rag",
    "use_legacy_rag",
    "run_agent4",
    "error_message",
    "agent3_tests",
    "agent5_report",
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {column["name"] for column in inspector.get_columns("pipeline_runs")}
    for column_name in _DROP_COLUMNS:
        if column_name in existing:
            op.drop_column("pipeline_runs", column_name)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {column["name"] for column in inspector.get_columns("pipeline_runs")}

    if "use_rag" not in existing:
        op.add_column(
            "pipeline_runs",
            sa.Column("use_rag", sa.Boolean(), nullable=True, server_default=sa.true()),
        )
    if "use_legacy_rag" not in existing:
        op.add_column(
            "pipeline_runs",
            sa.Column(
                "use_legacy_rag",
                sa.Boolean(),
                nullable=True,
                server_default=sa.false(),
            ),
        )
    if "run_agent4" not in existing:
        op.add_column(
            "pipeline_runs",
            sa.Column(
                "run_agent4", sa.Boolean(), nullable=True, server_default=sa.true()
            ),
        )
    if "error_message" not in existing:
        op.add_column(
            "pipeline_runs", sa.Column("error_message", sa.Text(), nullable=True)
        )
    if "agent3_tests" not in existing:
        op.add_column(
            "pipeline_runs",
            sa.Column(
                "agent3_tests",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )
    if "agent5_report" not in existing:
        op.add_column(
            "pipeline_runs",
            sa.Column(
                "agent5_report",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )
