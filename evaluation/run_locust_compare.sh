#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.loadtest.yml --profile load-test)
LOCUST_BIN="${LOCUST_BIN:-locust}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker Compose CLI is required on a Docker-capable host." >&2
  exit 2
fi
if ! command -v "$LOCUST_BIN" >/dev/null 2>&1; then
  echo "Locust is missing. Install the optional dependency with: python -m pip install -r requirements-loadtest.txt" >&2
  exit 2
fi

mkdir -p evaluation/artifacts
run_profile() {
  local workers="$1"
  local label="$2"
  "${COMPOSE[@]}" up -d --build --wait --scale "agent-worker=$workers"
  "${COMPOSE[@]}" ps
  "$LOCUST_BIN" -f evaluation/locustfile.py --host http://127.0.0.1:8000 \
    --headless -u "${BPC_LOCUST_USERS:-10}" -r "${BPC_LOCUST_SPAWN_RATE:-2}" \
    --run-time "${BPC_LOCUST_DURATION:-2m}" --csv "evaluation/artifacts/${label}"
}

run_profile 1 one-worker
run_profile 3 three-workers
echo "Raw Locust CSVs are under evaluation/artifacts/. Compare custom WORKFLOW p50/p95, RPS and failures; do not treat stub tokens/cost as provider measurements."
