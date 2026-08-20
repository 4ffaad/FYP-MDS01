"""Store the decision threshold used for each prediction."""

from alembic import op
import sqlalchemy as sa


revision = "009_prediction_threshold"
down_revision = "008_calibration_scores"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add a per-prediction threshold for honest result summaries."""

    op.add_column("predictions", sa.Column("threshold", sa.Float(), nullable=False, server_default="0.5"))


def downgrade() -> None:
    """Remove the stored decision threshold."""

    op.drop_column("predictions", "threshold")
