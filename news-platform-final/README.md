# News Aggregation Platform + Peoples Feedback Client

AI-powered news aggregation platform with automated scraping, AI rephrasing (English + Telugu),
ranking, AWS sync, and social media posting.

## Architecture

```
news-platform-final/
├── backend/                  # FastAPI + SQLAlchemy + APScheduler
│   ├── app/
│   │   ├── api/              # REST endpoints (articles, auth, scheduler, youtube, polls, etc.)
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── scrapers/         # Source-specific scrapers (CNN, Telugu news, etc.)
│   │   ├── services/         # AI service, auth, category, social, youtube
│   │   └── tasks/            # Celery tasks + in-process scheduler
│   ├── manage.py             # CLI management tool
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                 # React CRA — Admin UI
│   ├── src/App.js            # Single-file admin dashboard
│   ├── src/services/api.js   # Admin API client
│   └── Dockerfile            # Production nginx build
├── peoples-feedback-client/  # Vite + React + TypeScript — Public news site
│   ├── src/pages/            # Home, News, NewsDetail, Telugu
│   ├── src/components/news/  # PremiumHeader, NewsLayout, ShareMenu, etc.
│   ├── src/lib/api.ts        # Public API client
│   └── src/types/news.ts     # Shared types + display helpers
├── docker-compose.yml        # Full stack (backend + redis + frontend)
└── update-nginx.sh           # EC2 nginx config script
```

## Quick Start (Local Development)

### Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # Edit with your DB and API keys
python manage.py init-db
uvicorn app.main:app --port 8005 --reload
```

### Admin Frontend
```bash
cd frontend
npm install
npm start  # Opens on http://localhost:3000
```
Default login: `admin` / `admin123`

### Peoples Feedback Client
```bash
cd peoples-feedback-client
npm install
npm run dev  # Opens on http://localhost:5173
```

### Docker Compose (Full Stack)
```bash
docker-compose up --build
```

## AWS EC2 Deployment

1. Start the backend on EC2 (port 8005)
2. Build and deploy peoples-feedback-client:
   ```bash
   cd peoples-feedback-client && npm run build
   # Copy dist/ to /var/www/peoples-feedback/ on EC2
   ```
3. Run nginx setup:
   ```bash
   sudo bash update-nginx.sh
   ```

## Pipeline Flow

```
Scrape → AI Rephrase (P1→P4 chain) → Ranking → AWS Sync → Social Posting
```

### AI Provider Chain
| Priority | Provider | Notes |
|----------|----------|-------|
| P1 | Gemini PRIMARY | Main AI provider |
| P2 | Gemini SECONDARY | Backup Gemini key |
| P3 | OpenAI GPT-4o-mini | Fallback |
| P4 | Ollama (local) | Offline fallback |
| Last | Original (cleaned) | Source names removed, paragraphs preserved |

### Article Flags
- `P` — Pending approval (reporter submissions)
- `N` — New (approved, awaiting AI)
- `A` — AI processed
- `Y` — Top News (ranked, visible on public site)
- `D` — Deleted (soft)

## Key Fixes Applied

1. **Mobile responsive** — Improved header, cards, and typography for mobile browsers
2. **Load More button** — Fixed click handler with explicit event handling
3. **Mobile menu** — Horizontal scrollable pill bar replaces dropdowns on mobile
4. **AI Rephrase** — Source name removal, paragraph preservation, copyright-safe output
5. **Empty menu hiding** — Categories with 0 articles are hidden from navigation
6. **Code consolidation** — Removed duplicate files, standalone scripts, build artifacts
7. **S3 cleanup** — Confirmed no S3 code present (EC2-only deployment)
8. **Admin UI AWS** — Production Dockerfile with nginx SPA routing + API proxy
9. **Category images** — Full category-specific placeholder image mapping
10. **Image overlay** — Tricolor gradient overlay for copyright differentiation
11. **YouTube workflow** — Fixed save to include Telugu, flag=Y, proper slug
12. **General improvements** — ai_status in responses, mobile-first design, error handling
