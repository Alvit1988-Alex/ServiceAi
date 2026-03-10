"""Backfill ok bot channels for existing bots."""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0010_backfill_ok"
down_revision = "0009_add_ok_channel_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO bot_channels (bot_id, channel_type, config, is_active, created_at, updated_at)
        SELECT b.id, 'ok', '{}'::jsonb, false, now(), now()
        FROM bots AS b
        WHERE NOT EXISTS (
            SELECT 1
            FROM bot_channels AS bc
            WHERE bc.bot_id = b.id
              AND bc.channel_type::text = 'ok'
        )
        """
    )


def downgrade() -> None:
    # Intentionally no-op: this migration performs data backfill.
    # Automatically deleting ok channels on downgrade is unsafe because
    # we cannot reliably distinguish backfilled rows from real user-created rows.
    pass
