"""Store owner-scoped encrypted clinical observations."""

from alembic import op
import sqlalchemy as sa


revision = "034_clinical_annotations"
down_revision = "033_owner_source_retention"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clinical_annotations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("annotation_id", sa.String(length=64), nullable=False),
        sa.Column("recording_db_id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("payload_nonce", sa.LargeBinary(length=12), nullable=False),
        sa.Column("payload_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("crypto_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["recording_db_id"], ["recordings.id"],
            name="fk_clinical_annotations_recording", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"], ["users.id"], name="fk_clinical_annotations_owner"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"],
            name="fk_clinical_annotations_annotator"
        ),
        sa.UniqueConstraint("annotation_id", name="uq_clinical_annotations_annotation_id"),
    )
    op.create_index(
        "ix_clinical_annotations_recording_db_id",
        "clinical_annotations",
        ["recording_db_id"],
    )
    op.create_index(
        "ix_clinical_annotations_owner_user_id",
        "clinical_annotations",
        ["owner_user_id"],
    )
    op.create_index(
        "ix_clinical_annotations_created_by_user_id",
        "clinical_annotations",
        ["created_by_user_id"],
    )

    op.create_table(
        "clinical_access_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("recording_db_id", sa.Integer(), nullable=True),
        sa.Column("session_db_id", sa.Integer(), nullable=True),
        sa.Column("video_job_db_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["recording_db_id"], ["recordings.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["session_db_id"], ["sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["video_job_db_id"], ["video_detection_jobs.id"], ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "(recording_db_id IS NOT NULL AND session_db_id IS NULL AND video_job_db_id IS NULL) OR "
            "(recording_db_id IS NULL AND session_db_id IS NOT NULL AND video_job_db_id IS NULL) OR "
            "(recording_db_id IS NULL AND session_db_id IS NULL AND video_job_db_id IS NOT NULL)",
            name="ck_clinical_access_events_one_resource",
        ),
    )
    op.create_index(
        "ix_clinical_access_events_actor_user_id",
        "clinical_access_events",
        ["actor_user_id"],
    )
    op.create_index(
        "ix_clinical_access_events_recording_db_id",
        "clinical_access_events",
        ["recording_db_id"],
    )
    op.create_index(
        "ix_clinical_access_events_session_db_id",
        "clinical_access_events",
        ["session_db_id"],
    )
    op.create_index(
        "ix_clinical_access_events_video_job_db_id",
        "clinical_access_events",
        ["video_job_db_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_clinical_access_events_video_job_db_id",
        table_name="clinical_access_events",
    )
    op.drop_index(
        "ix_clinical_access_events_session_db_id",
        table_name="clinical_access_events",
    )
    op.drop_index(
        "ix_clinical_access_events_recording_db_id",
        table_name="clinical_access_events",
    )
    op.drop_index(
        "ix_clinical_access_events_actor_user_id",
        table_name="clinical_access_events",
    )
    op.drop_table("clinical_access_events")
    op.drop_index(
        "ix_clinical_annotations_created_by_user_id", table_name="clinical_annotations"
    )
    op.drop_index(
        "ix_clinical_annotations_owner_user_id", table_name="clinical_annotations"
    )
    op.drop_index(
        "ix_clinical_annotations_recording_db_id", table_name="clinical_annotations"
    )
    op.drop_table("clinical_annotations")
