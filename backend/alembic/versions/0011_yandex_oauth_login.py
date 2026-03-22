"""Add Yandex OAuth login support."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0011_yandex_oauth_login"
down_revision = "0010_backfill_ok"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("yandex_id", sa.String(length=255), nullable=True))
    op.create_unique_constraint("uq_users_yandex_id", "users", ["yandex_id"])
    op.create_index("ix_users_yandex_id", "users", ["yandex_id"], unique=False)

    oauth_login_session_status_enum = postgresql.ENUM(
        "pending",
        "completed",
        "consumed",
        "failed",
        name="oauth_login_session_status",
        create_type=False,
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_namespace n ON n.oid = t.typnamespace
                WHERE t.typname = 'oauth_login_session_status'
            ) THEN
                CREATE TYPE oauth_login_session_status AS ENUM ('pending', 'completed', 'consumed', 'failed');
            END IF;
        END$$;
        """
    )

    op.create_table(
        "oauth_login_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("state_token", sa.String(length=255), nullable=False),
        sa.Column("code_verifier", sa.String(length=255), nullable=True),
        sa.Column("status", oauth_login_session_status_enum, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("completion_token", sa.String(length=255), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("state_token", name="uq_oauth_login_sessions_state_token"),
        sa.UniqueConstraint("completion_token", name="uq_oauth_login_sessions_completion_token"),
    )
    op.create_index("ix_oauth_login_sessions_state_token", "oauth_login_sessions", ["state_token"], unique=False)
    op.create_index(
        "ix_oauth_login_sessions_completion_token",
        "oauth_login_sessions",
        ["completion_token"],
        unique=False,
    )
    op.create_index("ix_oauth_login_sessions_expires_at", "oauth_login_sessions", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_oauth_login_sessions_expires_at", table_name="oauth_login_sessions")
    op.drop_index("ix_oauth_login_sessions_completion_token", table_name="oauth_login_sessions")
    op.drop_index("ix_oauth_login_sessions_state_token", table_name="oauth_login_sessions")
    op.drop_table("oauth_login_sessions")
    op.execute("DROP TYPE IF EXISTS oauth_login_session_status")

    op.drop_index("ix_users_yandex_id", table_name="users")
    op.drop_constraint("uq_users_yandex_id", "users", type_="unique")
    op.drop_column("users", "yandex_id")
