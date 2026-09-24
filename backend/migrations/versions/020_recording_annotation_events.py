"""Store sanitized embedded EEG event timing separately from seizure intervals."""

from alembic import op
import sqlalchemy as sa


revision = "020_recording_annotation_events"
down_revision = "019_recording_source_format"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add internal JSON for normalized, non-text event markers."""

    op.add_column("recordings", sa.Column("annotation_events_json", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove normalized embedded event markers."""

    op.drop_column("recordings", "annotation_events_json")