"""Add consumed_at to pending_logins."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_pending_login_consume"
down_revision = "0002_telegram_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pending_logins", sa.Column("consumed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("pending_logins", "consumed_at")
