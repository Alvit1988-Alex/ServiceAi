"""One-time script to create initial admin user.

Usage (from backend/ directory):

    set PYTHONPATH=.
    python app/init_superuser.py

"""

from __future__ import annotations

import asyncio
import os

from sqlalchemy import select

from app.database import async_session_factory
from app.modules.accounts.models import User, UserRole
from app.modules.accounts.schemas import UserCreate
from app.modules.accounts.service import AccountsService, UsersService

# просто импортируем модели, чтобы зарегистрировать их в маппере
from app.modules.dialogs.models import Dialog  # noqa: F401
from app.modules.bots.models import Bot       # noqa: F401


async def create_initial_admin() -> None:
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    admin_full_name = os.getenv("ADMIN_FULL_NAME") or "Admin"

    if not admin_email or not admin_password:
        print(
            "[init_superuser] Пропускаем создание администратора: "
            "ADMIN_EMAIL или ADMIN_PASSWORD не заданы в окружении."
        )
        return

    async with async_session_factory() as session:
        # Проверяем, есть ли уже такой пользователь
        result = await session.execute(
            select(User).where(User.email == admin_email)
        )
        existing = result.scalars().first()

        accounts_service = AccountsService()

        if existing:
            account = await accounts_service.get_or_create_for_owner(
                session=session, owner=existing
            )
            print(
                f"[init_superuser] User {admin_email} уже существует "
                f"(id={existing.id}, account_id={account.id}), ничего не делаем."
            )
            return

        users_service = UsersService()

        user_in = UserCreate(
            email=admin_email,
            full_name=admin_full_name,
            role=UserRole.admin,
            is_active=True,
            password=admin_password,
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
