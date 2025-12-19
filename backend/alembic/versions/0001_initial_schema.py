"""Initial schema for ServiceAI."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_role_enum = sa.Enum("admin", "owner", "operator", name="user_role")
    channel_type_enum = sa.Enum(
        "telegram", "whatsapp_green", "whatsapp_360", "whatsapp_custom", "avito", "max", "webchat", name="channel_type"
    )
    dialog_status_enum = sa.Enum("auto", "wait_operator", "wait_user", name="dialog_status")
    dialog_message_sender_enum = sa.Enum("user", "bot", "operator", name="dialog_message_sender")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "account_operators",
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.PrimaryKeyConstraint("account_id", "user_id"),
    )

    op.create_table(
        "bots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "bot_channels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel_type", channel_type_enum, nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_bot_channels_bot_id", "bot_channels", ["bot_id"], unique=False)
    op.create_index("ix_bot_channels_channel_type", "bot_channels", ["channel_type"], unique=False)

    op.create_table(
        "dialogs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel_type", channel_type_enum, nullable=False),
        sa.Column("external_chat_id", sa.String(length=255), nullable=False),
        sa.Column("external_user_id", sa.String(length=255), nullable=False),
        sa.Column("status", dialog_status_enum, nullable=False),
        sa.Column("closed", sa.Boolean(), nullable=False),
        sa.Column("last_message_at", sa.DateTime(), nullable=False),
        sa.Column("last_user_message_at", sa.DateTime(), nullable=True),
        sa.Column("unread_messages_count", sa.Integer(), nullable=False),
        sa.Column("is_locked", sa.Boolean(), nullable=False),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("assigned_admin_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("waiting_time_seconds", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_dialogs_bot_id", "dialogs", ["bot_id"], unique=False)
    op.create_index("ix_dialogs_channel_type", "dialogs", ["channel_type"], unique=False)
    op.create_index("ix_dialogs_external_chat_id", "dialogs", ["external_chat_id"], unique=False)
    op.create_index("ix_dialogs_external_user_id", "dialogs", ["external_user_id"], unique=False)
    op.create_index("ix_dialogs_assigned_admin_id", "dialogs", ["assigned_admin_id"], unique=False)
    op.create_index("ix_dialog_bot_channel_chat", "dialogs", ["bot_id", "channel_type", "external_chat_id"], unique=False)

    op.create_table(
        "ai_instructions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ai_instructions_bot_id", "ai_instructions", ["bot_id"], unique=True)

    op.create_table(
        "dialog_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dialog_id", sa.Integer(), sa.ForeignKey("dialogs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender", dialog_message_sender_enum, nullable=False),
        sa.Column("text", sa.String(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_dialog_messages_dialog_id", "dialog_messages", ["dialog_id"], unique=False)

    op.create_table(
        "knowledge_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("chunks_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_knowledge_files_bot_id", "knowledge_files", ["bot_id"], unique=False)

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("file_id", sa.Integer(), sa.ForeignKey("knowledge_files.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_knowledge_chunks_file_id", "knowledge_chunks", ["file_id"], unique=False)
    op.create_index("ix_knowledge_chunks_bot_id", "knowledge_chunks", ["bot_id"], unique=False)

    op.create_table(
        "integration_logs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("bot_id", sa.BigInteger(), sa.ForeignKey("bots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("channel_type", sa.String(length=32), nullable=False),
        sa.Column("direction", sa.String(length=8), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("external_id", sa.String(length=128), nullable=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("endpoint", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("integration_logs")
    op.drop_index("ix_knowledge_chunks_bot_id", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_file_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_index("ix_knowledge_files_bot_id", table_name="knowledge_files")
    op.drop_table("knowledge_files")
    op.drop_index("ix_dialog_messages_dialog_id", table_name="dialog_messages")
    op.drop_table("dialog_messages")
    op.drop_index("ix_ai_instructions_bot_id", table_name="ai_instructions")
    op.drop_table("ai_instructions")
    op.drop_index("ix_dialog_bot_channel_chat", table_name="dialogs")
    op.drop_index("ix_dialogs_assigned_admin_id", table_name="dialogs")
    op.drop_index("ix_dialogs_external_user_id", table_name="dialogs")
    op.drop_index("ix_dialogs_external_chat_id", table_name="dialogs")
    op.drop_index("ix_dialogs_channel_type", table_name="dialogs")
    op.drop_index("ix_dialogs_bot_id", table_name="dialogs")
    op.drop_table("dialogs")
    op.drop_index("ix_bot_channels_channel_type", table_name="bot_channels")
    op.drop_index("ix_bot_channels_bot_id", table_name="bot_channels")
    op.drop_table("bot_channels")
    op.drop_table("bots")
    op.drop_table("account_operators")
    op.drop_table("accounts")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS dialog_message_sender")
    op.execute("DROP TYPE IF EXISTS dialog_status")
    op.execute("DROP TYPE IF EXISTS channel_type")
    op.execute("DROP TYPE IF EXISTS user_role")
