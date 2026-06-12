#!/usr/bin/env bash
# Start the backend (FastAPI) and frontend (Vite) together for local development.
# Ctrl-C stops both. Run from anywhere: ./dev.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Kill both child processes when this script exits (Ctrl-C included).
cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT

echo "→ backend  http://localhost:8000  (docs at /docs)"
( cd "$ROOT/backend" && .venv/bin/uvicorn app.main:app --reload --port 8000 ) &

echo "→ frontend http://localhost:5173"
( cd "$ROOT/frontend" && npm run dev ) &

wait
