"""Store owner-scoped patient identity only as authenticated ciphertext."""

from alembic import op
import sqlalchemy as sa


revision = "022_case_patient_profiles"
down_revision = "021_recording_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create a profile table with ciphertext and human-review metadata."""

    op.create_table(
        "case_patient_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.String(length=64), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("identity_nonce", sa.LargeBinary(length=12), nullable=False),
        sa.Column("identity_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("crypto_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id", name="uq_case_patient_profiles_case_id"),
    )
    op.create_index(
        "ix_case_patient_profiles_case_id", "case_patient_profiles", ["case_id"], unique=False
    )
    op.create_index(
        "ix_case_patient_profiles_owner_user_id",
        "case_patient_profiles",
        ["owner_user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove encrypted patient profiles."""

    op.drop_index("ix_case_patient_profiles_owner_user_id", table_name="case_patient_profiles")
    op.drop_index("ix_case_patient_profiles_case_id", table_name="case_patient_profiles")
    op.drop_table("case_patient_profiles")
