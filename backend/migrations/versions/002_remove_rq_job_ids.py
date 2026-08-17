"""Remove fields that only supported the deleted RQ worker."""

from alembic import op
import sqlalchemy as sa


revision = "002_remove_rq_job_ids"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Drop RQ job identifiers from session and attempt records.

    The first migration is kept unchanged because it may already have been
    applied to an existing database. This migration safely brings that schema
    forward after Redis/RQ removal.
    """

    op.drop_index("ix_sessions_job_id", table_name="sessions")
    op.drop_index("ix_processing_attempts_job_id", table_name="processing_attempts")
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.drop_column("job_id")
    with op.batch_alter_table("processing_attempts") as batch_op:
        batch_op.drop_column("job_id")


def downgrade() -> None:
    """Restore the legacy RQ job identifier columns and indexes."""

    with op.batch_alter_table("processing_attempts") as batch_op:
        batch_op.add_column(sa.Column("job_id", sa.String(), nullable=True))
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.add_column(sa.Column("job_id", sa.String(), nullable=True))
    op.create_index("ix_processing_attempts_job_id", "processing_attempts", ["job_id"])
    op.create_index("ix_sessions_job_id", "sessions", ["job_id"])
