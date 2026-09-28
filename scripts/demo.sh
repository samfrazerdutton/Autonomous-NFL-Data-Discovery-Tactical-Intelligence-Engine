#!/usr/bin/env bash
# One-command GRIDSTATE demo: ingest the committed sample data, build the state
# graph, run the discovery engine, then start the API and frontend dev server.
# Works under WSL, Linux, macOS, and git-bash on Windows.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== GRIDSTATE demo =="

cd backend
if [ ! -d .venv ]; then
  echo "Creating virtualenv..."
  python -m venv .venv
fi

if [ -f .venv/Scripts/python.exe ]; then
  VENV_PY=.venv/Scripts/python.exe   # Windows venv layout (native Windows Python, incl. under git-bash)
else
  VENV_PY=.venv/bin/python           # POSIX venv layout
fi

echo "Installing backend dependencies..."
"$VENV_PY" -m pip install --quiet --upgrade pip
"$VENV_PY" -m pip install --quiet -r requirements.txt

echo "Running ingestion + state graph + discovery engine (uses the committed"
echo "DEMO sample unless backend/data/raw/pbp_<season>.parquet already exists)..."
"$VENV_PY" scripts/run_pipeline.py 2022 2023

echo "Starting API on http://localhost:8000 ..."
"$VENV_PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!

cd ../frontend
if [ ! -d node_modules ]; then
  echo "Installing frontend dependencies..."
  npm install
fi

echo "Starting frontend on http://localhost:5173 ..."
npm run dev -- --port 5173 &
FRONTEND_PID=$!

cleanup() {
  echo ""
  echo "Stopping GRIDSTATE..."
  kill "$API_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo ""
echo "GRIDSTATE is running:"
echo "  API:      http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both."
wait
