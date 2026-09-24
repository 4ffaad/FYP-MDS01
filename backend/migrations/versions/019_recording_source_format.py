"""Record the source EEG reader format for processing provenance."""

from alembic import op
import sqlalchemy as sa

revision = "019_recording_source_format"
down_revision = "018_video_visualization"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Store the non-sensitive source format used for each EEG recording."""

    op.add_column("recordings", sa.Column("source_format", sa.String(length=32), nullable=True))


def downgrade() -> None:
    """Remove the source format provenance field."""

    op.drop_column("recordings", "source_format")
