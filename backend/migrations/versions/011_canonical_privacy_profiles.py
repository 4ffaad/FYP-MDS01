"""Normalize historical privacy values to the fixed privacy pipeline."""

from alembic import op


revision = "011_canonical_privacy_profiles"
down_revision = "010_upload_drafts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Map historical method names to the current baseline and combined profiles."""

    op.execute(
        "UPDATE sessions SET privacy_method = 'metadata-scrub' "
        "WHERE privacy_method IN ('control', 'raw-control')"
    )
    op.execute(
        "UPDATE sessions SET privacy_method = 'metadata-scrub+signal-obfuscation' "
        "WHERE privacy_method IN ('signal-obfuscation', 'cancellable-psd-template', 'cancellable-signal-projection')"
    )


def downgrade() -> None:
    """Restore the previous single-method labels where possible."""

    op.execute(
        "UPDATE sessions SET privacy_method = 'signal-obfuscation' "
        "WHERE privacy_method = 'metadata-scrub+signal-obfuscation'"
    )
