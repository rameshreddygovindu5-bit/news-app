# NewsAI Platform — Setup & Deployment Guide

## Architecture

```
news-platform-final/          ← This repo
├── backend/                  ← FastAPI + Celery + AI pipeline
├── frontend/                 ← React admin dashboard (port 3000)
├── docker-compose.yml        ← Runs all services
└── ...

peoples-feedback-client/      ← Public news site (port 3001)
├── src/
│   ├── pages/Telugu.tsx      ← Native Telugu news (no Google Translate reload)
│   ├── lib/api.ts            ← Shared API client (polls, wishes, articles)
│   └── components/
└── Dockerfile
```

## Ports
| Service        | Local Port | Description           |
|----------------|------------|-----------------------|
| Backend API    | 8005       | FastAPI               |
| Admin Frontend | 3000       | React admin           |
| PF Client      | 3001       | Public news site      |
| Redis          | 6380       | Task queue            |

---

## Local Development

### 1. Clone & Configure
```bash
git clone <repo>
cd news-platform-final
cp backend/.env.example backend/.env
# Edit backend/.env — add GEMINI_API_KEY, AWS credentials etc.
```

### 2. Run with Docker Compose
```bash
# Both projects must be siblings:
# ├── news-platform-final/
# └── peoples-feedback-client/

docker compose up --build -d
```

Services start in order: Redis → Backend → Celery Worker → Celery Beat → Frontend → PF Client.

### 3. Run Backend Locally (no Docker)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload
```

### 4. Run Frontend Locally
```bash
# Admin dashboard
cd frontend
npm install && npm start       # http://localhost:3000

# Public client
cd peoples-feedback-client
npm install && npm run dev     # http://localhost:3001
```

---

## AWS EC2 Deployment

### Prerequisites
- EC2 instance (t3.medium+, Ubuntu 22.04)
- Security group: open ports 22, 80, 443, 3000, 3001, 8005
- Docker + Docker Compose installed

### Deploy
```bash
# On EC2
git pull
cd news-platform-final
docker compose pull
docker compose up --build -d
```

### Environment Variables (backend/.env)
```env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/newsagg
DATABASE_URL_SYNC=postgresql://user:pass@host:5432/newsagg
REDIS_URL=redis://redis:6379/0

# AI (at least one required)
GEMINI_API_KEY=...
OPENAI_API_KEY=...

# AWS remote DB (for sync)
AWS_DB_HOST=...
AWS_DB_PORT=5432
AWS_DB_NAME=news_db_fe
AWS_DB_USER=...
AWS_DB_PASSWORD=...

# Social (optional)
FB_PAGE_ACCESS_TOKEN=...
FB_PAGE_ID=...
SOCIAL_SITE_URL=https://www.peoples-feedback.com
```

### nginx Reverse Proxy (EC2)
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Admin dashboard
    location /admin/ {
        proxy_pass http://localhost:3000/;
    }

    # Public site
    location / {
        proxy_pass http://localhost:3001/;
    }

    # API
    location /api/ {
        proxy_pass http://localhost:8005/api/;
        proxy_read_timeout 120s;
    }
}
```

---

## Key Fixes in This Version

### ✅ Telugu Page — No More Reload Loop
`Telugu.tsx` and `TeluguDetail.tsx` previously called `window.location.reload()` to force Google Translate — causing an infinite reload cycle every time you clicked the Telugu button.

**Fixed:** Removed both `useEffect` reload blocks. The Telugu page displays native Telugu content from the database (`telugu_title` / `telugu_content` fields) — instant load, no Google Translate dependency.

### ✅ AI Reprocess Button Now Works
The purple `AI` button in the Articles table was calling `POST /api/articles/:id/reprocess` which didn't exist — every click silently returned 404.

**Fixed:** Added the endpoint. It resets `ai_status="pending"` and queues the article through the full AI pipeline (rephrase + Telugu translation + category + slug). Falls back to synchronous if Celery is unavailable. Triggers AWS sync on completion.

### ✅ Polls API Unified
`PollWidget.tsx` was using raw `fetch()` calls bypassing the shared API client and proxy config. Added `getPolls()` and `voteOnPoll()` to `newsApi`, updated PollWidget to use them.

### ✅ Articles Search Debounce
Added 500ms auto-search on keyword change + explicit Search button. Previously only triggered on Enter keypress.

### ✅ Local ↔ AWS Always in Sync
Every write operation (create, update, delete, approve, reprocess) now triggers `sync_to_aws` automatically. The background `_run_ai_and_rank` also syncs after AI completes.

### ✅ Cleanup
- Removed 13 debug/test scripts from backend root
- Removed `scratch/` folder
- Removed `google_news_service.py` (duplicate of scraper)  
- Removed all `__pycache__` directories
- Removed `newsagg.db` (SQLite dev file)

---

## Default Credentials
- Admin login: `admin` / `admin123`
- Change immediately after first login via Users page

## Pipeline Flow
```
Reporter submits (P) → Admin approves (N) → AI processes (A) → Rank selects Top 100 (Y)
                                        ↕
                               AWS sync at every step
```
