"""Add standalone video privacy job metadata."""

from alembic import op
import sqlalchemy as sa


revision = "012_video_privacy_jobs"
down_revision = "011_canonical_privacy_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "video_privacy_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("profile", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("display_label", sa.String(length=64), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("fps", sa.Float(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("current_stage", sa.String(length=32), nullable=True),
        sa.Column("original_path", sa.String(length=1024), nullable=True),
        sa.Column("output_path", sa.String(length=1024), nullable=True),
        sa.Column("preview_path", sa.String(length=1024), nullable=True),
        sa.Column("quality_flags_json", sa.Text(), nullable=False),
        sa.Column("output_usable", sa.Boolean(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("original_removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(length=256), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_video_privacy_jobs_job_id", "video_privacy_jobs", ["job_id"], unique=True)
    op.create_index("ix_video_privacy_jobs_profile", "video_privacy_jobs", ["profile"], unique=False)
    op.create_index("ix_video_privacy_jobs_status", "video_privacy_jobs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_video_privacy_jobs_status", table_name="video_privacy_jobs")
    op.drop_index("ix_video_privacy_jobs_profile", table_name="video_privacy_jobs")
    op.drop_index("ix_video_privacy_jobs_job_id", table_name="video_privacy_jobs")
    op.drop_table("video_privacy_jobs")
