"""add operator handoff settings to bots

Revision ID: 0015_operator_handoff_settings
Revises: 0014_dialog_message_operator
Create Date: 2026-07-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0015_operator_handoff_settings"
down_revision = "0014_dialog_message_operator"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bots",
        sa.Column("operator_handoff_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "bots",
        sa.Column(
            "operator_trigger_phrases",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.execute("UPDATE bots SET operator_handoff_enabled = false WHERE operator_handoff_enabled IS NULL")
    op.execute("UPDATE bots SET operator_trigger_phrases = '[]'::jsonb WHERE operator_trigger_phrases IS NULL")


def downgrade() -> None:
    op.drop_column("bots", "operator_trigger_phrases")
    op.drop_column("bots", "operator_handoff_enabled")
