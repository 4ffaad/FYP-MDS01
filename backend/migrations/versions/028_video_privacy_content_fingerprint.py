"""Bind video privacy idempotency keys to streamed upload fingerprints."""

from alembic import op
import sqlalchemy as sa


revision = "028_video_privacy_fingerprint"
down_revision = "027_owner_case_artifact_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "video_privacy_jobs",
        sa.Column("content_fingerprint", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("video_privacy_jobs", "content_fingerprint")
