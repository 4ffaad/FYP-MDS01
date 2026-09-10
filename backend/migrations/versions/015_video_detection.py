"""Add independent, owned video detection jobs."""
from alembic import op
import sqlalchemy as sa

revision = "015_video_detection"
down_revision = "014_local_authentication"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "video_detection_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("job_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("current_stage", sa.String(32), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("fps", sa.Float(), nullable=False),
        sa.Column("original_path", sa.String(), nullable=True),
        sa.Column("video_path", sa.String(), nullable=True),
        sa.Column("predictions_path", sa.String(), nullable=True),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_video_detection_jobs_job_id", "video_detection_jobs", ["job_id"], unique=True)
    op.create_index("ix_video_detection_jobs_owner_user_id", "video_detection_jobs", ["owner_user_id"])


def downgrade():
    op.drop_table("video_detection_jobs")
