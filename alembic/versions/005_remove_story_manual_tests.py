"""Remove obsolete story_manual_tests table.

Revision ID: 005_remove_story_manual_tests
Revises: 004_remove_audit_auto
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "005_remove_story_manual_tests"
down_revision = "004_remove_audit_auto"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS story_manual_tests")


def downgrade() -> None:
    op.execute(
        """
        CREATE TABLE story_manual_tests (
            id SERIAL PRIMARY KEY,
            story_id VARCHAR(100) NOT NULL,
            tests_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            generation_model VARCHAR(100),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_story_manual_tests_story_id ON story_manual_tests (story_id)"
    )
