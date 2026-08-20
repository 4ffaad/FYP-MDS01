"""Rename public privacy modes and add private retained-artifact metadata."""

from alembic import op
import sqlalchemy as sa


revision = "007_privacy_methods_retention"
down_revision = "006_reference_annotations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Normalize privacy method names and store score/retention metadata."""

    op.execute(
        "UPDATE sessions SET privacy_method = 'metadata-scrub' "
        "WHERE privacy_method = 'control'"
    )
    op.execute(
        "UPDATE sessions SET privacy_method = 'signal-obfuscation' "
        "WHERE privacy_method = 'cancellable-signal-projection'"
    )
    op.alter_column("sessions", "privacy_method", server_default="metadata-scrub")
    with op.batch_alter_table("recordings") as batch_op:
        batch_op.add_column(sa.Column("retained_artifact_path", sa.String(), nullable=True))
    with op.batch_alter_table("predictions") as batch_op:
        batch_op.add_column(
            sa.Column("score_type", sa.String(length=64), nullable=False, server_default="development_score")
        )
        batch_op.add_column(sa.Column("calibration_method", sa.String(length=64), nullable=True))


def downgrade() -> None:
    """Restore historical method names and remove the added metadata."""

    op.execute(
        "UPDATE sessions SET privacy_method = 'control' "
        "WHERE privacy_method = 'metadata-scrub'"
    )
    op.execute(
        "UPDATE sessions SET privacy_method = 'cancellable-signal-projection' "
        "WHERE privacy_method = 'signal-obfuscation'"
    )
    op.alter_column("sessions", "privacy_method", server_default="control")
    with op.batch_alter_table("predictions") as batch_op:
        batch_op.drop_column("calibration_method")
        batch_op.drop_column("score_type")
    with op.batch_alter_table("recordings") as batch_op:
        batch_op.drop_column("retained_artifact_path")
