"""Slim down story_analysis: drop unused analysis output columns.

Revision ID: 013_slim_story_analysis
Revises: 012_slim_stories
Create Date: 2026-08-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "013_slim_story_analysis"
down_revision: Union[str, None] = "012_slim_stories"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_DROP_COLUMNS = (
    "recommended_test_type",
    "clarification_questions",
    "resolved_from_references",
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {column["name"] for column in inspector.get_columns("story_analysis")}
    for column_name in _DROP_COLUMNS:
        if column_name in existing:
            op.drop_column("story_analysis", column_name)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {column["name"] for column in inspector.get_columns("story_analysis")}

    if "recommended_test_type" not in existing:
        op.add_column(
            "story_analysis",
            sa.Column("recommended_test_type", sa.String(length=100), nullable=True),
        )
    if "clarification_questions" not in existing:
        op.add_column(
            "story_analysis",
            sa.Column(
                "clarification_questions",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )
    if "resolved_from_references" not in existing:
        op.add_column(
            "story_analysis",
            sa.Column(
                "resolved_from_references",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )
