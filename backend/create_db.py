import asyncio

from app.database import Base, engine

# Импортируем модели, чтобы они зарегистрировались в Base.metadata
from app.modules.accounts import models as accounts_models  # noqa: F401
from app.modules.ai import models as ai_models  # noqa: F401
from app.modules.bots import models as bots_models  # noqa: F401
from app.modules.channels import models as channels_models  # noqa: F401
from app.modules.dialogs import models as dialogs_models  # noqa: F401
from app.modules.diagnostics import models as diagnostics_models  # noqa: F401


async def create_all_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Все таблицы успешно созданы в базе данных.")


if __name__ == "__main__":
    asyncio.run(create_all_tables())
