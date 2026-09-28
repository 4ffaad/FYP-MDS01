"""Scope case profile and report identities to their owner."""

from alembic import op
import sqlalchemy as sa


revision = "027_owner_case_artifact_keys"
down_revision = "026_video_privacy_idem"
branch_labels = None
depends_on = None


CASE_REPORT_PK_NAMING = {"pk": "pk_%(table_name)s"}


def upgrade() -> None:
    with op.batch_alter_table("case_patient_profiles") as batch_op:
        batch_op.drop_constraint(
            "uq_case_patient_profiles_case_id",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_case_patient_profiles_owner_case",
            ["owner_user_id", "case_id"],
        )

    bind = op.get_bind()
    previous_pk_name = sa.inspect(bind).get_pk_constraint("case_source_reports").get("name")
    with op.batch_alter_table(
        "case_source_reports",
        naming_convention=CASE_REPORT_PK_NAMING,
    ) as batch_op:
        batch_op.drop_constraint(
            previous_pk_name or "pk_case_source_reports",
            type_="primary",
        )
        batch_op.create_primary_key(
            "pk_case_source_reports_owner_case",
            ["owner_user_id", "case_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    current_pk_name = sa.inspect(bind).get_pk_constraint("case_source_reports").get("name")
    with op.batch_alter_table(
        "case_source_reports",
        naming_convention=CASE_REPORT_PK_NAMING,
    ) as batch_op:
        batch_op.drop_constraint(
            current_pk_name or "pk_case_source_reports_owner_case",
            type_="primary",
        )
        batch_op.create_primary_key("case_source_reports_pkey", ["case_id"])

    with op.batch_alter_table("case_patient_profiles") as batch_op:
        batch_op.drop_constraint(
            "uq_case_patient_profiles_owner_case",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_case_patient_profiles_case_id",
            ["case_id"],
        )
