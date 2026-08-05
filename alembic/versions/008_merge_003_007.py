"""Merge heads 003_add_reports_to_pipeline_runs + 007_remove_story_manual_tests

Revision ID: 008_merge_003_007
Revises: 003_add_reports_to_pipeline_runs, 007_remove_story_manual_tests
Create Date: 2026-07-28 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "008_merge_003_007"
down_revision = ("003_add_reports_to_pipeline_runs", "007_remove_story_manual_tests")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge-only revision: no schema changes. This unifies two head revisions.
    pass


def downgrade() -> None:
    pass
