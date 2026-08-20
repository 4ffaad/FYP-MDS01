"""Store raw and calibrated model scores separately."""

from alembic import op
import sqlalchemy as sa


revision = "008_calibration_scores"
down_revision = "007_privacy_methods_retention"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add optional score fields used only by reviewed calibrated models."""

    op.add_column("predictions", sa.Column("raw_score", sa.Float(), nullable=True))
    op.add_column("predictions", sa.Column("calibrated_probability", sa.Float(), nullable=True))


def downgrade() -> None:
    """Remove optional raw and calibrated score fields."""

    op.drop_column("predictions", "calibrated_probability")
    op.drop_column("predictions", "raw_score")
