"""create story_manual_tests table

Revision ID: 006_create_story_manual_tests
Revises: 005_remove_story_manual_tests
Create Date: 2026-07-28 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "006_create_story_manual_tests"
down_revision = "005_remove_story_manual_tests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "story_manual_tests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("story_id", sa.String(length=200), nullable=False, index=False),
        sa.Column("tests_json", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("generation_model", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    # index on story_id
    op.create_index("ix_story_manual_tests_story_id", "story_manual_tests", ["story_id"])


def downgrade() -> None:
    op.drop_index("ix_story_manual_tests_story_id", table_name="story_manual_tests")
    op.drop_table("story_manual_tests")
