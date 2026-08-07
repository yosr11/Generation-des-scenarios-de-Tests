"""015_slim_generated_scenarios

Revision ID: 015_slim_generated_scenarios
Revises: 014_slim_story_business_models
Create Date: 2026-08-07
"""

from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "015_slim_generated_scenarios"
down_revision: Union[str, None] = "014_slim_story_business_models"
branch_labels = None
depends_on = None

_TABLE = "generated_scenarios"
_DROP_COLUMNS = ("model", "source_ustype")


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = {c["name"] for c in inspector.get_columns(_TABLE)}
    for col in _DROP_COLUMNS:
        if col in existing:
            op.drop_column(_TABLE, col)


def downgrade() -> None:
    op.add_column(
        _TABLE, sa.Column("source_ustype", sa.String(100), nullable=True)
    )
    op.add_column(
        _TABLE, sa.Column("model", sa.String(100), nullable=True)
    )
