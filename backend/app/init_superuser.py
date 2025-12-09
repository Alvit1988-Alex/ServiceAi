"""One-time script to create initial admin user.

Usage (from backend/ directory):

    set PYTHONPATH=.
    python app/init_superuser.py

"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.database import async_session_factory
from app.modules.accounts.models import User, UserRole
from app.modules.accounts.schemas import UserCreate
from app.modules.accounts.service import AccountsService, UsersService

# просто импортируем модели, чтобы зарегистрировать их в маппере
from app.modules.dialogs.models import Dialog  # noqa: F401
from app.modules.bots.models import Bot       # noqa: F401



ADMIN_EMAIL = "admin@admin.com"
ADMIN_PASSWORD = "admin"
ADMIN_FULL_NAME = "Admin"


async def create_initial_admin() -> None:
    async with async_session_factory() as session:
        # Проверяем, есть ли уже такой пользователь
        result = await session.execute(
            select(User).where(User.email == ADMIN_EMAIL)
        )
        existing = result.scalars().first()

        accounts_service = AccountsService()

        if existing:
            account = await accounts_service.get_or_create_for_owner(
                session=session, owner=existing
            )
            print(
                f"[init_superuser] User {ADMIN_EMAIL} уже существует "
                f"(id={existing.id}, account_id={account.id}), ничего не делаем."
            )
            return

        users_service = UsersService()

        user_in = UserCreate(
            email=ADMIN_EMAIL,
            full_name=ADMIN_FULL_NAME,
            role=UserRole.ADMIN,
            is_active=True,
            password=ADMIN_PASSWORD,
        )

        user = await users_service.create(session, user_in)
        account = await accounts_service.get_or_create_for_owner(session=session, owner=user)
        print(
            f"[init_superuser] Создан админ: {user.email} (id={user.id}, "
            f"account_id={account.id})"
        )


def main() -> None:
    asyncio.run(create_initial_admin())


if __name__ == "__main__":
    main()
