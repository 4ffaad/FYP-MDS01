"""Store new VSViG result payloads as authenticated ciphertext in PostgreSQL."""

from alembic import op
import sqlalchemy as sa


revision = "037_encrypted_video_results"
down_revision = "036_on_demand_veeg_playback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("video_detection_jobs") as batch_op:
        batch_op.add_column(sa.Column("result_nonce", sa.LargeBinary(), nullable=True))
        batch_op.add_column(sa.Column("result_ciphertext", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("video_detection_jobs") as batch_op:
        batch_op.drop_column("result_ciphertext")
        batch_op.drop_column("result_nonce")
