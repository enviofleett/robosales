#!/bin/bash
cd "$(dirname "$0")"

# Kill any existing server on port 8000
pkill -f "uvicorn server.main:app" 2>/dev/null || true
sleep 1

echo "=========================================================="
echo " Starting Harvey Cloud SaaS Dashboard on port 8000...     "
echo " Open http://localhost:8000 or http://127.0.0.1:8000      "
echo "=========================================================="

exec ./.venv/bin/uvicorn server.main:app --host 127.0.0.1 --port 8000
