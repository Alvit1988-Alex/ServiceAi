"""Add dialog fields and adjust dialog status enum."""

from alembic import op
import sqlalchemy as sa

from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20240702_01"
down_revision = "20240601_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update dialog status enum to lower-case values
    op.execute("ALTER TYPE dialog_status RENAME TO dialog_status_old")
    dialog_status_enum = sa.Enum("auto", "wait_operator", "wait_user", name="dialog_status")
    dialog_status_enum.create(op.get_bind())
    op.alter_column(
        "dialogs",
        "status",
        existing_type=sa.Enum("AUTO", "WAIT_OPERATOR", "WAIT_USER", name="dialog_status_old"),
        type_=dialog_status_enum,
        postgresql_using="LOWER(status::text)::dialog_status",
    )
    op.execute("DROP TYPE dialog_status_old")

    # Rename existing column
    op.drop_index("ix_dialog_bot_user_external", table_name="dialogs")
    op.alter_column("dialogs", "user_external_id", new_column_name="external_user_id")

    # Add new columns
    op.add_column(
        "dialogs",
        sa.Column(
            "channel_type",
            sa.Enum(
                "telegram",
                "whatsapp_green",
                "whatsapp_360",
                "whatsapp_custom",
                "avito",
                "max",
                "webchat",
                name="channel_type",
            ),
            nullable=False,
            server_default="webchat",
        ),
    )
    op.add_column(
        "dialogs",
        sa.Column("external_chat_id", sa.String(length=255), nullable=False, server_default=""),
    )
    op.add_column(
        "dialogs",
        sa.Column("last_message_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.add_column(
        "dialogs",
        sa.Column("unread_messages_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "dialogs",
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "dialogs",
        sa.Column("locked_until", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "dialogs",
        sa.Column("assigned_admin_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "dialogs",
        sa.Column("waiting_time_seconds", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_foreign_key(
        "fk_dialog_assigned_admin",
        "dialogs",
        "users",
        ["assigned_admin_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index("ix_dialog_channel_type", "dialogs", ["channel_type"], unique=False)
    op.create_index("ix_dialog_external_chat_id", "dialogs", ["external_chat_id"], unique=False)
    op.create_index("ix_dialog_external_user_id", "dialogs", ["external_user_id"], unique=False)
    op.create_index("ix_dialog_assigned_admin_id", "dialogs", ["assigned_admin_id"], unique=False)
    op.create_index(
        "ix_dialog_bot_channel_chat",
        "dialogs",
        ["bot_id", "channel_type", "external_chat_id"],
        unique=False,
    )

    # Clean server defaults now that data is backfilled
    op.alter_column("dialogs", "channel_type", server_default=None)
    op.alter_column("dialogs", "external_chat_id", server_default=None)
    op.alter_column("dialogs", "last_message_at", server_default=None)
    op.alter_column("dialogs", "unread_messages_count", server_default=None)
    op.alter_column("dialogs", "is_locked", server_default=None)
    op.alter_column("dialogs", "waiting_time_seconds", server_default=None)


def downgrade() -> None:
    op.alter_column("dialogs", "waiting_time_seconds", server_default="0")
    op.alter_column("dialogs", "is_locked", server_default=sa.text("false"))
    op.alter_column("dialogs", "unread_messages_count", server_default="0")
    op.alter_column("dialogs", "last_message_at", server_default=sa.text("now()"))
    op.alter_column("dialogs", "external_chat_id", server_default="")
    op.alter_column("dialogs", "channel_type", server_default="webchat")

    op.drop_index("ix_dialog_bot_channel_chat", table_name="dialogs")
    op.drop_index("ix_dialog_assigned_admin_id", table_name="dialogs")
    op.drop_index("ix_dialog_external_user_id", table_name="dialogs")
    op.drop_index("ix_dialog_external_chat_id", table_name="dialogs")
    op.drop_index("ix_dialog_channel_type", table_name="dialogs")

    op.drop_constraint("fk_dialog_assigned_admin", "dialogs", type_="foreignkey")

    op.drop_column("dialogs", "waiting_time_seconds")
    op.drop_column("dialogs", "assigned_admin_id")
    op.drop_column("dialogs", "locked_until")
    op.drop_column("dialogs", "is_locked")
    op.drop_column("dialogs", "unread_messages_count")
    op.drop_column("dialogs", "last_message_at")
    op.drop_column("dialogs", "external_chat_id")
    op.drop_column("dialogs", "channel_type")

    op.alter_column("dialogs", "external_user_id", new_column_name="user_external_id")
    op.create_index(
        "ix_dialog_bot_user_external", "dialogs", ["bot_id", "user_external_id"], unique=False
    )

    op.execute("ALTER TYPE dialog_status RENAME TO dialog_status_old")
    old_dialog_status_enum = sa.Enum("AUTO", "WAIT_OPERATOR", "WAIT_USER", name="dialog_status")
    old_dialog_status_enum.create(op.get_bind())
    op.alter_column(
        "dialogs",
        "status",
        existing_type=postgresql.ENUM("auto", "wait_operator", "wait_user", name="dialog_status_old"),
        type_=old_dialog_status_enum,
        postgresql_using="UPPER(status::text)::dialog_status",
    )
    op.execute("DROP TYPE dialog_status_old")
