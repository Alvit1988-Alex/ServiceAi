"""Add Bitrix24 integration tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0005_bitrix24_integrations"
down_revision = "0004_add_user_avatar_url"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bitrix_integrations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("portal_url", sa.String(length=255), nullable=False),
        sa.Column("member_id", sa.String(length=255), nullable=True),
        sa.Column("access_token", sa.String(length=2048), nullable=True),
        sa.Column("refresh_token", sa.String(length=2048), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("scope", sa.String(length=1000), nullable=True),
        sa.Column("auto_create_lead_on_first_message", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("bot_id", name="uq_bitrix_integrations_bot_id"),
    )
    op.create_index("ix_bitrix_integrations_bot_id", "bitrix_integrations", ["bot_id"], unique=False)

    op.create_table(
        "bitrix_dialog_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dialog_id", sa.Integer(), sa.ForeignKey("dialogs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bitrix_chat_id", sa.String(length=255), nullable=True),
        sa.Column("bitrix_lead_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("dialog_id", name="uq_bitrix_dialog_links_dialog_id"),
    )
    op.create_index("ix_bitrix_dialog_links_bot_id", "bitrix_dialog_links", ["bot_id"], unique=False)
    op.create_index("ix_bitrix_dialog_links_chat_id", "bitrix_dialog_links", ["bitrix_chat_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_bitrix_dialog_links_chat_id", table_name="bitrix_dialog_links")
    op.drop_index("ix_bitrix_dialog_links_bot_id", table_name="bitrix_dialog_links")
    op.drop_table("bitrix_dialog_links")

    op.drop_index("ix_bitrix_integrations_bot_id", table_name="bitrix_integrations")
    op.drop_table("bitrix_integrations")
