"""Store the requested privacy configuration with each session."""

from alembic import op
import sqlalchemy as sa


revision = "003_add_requested_privacy_method"
down_revision = "002_remove_rq_job_ids"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add a non-sensitive requested privacy configuration field."""

    op.add_column(
        "sessions",
        sa.Column(
            "privacy_method",
            sa.String(length=64),
            nullable=False,
            server_default="raw-control",
        ),
    )


def downgrade() -> None:
    """Remove the requested privacy configuration field."""

    op.drop_column("sessions", "privacy_method")
