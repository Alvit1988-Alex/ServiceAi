"""add account public id and bot admins

Revision ID: 0012_account_public_id_and_bot_admins
Revises: 0011_yandex_oauth_login
Create Date: 2026-03-29 00:00:00.000000
"""

import random

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0012_account_public_id_and_bot_admins"
down_revision = "0011_yandex_oauth_login"
branch_labels = None
depends_on = None


bot_admin_role = sa.Enum("superadmin", "admin", name="bot_admin_role")


def _generate_unique_public_id(used: set[str]) -> str:
    for _ in range(100):
        candidate = f"{random.randint(0, 99999999):08d}"
        if candidate not in used:
            used.add(candidate)
            return candidate
    raise RuntimeError("Unable to backfill unique account public_id")


def upgrade() -> None:
    op.add_column("accounts", sa.Column("public_id", sa.String(length=8), nullable=True))

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id FROM accounts ORDER BY id")).fetchall()
    used_ids: set[str] = set()

    for row in rows:
        public_id = _generate_unique_public_id(used_ids)
        conn.execute(
            sa.text("UPDATE accounts SET public_id=:public_id WHERE id=:account_id"),
            {"public_id": public_id, "account_id": int(row.id)},
        )

    op.alter_column("accounts", "public_id", nullable=False)
    op.create_index("ix_accounts_public_id", "accounts", ["public_id"], unique=True)

    bot_admin_role.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "bot_admins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bot_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", bot_admin_role, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["bot_id"], ["bots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bot_id", "user_id", name="uq_bot_admins_bot_user"),
    )
    op.create_index(op.f("ix_bot_admins_bot_id"), "bot_admins", ["bot_id"], unique=False)
    op.create_index(op.f("ix_bot_admins_user_id"), "bot_admins", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_bot_admins_user_id"), table_name="bot_admins")
    op.drop_index(op.f("ix_bot_admins_bot_id"), table_name="bot_admins")
    op.drop_table("bot_admins")
    bot_admin_role.drop(op.get_bind(), checkfirst=True)

    op.drop_index("ix_accounts_public_id", table_name="accounts")
    op.drop_column("accounts", "public_id")
