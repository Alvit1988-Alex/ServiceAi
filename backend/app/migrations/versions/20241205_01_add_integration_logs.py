"""Add integration logs table for diagnostics."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20241205_01"
down_revision = "20240926_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration_logs",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=False),
            primary_key=True,
        ),
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
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("endpoint", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("integration_logs")

