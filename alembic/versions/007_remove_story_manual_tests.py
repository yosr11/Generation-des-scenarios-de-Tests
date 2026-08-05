"""Remove story_manual_tests again and prevent its recreation.

Revision ID: 007_remove_story_manual_tests
Revises: 006_create_story_manual_tests
Create Date: 2026-07-28 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "007_remove_story_manual_tests"
down_revision = "006_create_story_manual_tests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS story_manual_tests")


def downgrade() -> None:
    op.create_table(
        "story_manual_tests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("story_id", sa.String(length=200), nullable=False, index=False),
        sa.Column(
            "tests_json",
            sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("generation_model", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_story_manual_tests_story_id", "story_manual_tests", ["story_id"])
