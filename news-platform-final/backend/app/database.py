"""
Database Configuration
======================
Provides:
  - async_engine / AsyncSessionLocal  — for FastAPI async routes
  - sync_engine  / SyncSessionLocal   — for Celery workers
  - create_tables()                   — auto-creates all tables + seeds defaults on startup
  - get_db()                          — FastAPI dependency
"""
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import create_engine, text
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Async engine (FastAPI routes) ─────────────────────────────────────
_async_engine_kwargs = {"echo": False, "pool_pre_ping": True}
if "sqlite" not in settings.DATABASE_URL:
    _async_engine_kwargs.update({"pool_size": 20, "max_overflow": 10})

async_engine = create_async_engine(settings.DATABASE_URL, **_async_engine_kwargs)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ── Sync engine (Celery workers) ──────────────────────────────────────
_sync_engine_kwargs = {"echo": False, "pool_pre_ping": True}
if "sqlite" not in settings.DATABASE_URL_SYNC:
    _sync_engine_kwargs.update({"pool_size": 10, "max_overflow": 5})

sync_engine = create_engine(settings.DATABASE_URL_SYNC, **_sync_engine_kwargs)
SyncSessionLocal = sessionmaker(bind=sync_engine)


class Base(DeclarativeBase):
    pass


# ── FastAPI dependency ─────────────────────────────────────────────────
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ── Startup: create tables + seed defaults ─────────────────────────────
async def create_tables():
    """
    Called once from main.py lifespan on startup.
    Creates all ORM-mapped tables if they don't exist, then seeds
    default categories and the default admin user if missing.
    """
    # Import models so SQLAlchemy knows about them before create_all
    from app.models import models as _  # noqa: F401

    async with async_engine.begin() as conn:
        # Enable WAL mode for high-concurrency (FastAPI reads while Celery writes)
        await conn.execute(text("PRAGMA journal_mode=WAL;"))
        await conn.run_sync(Base.metadata.create_all)
    logger.info("[DB] All tables verified / created (WAL Mode)")

    await _seed_defaults()


async def _seed_defaults():
    """Insert default categories, admin user, and Peoples Feedback source if DB is fresh."""
    from app.models.models import Category, AdminUser, NewsSource
    from app.services.auth_service import hash_password
    from sqlalchemy import select, text

    async with AsyncSessionLocal() as db:
        # ── Enable pg_trgm for similarity search (if PostgreSQL) ───────
        if "postgresql" in settings.DATABASE_URL:
            try:
                await db.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
                await db.commit()
            except Exception:
                await db.rollback()

        # ── Default categories ────────────────────────────────────────
        existing_cats = (await db.execute(select(Category))).scalars().all()
        if not existing_cats:
            for name in settings.CATEGORIES:
                slug = name.lower().replace(" ", "-")
                db.add(Category(name=name, slug=slug, description=f"{name} news"))
            await db.commit()
            logger.info(
                f"[DB] Seeded {len(settings.CATEGORIES)} default categories: "
                f"{', '.join(settings.CATEGORIES)}"
            )

        # ── Default admin user ────────────────────────────────────────
        existing_admin = (
            await db.execute(
                select(AdminUser).where(AdminUser.username == "admin")
            )
        ).scalar_one_or_none()
        if not existing_admin:
            db.add(AdminUser(
                username="admin",
                password_hash=hash_password("admin123"),
                role="admin",
                email="admin@newsplatform.local",
                is_active=True,
            ))
            await db.commit()
            logger.info(
                "[DB] Default admin user created — username: admin, password: admin123"
                " — CHANGE THIS IN PRODUCTION!"
            )

        # ── Default "Peoples Feedback" source ─────────────────────────
        from sqlalchemy import or_
        existing_pf = (
            await db.execute(
                select(NewsSource).where(
                    or_(
                        NewsSource.name.ilike("Peoples Feedback"),
                        NewsSource.name.ilike("PeoplesFeedback"),
                    )
                )
            )
        ).scalar_one_or_none()
        if not existing_pf:
            db.add(NewsSource(
                name="Peoples Feedback",
                url="https://www.peoples-feedback.com",
                language="en",
                scraper_type="manual",
                is_enabled=True,
                is_paused=False,
                credibility_score=1.0,
                priority=10,
            ))
            await db.commit()
            logger.info("[DB] Default 'Peoples Feedback' source created")

        # ── Default scraped sources — ALL registered scrapers ─────────
        default_sources = [
            # ── English / International ──
            {
                "name": "Times of India",
                "url": "https://timesofindia.indiatimes.com",
                "language": "en",
                "scraper_type": "timesofindia",
                "is_enabled": True,
                "credibility_score": 0.85,
                "priority": 8,
                "scraper_config": {"max_articles": 50},
            },
            {
                "name": "Al Jazeera",
                "url": "https://www.aljazeera.com",
                "language": "en",
                "scraper_type": "aljazeera",
                "is_enabled": True,
                "credibility_score": 0.8,
                "priority": 7,
                "scraper_config": {"max_articles": 40},
            },
            {
                "name": "OneIndia English",
                "url": "https://www.oneindia.com",
                "language": "en",
                "scraper_type": "oneindia english",
                "is_enabled": True,
                "credibility_score": 0.7,
                "priority": 6,
                "scraper_config": {"max_articles": 40, "fetch_full_content": True},
            },
            # ── Telugu / Regional ──
            {
                "name": "GreatAndhra",
                "url": "https://www.greatandhra.com",
                "language": "en",
                "scraper_type": "greatandhra",
                "is_enabled": True,
                "credibility_score": 0.7,
                "priority": 6,
                "scraper_config": {"max_articles": 60, "fetch_full_content": True, "request_delay": 0.8},
            },
            {
                "name": "Eenadu",
                "url": "https://www.eenadu.net",
                "language": "te",
                "scraper_type": "eenadu",
                "is_enabled": True,
                "credibility_score": 0.8,
                "priority": 7,
                "scraper_config": {"max_articles": 50},
            },
            {
                "name": "Sakshi",
                "url": "https://www.sakshi.com",
                "language": "te",
                "scraper_type": "sakshi",
                "is_enabled": True,
                "credibility_score": 0.8,
                "priority": 7,
                "scraper_config": {"max_articles": 50},
            },
            {
                "name": "TV9 Telugu",
                "url": "https://www.tv9telugu.com",
                "language": "te",
                "scraper_type": "tv9 telugu",
                "is_enabled": True,
                "credibility_score": 0.75,
                "priority": 6,
                "scraper_config": {"max_articles": 40},
            },
            {
                "name": "OneIndia Telugu",
                "url": "https://telugu.oneindia.com",
                "language": "te",
                "scraper_type": "oneindia telugu",
                "is_enabled": True,
                "credibility_score": 0.7,
                "priority": 5,
                "scraper_config": {"max_articles": 40, "fetch_full_content": True},
            },
            {
                "name": "PrabhaNews",
                "url": "https://www.prabhanews.com",
                "language": "te",
                "scraper_type": "prabhanews",
                "is_enabled": True,
                "credibility_score": 0.65,
                "priority": 5,
                "scraper_config": {"max_articles": 30},
            },
            {
                "name": "Telugu123",
                "url": "https://www.telugu123.com",
                "language": "te",
                "scraper_type": "telugu123",
                "is_enabled": True,
                "credibility_score": 0.6,
                "priority": 4,
                "scraper_config": {"max_articles": 30},
            },
            {
                "name": "TeluguTimes Telugu",
                "url": "https://www.telugutimes.net",
                "language": "te",
                "scraper_type": "telugutimes telugu",
                "is_enabled": True,
                "credibility_score": 0.6,
                "priority": 4,
                "scraper_config": {"max_articles": 30},
            },
        ]
        for src_data in default_sources:
            existing = (
                await db.execute(
                    select(NewsSource).where(NewsSource.name == src_data["name"])
                )
            ).scalar_one_or_none()
            if not existing:
                db.add(NewsSource(
                    name=src_data["name"],
                    url=src_data["url"],
                    language=src_data["language"],
                    scraper_type=src_data["scraper_type"],
                    is_enabled=src_data["is_enabled"],
                    is_paused=False,
                    credibility_score=src_data["credibility_score"],
                    priority=src_data["priority"],
                    scraper_config=src_data.get("scraper_config", {}),
                ))
                logger.info(f"[DB] Seeded source: {src_data['name']}")
        await db.commit()
