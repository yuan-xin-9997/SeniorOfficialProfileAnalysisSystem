from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.schemas.common import success

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(body: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User inactive")
    settings = get_settings()
    token = create_access_token(str(user.id), user.role)
    data = TokenResponse(
        access_token=token,
        expires_in=settings.JWT_EXPIRE_HOURS * 3600,
        user=UserOut(id=str(user.id), username=user.username, role=user.role, is_active=user.is_active),
    )
    return success(data.model_dump())


@router.get("/me")
async def me(user: Annotated[User, Depends(get_current_user)]):
    return success(
        UserOut(id=str(user.id), username=user.username, role=user.role, is_active=user.is_active).model_dump()
    )


@router.post("/logout")
async def logout(_user: Annotated[User, Depends(get_current_user)]):
    return success(message="logged out")
