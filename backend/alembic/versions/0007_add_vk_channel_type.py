"""Add vk value to channel_type enum."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0007_add_vk_channel_type"
down_revision = "0006_add_bitrix_openline_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE channel_type ADD VALUE IF NOT EXISTS 'vk'")


def downgrade() -> None:
    bind = op.get_bind()
    vk_exists = bind.execute(sa.text("SELECT EXISTS (SELECT 1 FROM bot_channels WHERE channel_type::text = 'vk')")).scalar()
    if vk_exists:
        raise RuntimeError("Cannot downgrade: bot_channels contains channel_type='vk'")

    vk_dialog_exists = bind.execute(sa.text("SELECT EXISTS (SELECT 1 FROM dialogs WHERE channel_type::text = 'vk')")).scalar()
    if vk_dialog_exists:
        raise RuntimeError("Cannot downgrade: dialogs contains channel_type='vk'")

    # Downgrade will fail if 'vk' values exist; guarded above.
    op.execute(
        """
        CREATE TYPE channel_type_new AS ENUM (
            'telegram',
            'whatsapp_green',
            'whatsapp_360',
            'whatsapp_custom',
            'avito',
            'max',
            'webchat'
        )
        """
    )
    op.execute(
        """
        ALTER TABLE bot_channels
        ALTER COLUMN channel_type
        TYPE channel_type_new
        USING channel_type::text::channel_type_new
        """
    )
    op.execute(
        """
        ALTER TABLE dialogs
        ALTER COLUMN channel_type
        TYPE channel_type_new
        USING channel_type::text::channel_type_new
        """
    )
    op.execute("DROP TYPE channel_type")
    op.execute("ALTER TYPE channel_type_new RENAME TO channel_type")
