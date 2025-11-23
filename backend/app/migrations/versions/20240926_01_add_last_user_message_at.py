"""Add last_user_message_at field to dialogs."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20240926_01"
down_revision = "20240702_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dialogs",
        sa.Column("last_user_message_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("dialogs", "last_user_message_at")
