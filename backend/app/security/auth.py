"""Authentication dependencies and helpers."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.accounts.models import User
from app.security.jwt import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    """Return the currently authenticated user based on the access token."""

    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise unauthorized

        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalars().first()
        if user is None or not user.is_active:
            raise unauthorized

        return user
    except Exception as exc:  # noqa: BLE001 - all errors should return 401
        raise unauthorized from exc
