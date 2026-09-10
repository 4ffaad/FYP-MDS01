"""Add local accounts, login sessions, and record ownership."""

from alembic import op
import sqlalchemy as sa


revision = "014_local_authentication"
down_revision = "013_calibration_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=True),
        sa.Column("auth_provider", sa.String(length=32), nullable=False),
        sa.Column("external_subject", sa.String(length=256), nullable=True),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("external_subject"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_external_subject", "users", ["external_subject"], unique=True)
    op.create_index("ix_users_public_id", "users", ["public_id"], unique=True)

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_auth_sessions_token_hash", "auth_sessions", ["token_hash"], unique=True)
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"], unique=False)

    for table in ("sessions", "upload_drafts", "video_privacy_jobs"):
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(sa.Column("owner_user_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                f"fk_{table}_owner_user_id",
                "users",
                ["owner_user_id"],
                ["id"],
            )
            batch_op.create_index(f"ix_{table}_owner_user_id", ["owner_user_id"], unique=False)


def downgrade() -> None:
    for table in ("sessions", "upload_drafts", "video_privacy_jobs"):
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_index(f"ix_{table}_owner_user_id")
            batch_op.drop_constraint(f"fk_{table}_owner_user_id", type_="foreignkey")
            batch_op.drop_column("owner_user_id")
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_token_hash", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_index("ix_users_public_id", table_name="users")
    op.drop_index("ix_users_external_subject", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
