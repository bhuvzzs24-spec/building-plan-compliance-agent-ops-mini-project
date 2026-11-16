#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REQUIRED_IMPORTS='import fastapi, uvicorn, pydantic, langgraph, chromadb, pypdf'
PYTHON_BIN=""

dependency_check() {
  "$1" -c "$REQUIRED_IMPORTS" >/dev/null 2>&1
}

# Prefer the active developer Python, then a fully provisioned project venv.
if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python" ] && dependency_check "$VIRTUAL_ENV/bin/python"; then
  PYTHON_BIN="$VIRTUAL_ENV/bin/python"
elif command -v python3 >/dev/null 2>&1 && dependency_check "$(command -v python3)"; then
  PYTHON_BIN="$(command -v python3)"
elif [ -x "$ROOT_DIR/.venv/bin/python" ] && dependency_check "$ROOT_DIR/.venv/bin/python"; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
fi

if [ -z "$PYTHON_BIN" ]; then
  echo "Required local Python packages are missing (FastAPI, Uvicorn, Pydantic, LangGraph, ChromaDB, pypdf)." >&2
  if [ "${INSTALL_LOCAL_DEPS:-0}" != "1" ]; then
    echo "No package downloads were attempted. To opt in to a project-local install, rerun with INSTALL_LOCAL_DEPS=1." >&2
    echo "This creates/uses .venv and installs requirements-local.txt; it does not modify other virtual environments." >&2
    exit 2
  fi
  if [ ! -x "$ROOT_DIR/.venv/bin/python" ]; then
    python3 -m venv "$ROOT_DIR/.venv"
  fi
  "$ROOT_DIR/.venv/bin/python" -m pip install --disable-pip-version-check -r requirements-local.txt
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
  if ! dependency_check "$PYTHON_BIN"; then
    echo "Local dependency installation did not provide all required imports." >&2
    exit 2
  fi
fi

for port in 8000 5500; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Port $port is already in use. Stop its existing service before starting this demo." >&2
    exit 3
  fi
done

# The local mode intentionally selects the bounded in-process worker queue.
unset REDIS_URL || true
export RUN_DB_PATH="${RUN_DB_PATH:-$ROOT_DIR/data/run_state.sqlite3}"
export CHROMA_PERSIST_DIR="${CHROMA_PERSIST_DIR:-$ROOT_DIR/data/chroma_db}"
export INDEX_MANIFEST_PATH="${INDEX_MANIFEST_PATH:-$ROOT_DIR/data/index_manifest.json}"

echo "Checking/indexing the local bye-laws corpus (unchanged sources are reused)..."
"$PYTHON_BIN" -m agents.rag.index_pdfs

API_PID=""
FRONTEND_PID=""
cleanup() {
  if [ -n "$FRONTEND_PID" ]; then kill "$FRONTEND_PID" 2>/dev/null || true; fi
  if [ -n "$API_PID" ]; then kill "$API_PID" 2>/dev/null || true; fi
  if [ -n "$FRONTEND_PID" ]; then wait "$FRONTEND_PID" 2>/dev/null || true; fi
  if [ -n "$API_PID" ]; then wait "$API_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM

"$PYTHON_BIN" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!
"$PYTHON_BIN" -m http.server 5500 --bind 127.0.0.1 --directory frontend &
FRONTEND_PID=$!

ready=0
for _ in $(seq 1 40); do
  if curl --silent --fail http://localhost:8000/health/ready >/dev/null; then
    ready=1
    break
  fi
  if ! kill -0 "$API_PID" 2>/dev/null || ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    echo "A local service exited during startup; inspect the messages above." >&2
    exit 4
  fi
  sleep 0.5
done
if [ "$ready" != "1" ]; then
  echo "API readiness did not succeed at http://localhost:8000/health/ready." >&2
  exit 4
fi

echo "Local demo is ready: http://localhost:5500 (API: http://localhost:8000/docs)."
echo "Redis is disabled; POST /runs uses the bounded in-process worker pool. Press Ctrl+C to stop both servers."
wait "$API_PID"
