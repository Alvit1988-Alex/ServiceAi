"""Add Telegram auth fields and pending_logins."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0002_telegram_auth"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("telegram_id", sa.BigInteger(), nullable=True))
    op.add_column("users", sa.Column("username", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("first_name", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(length=255), nullable=True))
    op.create_unique_constraint("uq_users_telegram_id", "users", ["telegram_id"])
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=False)

    pending_login_status_enum = postgresql.ENUM(
        "pending",
        "confirmed",
        "expired",
        name="pending_login_status",
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
                WHERE t.typname = 'pending_login_status'
            ) THEN
                CREATE TYPE pending_login_status AS ENUM ('pending', 'confirmed', 'expired');
            END IF;
        END$$;
        """
    )

    op.create_table(
        "pending_logins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            pending_login_status_enum,
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("token", name="uq_pending_logins_token"),
    )
    op.create_index("ix_pending_logins_token", "pending_logins", ["token"], unique=False)
    op.create_index("ix_pending_logins_telegram_id", "pending_logins", ["telegram_id"], unique=False)
    op.create_index("ix_pending_logins_expires_at", "pending_logins", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_pending_logins_expires_at", table_name="pending_logins")
    op.drop_index("ix_pending_logins_telegram_id", table_name="pending_logins")
    op.drop_index("ix_pending_logins_token", table_name="pending_logins")
    op.drop_table("pending_logins")

    op.drop_constraint("uq_users_telegram_id", "users", type_="unique")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
    op.drop_column("users", "username")
    op.drop_column("users", "telegram_id")

    op.execute("DROP TYPE IF EXISTS pending_login_status CASCADE")
