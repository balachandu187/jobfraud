#!/usr/bin/env bash
# JobShield AI — one-command local startup (macOS / Linux / Git Bash / WSL).
#
#   ./run.sh            build the React UI if needed, then serve everything on :8000
#   ./run.sh --no-build skip the frontend build step
#   ./run.sh --reload   enable uvicorn auto-reload for backend development
#
# Serves the FastAPI backend and the compiled React app from a single port, so the
# UI and API share an origin and no proxy is required in production.
set -euo pipefail

cd "$(dirname "$0")"

PORT="${JOBSHIELD_PORT:-8000}"
HOST="${JOBSHIELD_HOST:-0.0.0.0}"
BUILD=1
RELOAD=0

for arg in "$@"; do
  case "$arg" in
    --no-build) BUILD=0 ;;
    --reload)   RELOAD=1 ;;
    -h|--help)  sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

PYTHON="${PYTHON:-python3}"
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON=python

echo "[1/4] Checking Python dependencies..."
if ! "$PYTHON" -c "import fastapi, sklearn, pandas, bs4" >/dev/null 2>&1; then
  echo "      Installing from requirements.txt (this runs once)..."
  "$PYTHON" -m pip install -q -r requirements.txt
fi

echo "[2/4] Checking trained model artifacts..."
if [ ! -f saved_models/model.pkl ] || [ ! -f saved_models/tfidf_vectorizer.pkl ]; then
  echo "      Artifacts missing — generating dataset and training..."
  "$PYTHON" data/create_dataset.py
  "$PYTHON" model/train_model.py
fi

if [ "$BUILD" -eq 1 ]; then
  echo "[3/4] Building the React UI..."
  if command -v npm >/dev/null 2>&1; then
    ( cd frontend && { [ -d node_modules ] || npm install --silent; } && npm run build --silent )
  else
    echo "      npm not found — skipping. The API will still run; install Node.js for the UI."
  fi
else
  echo "[3/4] Skipping frontend build (--no-build)."
fi

echo "[4/4] Starting JobShield AI on http://localhost:${PORT}"
echo "      API docs: http://localhost:${PORT}/docs"
export JOBSHIELD_RELOAD="$RELOAD"
exec "$PYTHON" api.py
