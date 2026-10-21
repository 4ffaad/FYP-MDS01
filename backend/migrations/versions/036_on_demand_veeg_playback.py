"""Track encrypted reference playback separately from model jobs."""

from alembic import op
import sqlalchemy as sa


revision = "036_on_demand_veeg_playback"
down_revision = "035_video_until_deletion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("video_detection_jobs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "playback_status",
                sa.String(length=24),
                nullable=False,
                server_default=sa.text("'not_applicable'"),
            )
        )
        batch_op.add_column(
            sa.Column("source_frame_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("source_width", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("source_height", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("playback_path", sa.String(), nullable=True))

    op.execute(
        "UPDATE video_detection_jobs "
        "SET playback_status = CASE "
        "WHEN visualization_path IS NOT NULL THEN 'ready' "
        "WHEN original_path IS NOT NULL THEN 'conversion_required' "
        "ELSE 'unavailable' END "
        "WHERE reference_only = TRUE"
    )
    op.execute(
        "UPDATE video_detection_jobs "
        "SET playback_path = visualization_path "
        "WHERE reference_only = TRUE AND visualization_path IS NOT NULL"
    )


def downgrade() -> None:
    with op.batch_alter_table("video_detection_jobs") as batch_op:
        batch_op.drop_column("playback_path")
        batch_op.drop_column("source_height")
        batch_op.drop_column("source_width")
        batch_op.drop_column("source_frame_count")
        batch_op.drop_column("playback_status")
