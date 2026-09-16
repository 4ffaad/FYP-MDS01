"""Add a local development administrator flag."""

from alembic import op
import sqlalchemy as sa


revision = "017_demo_admin_role"
down_revision = "016_case_grouping"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("users", "is_admin")