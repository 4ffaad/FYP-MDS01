"""Persist sanitized Nicolet video sync anchors and owner-scoped links."""

from alembic import op
import sqlalchemy as sa


revision = "031_verified_veeg_sync"
down_revision = "030_video_blur_strength"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("recordings") as batch_op:
        batch_op.add_column(
            sa.Column(
                "video_sync_status",
                sa.String(length=24),
                server_default=sa.text("'unavailable'"),
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("video_sync_nonce", sa.LargeBinary(), nullable=True))
        batch_op.add_column(sa.Column("video_sync_ciphertext", sa.LargeBinary(), nullable=True))

    with op.batch_alter_table("video_detection_jobs") as batch_op:
        batch_op.add_column(sa.Column("source_name_token", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("source_group_id", sa.String(length=36), nullable=True))
        batch_op.add_column(
            sa.Column(
                "sync_group_complete",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("eeg_recording_db_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "eeg_sync_status",
                sa.String(length=24),
                server_default=sa.text("'unavailable'"),
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("eeg_sync_nonce", sa.LargeBinary(), nullable=True))
        batch_op.add_column(sa.Column("eeg_sync_ciphertext", sa.LargeBinary(), nullable=True))
        batch_op.create_foreign_key(
            "fk_video_detection_jobs_eeg_recording_db_id_recordings",
            "recordings",
            ["eeg_recording_db_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_index(
        "ix_video_detection_jobs_source_name_token",
        "video_detection_jobs",
        ["source_name_token"],
    )
    op.create_index(
        "ix_video_detection_jobs_source_group_id",
        "video_detection_jobs",
        ["source_group_id"],
    )
    op.create_index(
        "ix_video_detection_jobs_eeg_recording_db_id",
        "video_detection_jobs",
        ["eeg_recording_db_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_video_detection_jobs_eeg_recording_db_id",
        table_name="video_detection_jobs",
    )
    op.drop_index(
        "ix_video_detection_jobs_source_group_id",
        table_name="video_detection_jobs",
    )
    op.drop_index(
        "ix_video_detection_jobs_source_name_token",
        table_name="video_detection_jobs",
    )
    with op.batch_alter_table("video_detection_jobs") as batch_op:
        batch_op.drop_constraint(
            "fk_video_detection_jobs_eeg_recording_db_id_recordings",
            type_="foreignkey",
        )
        batch_op.drop_column("eeg_sync_ciphertext")
        batch_op.drop_column("eeg_sync_nonce")
        batch_op.drop_column("eeg_sync_status")
        batch_op.drop_column("eeg_recording_db_id")
        batch_op.drop_column("sync_group_complete")
        batch_op.drop_column("source_group_id")
        batch_op.drop_column("source_name_token")
    with op.batch_alter_table("recordings") as batch_op:
        batch_op.drop_column("video_sync_ciphertext")
        batch_op.drop_column("video_sync_nonce")
        batch_op.drop_column("video_sync_status")
