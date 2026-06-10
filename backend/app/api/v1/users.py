from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import UserCreate, UserOut, UserUpdate
from app.schemas.common import success
from app.core.security import hash_password
from app.models.user import User as UserModel

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
async def list_users(
    _admin: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    total = await db.scalar(select(func.count()).select_from(UserModel))
    result = await db.execute(
        select(UserModel).offset((page - 1) * page_size).limit(page_size).order_by(UserModel.created_at.desc())
    )
    users = result.scalars().all()
    items = [
        UserOut(id=str(u.id), username=u.username, role=u.role, is_active=u.is_active).model_dump() for u in users
    ]
    return success({"items": items, "total": total or 0, "page": page, "page_size": page_size})


@router.post("")
async def create_user(
    body: UserCreate,
    _admin: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    existing = await db.execute(select(UserModel).where(UserModel.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")
    user = UserModel(username=body.username, password_hash=hash_password(body.password), role=body.role)
    db.add(user)
    await db.flush()
    return success(
        UserOut(id=str(user.id), username=user.username, role=user.role, is_active=user.is_active).model_dump(),
        message="created",
    )


@router.put("/{user_id}")
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    _admin: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if body.password:
        user.password_hash = hash_password(body.password)
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    await db.flush()
    return success(
        UserOut(id=str(user.id), username=user.username, role=user.role, is_active=user.is_active).model_dump()
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: UUID,
    admin: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if admin.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    return success(message="deleted")
