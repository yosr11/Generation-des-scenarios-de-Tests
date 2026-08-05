"""Add agent2_tests and agent5_report JSONB columns to pipeline_runs.

Revision ID: 003_add_reports_to_pipeline_runs
Revises: 002_add_user_fields_and_pipeline_runs
Create Date: 2026-07-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003_add_reports_to_pipeline_runs"
down_revision: Union[str, None] = "002_add_user_fields_and_pipeline_runs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("pipeline_runs") as batch_op:
        batch_op.add_column(
            sa.Column("agent2_tests", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
        )
        batch_op.add_column(
            sa.Column("agent5_report", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("pipeline_runs") as batch_op:
        batch_op.drop_column("agent5_report")
        batch_op.drop_column("agent2_tests")
