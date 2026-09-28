"""Allow automatically extracted profiles to remain explicitly unverified."""

from alembic import op
import sqlalchemy as sa


revision = "029_profile_verification_status"
down_revision = "028_video_privacy_fingerprint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("case_patient_profiles") as batch_op:
        batch_op.add_column(
            sa.Column(
                "verification_status",
                sa.String(length=24),
                server_default=sa.text("'reviewed'"),
                nullable=False,
            )
        )
        batch_op.alter_column(
            "reviewed_by_user_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.alter_column(
            "reviewed_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=True,
        )
        batch_op.create_check_constraint(
            "ck_case_patient_profiles_verification_status",
            "verification_status IN ('reviewed', 'auto_extracted')",
        )


def downgrade() -> None:
    bind = op.get_bind()
    auto_extracted = bind.execute(
        sa.text(
            "SELECT 1 FROM case_patient_profiles "
            "WHERE verification_status = 'auto_extracted' LIMIT 1"
        )
    ).first()
    if auto_extracted is not None:
        raise RuntimeError(
            "Cannot downgrade while auto-extracted patient profiles exist; "
            "review or delete them before downgrading."
        )

    with op.batch_alter_table("case_patient_profiles") as batch_op:
        batch_op.drop_constraint(
            "ck_case_patient_profiles_verification_status",
            type_="check",
        )
        batch_op.alter_column(
            "reviewed_by_user_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.alter_column(
            "reviewed_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
        )
        batch_op.drop_column("verification_status")
