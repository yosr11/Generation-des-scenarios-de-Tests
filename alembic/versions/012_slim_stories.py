"""Slim down stories: drop raw/llm descriptions and unused Jira metadata.

Revision ID: 012_slim_stories
Revises: 011_slim_pipeline_runs
Create Date: 2026-08-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "012_slim_stories"
down_revision: Union[str, None] = "011_slim_pipeline_runs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_DROP_COLUMNS = (
    "description_raw",
    "description_llm",
    "acceptance_criteria_raw",
    "fix_versions",
    "requirement_status",
    "references_json",
    "flags",
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {column["name"] for column in inspector.get_columns("stories")}
    for column_name in _DROP_COLUMNS:
        if column_name in existing:
            op.drop_column("stories", column_name)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {column["name"] for column in inspector.get_columns("stories")}

    if "description_raw" not in existing:
        op.add_column("stories", sa.Column("description_raw", sa.Text(), nullable=True))
    if "description_llm" not in existing:
        op.add_column("stories", sa.Column("description_llm", sa.Text(), nullable=True))
    if "acceptance_criteria_raw" not in existing:
        op.add_column(
            "stories", sa.Column("acceptance_criteria_raw", sa.Text(), nullable=True)
        )
    if "fix_versions" not in existing:
        op.add_column(
            "stories",
            sa.Column(
                "fix_versions",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )
    if "requirement_status" not in existing:
        op.add_column(
            "stories",
            sa.Column(
                "requirement_status",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )
    if "references_json" not in existing:
        op.add_column(
            "stories",
            sa.Column(
                "references_json",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )
    if "flags" not in existing:
        op.add_column(
            "stories",
            sa.Column(
                "flags",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )
