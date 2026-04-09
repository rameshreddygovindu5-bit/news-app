"""Authentication and User Management endpoints."""

from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.models import AdminUser
from app.schemas.schemas import LoginRequest, TokenResponse, UserCreate, UserResponse, UserUpdate
from app.services.auth_service import (
    verify_password, hash_password, create_access_token, get_current_user, require_admin
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AdminUser).where(AdminUser.username == request.username, AdminUser.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    token = create_access_token(data={"sub": user.username, "role": user.role})
    return TokenResponse(access_token=token, username=user.username, role=user.role)


@router.get("/me")
async def get_me(current_user: AdminUser = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "email": current_user.email, "role": current_user.role}


# ===== USER MANAGEMENT (admin only) =====

@router.get("/users", response_model=List[UserResponse])
async def list_users(db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(require_admin)):
    result = await db.execute(select(AdminUser).order_by(AdminUser.created_at.desc()))
    return result.scalars().all()


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    data: UserCreate, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(require_admin)
):
    # Check duplicate
    existing = await db.execute(select(AdminUser).where(AdminUser.username == data.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    user = AdminUser(
        username=data.username,
        password_hash=hash_password(data.password),
        email=data.email,
        role=data.role.value,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int, data: UserUpdate, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(require_admin)
):
    result = await db.execute(select(AdminUser).where(AdminUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "role" and value:
            setattr(user, key, value.value if hasattr(value, 'value') else value)
        else:
            setattr(user, key, value)

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(require_admin)
):
    result = await db.execute(select(AdminUser).where(AdminUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete default admin")

    user.is_active = False
    await db.commit()
    return {"message": f"User '{user.username}' deactivated"}
