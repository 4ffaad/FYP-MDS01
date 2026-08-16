"""Initial SeizureAI backend schema."""

from alembic import op
import sqlalchemy as sa


revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("patient_reference", sa.String(), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("original_path", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("current_stage", sa.String()),
        sa.Column("job_id", sa.String()),
        sa.Column("error_message", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("ix_sessions_session_id", "sessions", ["session_id"])
    op.create_index("ix_sessions_status", "sessions", ["status"])
    op.create_index("ix_sessions_job_id", "sessions", ["job_id"])

    op.create_table(
        "recordings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("record_id", sa.String(), nullable=False),
        sa.Column("session_db_id", sa.Integer(), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("sequence_index", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("extracted_path", sa.String()),
        sa.Column("deidentified_path", sa.String()),
        sa.Column("preprocessed_path", sa.String()),
        sa.Column("duration_seconds", sa.Float()),
        sa.Column("sampling_rate", sa.Integer()),
        sa.Column("channel_count", sa.Integer()),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error_message", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("record_id"),
    )
    op.create_index("ix_recordings_record_id", "recordings", ["record_id"])
    op.create_index("ix_recordings_session_db_id", "recordings", ["session_db_id"])
    op.create_index("ix_recordings_status", "recordings", ["status"])

    op.create_table(
        "processing_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recording_db_id", sa.Integer(), sa.ForeignKey("recordings.id")),
        sa.Column("session_db_id", sa.Integer(), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("stage", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error_message", sa.String()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_processing_attempts_recording_db_id", "processing_attempts", ["recording_db_id"])
    op.create_index("ix_processing_attempts_session_db_id", "processing_attempts", ["session_db_id"])
    op.create_index("ix_processing_attempts_job_id", "processing_attempts", ["job_id"])

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recording_db_id", sa.Integer(), sa.ForeignKey("recordings.id"), nullable=False),
        sa.Column("window_index", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("seizure_detected", sa.Boolean(), nullable=False),
        sa.Column("start_seconds", sa.Float(), nullable=False),
        sa.Column("end_seconds", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_predictions_recording_db_id", "predictions", ["recording_db_id"])

    op.create_table(
        "explanations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prediction_db_id", sa.Integer(), sa.ForeignKey("predictions.id"), nullable=False),
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("explanation_path", sa.String(), nullable=False),
        sa.Column("explanation_data", sa.String()),
        sa.Column("is_clinical", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_explanations_prediction_db_id", "explanations", ["prediction_db_id"])


def downgrade() -> None:
    op.drop_table("explanations")
    op.drop_table("predictions")
    op.drop_table("processing_attempts")
    op.drop_table("recordings")
    op.drop_table("sessions")
