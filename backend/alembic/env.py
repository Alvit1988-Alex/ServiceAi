from __future__ import annotations

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from app.config import settings  # noqa: E402
from app.database import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

db_url_for_alembic = settings.database_url.replace("%", "%%")
config.set_main_option("sqlalchemy.url", db_url_for_alembic)



def _include_models() -> None:
    """Ensure all model modules are imported for Alembic's autogeneration."""
    import app.modules.accounts.models  # noqa: F401
    import app.modules.auth.models  # noqa: F401
    import app.modules.ai.models  # noqa: F401
    import app.modules.bots.models  # noqa: F401
    import app.modules.channels.models  # noqa: F401
    import app.modules.dialogs.models  # noqa: F401
    import app.modules.diagnostics.models  # noqa: F401


_include_models()

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    def do_run_migrations(connection: Connection) -> None:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async def run_with_connection() -> None:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
        await connectable.dispose()

    asyncio.run(run_with_connection())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
