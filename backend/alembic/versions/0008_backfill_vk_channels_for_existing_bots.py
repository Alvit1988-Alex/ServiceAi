"""Backfill vk bot channels for existing bots."""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0008_backfill_vk_channels_for_existing_bots"
down_revision = "0007_add_vk_channel_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO bot_channels (bot_id, channel_type, config, is_active, created_at, updated_at)
        SELECT b.id, 'vk', '{}'::jsonb, false, now(), now()
        FROM bots AS b
        WHERE NOT EXISTS (
            SELECT 1
            FROM bot_channels AS bc
            WHERE bc.bot_id = b.id
              AND bc.channel_type::text = 'vk'
        )
        """
    )


def downgrade() -> None:
    # Intentionally no-op: this migration performs data backfill.
    # Automatically deleting vk channels on downgrade is unsafe because
    # we cannot reliably distinguish backfilled rows from real user-created rows.
    pass
