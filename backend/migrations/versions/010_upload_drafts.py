"""Add encrypted temporary upload drafts."""

from alembic import op
import sqlalchemy as sa


revision = "010_upload_drafts"
down_revision = "009_prediction_threshold"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create metadata for short-lived encrypted uploads."""

    op.create_table(
        "upload_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_id", sa.String(length=64), nullable=False),
        sa.Column("encrypted_path", sa.String(length=1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("draft_id"),
    )
    op.create_index("ix_upload_drafts_draft_id", "upload_drafts", ["draft_id"])


def downgrade() -> None:
    """Remove temporary upload draft metadata."""

    op.drop_index("ix_upload_drafts_draft_id", table_name="upload_drafts")
    op.drop_table("upload_drafts")
