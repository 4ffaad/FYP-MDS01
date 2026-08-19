"""Remove the unused direct patient reference from upload sessions."""

from alembic import op
import sqlalchemy as sa


revision = "004_remove_patient_reference"
down_revision = "003_add_requested_privacy_method"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Drop plaintext patient references and normalize the control default."""

    op.execute("UPDATE sessions SET privacy_method = 'control' WHERE privacy_method = 'raw-control'")
    op.alter_column("sessions", "privacy_method", server_default="control")
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.drop_column("patient_reference")


def downgrade() -> None:
    """Restore the legacy field only for rollback compatibility."""

    with op.batch_alter_table("sessions") as batch_op:
        batch_op.add_column(sa.Column("patient_reference", sa.String(), nullable=True))
    op.alter_column("sessions", "privacy_method", server_default="raw-control")
