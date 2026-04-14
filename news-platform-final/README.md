# News Aggregation Platform — v2.1.0

AI-powered news aggregation: scrape → translate → AI-rephrase → categorise → sync to AWS.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  ADMIN UI (React)          port 3000                                │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │  Dashboard  │  │   Articles   │  │  Scheduler   │  …            │
│  └─────────────┘  └──────────────┘  └──────────────┘               │
└────────────────────────────┬────────────────────────────────────────┘
                             │ REST / JSON
┌────────────────────────────▼────────────────────────────────────────┐
│  FastAPI Backend           port 8005                                │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │  /api/      │  │  /api/       │  │  /api/       │               │
│  │  articles   │  │  scheduler   │  │  sources     │  …            │
│  └─────────────┘  └──────────────┘  └──────────────┘               │
└──────┬──────────────────────────────────────────┬───────────────────┘
       │ SQLAlchemy async                          │ Celery tasks
       ▼                                           ▼
┌──────────────┐   ┌───────────────────────────────────────────────────┐
│  PostgreSQL  │   │  Celery Worker + Beat (Redis broker)               │
│  (local/RDS) │   │                                                    │
└──────────────┘   │  Every 30 min:  ① Scrape all sources              │
                   │  +5 min:        ② AI enrich (rephrase+categorise) │
                   │  +10 min:       ③ Rank top-100                    │
                   │  +15 min:       ④ Sync delta → AWS PostgreSQL     │
                   │  +20 min:       ⑤ Update category counts          │
                   │  +25 min:       ⑥ Soft-delete articles > 15 days  │
                   └───────────────────────────────────────────────────┘
```

---

## Quick Start (Docker Compose)

```bash
# 1. Clone / extract the project
cd news-platform-fixed

# 2. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env — set DB credentials, AI API keys, AWS creds

# 3. Start all services
docker compose up -d

# 4. Watch logs
docker compose logs -f backend celery_worker celery_beat
```

Open **http://localhost:3000** → login as `admin / admin123`.

---

## Manual / Local Development

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate    # Linux/Mac
# venv\Scripts\activate                             # Windows

pip install -r requirements.txt

# Start FastAPI (dev)
uvicorn app.main:app --reload --port 8005

# Start Celery worker (separate terminal)
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4

# Start Celery beat (separate terminal)
celery -A app.tasks.celery_app beat --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
REACT_APP_API_URL=http://127.0.0.1:8005 npm start
```

---

## Manual Pipeline Triggers

Run individual pipeline steps from the command line:

```bash
cd backend
python -m app.tasks.celery_app --run        # Full pipeline
python -m app.tasks.celery_app --scrape     # Scrape only
python -m app.tasks.celery_app --ai         # AI enrichment only
python -m app.tasks.celery_app --rank       # Top-100 ranking only
python -m app.tasks.celery_app --aws        # AWS sync only
python -m app.tasks.celery_app --social     # Social posting only
python -m app.tasks.celery_app --cleanup    # Cleanup only
```

Or via the Admin UI → **Scheduler** page → click any trigger button.

---

## Pipeline Flow

```
Scraper (GreatAndhra / CNN / Eenadu / …)
   │
   ▼  raw article saved  flag=A  ai_status=pending
AI Service (Gemini → OpenAI → fallback)
   │  rewrite title + content in English
   │  classify → canonical category
   │  generate tags + SEO slug
   ▼  flag=A  ai_status=completed
Top-100 Ranker
   │  score = (priority×15) + (credibility×25) + recency_decay
   │  pick top 100 with category diversity
   ▼  flag=Y  (top news)
AWS Sync
   │  delta upsert: categories → sources → articles
   ▼  AWS production DB updated
Social Poster (optional)
   │  post Y-flag articles to FB / X / IG / WhatsApp
   ▼  is_posted_* = True
```

---

## Category System

Canonical list (backend ↔ frontend ↔ AWS must all match):

| Category      | Example sources              |
|---------------|------------------------------|
| Home          | Breaking / local / crime     |
| World         | International news           |
| Politics      | Government / elections       |
| Business      | Economy / finance / markets  |
| Tech          | Technology / AI / gadgets    |
| Health        | Medical / wellness           |
| Science       | Research / space / climate   |
| Entertainment | Movies / music / celebrity   |
| Events        | Festivals / events           |
| Sports        | Cricket / football / IPL     |

To add a new category: update **all three** locations:
1. `backend/app/config.py` → `Settings.CATEGORIES`
2. `backend/app/services/category_service.py` → `CANONICAL_CATEGORIES`
3. `frontend/src/App.js` → `const CATS`

---

## Article Flag States

| Flag | Meaning                          | Set by              |
|------|----------------------------------|---------------------|
| `P`  | Pending reporter approval        | Reporter submit      |
| `N`  | New / just scraped               | Scraper              |
| `A`  | AI processed                     | AI worker            |
| `Y`  | Top 100 (live on client site)    | Ranking task         |
| `D`  | Soft-deleted (> 15 days old)     | Cleanup task         |

---

## Scheduler Configuration

All intervals configurable from the Admin UI (**Scheduler** page) or via `.env`:

| Setting                      | Default  | Description                        |
|------------------------------|----------|------------------------------------|
| `SCHEDULE_SCRAPE_MINUTES`    | `0,30`   | Scrape at :00 and :30 every hour   |
| `SCHEDULE_AI_MINUTES`        | `5,35`   | AI enrich 5 min after scrape       |
| `SCHEDULE_RANKING_MINUTES`   | `10,40`  | Rank 5 min after AI                |
| `SCHEDULE_AWS_SYNC_MINUTES`  | `15,45`  | Sync 5 min after rank              |
| `SCHEDULE_CATEGORY_MINUTES`  | `20,50`  | Category counts maintenance        |
| `SCHEDULE_CLEANUP_MINUTES`   | `25,55`  | Soft-delete old articles           |

Each job can be independently enabled/disabled from the UI without restart.

---

## AWS Deployment

### Prerequisites
- AWS EC2 (or any Linux host) with Docker + Docker Compose
- AWS RDS PostgreSQL (or self-managed PostgreSQL on EC2)
- Security group: allow inbound 8005 (backend), 3000 (frontend), 5432 (DB)

### Steps

```bash
# On your server
git clone <your-repo> news-platform
cd news-platform

# Configure environment
cp backend/.env.example backend/.env
nano backend/.env
# Set:
#   DATABASE_URL  →  your RDS endpoint
#   AWS_DB_*      →  production DB for sync
#   GEMINI_API_KEY / OPENAI_API_KEY
#   SECRET_KEY    →  strong random string

# Set REACT_APP_API_URL to your server's public IP/domain
export REACT_APP_API_URL=http://YOUR_SERVER_IP:8005

docker compose up -d --build
docker compose ps     # verify all services healthy
```

### Nginx Reverse Proxy (recommended for production)

```nginx
server {
    listen 80;
    server_name admin.yourdomain.com;

    location /api/ {
        proxy_pass http://localhost:8005;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
    }
}
```

---

## Scraper Notes

### CNN Scraper
- Scrapes 12 sections: homepage, world, politics, us, health, tech, business, entertainment, style, travel, science, sport
- Two-phase: collect links → fetch articles sequentially (0.8s delay between requests)
- Full article content extraction via CNN DOM selectors
- Retry with exponential backoff (2 retries default)
- Config keys: `max_articles`, `section_max_pages`, `request_delay`, `fetch_full_content`

### GreatAndhra Scraper
- English: `https://www.greatandhra.com`
- Telugu: `https://telugu.greatandhra.com`
- Deep-paginates `/latest` (primary) + supplementary sections
- Sequential fetching to avoid server 403 blocks

To add a scraper, create `backend/app/scrapers/your_scraper.py`, subclass `BaseScraper`, implement `scrape()`, and call `ScraperFactory.register("name", YourScraper)`.

---

## Troubleshooting

**Celery tasks not running**
```bash
docker compose logs celery_worker celery_beat
# Check Redis is reachable
docker compose exec celery_worker celery -A app.tasks.celery_app inspect active
```

**AWS sync failing**
```bash
# Check credentials in .env
# Verify AWS DB host is reachable from your server
docker compose exec backend python -c "import psycopg2; psycopg2.connect(host='YOUR_AWS_HOST', ...)"
```

**AI enrichment failing**
- Check `GEMINI_API_KEY` or `OPENAI_API_KEY` is set in `.env`
- Check `AI_PROVIDER_CHAIN` order in `.env`
- View logs: `docker compose logs celery_worker | grep "\[AI\]"`

**Category mismatch**
- Ensure `config.py CATEGORIES`, `category_service.py CANONICAL_CATEGORIES`, and `App.js CATS` all contain the same values
