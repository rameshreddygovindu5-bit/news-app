"""News Articles CRUD, reporter submission, and admin approval API."""

import hashlib
import re
import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc

from app.database import get_db, AsyncSessionLocal
from app.models.models import NewsArticle, NewsSource, AdminUser
from app.schemas.schemas import (
    NewsArticleResponse, NewsArticleUpdate, NewsArticleListResponse,
    ManualNewsCreate, FlagEnum, ArticleApproval, BulkIDs, BulkApproval
)
from app.services.auth_service import get_current_user, require_admin
from app.services.category_service import category_service

logger = logging.getLogger(__name__)

def trigger_sync():
    """Trigger the coordinated master pipeline (AI -> Rank -> AWS Sync)."""
    try:
        from app.tasks.celery_app import run_master_heartbeat
        run_master_heartbeat.delay()
    except Exception:
        # Fallback to direct thread if Celery is down
        import threading
        from app.tasks.celery_app import run_master_heartbeat as pulse_func
        threading.Thread(target=pulse_func, daemon=True).start()

def _make_slug(title: str) -> str:
    import re
    s = title.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "_", s).strip("_")
    return s[:200] if s else None


async def _run_ai_and_rank(article_id: int):
    """Run AI rephrase + auto-rank in background after manual/submit/youtube save."""
    import asyncio
    async with AsyncSessionLocal() as db:
        try:
            from app.services.ai_service import ai_service
            art = (await db.execute(select(NewsArticle).where(NewsArticle.id == article_id))).scalar_one_or_none()
            if not art:
                return
            # AI process
            result = await asyncio.to_thread(
                ai_service.process_article,
                art.original_title, art.original_content or ""
            )
            art.rephrased_title = result["rephrased_title"]
            art.rephrased_content = result["rephrased_content"]
            art.telugu_title = result.get("telugu_title", "")
            art.telugu_content = result.get("telugu_content", "")
            art.translated_title = result.get("translated_title", art.original_title)
            art.translated_content = result.get("translated_content", art.original_content)
            art.category = result["category"]
            art.slug = result.get("slug") or _make_slug(result["rephrased_title"])
            art.tags = result.get("tags", [])
            art.ai_status = "AI_SUCCESS"
            art.processed_at = datetime.now(timezone.utc)
            # Auto-rank: set flag=Y so it appears in top news and client UI
            art.flag = "Y"
            art.rank_score = 500  # High initial score for manual/submitted articles
            await db.commit()
            logger.info(f"[AUTO-AI] Article {article_id} processed + ranked (Y)")
            # Trigger master pulse immediately
            trigger_sync()
        except Exception as e:
            logger.error(f"[AUTO-AI] Failed for article {article_id}: {e}")

router = APIRouter(prefix="/api/articles", tags=["News Articles"])


def generate_slug(title: str) -> str:
    """Generate a URL-friendly slug from a title."""
    s = title.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "_", s).strip("_")
    return s


def article_to_response(article, source_name: str = None) -> dict:
    return {
        "id": article.id, "source_id": article.source_id,
        "original_title": article.original_title, "original_content": article.original_content,
        "original_url": article.original_url, "original_language": article.original_language,
        "published_at": article.published_at,
        "translated_title": article.translated_title, "translated_content": article.translated_content,
        "rephrased_title": article.rephrased_title, "rephrased_content": article.rephrased_content,
        "telugu_title": article.telugu_title, "telugu_content": article.telugu_content,
        "category": article.category, "slug": article.slug, "tags": article.tags or [],
        "content_hash": article.content_hash, "is_duplicate": article.is_duplicate,
        "flag": article.flag, "rank_score": article.rank_score or 0,
        "image_url": article.image_url, "author": article.author,
        "submitted_by": article.submitted_by,
        "ai_status": getattr(article, 'ai_status', 'unknown'),
        "is_posted_fb": getattr(article, 'is_posted_fb', False),
        "created_at": article.created_at, "updated_at": article.updated_at,
        "processed_at": article.processed_at,
        "source_name": source_name or "Peoples Feedback",
    }


# ===== LIST / SEARCH =====

@router.get("", response_model=NewsArticleListResponse)
async def list_articles(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None, category: Optional[str] = None,
    source_id: Optional[int] = None, flag: Optional[str] = None,
    flags: Optional[str] = None, has_telugu: Optional[str] = None,
    telugu_page: Optional[bool] = Query(None),
    date_from: Optional[str] = None, date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List articles. Use `flags=A,Y` for published-only (public client).
    Use `flag=N` for single flag. `flags` takes precedence over `flag`."""
    query = select(NewsArticle, NewsSource.name.label("source_name")).join(
        NewsSource, NewsArticle.source_id == NewsSource.id)
    count_query = select(func.count(NewsArticle.id)).select_from(NewsArticle)
    filters = [NewsArticle.is_duplicate == False]
    if keyword:
        kw = f"%{keyword}%"
        filters.append(or_(
            NewsArticle.original_title.ilike(kw), NewsArticle.rephrased_title.ilike(kw),
            NewsArticle.telugu_title.ilike(kw),
            NewsArticle.original_content.ilike(kw), NewsArticle.rephrased_content.ilike(kw),
            NewsArticle.telugu_content.ilike(kw)
        ))
    if category: filters.append(NewsArticle.category == category)
    if source_id: filters.append(NewsArticle.source_id == source_id)
    if flags:
        flag_list = [f.strip() for f in flags.split(",") if f.strip()]
        filters.append(NewsArticle.flag.in_(flag_list))
    elif flag:
        filters.append(NewsArticle.flag == flag)
    if has_telugu == 'true':
        filters.append(and_(NewsArticle.telugu_title != None, NewsArticle.telugu_title != ''))
    elif telugu_page:
        # Strictly Telugu page content
        filters.append(and_(NewsArticle.telugu_title != None, NewsArticle.telugu_title != ''))
    else:
        # Default (Home/English pages): Must have English content
        filters.append(or_(
            and_(NewsArticle.rephrased_title != None, NewsArticle.rephrased_title != ''),
            NewsArticle.original_language == 'en'
        ))

    if date_from: filters.append(NewsArticle.created_at >= date_from)
    if date_to: filters.append(NewsArticle.created_at <= date_to)
    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    query = query.order_by(desc(NewsArticle.published_at), desc(NewsArticle.created_at)).offset(offset).limit(page_size)
    rows = (await db.execute(query)).all()
    return NewsArticleListResponse(
        articles=[article_to_response(r[0], r[1]) for r in rows],
        total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size)


@router.get("/top-news")
async def get_top_news(
    limit: int = Query(500, ge=1, le=1000), 
    telugu_page: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    query = select(NewsArticle, NewsSource.name.label("source_name")).join(
        NewsSource, NewsArticle.source_id == NewsSource.id
    ).where(NewsArticle.flag == "Y", NewsArticle.is_duplicate == False)
    
    if telugu_page:
        query = query.where(and_(NewsArticle.telugu_title != None, NewsArticle.telugu_title != ''))
    else:
        query = query.where(or_(
            and_(NewsArticle.rephrased_title != None, NewsArticle.rephrased_title != ''),
            NewsArticle.original_language == 'en'
        ))
        
    query = query.order_by(desc(NewsArticle.published_at), desc(NewsArticle.created_at)).limit(limit)
    rows = (await db.execute(query)).all()
    return [article_to_response(r[0], r[1]) for r in rows]


@router.get("/by-category/{category}")
async def get_articles_by_category(
    category: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    telugu_page: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    # "Home" is a special sentinel: return all categories (latest news across everything)
    if category.lower() == "home":
        base = [NewsArticle.flag.in_(["A", "Y"]), NewsArticle.is_duplicate == False]
    else:
        base = [NewsArticle.category == category, NewsArticle.flag.in_(["A", "Y"]), NewsArticle.is_duplicate == False]
    
    if telugu_page:
        base.append(and_(NewsArticle.telugu_title != None, NewsArticle.telugu_title != ''))
    else:
        base.append(or_(
            and_(NewsArticle.rephrased_title != None, NewsArticle.rephrased_title != ''),
            NewsArticle.original_language == 'en'
        ))

    total_result = await db.execute(select(func.count(NewsArticle.id)).where(and_(*base)))
    total = total_result.scalar() or 0
    
    if total == 0 and not telugu_page:
        # Fallback for English: take latest 2 months news for this category
        from datetime import timedelta
        two_months_ago = datetime.now(timezone.utc) - timedelta(days=60)
        base = [
            NewsArticle.category == category, 
            NewsArticle.flag.in_(["N", "A", "Y"]), 
            NewsArticle.is_duplicate == False,
            NewsArticle.original_language == 'en',
            or_(NewsArticle.published_at >= two_months_ago, NewsArticle.created_at >= two_months_ago)
        ]
        total_result = await db.execute(select(func.count(NewsArticle.id)).where(and_(*base)))
        total = total_result.scalar() or 0
        
    query = select(NewsArticle, NewsSource.name.label("source_name")).join(
        NewsSource, NewsArticle.source_id == NewsSource.id
    ).where(and_(*base)).order_by(desc(NewsArticle.published_at)).offset((page-1)*page_size).limit(page_size)
    rows = (await db.execute(query)).all()
    return {
        "articles": [article_to_response(r[0], r[1]) for r in rows], 
        "total": total, "page": page, "page_size": page_size, 
        "total_pages": (total + page_size - 1) // page_size, 
        "category": category,
        "is_fallback": total > 0 and not any(r[0].flag == "Y" for r in rows)
    }


# ===== PENDING APPROVAL QUEUE (admin) =====

@router.get("/pending")
async def get_pending_articles(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(require_admin),
):
    """Get articles pending admin approval (flag=P)."""
    base = (NewsArticle.flag == "P",)
    total = (await db.execute(select(func.count(NewsArticle.id)).where(*base))).scalar() or 0
    query = select(NewsArticle, NewsSource.name.label("source_name")).join(
        NewsSource, NewsArticle.source_id == NewsSource.id
    ).where(*base).order_by(desc(NewsArticle.created_at)).offset((page-1)*page_size).limit(page_size)
    rows = (await db.execute(query)).all()
    return {"articles": [article_to_response(r[0], r[1]) for r in rows], "total": total, "page": page, "page_size": page_size}


@router.post("/{article_id}/approve")
async def approve_article(
    article_id: int, data: ArticleApproval,
    db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(require_admin),
):
    """Admin approves or rejects a pending article.
    action: 'approve' â†’ flag=N (goes to AI pipeline)
            'approve_direct' â†’ flag=Y (skip AI, goes to Top News)
            'reject' â†’ flag=D
    """
    article = (await db.execute(select(NewsArticle).where(NewsArticle.id == article_id))).scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if data.action == "approve":
        article.flag = "N"  # Send to AI pipeline
    elif data.action == "approve_direct":
        article.flag = "Y"  # Direct to Top News (skip AI)
        article.processed_at = datetime.now(timezone.utc)
    elif data.action == "reject":
        article.flag = "D"
        article.deleted_at = datetime.now(timezone.utc)
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use: approve, approve_direct, reject")

    await db.commit()

    # Automation: Trigger sync for all approval/rejection actions
    trigger_sync()

    return {"message": f"Article {data.action}d", "id": article_id, "new_flag": article.flag}


@router.post("/bulk-approve")
async def bulk_approve_articles(
    data: BulkApproval,
    db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(require_admin),
):
    """Admin approves/rejects multiple articles at once."""
    from sqlalchemy import update
    
    target_flag = "N"
    if data.action == "approve_direct": target_flag = "Y"
    elif data.action == "reject": target_flag = "D"
    
    values = {"flag": target_flag, "updated_at": datetime.now(timezone.utc)}
    if target_flag == "Y": values["processed_at"] = datetime.now(timezone.utc)
    if target_flag == "D": values["deleted_at"] = datetime.now(timezone.utc)

    stmt = update(NewsArticle).where(NewsArticle.id.in_(data.ids)).values(**values)
    result = await db.execute(stmt)
    await db.commit()
    
    trigger_sync()
    return {"message": f"Bulk {data.action} completed", "count": result.rowcount}


# ===== REPORTER SUBMISSIONS =====

@router.get("/my-submissions")
async def get_my_submissions(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db), user: AdminUser = Depends(get_current_user),
):
    """Reporter sees their own submitted articles."""
    base = (NewsArticle.submitted_by == user.username,)
    total = (await db.execute(select(func.count(NewsArticle.id)).where(*base))).scalar() or 0
    query = select(NewsArticle, NewsSource.name.label("source_name")).join(
        NewsSource, NewsArticle.source_id == NewsSource.id
    ).where(*base).order_by(desc(NewsArticle.created_at)).offset((page-1)*page_size).limit(page_size)
    rows = (await db.execute(query)).all()
    return {"articles": [article_to_response(r[0], r[1]) for r in rows], "total": total, "page": page, "page_size": page_size}


@router.post("/submit", status_code=201)
async def submit_article(
    data: ManualNewsCreate,
    db: AsyncSession = Depends(get_db),
    user: AdminUser = Depends(get_current_user),
):
    """Reporter submits an article for admin approval (flag=P).
    Admin submissions go directly (flag=A or flag=Y for PF)."""
    content_hash = hashlib.sha256(f"{data.title}|{user.username}|{datetime.now().isoformat()}".encode()).hexdigest()

    source_id = data.source_id
    source_name = "Peoples Feedback"
    
    # End-to-end: Ensure Peoples Feedback is the default source
    pf_source = (await db.execute(select(NewsSource).where(
        or_(NewsSource.name.ilike("Peoples Feedback"), NewsSource.name.ilike("PeoplesFeedback"))
    ))).scalar_one_or_none()
    
    if not source_id and pf_source:
        source_id = pf_source.id
        source_name = pf_source.name
    elif source_id:
        source = (await db.execute(select(NewsSource).where(NewsSource.id == source_id))).scalar_one_or_none()
        if source: source_name = source.name
    
    if not source_id:
        # Fallback to first available if PF not found
        source = (await db.execute(select(NewsSource).limit(1))).scalar_one_or_none()
        if source: 
            source_id = source.id
            source_name = source.name
        else: raise HTTPException(status_code=400, detail="No news sources available")

    is_pf = source_name.lower().strip() in ["peoples feedback", "peoplesfeedback"]
    is_admin = user.role == "admin"

    # Flag logic: Reporter â†’ P (pending), Admin PF â†’ Y, Admin other â†’ A
    if is_admin:
        target_flag = "Y" if is_pf else "A"
    else:
        target_flag = "P"  # Reporter: always pending approval

    article = NewsArticle(
        source_id=source_id, original_title=data.title, original_content=data.content,
        rephrased_title=data.title, rephrased_content=data.content,
        translated_title=data.title, translated_content=data.content,
        category=category_service.normalize(data.category or "General"), 
        slug=_make_slug(data.title), tags=data.tags or [],
        content_hash=content_hash, flag=target_flag,
        image_url=data.image_url, original_language="en",
        published_at=datetime.now(timezone.utc), processed_at=datetime.now(timezone.utc) if target_flag != "P" else None,
        submitted_by=user.username,
        ai_status="AI_SUCCESS" if is_admin else "pending",
        scrape_metadata={"ai_method": "manual"} if is_admin else None
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)

    # Run AI processing + auto-rank in background for admin submissions
    if target_flag != "P":
        import asyncio
        asyncio.create_task(_run_ai_and_rank(article.id))
        # Trigger AWS sync after a small delay
        from app.tasks.celery_app import sync_to_aws
        try:
            sync_to_aws.apply_async(countdown=30) # Give AI time to finish
        except: pass

    status_msg = "submitted for approval" if target_flag == "P" else "created and automated processing started"
    return {"message": f"Article {status_msg}", "id": article.id, "flag": target_flag}


# ===== CRUD =====

@router.get("/{id_or_slug}")
async def get_article(id_or_slug: str, db: AsyncSession = Depends(get_db)):
    """Public article detail by ID or Slug. Excludes pending (P) and deleted (D)."""
    filters = [NewsArticle.flag.notin_(["P", "D"])]
    
    if id_or_slug.isdigit():
        filters.append(NewsArticle.id == int(id_or_slug))
    else:
        filters.append(NewsArticle.slug == id_or_slug)
        
    query = select(NewsArticle, NewsSource.name.label("source_name")).join(
        NewsSource, NewsArticle.source_id == NewsSource.id
    ).where(and_(*filters))
    
    row = (await db.execute(query)).first()
    if not row:
        # If slug not found, try searching by id if it was a string that LOOKS like a slug but isn't
        raise HTTPException(status_code=404, detail="Article not found")
    return article_to_response(row[0], row[1])


@router.put("/{article_id}")
async def update_article(
    article_id: int, data: NewsArticleUpdate,
    db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(require_admin),
):
    article = (await db.execute(select(NewsArticle).where(NewsArticle.id == article_id))).scalar_one_or_none()
    if not article: raise HTTPException(status_code=404, detail="Article not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        if key == "flag" and value:
            setattr(article, key, value.value if hasattr(value, 'value') else value)
        else:
            setattr(article, key, value)
    if data.flag and data.flag.value == "D":
        article.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(article)

    # Automation: Trigger AWS sync for all updates
    trigger_sync()

    return {"message": "Article updated", "id": article_id}


@router.delete("/{article_id}")
async def delete_article(article_id: int, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(require_admin)):
    article = (await db.execute(select(NewsArticle).where(NewsArticle.id == article_id))).scalar_one_or_none()
    if not article: raise HTTPException(status_code=404, detail="Article not found")
    article.flag = "D"
    article.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    # Trigger master pulse
    trigger_sync()

    return {"message": "Article deleted (soft)", "id": article_id}


@router.post("/{article_id}/reprocess", status_code=202)
async def reprocess_article(
    article_id: int, db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    """Re-queue a single article through the full AI pipeline (rephrase + Telugu + category + slug)."""
    article = (await db.execute(select(NewsArticle).where(NewsArticle.id == article_id))).scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Reset AI status so the batch worker picks it up again
    article.ai_status = "pending"
    article.ai_error_count = 0
    await db.commit()

    # Try Celery async first; fall back to running directly in thread
    try:
        from app.tasks.celery_app import process_ai_batch
        process_ai_batch.delay()
        return {"message": f"Article {article_id} queued for AI reprocessing (async)", "mode": "celery"}
    except Exception:
        import asyncio
        from app.tasks.celery_app import worker_process_ai
        try:
            result = await asyncio.to_thread(worker_process_ai, article_id)
            if result:
                try:
                    from app.tasks.celery_app import sync_to_aws
                    sync_to_aws.delay()
                except Exception:
                    pass
                return {"message": f"Article {article_id} reprocessed (sync)", "mode": "sync"}
            else:
                raise HTTPException(status_code=500, detail="AI reprocessing failed — check AI credentials")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Reprocess failed: {str(e)[:200]}")


@router.post("/bulk-reprocess")
async def bulk_reprocess_articles(
    data: BulkIDs,
    db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(require_admin),
):
    """Admin queues multiple articles for AI reprocessing."""
    from sqlalchemy import update
    stmt = update(NewsArticle).where(NewsArticle.id.in_(data.ids)).values(
        ai_status="pending", ai_error_count=0, updated_at=datetime.now(timezone.utc)
    )
    result = await db.execute(stmt)
    await db.commit()
    
    try:
        from app.tasks.celery_app import process_ai_batch
        process_ai_batch.delay()
    except: pass
    
    return {"message": "Bulk AI reprocessing queued", "count": result.rowcount}


@router.post("/bulk-delete")
async def bulk_delete_articles(
    data: BulkIDs,
    db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(require_admin),
):
    """Admin soft-deletes multiple articles."""
    from sqlalchemy import update
    stmt = update(NewsArticle).where(NewsArticle.id.in_(data.ids)).values(
        flag="D", deleted_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
    )
    result = await db.execute(stmt)
    await db.commit()
    
    trigger_sync()
    return {"message": "Bulk deletion completed", "count": result.rowcount}


@router.post("/manual", status_code=201)
async def create_manual_article(
    data: ManualNewsCreate, db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    """Admin creates article directly (bypasses approval)."""
    content_hash = hashlib.sha256(f"{data.title}|manual|{datetime.now().isoformat()}".encode()).hexdigest()
    source_id = data.source_id
    source_name = "Peoples Feedback"
    
    # End-to-end: Ensure Peoples Feedback is the default source
    pf_source = (await db.execute(select(NewsSource).where(
        or_(NewsSource.name.ilike("Peoples Feedback"), NewsSource.name.ilike("PeoplesFeedback"))
    ))).scalar_one_or_none()
    
    if not source_id and pf_source:
        source_id = pf_source.id
        source_name = pf_source.name
    elif source_id:
        source = (await db.execute(select(NewsSource).where(NewsSource.id == source_id))).scalar_one_or_none()
        if source: source_name = source.name
        
    if not source_id:
        source = (await db.execute(select(NewsSource).limit(1))).scalar_one_or_none()
        if source: source_id = source.id; source_name = source.name
        else: raise HTTPException(status_code=400, detail="No sources available")

    is_pf = source_name.lower().strip() in ["peoples feedback", "peoplesfeedback"]
    target_flag = "Y" if is_pf else "A"

    article = NewsArticle(
        source_id=source_id, original_title=data.title, original_content=data.content,
        rephrased_title=data.title, rephrased_content=data.content,
        translated_title=data.title, translated_content=data.content,
        category=category_service.normalize(data.category or "General"), 
        slug=_make_slug(data.title), tags=data.tags or [],
        content_hash=content_hash, flag=target_flag,
        image_url=data.image_url, original_language="en",
        published_at=datetime.now(timezone.utc), processed_at=datetime.now(timezone.utc),
        submitted_by="admin",
        ai_status="AI_SUCCESS",
        scrape_metadata={"ai_method": "manual"}
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)
    # Run AI processing + auto-rank in background
    import asyncio
    asyncio.create_task(_run_ai_and_rank(article.id))
    
    # Trigger master pulse
    trigger_sync()

    return {"message": "Article created, AI processing started", "id": article.id}


@router.post("/suggest")
async def suggest_metadata(
    data: ManualNewsCreate,
    db: AsyncSession = Depends(get_db), auth: AdminUser = Depends(get_current_user),
):
    """AI analyzes draft title/content to suggest category and tags."""
    if not data.title or not data.content:
        raise HTTPException(status_code=400, detail="Title and content required for analysis")
    
    from app.services.ai_service import ai_service
    try:
        # Use a lighter analytical call instead of full processing
        res = await ai_service.analyze_reporter_draft(data.title, data.content)
        return {
            "suggested_category": res.get("category", "Home"),
            "suggested_tags": res.get("tags", []),
            "summary": res.get("summary", "")
        }
    except Exception as e:
        logger.error(f"[AI-SUGGEST] Failed: {e}")
        return {"suggested_category": "Home", "suggested_tags": [], "error": str(e)}


