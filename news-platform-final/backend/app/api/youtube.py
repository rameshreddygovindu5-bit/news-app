"""YouTube Import API — fetch transcript, translate, AI rephrase, save."""

import hashlib
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.models import NewsArticle, NewsSource, AdminUser
from app.schemas.schemas import YouTubeProcessRequest, YouTubeProcessResponse, YouTubeSaveRequest
from app.services.auth_service import require_admin
from app.services.youtube_service import process_youtube_video

router = APIRouter(prefix="/api/youtube", tags=["YouTube Import"])


@router.post("/process", response_model=YouTubeProcessResponse)
async def process_youtube_url(
    data: YouTubeProcessRequest,
    admin: AdminUser = Depends(require_admin),
):
    """Fetch YouTube transcript, translate, and AI rephrase. Returns preview."""
    result = process_youtube_video(data.url)
    if result.get("error") and not result.get("rephrased_title"):
        raise HTTPException(status_code=400, detail=result["error"])
    return YouTubeProcessResponse(**{k: result.get(k) for k in YouTubeProcessResponse.model_fields})


@router.post("/save", status_code=201)
async def save_youtube_article(
    data: YouTubeSaveRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    """Save processed YouTube content as a news article."""
    content_hash = hashlib.sha256(f"{data.video_url}|youtube|{datetime.now().isoformat()}".encode()).hexdigest()

    # Check duplicate
    existing = (await db.execute(
        select(NewsArticle).where(NewsArticle.original_url == data.video_url)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail=f"Article from this video already exists (ID: {existing.id})")

    source_id = data.source_id
    if not source_id:
        source = (await db.execute(select(NewsSource).limit(1))).scalar_one_or_none()
        if source:
            source_id = source.id
        else:
            raise HTTPException(status_code=400, detail="No sources available")

    from app.services.category_service import category_service
    article = NewsArticle(
        source_id=source_id,
        original_title=data.title,
        original_content=data.content,
        original_url=data.video_url,
        rephrased_title=data.title,
        rephrased_content=data.content,
        translated_title=data.title,
        translated_content=data.content,
        category=category_service.normalize(data.category or "General"),
        tags=data.tags or [],
        content_hash=content_hash,
        flag="A",  # Mark as processed immediately since data comes from process endpoint
        image_url=data.image_url,
        original_language="en",
        published_at=datetime.now(timezone.utc),
        submitted_by="youtube-import",
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)

    # Trigger AWS sync immediately for YouTube imports (since flag=A)
    from app.tasks.celery_app import sync_to_aws
    try:
        sync_to_aws.delay()
    except Exception:
        pass

    return {"message": "YouTube article saved successfully", "id": article.id}
