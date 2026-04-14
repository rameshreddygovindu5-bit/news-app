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
from sqlalchemy import create_engine
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Async engine (FastAPI routes) ─────────────────────────────────────
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ── Sync engine (Celery workers) ──────────────────────────────────────
sync_engine = create_engine(
    settings.DATABASE_URL_SYNC,
    echo=False,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
)
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
        await conn.run_sync(Base.metadata.create_all)
    logger.info("[DB] All tables verified / created")

    await _seed_defaults()


async def _seed_defaults():
    """Insert default categories, admin user, and Peoples Feedback source if DB is fresh."""
    from app.models.models import Category, AdminUser, NewsSource
    from app.services.auth_service import hash_password
    from sqlalchemy import select, text

    async with AsyncSessionLocal() as db:
        # ── Enable pg_trgm for similarity search (if PostgreSQL) ───────
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
