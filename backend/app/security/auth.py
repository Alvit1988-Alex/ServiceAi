"""Authentication dependencies and helpers."""

from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.security.jwt import create_access_token, create_refresh_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user():
    """Stub for future authentication logic."""

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="get_current_user is not implemented yet",
    )
