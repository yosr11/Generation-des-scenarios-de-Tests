"""016_slim_validation_story

Revision ID: 016_slim_validation_story
Revises: 015_slim_generated_scenarios
Create Date: 2026-08-07
"""

from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "016_slim_validation_story"
down_revision: Union[str, None] = "015_slim_generated_scenarios"
branch_labels = None
depends_on = None

_TABLE = "validation_story"
_DROP_COLUMNS = ("llm_quality_model_alias", "correction_instructions")


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = {c["name"] for c in inspector.get_columns(_TABLE)}
    for col in _DROP_COLUMNS:
        if col in existing:
            op.drop_column(_TABLE, col)


def downgrade() -> None:
    op.add_column(
        _TABLE, sa.Column("llm_quality_model_alias", sa.String(100), nullable=True)
    )
    op.add_column(
        _TABLE,
        sa.Column("correction_instructions", sa.JSON(), nullable=True),
    )
