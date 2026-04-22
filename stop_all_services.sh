#!/bin/bash
echo "Stopping all News Platform services..."
for PORT in 8005 3003 5174; do
  PID=$(lsof -ti tcp:$PORT 2>/dev/null || true)
  if [ -n "$PID" ]; then
    kill -9 $PID 2>/dev/null || true
    echo "  Stopped port $PORT (PID $PID)"
  fi
done
echo "All services stopped."
