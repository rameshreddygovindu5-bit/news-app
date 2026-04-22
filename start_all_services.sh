#!/bin/bash
# ─────────────────────────────────────────────────────────────
# News Platform v3.0 — Start All Services
# Backend API: port 8005
# Admin Dashboard: port 3003  
# Public News Client: port 5174
# ─────────────────────────────────────────────────────────────
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/news-platform-final/backend"
ADMIN="$ROOT/news-platform-final/frontend"
CLIENT="$ROOT/peoples-feedback-client"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

echo "╔════════════════════════════════════════════════╗"
echo "║   News Platform v3.0 — Service Startup         ║"
echo "╚════════════════════════════════════════════════╝"

# ── 1. Kill any existing processes on these ports ──────────────
for PORT in 8005 3003 5174; do
  PID=$(lsof -ti tcp:$PORT 2>/dev/null || true)
  if [ -n "$PID" ]; then
    echo "  Killing existing process on port $PORT (PID $PID)"
    kill -9 $PID 2>/dev/null || true
    sleep 0.5
  fi
done

# ── 2. Backend API — FastAPI on port 8005 ─────────────────────
echo ""
echo "▶ Starting Backend API on port 8005..."
cd "$BACKEND"
if [ ! -d "venv" ]; then
  python3 -m venv venv
  venv/bin/pip install -q -r requirements.txt
fi
nohup venv/bin/uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8005 \
  --workers 1 \
  --loop asyncio \
  > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID  →  http://localhost:8005"
echo "  Logs: $LOG_DIR/backend.log"

# ── 3. Wait for backend to be ready ───────────────────────────
echo ""
echo "  Waiting for backend to be ready..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8005/health > /dev/null 2>&1; then
    echo "  ✅ Backend ready (${i}s)"
    break
  fi
  sleep 1
  if [ $i -eq 30 ]; then
    echo "  ⚠ Backend not ready after 30s — check logs: $LOG_DIR/backend.log"
  fi
done

# ── 4. Admin Dashboard — CRA on port 3003 ─────────────────────
echo ""
echo "▶ Starting Admin Dashboard on port 3003..."
cd "$ADMIN"
if [ ! -d "node_modules" ]; then
  echo "  Installing admin dependencies..."
  npm install --silent
fi
PORT=3003 nohup npm start > "$LOG_DIR/admin.log" 2>&1 &
ADMIN_PID=$!
echo "  Admin PID: $ADMIN_PID  →  http://localhost:3003"
echo "  Logs: $LOG_DIR/admin.log"

# ── 5. Public News Client — Vite on port 5174 ─────────────────
echo ""
echo "▶ Starting Public News Client on port 5174..."
cd "$CLIENT"
if [ ! -d "node_modules" ]; then
  echo "  Installing client dependencies..."
  npm install --silent
fi
nohup npm run dev -- --port 5174 --host > "$LOG_DIR/client.log" 2>&1 &
CLIENT_PID=$!
echo "  Client PID: $CLIENT_PID  →  http://localhost:5174"
echo "  Logs: $LOG_DIR/client.log"

# ── 6. Trigger immediate full pipeline ────────────────────────
echo ""
echo "▶ Triggering immediate pipeline: Scrape → AI → Rank → Sync"
sleep 3  # brief wait for backend to fully initialize
curl -sf -X POST http://localhost:8005/api/scheduler/trigger \
  -H "Content-Type: application/json" \
  -d '{"job":"full_pipeline"}' > /dev/null 2>&1 \
  && echo "  ✅ Pipeline triggered" \
  || echo "  ⚠ Pipeline trigger failed — scheduler will auto-start on backend startup"

# ── 7. Summary ────────────────────────────────────────────────
echo ""
echo "╔════════════════════════════════════════════════╗"
echo "║  All Services Running                          ║"
echo "╠════════════════════════════════════════════════╣"
echo "║  Backend API:      http://localhost:8005       ║"
echo "║  Admin Dashboard:  http://localhost:3003       ║"
echo "║  Public Client:    http://localhost:5174       ║"
echo "║  Health Check:     http://localhost:8005/health║"
echo "╠════════════════════════════════════════════════╣"
echo "║  Logs: $LOG_DIR"
echo "╚════════════════════════════════════════════════╝"
echo ""
echo "PIDs: Backend=$BACKEND_PID Admin=$ADMIN_PID Client=$CLIENT_PID"
echo "To stop all: kill $BACKEND_PID $ADMIN_PID $CLIENT_PID"
