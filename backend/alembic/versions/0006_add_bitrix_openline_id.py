"""Add openline_id to bitrix_integrations."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0006_add_bitrix_openline_id"
down_revision = "0005_bitrix24_integrations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bitrix_integrations", sa.Column("openline_id", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("bitrix_integrations", "openline_id")
