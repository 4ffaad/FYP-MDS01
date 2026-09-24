"""Persist private EEG source checksum and format-conversion provenance."""

from alembic import op
import sqlalchemy as sa


revision = "021_recording_provenance"
down_revision = "020_recording_annotation_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add owner-internal provenance fields without exposing source metadata."""

    op.add_column("recordings", sa.Column("source_checksum_sha256", sa.String(length=64), nullable=True))
    op.add_column("recordings", sa.Column("conversion_details_json", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove private provenance fields."""

    op.drop_column("recordings", "conversion_details_json")
    op.drop_column("recordings", "source_checksum_sha256")
