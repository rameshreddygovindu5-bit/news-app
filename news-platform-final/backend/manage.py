#!/usr/bin/env python3
"""
manage.py — News Platform Management CLI
=========================================
Replaces all one-off scripts. Run from the backend/ directory:

  python manage.py <command>

Commands:
  init-db          Create all DB tables + seed categories + default admin user
  create-admin     Interactively create a new admin user
  pulse            Run the master heartbeat (AI→Rank→Sync) - Coordinated
  deep-sync        Nuclear option: Full integrity scan & push to AWS
  scrape           Scrape all enabled sources
  ai               Run AI enrichment batch
  rank             Update Top-100 ranking
  sync             Delta-sync to AWS production DB
  cleanup          Soft-delete articles older than 15 days
  categories       Refresh category article counts
  social           Post top-ranked articles to social media
  status           Show DB counts and last job log
  legacy-pipeline  Run original fragmented pipeline
"""
import sys
import importlib

# Fix Windows encoding issues for unicode characters
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger("manage")
import importlib
ca_module = importlib.import_module("app.tasks.celery_app")


# ── init-db ───────────────────────────────────────────────────────────
async def cmd_init_db():
    from app.database import create_tables
    await create_tables()
    logger.info("[MANAGE] Database initialised successfully ✓")


# ── create-admin ──────────────────────────────────────────────────────
def cmd_create_admin():
    import getpass
    from app.database import SyncSessionLocal
    from app.models.models import AdminUser
    from app.services.auth_service import hash_password
    from sqlalchemy import select

    username = input("Username: ").strip()
    if not username:
        print("Username required"); return
    password = getpass.getpass("Password: ")
    if len(password) < 6:
        print("Password must be at least 6 characters"); return
    email = input("Email (optional): ").strip() or None

    db = SyncSessionLocal()
    try:
        existing = db.execute(
            select(AdminUser).where(AdminUser.username == username)
        ).scalar_one_or_none()
        if existing:
            print(f"User '{username}' already exists"); return
        db.add(AdminUser(
            username=username,
            password_hash=hash_password(password),
            email=email, role="admin", is_active=True,
        ))
        db.commit()
        logger.info(f"[MANAGE] Admin user '{username}' created ✓")
    finally:
        db.close()





# ── status ────────────────────────────────────────────────────────────
def cmd_status():
    from app.database import SyncSessionLocal
    from app.models.models import NewsArticle, NewsSource, JobExecutionLog, Category
    from sqlalchemy import select, func

    db = SyncSessionLocal()
    try:
        total     = db.execute(select(func.count(NewsArticle.id))).scalar() or 0
        top       = db.execute(select(func.count(NewsArticle.id)).where(NewsArticle.flag == "Y")).scalar() or 0
        pending   = db.execute(select(func.count(NewsArticle.id)).where(NewsArticle.ai_status == "pending", NewsArticle.is_duplicate == False)).scalar() or 0
        duplicate = db.execute(select(func.count(NewsArticle.id)).where(NewsArticle.ai_status == "skipped_duplicate")).scalar() or 0
        failed    = db.execute(select(func.count(NewsArticle.id)).where(NewsArticle.ai_status == "failed")).scalar() or 0
        sources   = db.execute(select(func.count(NewsSource.id)).where(NewsSource.is_enabled == True)).scalar() or 0
        cats      = db.execute(select(func.count(Category.id))).scalar() or 0
        last      = db.execute(select(JobExecutionLog).order_by(JobExecutionLog.started_at.desc()).limit(1)).scalar_one_or_none()

        bar = "-" * 48
        print(f"\n{bar}")
        print(f"  {'Articles total':<22}: {total:,}")
        print(f"  {'Top News (Y)':<22}: {top}")
        print(f"  {'AI pending (New)':<22}: {pending}")
        print(f"  {'Duplicates (Skipped)':<22}: {duplicate}")
        print(f"  {'AI failed':<22}: {failed}")
        print(f"  {'Active sources':<22}: {sources}")
        print(f"  {'Categories':<22}: {cats}")
        if last:
            print(f"  {'Last job':<22}: {last.job_name} [{last.status}]")
            print(f"  {'  started':<22}: {last.started_at}")
        print(f"{bar}\n")
    finally:
        db.close()


# ── Command dispatch ──────────────────────────────────────────────────
COMMANDS = {
    "init-db":      lambda: asyncio.run(cmd_init_db()),
    "create-admin": cmd_create_admin,
    "pulse":        lambda: ca_module.run_master_heartbeat(),
    "deep-sync":    lambda: ca_module.full_integrity_sync(),
    "scrape":       lambda: ca_module.scrape_all_sources(),
    "ai":           lambda: ca_module.process_ai_batch(),
    "rank":         lambda: ca_module.update_top_100_ranking(),
    "sync":         lambda: ca_module.sync_to_aws(),
    "cleanup":      lambda: ca_module.cleanup_old_articles(),
    "categories":   lambda: ca_module.update_category_counts(),
    "social":       lambda: ca_module.post_to_social(),
    "status":       cmd_status,
    "legacy-pipeline": lambda: ca_module.run_full_pipeline(),
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        print("Available commands: " + ", ".join(COMMANDS))
        sys.exit(1 if len(sys.argv) > 1 else 0)
    COMMANDS[sys.argv[1]]()
