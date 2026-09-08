"""Persist the privacy profile and calibration provenance per prediction."""

from alembic import op
import sqlalchemy as sa


revision = "013_calibration_provenance"
down_revision = "012_video_privacy_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add reproducibility metadata to window predictions."""

    op.add_column("predictions", sa.Column("calibration_version", sa.String(length=128), nullable=True))
    op.add_column("predictions", sa.Column("calibration_dataset", sa.String(length=128), nullable=True))
    op.add_column(
        "predictions",
        sa.Column("privacy_method", sa.String(length=64), nullable=False, server_default="metadata-scrub"),
    )


def downgrade() -> None:
    """Remove per-prediction calibration provenance."""

    op.drop_column("predictions", "privacy_method")
    op.drop_column("predictions", "calibration_dataset")
    op.drop_column("predictions", "calibration_version")
