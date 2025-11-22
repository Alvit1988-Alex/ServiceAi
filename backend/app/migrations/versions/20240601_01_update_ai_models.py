"""Update AI models for instructions and knowledge base."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20240601_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS knowledge_chunks CASCADE")
    op.execute("DROP TABLE IF EXISTS knowledge_files CASCADE")
    op.execute("DROP TABLE IF EXISTS ai_instructions CASCADE")

    op.create_table(
        "ai_instructions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_id", sa.Integer(), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
    )
    op.create_index(
        "ix_ai_instructions_bot_id", "ai_instructions", ["bot_id"], unique=True
    )

    op.create_table(
        "knowledge_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_id", sa.Integer(), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("chunks_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
    )
    op.create_index(
        "ix_knowledge_files_bot_id", "knowledge_files", ["bot_id"], unique=False
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "file_id",
            sa.Integer(),
            sa.ForeignKey("knowledge_files.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "bot_id", sa.Integer(), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
    )
    op.create_index(
        "ix_knowledge_chunks_file_id", "knowledge_chunks", ["file_id"], unique=False
    )
    op.create_index(
        "ix_knowledge_chunks_bot_id", "knowledge_chunks", ["bot_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_bot_id", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_file_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")

    op.drop_index("ix_knowledge_files_bot_id", table_name="knowledge_files")
    op.drop_table("knowledge_files")

    op.drop_index("ix_ai_instructions_bot_id", table_name="ai_instructions")
    op.drop_table("ai_instructions")
