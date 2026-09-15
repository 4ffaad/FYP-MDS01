"""Add opaque case grouping for longitudinal, privacy-safe review."""

from alembic import op
import sqlalchemy as sa

revision = "016_case_grouping"
down_revision = "015_video_detection"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.add_column(sa.Column("case_id", sa.String(64), nullable=True))
        batch_op.create_index("ix_sessions_case_id", ["case_id"], unique=False)
    with op.batch_alter_table("video_detection_jobs") as batch_op:
        batch_op.add_column(sa.Column("case_id", sa.String(64), nullable=True))
        batch_op.create_index("ix_video_detection_jobs_case_id", ["case_id"], unique=False)


def downgrade():
    with op.batch_alter_table("video_detection_jobs") as batch_op:
        batch_op.drop_index("ix_video_detection_jobs_case_id")
        batch_op.drop_column("case_id")
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.drop_index("ix_sessions_case_id")
        batch_op.drop_column("case_id")
