"""deduplicate bot channels and enforce unique bot/type

Revision ID: 0013_bot_channels_unique_per_type
Revises: 0012_account_public_id_botadm
Create Date: 2026-05-04 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0013_bot_channels_unique_per_type"
down_revision = "0012_account_public_id_botadm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DELETE FROM bot_channels bc
            USING bot_channels newer
            WHERE bc.bot_id = newer.bot_id
              AND bc.channel_type = newer.channel_type
              AND (
                (bc.is_active = false AND newer.is_active = true)
                OR (bc.is_active = newer.is_active AND bc.id < newer.id)
              )
            """
        )
    )
    op.create_unique_constraint(
        "uq_bot_channels_bot_id_channel_type",
        "bot_channels",
        ["bot_id", "channel_type"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_bot_channels_bot_id_channel_type", "bot_channels", type_="unique")
