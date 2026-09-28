"""Store owner-scoped pointers for encrypted case source reports."""

from alembic import op
import sqlalchemy as sa


revision = "025_case_source_report"
down_revision = "024_upload_draft"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "case_source_reports",
        sa.Column("case_id", sa.String(length=64), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("artifact_id", sa.String(length=32), nullable=True),
        sa.Column("cleanup_artifact_id", sa.String(length=32), nullable=True),
        sa.Column("crypto_version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint(
            "artifact_id IS NOT NULL OR cleanup_artifact_id IS NOT NULL",
            name="ck_case_source_reports_has_artifact_pointer",
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("case_id"),
    )
    op.create_index(
        "ix_case_source_reports_owner_user_id",
        "case_source_reports",
        ["owner_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_case_source_reports_owner_user_id",
        table_name="case_source_reports",
    )
    op.drop_table("case_source_reports")
