"""Add user fields (jira_username, display_name, is_active, last_login_at) and pipeline_runs table.

Revision ID: 002_add_user_fields_and_pipeline_runs
Revises: 001_initial
Create Date: 2026-06-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_add_user_fields_and_pipeline_runs"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Add new columns to users table ──
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("display_name", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("jira_username", sa.String(255), nullable=True, index=True))
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))
        batch_op.add_column(sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))

    # Create index on jira_username
    try:
        op.create_index("ix_users_jira_username", "users", ["jira_username"], unique=False)
    except Exception:
        pass  # Index may already exist if running against an existing DB

    # ── Create pipeline_runs table ──
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("story_id", sa.String(100), nullable=False, index=True),
        sa.Column("launched_by", sa.String(255), nullable=False, index=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="running"),
        sa.Column("use_rag", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("use_legacy_rag", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("run_agent4", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tests_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pipeline_runs_story_id", "pipeline_runs", ["story_id"], unique=False)
    op.create_index("ix_pipeline_runs_launched_by", "pipeline_runs", ["launched_by"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_pipeline_runs_launched_by", table_name="pipeline_runs")
    op.drop_index("ix_pipeline_runs_story_id", table_name="pipeline_runs")
    op.drop_table("pipeline_runs")

    try:
        op.drop_index("ix_users_jira_username", table_name="users")
    except Exception:
        pass

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("last_login_at")
        batch_op.drop_column("is_active")
        batch_op.drop_column("jira_username")
        batch_op.drop_column("display_name")
