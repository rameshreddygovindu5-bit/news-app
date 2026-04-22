#!/bin/bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Stopping all News Platform services..."
for PORT in 8005 3003 5174; do
  PID=$(lsof -ti tcp:$PORT 2>/dev/null || true)
  [ -n "$PID" ] && { kill -9 $PID 2>/dev/null; echo "  Stopped port $PORT (PID $PID)"; } || echo "  Port $PORT: not running"
done
echo "All services stopped."
