"""Store safe dataset reference annotations on recordings."""

from alembic import op
import sqlalchemy as sa


revision = "006_reference_annotations"
down_revision = "005_signal_projection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add an annotation source and relative seizure intervals."""

    op.add_column("recordings", sa.Column("reference_annotation_source", sa.String(), nullable=True))
    op.add_column("recordings", sa.Column("reference_intervals_json", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove stored dataset reference annotations."""

    op.drop_column("recordings", "reference_intervals_json")
    op.drop_column("recordings", "reference_annotation_source")
