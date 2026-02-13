from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.accounts.models import Account, User, UserRole, account_operators
from app.modules.bots.models import Bot
from app.security.auth import get_current_user


async def get_db_session(db: AsyncSession = Depends(get_db)) -> AsyncSession:
    """Dependency that provides a database session."""

    return db


async def get_accessible_account_ids(session: AsyncSession, user: User) -> list[int] | None:
    """Return accessible account ids for user or None for full access."""

    if user.role == UserRole.admin:
        return None

    owned_result = await session.execute(select(Account.id).where(Account.owner_id == user.id))
    operated_result = await session.execute(
        select(account_operators.c.account_id).where(account_operators.c.user_id == user.id)
    )

    account_ids = set(owned_result.scalars().all())
    account_ids.update(operated_result.scalars().all())
    return list(account_ids)


async def require_bot_access(bot_id: int, session: AsyncSession, user: User) -> Bot:
    """Fetch bot only if it is accessible for the user."""

    if user.role == UserRole.admin:
        stmt = select(Bot).where(Bot.id == bot_id)
    else:
        account_ids = await get_accessible_account_ids(session=session, user=user)
        if not account_ids:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")
        stmt = select(Bot).where(Bot.id == bot_id, Bot.account_id.in_(account_ids))

    bot = (await session.execute(stmt)).scalars().first()
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")
    return bot


async def get_accessible_bot(
    bot_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Bot:
    return await require_bot_access(bot_id, session, current_user)


# Placeholder for future common dependencies (authentication, services, etc.).
# def get_current_user():
#     ...
