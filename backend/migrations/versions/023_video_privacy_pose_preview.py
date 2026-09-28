"""Link privacy previews to cases and persist pose coverage counts."""

from alembic import op
import sqlalchemy as sa


revision = "023_video_privacy_pose_preview"
down_revision = "022_case_patient_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "video_privacy_jobs",
        sa.Column("case_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "video_privacy_jobs",
        sa.Column("pose_detected_frames", sa.Integer(), nullable=True),
    )
    op.add_column(
        "video_privacy_jobs",
        sa.Column("pose_sampled_frames", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_video_privacy_jobs_case_id",
        "video_privacy_jobs",
        ["case_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_video_privacy_jobs_case_id", table_name="video_privacy_jobs")
    op.drop_column("video_privacy_jobs", "pose_sampled_frames")
    op.drop_column("video_privacy_jobs", "pose_detected_frames")
    op.drop_column("video_privacy_jobs", "case_id")
