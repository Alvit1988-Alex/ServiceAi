from fastapi import Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.modules.accounts.models import Account, User, UserRole, account_operators
from app.modules.bots.models import Bot, BotAdmin
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


async def get_bot_access_role(session: AsyncSession, user: User, bot: Bot) -> str | None:
    if user.role == UserRole.admin or bot.account.owner_id == user.id:
        return "owner"

    admin = await session.scalar(select(BotAdmin).where(BotAdmin.bot_id == bot.id, BotAdmin.user_id == user.id))
    if admin:
        return admin.role.value

    account_ids = await get_accessible_account_ids(session=session, user=user)
    if account_ids is None or bot.account_id in account_ids:
        return "account_operator"

    return None


async def require_bot_access(bot_id: int, session: AsyncSession, user: User) -> Bot:
    """Fetch bot only if it is accessible for the user."""

    stmt = select(Bot).options(selectinload(Bot.account)).where(Bot.id == bot_id)

    if user.role != UserRole.admin:
        account_ids = await get_accessible_account_ids(session=session, user=user)
        account_clauses = []
        if account_ids:
            account_clauses.append(Bot.account_id.in_(account_ids))

        stmt = stmt.outerjoin(BotAdmin, BotAdmin.bot_id == Bot.id).where(
            or_(
                *account_clauses,
                BotAdmin.user_id == user.id,
            )
        )

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


async def get_bot_for_dialogs(
    bot_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Bot:
    bot = await require_bot_access(bot_id, session, current_user)
    role = await get_bot_access_role(session=session, user=current_user, bot=bot)
    if role in {"owner", "superadmin", "admin", "account_operator"}:
        return bot
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


async def get_bot_for_ai(
    bot_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Bot:
    bot = await require_bot_access(bot_id, session, current_user)
    role = await get_bot_access_role(session=session, user=current_user, bot=bot)
    if role in {"owner", "superadmin", "account_operator"}:
        return bot
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


async def get_bot_for_settings_read(
    bot_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Bot:
    bot = await require_bot_access(bot_id, session, current_user)
    role = await get_bot_access_role(session=session, user=current_user, bot=bot)
    if role in {"owner", "superadmin", "account_operator"}:
        return bot
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


async def get_bot_owner_only(
    bot_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Bot:
    bot = await require_bot_access(bot_id, session, current_user)
    role = await get_bot_access_role(session=session, user=current_user, bot=bot)
    if role == "owner":
        return bot
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can modify bot settings")


async def require_owner_or_superadmin(
    bot_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> tuple[Bot, str, User]:
    bot = await require_bot_access(bot_id, session, current_user)
    role = await get_bot_access_role(session=session, user=current_user, bot=bot)
    if role not in {"owner", "superadmin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return bot, role or "", current_user
