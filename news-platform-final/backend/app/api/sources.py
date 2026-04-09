"""News Sources CRUD API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.models import NewsSource, AdminUser, NewsArticle
from app.schemas.schemas import (
    NewsSourceCreate, NewsSourceUpdate, NewsSourceResponse
)
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/sources", tags=["News Sources"])


@router.get("", response_model=List[NewsSourceResponse])
async def list_sources(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NewsSource).order_by(NewsSource.name)
    )
    return result.scalars().all()


@router.get("/{source_id}", response_model=NewsSourceResponse)
async def get_source(source_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NewsSource).where(NewsSource.id == source_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.post("", response_model=NewsSourceResponse, status_code=201)
async def create_source(
    data: NewsSourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    source = NewsSource(**data.model_dump())
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


@router.put("/{source_id}", response_model=NewsSourceResponse)
async def update_source(
    source_id: int,
    data: NewsSourceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    result = await db.execute(
        select(NewsSource).where(NewsSource.id == source_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(source, key, value)

    await db.commit()
    await db.refresh(source)
    return source


@router.delete("/{source_id}")
async def delete_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    result = await db.execute(
        select(NewsSource).where(NewsSource.id == source_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    await db.delete(source)
    await db.commit()
    return {"message": f"Source '{source.name}' deleted"}


@router.post("/{source_id}/toggle-pause")
async def toggle_pause(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    result = await db.execute(
        select(NewsSource).where(NewsSource.id == source_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    source.is_paused = not source.is_paused
    await db.commit()
    return {"message": f"Source {'paused' if source.is_paused else 'resumed'}", "is_paused": source.is_paused}


@router.post("/{source_id}/toggle-enable")
async def toggle_enable(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    result = await db.execute(
        select(NewsSource).where(NewsSource.id == source_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    source.is_enabled = not source.is_enabled
    await db.commit()
    return {"message": f"Source {'enabled' if source.is_enabled else 'disabled'}", "is_enabled": source.is_enabled}


@router.get("/{source_id}/stats")
async def get_source_stats(source_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NewsSource).where(NewsSource.id == source_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    total = await db.execute(
        select(func.count(NewsArticle.id)).where(NewsArticle.source_id == source_id)
    )
    new_count = await db.execute(
        select(func.count(NewsArticle.id)).where(
            NewsArticle.source_id == source_id, NewsArticle.flag == "N"
        )
    )
    processed_count = await db.execute(
        select(func.count(NewsArticle.id)).where(
            NewsArticle.source_id == source_id, NewsArticle.flag == "A"
        )
    )

    return {
        "source": source.name,
        "total_articles": total.scalar() or 0,
        "new_articles": new_count.scalar() or 0,
        "processed_articles": processed_count.scalar() or 0,
        "last_scraped": source.last_scraped_at,
    }
