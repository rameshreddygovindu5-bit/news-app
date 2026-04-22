#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# News Platform v3.1.0 — Full Deployment & Service Manager
# Starts all services, waits for health, triggers pipeline
# ═══════════════════════════════════════════════════════════════
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/news-platform-final/backend"
ADMIN="$ROOT/news-platform-final/frontend"
CLIENT="$ROOT/peoples-feedback-client"
LOGS="$ROOT/logs"
mkdir -p "$LOGS"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; }

# ── Stop existing processes ─────────────────────────────────────
log "Stopping existing processes on ports 8005, 3003, 5174..."
for PORT in 8005 3003 5174; do
  PID=$(lsof -ti tcp:$PORT 2>/dev/null || true)
  [ -n "$PID" ] && kill -9 $PID 2>/dev/null || true
done
sleep 1

# ── Reset stuck articles before starting ───────────────────────
log "Resetting stuck articles..."
cd "$BACKEND"
python3 -c "
import sqlite3
conn = sqlite3.connect('newsagg.db')
cur = conn.cursor()
cur.execute(\"UPDATE news_articles SET ai_status=\'pending\', ai_error_count=0 WHERE ai_status IN (\'processing\',\'failed\')\" )
conn.commit()
n = cur.rowcount
conn.close()
print(f\"Reset {n} articles\" if n else \"No stuck articles\")
" 2>/dev/null || true

# ── Backend ─────────────────────────────────────────────────────
log "Starting Backend API on :8005..."
cd "$BACKEND"
[ -f venv/bin/activate ] || python3 -m venv venv
source venv/bin/activate 2>/dev/null || true
pip install -q -r requirements.txt --quiet 2>/dev/null || true
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8005 --workers 1 \
  > "$LOGS/backend.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$LOGS/backend.pid"

# Wait for backend
log "Waiting for backend health check..."
for i in $(seq 1 40); do
  curl -sf http://localhost:8005/health > /dev/null 2>&1 && { log "✅ Backend ready (${i}s)"; break; }
  sleep 1
  [ $i -eq 40 ] && { warn "Backend health check timeout — check $LOGS/backend.log"; }
done

# ── Admin Dashboard ─────────────────────────────────────────────
log "Starting Admin Dashboard on :3003..."
cd "$ADMIN"
[ -d node_modules ] || npm install --silent
PORT=3003 nohup npm start > "$LOGS/admin.log" 2>&1 &
ADMIN_PID=$!
echo $ADMIN_PID > "$LOGS/admin.pid"

# ── Public Client ───────────────────────────────────────────────
log "Starting Public News Client on :5174..."
cd "$CLIENT"
[ -d node_modules ] || npm install --silent
nohup npm run dev -- --port 5174 --host > "$LOGS/client.log" 2>&1 &
CLIENT_PID=$!
echo $CLIENT_PID > "$LOGS/client.pid"

# ── Trigger pipeline ────────────────────────────────────────────
log "Triggering immediate pipeline: Scrape → AI → Rank → Sync..."
sleep 5
curl -sf -X POST http://localhost:8005/api/scheduler/trigger \
  -H "Content-Type: application/json" -d '{"job":"full_pipeline"}' > /dev/null 2>&1 \
  && log "✅ Pipeline triggered" || warn "Manual pipeline trigger failed (auto-start will handle it)"

# ── Summary ─────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  News Platform v3.1.0 — All Services Up      ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Backend API:     http://localhost:8005       ║${NC}"
echo -e "${GREEN}║  Admin UI:        http://localhost:3003       ║${NC}"
echo -e "${GREEN}║  Public Client:   http://localhost:5174       ║${NC}"
echo -e "${GREEN}║  Health:          http://localhost:8005/health║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Logs: $LOGS  ${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
log "PIDs — Backend:$BACKEND_PID  Admin:$ADMIN_PID  Client:$CLIENT_PID"
log "To stop: bash stop_all.sh"
