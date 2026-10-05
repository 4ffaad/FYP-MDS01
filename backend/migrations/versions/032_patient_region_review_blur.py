"""Record the privacy transform used by retained VEEG review video."""

from alembic import op
import sqlalchemy as sa


revision = "032_patient_region_review_blur"
down_revision = "031_verified_veeg_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("video_detection_jobs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "review_privacy_method",
                sa.String(length=64),
                server_default=sa.text("'tracked-face-blur-with-full-frame-fallback'"),
                nullable=False,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("video_detection_jobs") as batch_op:
        batch_op.drop_column("review_privacy_method")
