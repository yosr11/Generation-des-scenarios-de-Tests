"""014_slim_story_business_models

Revision ID: 014_slim_story_business_models
Revises: 013_slim_story_analysis
Create Date: 2026-08-07
"""

from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "014_slim_story_business_models"
down_revision: Union[str, None] = "013_slim_story_analysis"
branch_labels = None
depends_on = None

_TABLE = "story_business_models"
_DROP_COLUMNS = ("model", "modeling_notes")


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = {c["name"] for c in inspector.get_columns(_TABLE)}
    for col in _DROP_COLUMNS:
        if col in existing:
            op.drop_column(_TABLE, col)


def downgrade() -> None:
    op.add_column(
        _TABLE, sa.Column("model", sa.String(100), nullable=True)
    )
    op.add_column(
        _TABLE, sa.Column("modeling_notes", sa.Text(), nullable=True)
    )
