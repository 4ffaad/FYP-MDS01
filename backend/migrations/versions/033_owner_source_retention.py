"""Retain new owner sources while preserving historical privacy policies."""
from alembic import op
import sqlalchemy as sa

revision = "033_owner_source_retention"
down_revision = "032_patient_region_review_blur"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("sessions") as batch:
        batch.add_column(sa.Column("retention_policy", sa.String(32), nullable=False, server_default="legacy"))
    with op.batch_alter_table("recordings") as batch:
        batch.add_column(sa.Column("original_artifact_path", sa.String(), nullable=True))

    with op.batch_alter_table("video_detection_jobs") as batch:
        batch.add_column(sa.Column("reference_only", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.alter_column("retention_expires_at", existing_type=sa.DateTime(), nullable=True)


def downgrade():
    # Downgrade keeps retained data; assign an expiry before restoring NOT NULL.
    op.execute("UPDATE video_detection_jobs SET retention_expires_at = '9999-12-31 00:00:00' WHERE retention_expires_at IS NULL")
    with op.batch_alter_table("video_detection_jobs") as batch:
        batch.drop_column("reference_only")
        batch.alter_column("retention_expires_at", existing_type=sa.DateTime(), nullable=False)
    with op.batch_alter_table("recordings") as batch:
        batch.drop_column("original_artifact_path")
    with op.batch_alter_table("sessions") as batch:
        batch.drop_column("retention_policy")
