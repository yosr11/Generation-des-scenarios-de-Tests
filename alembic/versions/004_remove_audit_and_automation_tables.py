"""Remove obsolete audit_logs and automation_classifications tables.

Revision ID: 004_remove_audit_and_automation_tables
Revises: 003_add_business_tables
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "004_remove_audit_auto"
down_revision = "003_add_business_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old audit table if it exists
    op.execute("DROP TABLE IF EXISTS audit_logs")

    # Drop old automation classification table if it exists
    op.execute("DROP TABLE IF EXISTS automation_classifications")


def downgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_identifier", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource", sa.String(length=255), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_user_identifier"), "audit_logs", ["user_identifier"], unique=False)

    op.create_table(
        "automation_classifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("story_id", sa.String(length=100), nullable=False),
        sa.Column("test_name", sa.Text(), nullable=False),
        sa.Column("classification", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.String(length=50), nullable=False),
        sa.Column("raison", sa.Text(), nullable=True),
        sa.Column("po_feedback", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_automation_classifications_story_id"), "automation_classifications", ["story_id"], unique=False)
