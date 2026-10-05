"""Persist each VSViG job's adjustable model-input blur setting."""

from alembic import op
import sqlalchemy as sa


revision = "030_video_blur_strength"
down_revision = "029_profile_verification_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("video_detection_jobs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "blur_strength_percent",
                sa.Integer(),
                server_default=sa.text("100"),
                nullable=False,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("video_detection_jobs") as batch_op:
        batch_op.drop_column("blur_strength_percent")
