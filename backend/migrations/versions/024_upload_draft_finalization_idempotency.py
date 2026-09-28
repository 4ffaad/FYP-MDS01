"""Associate finalized sessions with their upload draft for safe retries."""

from alembic import op
import sqlalchemy as sa


revision = "024_upload_draft"
down_revision = "023_video_privacy_pose_preview"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("upload_draft_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_sessions_upload_draft_id",
        "sessions",
        ["upload_draft_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_sessions_upload_draft_id", table_name="sessions")
    op.drop_column("sessions", "upload_draft_id")
