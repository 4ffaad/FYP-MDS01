"""Add owner-scoped idempotency hashes for video privacy jobs."""

from alembic import op
import sqlalchemy as sa


revision = "026_video_privacy_idem"
down_revision = "025_case_source_report"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "video_privacy_jobs",
        sa.Column("idempotency_key_hash", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "uq_video_privacy_owner_idempotency_hash",
        "video_privacy_jobs",
        ["owner_user_id", "idempotency_key_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_video_privacy_owner_idempotency_hash",
        table_name="video_privacy_jobs",
    )
    op.drop_column("video_privacy_jobs", "idempotency_key_hash")
