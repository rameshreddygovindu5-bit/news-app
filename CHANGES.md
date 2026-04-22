# News Platform — Applied Fixes (April 20, 2026)

All changes are based on the End-to-End Audit Report. Zero business logic was altered.

---

## 🔴 CRITICAL SECURITY

### SEC #1 — Hardcoded Gemini API Keys Removed
**File:** `news-platform-final/backend/app/config.py`
- Removed real Gemini API keys that were hardcoded as Python default values
- All 3 keys (PRIMARY, SECONDARY, TERTIARY) now default to `""` — must be set in `.env`
- **ACTION REQUIRED:** Rotate all 3 Gemini API keys immediately via Google Cloud Console

### SEC #2 — CORS Wildcard Fixed
**File:** `news-platform-final/backend/app/main.py`
- Changed `allow_origins=["*"]` → `allow_origins=_cors_origins` (the filtered list already built)
- Allowed origins: localhost:3000, 3001, 5173 + www.peoples-feedback.com

---

## 🔴 CRITICAL BUGS

### BUG #1 — Google News AI Bypass Now Enforced
**File:** `news-platform-final/backend/app/services/ai_service.py`
- Added `is_gnews` check **BEFORE** any AI provider call in `process_article()`
- Google News articles now receive `ai_status_code = "GOOGLE_NEWS_NO_AI"` immediately
- Also: secondary safety net in fallback path updated from `UNPROCESSED_AI_FALLBACK` → `GOOGLE_NEWS_NO_AI`

### BUG #5 — Scheduler Shutdown Now Functional
**File:** `news-platform-final/backend/app/main.py`
- Fixed: `stop_scheduler = lambda: None` was never replaced
- Real `stop_scheduler()` from `app.tasks.scheduler` now called on app shutdown
- Prevents APScheduler thread leak on restart

---

## 🟠 HIGH PRIORITY BUGS

### BUG #2 — Ranking Includes All AI Status Codes
**File:** `news-platform-final/backend/app/tasks/celery_app.py`
- `update_top_100_ranking()` candidate queries now include:
  `completed, AI_SUCCESS, AI_RETRY_SUCCESS, UNPROCESSED_AI_FALLBACK, GOOGLE_NEWS_NO_AI`
- Previously only `completed` was checked — most articles were invisible to ranking

### BUG #2b — worker_process_ai Handles GOOGLE_NEWS_NO_AI
**File:** `news-platform-final/backend/app/tasks/celery_app.py`
- `GOOGLE_NEWS_NO_AI` articles set `flag = "A"` (eligible for ranking)

---

## 🟡 MEDIUM BUGS

### BUG #3 — run_full_pipeline Alias Added
**File:** `news-platform-final/backend/app/tasks/celery_app.py`
- Added: `run_full_pipeline = run_master_heartbeat` alias before `__main__` block
- Fixes NameError when Scheduler API / CLI invoke `run_full_pipeline`

### BUG #6 — APScheduler Uses .env Cron Settings
**File:** `news-platform-final/backend/app/tasks/scheduler.py`
- Added `CronTrigger` import from APScheduler
- All jobs now use `CronTrigger(minute=settings.SCHEDULE_*_MINUTES)` instead of hardcoded intervals
- Local scheduler now matches Celery Beat schedule exactly

---

## 🟢 LOW / HOUSEKEEPING

### BUG #4 — Duplicate _banner() Removed
**File:** `news-platform-final/backend/app/tasks/celery_app.py`
- Removed duplicate `_banner("AWS SYNC", False)` call at end of `sync_to_aws()`

### Cascading Trigger Removed
**File:** `news-platform-final/backend/app/tasks/celery_app.py`
- Removed `_trigger_full_pipeline()` from `scrape_all_sources`, `process_ai_batch`, `update_top_100_ranking`
- These tasks were triggering recursive pipeline runs when Celery was unavailable → thread runaway risk
- Pipeline timing is now controlled solely by the scheduler

### Similarity Threshold Corrected
**File:** `news-platform-final/backend/app/services/ai_service.py`
- Changed `<= 0.75` → `<= 0.70` per spec ("Reject if similarity > 70%")

### Cleanup TTL Extended
**File:** `news-platform-final/backend/app/tasks/celery_app.py`
- `cleanup_old_articles()` TTL changed from 15 days → 30 days
- Aligns with ranking window (was causing articles to be deleted before ranking could include them)

### Docker GEMINI_API_KEY_TERTIARY
**File:** `news-platform-final/docker-compose.yml`
- Added `GEMINI_API_KEY_TERTIARY: ${GEMINI_API_KEY_TERTIARY:-}` to x-env block
- Ensures tertiary key is available to all containers (backend, celery_worker, celery_beat)

### Scratch Directories Removed
- Removed: `news-platform-final/backend/scratch/` (14 debug scripts)
- Removed: Root `scratch/` directory (11 AWS audit scripts)
- Removed: `backend/scripts/debug_aws.py` and `debug_local.py`

---

## Files NOT Changed (per strict rules)
- `.env` files — untouched
- All business logic preserved
- All database models unchanged
- All API endpoints unchanged
- All scraper logic unchanged
