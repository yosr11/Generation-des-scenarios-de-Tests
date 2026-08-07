"""Create dedicated reports table.

Revision ID: 009_create_reports
Revises: 008_merge_003_007
Create Date: 2026-08-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "009_create_reports"
down_revision: Union[str, None] = "008_merge_003_007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("reports"):
        op.create_table(
            "reports",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("story_id", sa.String(length=100), nullable=False),
            sa.Column("report_title", sa.Text(), nullable=True),
            sa.Column("report_version", sa.String(length=50), nullable=True),
            sa.Column("generated_timestamp", sa.String(length=100), nullable=True),
            sa.Column(
                "report_data",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    existing_indexes = {index["name"] for index in inspector.get_indexes("reports")}
    if "ix_reports_story_id" not in existing_indexes:
        op.create_index("ix_reports_story_id", "reports", ["story_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_reports_story_id", table_name="reports")
    op.drop_table("reports")