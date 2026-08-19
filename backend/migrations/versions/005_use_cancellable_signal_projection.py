"""Replace the detached PSD template mode with shared signal transformation."""

from alembic import op


revision = "005_signal_projection"
down_revision = "004_remove_patient_reference"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Rename existing experimental sessions to the shared pipeline mode."""

    op.execute(
        "UPDATE sessions SET privacy_method = 'cancellable-signal-projection' "
        "WHERE privacy_method = 'cancellable-psd-template'"
    )


def downgrade() -> None:
    """Restore the previous experimental mode name for rollback only."""

    op.execute(
        "UPDATE sessions SET privacy_method = 'cancellable-psd-template' "
        "WHERE privacy_method = 'cancellable-signal-projection'"
    )
