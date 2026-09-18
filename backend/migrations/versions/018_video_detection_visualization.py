"""Retain an encrypted privacy-safe video detection visualization."""

from alembic import op
import sqlalchemy as sa


revision = "018_video_visualization"
down_revision = "017_demo_admin_role"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "video_detection_jobs",
        sa.Column("visualization_path", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("video_detection_jobs", "visualization_path")