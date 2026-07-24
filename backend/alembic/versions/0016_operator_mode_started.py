"""add dialog operator mode started at

Revision ID: 0016_operator_mode_started
Revises: 0015_operator_handoff_settings
Create Date: 2026-07-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0016_operator_mode_started"
down_revision = "0015_operator_handoff_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("dialogs", sa.Column("operator_mode_started_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("dialogs", "operator_mode_started_at")
