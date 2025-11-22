from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db


async def get_db_session(db: AsyncSession = Depends(get_db)) -> AsyncSession:
    """Dependency that provides a database session."""

    return db


# Placeholder for future common dependencies (authentication, services, etc.).
# def get_current_user():
#     ...
