"""Authentication API router."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.modules.accounts.models import User
from app.modules.accounts.schemas import UserOut
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    Token,
)
from app.security import hashing
from app.security.auth import get_current_user
from app.security.jwt import (
    TokenDecodeError,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


async def _get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def _get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


@router.post("/login", response_model=LoginResponse)
async def login(
    data: LoginRequest, session: AsyncSession = Depends(get_db_session)
) -> Token:
    user = await _get_user_by_email(session=session, email=data.email)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    if not hashing.verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    data: RefreshRequest, session: AsyncSession = Depends(get_db_session)
) -> Token:
    try:
        payload = decode_refresh_token(data.refresh_token)
        user_id = payload.get("sub")
        if user_id is None:
            raise TokenDecodeError("Invalid token payload")
    except TokenDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        ) from exc

    user = await _get_user_by_id(session=session, user_id=int(user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserOut)
async def read_me(current_user: User = Depends(get_current_user)) -> UserOut:
    return current_user


@router.post("/change-password", response_model=UserOut)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> UserOut:
    user = await _get_user_by_id(session=session, user_id=current_user.id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not hashing.verify_password(data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password"
        )

    user.password_hash = hashing.hash_password(data.new_password)
    await session.commit()
    await session.refresh(user)
    return user
