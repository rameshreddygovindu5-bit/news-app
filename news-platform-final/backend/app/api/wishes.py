"""
Wishes API — Birthday greetings, festival wishes, special occasions.
Supports image upload, scheduling, and public display on homepage.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, or_
from pydantic import BaseModel

from app.database import get_db
from app.models.models import Wish, AdminUser
from app.services.auth_service import get_current_user, require_admin
logger = logging.getLogger(__name__)

def trigger_sync():
    """Trigger AWS sync with fallback to synchronous execution."""
    try:
        from app.tasks.celery_app import sync_to_aws
        sync_to_aws.delay()
    except Exception:
        # Fallback to direct thread if Celery is down
        import threading
        from app.tasks.celery_app import sync_to_aws as sync_func
        threading.Thread(target=sync_func, daemon=True).start()

router = APIRouter(prefix="/api/wishes", tags=["Wishes & Greetings"])


# ── Schemas ──────────────────────────────────────────────────────────

class WishCreate(BaseModel):
    title: str
    message: Optional[str] = ""
    wish_type: str = "birthday"  # birthday, festival, anniversary, custom
    person_name: Optional[str] = None
    occasion_date: Optional[datetime] = None
    image_url: Optional[str] = None
    display_on_home: bool = False
    expires_at: Optional[datetime] = None

class WishUpdate(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None
    wish_type: Optional[str] = None
    person_name: Optional[str] = None
    occasion_date: Optional[datetime] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    display_on_home: Optional[bool] = None
    expires_at: Optional[datetime] = None

class WishResponse(BaseModel):
    id: int
    title: str
    message: Optional[str] = None
    wish_type: str
    person_name: Optional[str] = None
    occasion_date: Optional[datetime] = None
    image_url: Optional[str] = None
    is_active: bool
    display_on_home: bool
    created_by: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    likes_count: int = 0

    model_config = {"from_attributes": True}


# ── Public Endpoints ─────────────────────────────────────────────────

@router.get("/active", response_model=List[WishResponse])
async def get_active_wishes(
    wish_type: Optional[str] = None,
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Public: Get active, non-expired wishes for display on the website."""
    now = datetime.now(timezone.utc)
    filters = [
        Wish.is_active == True,
        or_(Wish.expires_at == None, Wish.expires_at > now),
    ]
    if wish_type:
        filters.append(Wish.wish_type == wish_type)

    query = select(Wish).where(and_(*filters)).order_by(
        desc(Wish.display_on_home), desc(Wish.created_at)
    ).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/home", response_model=List[WishResponse])
async def get_home_wishes(db: AsyncSession = Depends(get_db)):
    """Public: Get wishes marked for homepage display (active & not expired)."""
    now = datetime.now(timezone.utc)
    query = select(Wish).where(
        Wish.is_active == True,
        Wish.display_on_home == True,
        or_(Wish.expires_at == None, Wish.expires_at > now),
    ).order_by(desc(Wish.created_at)).limit(10)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/{wish_id}/like", response_model=WishResponse)
async def like_wish(wish_id: int, db: AsyncSession = Depends(get_db)):
    """Public: Heart/Like a wish."""
    query = select(Wish).where(Wish.id == wish_id)
    result = await db.execute(query)
    wish = result.scalar_one_or_none()
    
    if not wish:
        raise HTTPException(status_code=404, detail="Wish not found")

    wish.likes_count = (wish.likes_count or 0) + 1
    await db.commit()
    await db.refresh(wish)
    
    logger.info(f"[WISH] Liked: {wish_id}. New count: {wish.likes_count}")
    trigger_sync()
    return wish


# ── Admin Endpoints ──────────────────────────────────────────────────

@router.get("", response_model=List[WishResponse])
async def list_all_wishes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_user),
):
    """Admin: List all wishes (including inactive)."""
    offset = (page - 1) * page_size
    query = select(Wish).order_by(desc(Wish.created_at)).offset(offset).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=WishResponse, status_code=201)
async def create_wish(
    data: WishCreate,
    db: AsyncSession = Depends(get_db),
    user: AdminUser = Depends(get_current_user),
):
    """Admin/Reporter: Create a new wish/greeting."""
    wish = Wish(
        title=data.title,
        message=data.message or "",
        wish_type=data.wish_type,
        person_name=data.person_name,
        occasion_date=data.occasion_date,
        image_url=data.image_url,
        display_on_home=data.display_on_home,
        is_active=True,
        created_by=user.username,
        expires_at=data.expires_at,
    )
    db.add(wish)
    await db.commit()
    await db.refresh(wish)
    logger.info(f"[WISH] Created: '{data.title}' by {user.username}")
    trigger_sync()
    return wish


@router.put("/{wish_id}", response_model=WishResponse)
async def update_wish(
    wish_id: int,
    data: WishUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    """Admin: Update a wish."""
    wish = (await db.execute(select(Wish).where(Wish.id == wish_id))).scalar_one_or_none()
    if not wish:
        raise HTTPException(status_code=404, detail="Wish not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(wish, key, value)

    await db.commit()
    await db.refresh(wish)
    trigger_sync()
    return wish


@router.delete("/{wish_id}")
async def delete_wish(
    wish_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    """Admin: Soft-delete a wish (set inactive)."""
    wish = (await db.execute(select(Wish).where(Wish.id == wish_id))).scalar_one_or_none()
    if not wish:
        raise HTTPException(status_code=404, detail="Wish not found")

    wish.is_active = False
    await db.commit()
    trigger_sync()
    return {"message": f"Wish '{wish.title}' deactivated", "id": wish_id}
