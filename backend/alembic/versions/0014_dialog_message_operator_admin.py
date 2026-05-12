"""add operator admin to dialog messages

Revision ID: 0014_dialog_message_operator
Revises: 0013_channels_unique
Create Date: 2026-05-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0014_dialog_message_operator"
down_revision = "0013_channels_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("dialog_messages", sa.Column("operator_admin_id", sa.Integer(), nullable=True))
    op.create_index(
        "ix_dialog_messages_operator_admin_id", "dialog_messages", ["operator_admin_id"], unique=False
    )
    op.create_foreign_key(
        "fk_dialog_messages_operator_admin_id_users",
        "dialog_messages",
        "users",
        ["operator_admin_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_dialog_messages_operator_admin_id_users", "dialog_messages", type_="foreignkey")
    op.drop_index("ix_dialog_messages_operator_admin_id", table_name="dialog_messages")
    op.drop_column("dialog_messages", "operator_admin_id")
