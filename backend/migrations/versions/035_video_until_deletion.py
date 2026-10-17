"""Retain non-expired standalone video jobs until explicit case deletion."""

from alembic import op


revision = "035_video_until_deletion"
down_revision = "034_clinical_annotations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Preserve existing artifacts; already-expired jobs may have been deleted.
    op.execute(
        "UPDATE video_detection_jobs "
        "SET retention_expires_at = NULL "
        "WHERE status != 'expired'"
    )


def downgrade() -> None:
    # The prior deadlines cannot be reconstructed without risking data loss.
    pass
