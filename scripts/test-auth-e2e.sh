#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
AUTH_V1_PYTHON="${AUTH_V1_PYTHON:-$ROOT_DIR/.venv_auth_v1/bin/python}"
AUTH_V2_PYTHON="${AUTH_V2_PYTHON:-$ROOT_DIR/.venv_auth_v2/bin/python}"
export AUTH_E2E_DATA_DIR
AUTH_E2E_DATA_DIR="$(mktemp -d)"
pids=()
cleanup() {
  for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
  if [[ "${KEEP_AUTH_E2E_LOGS:-0}" == 1 ]]; then
    echo "Auth test runtime: $AUTH_E2E_DATA_DIR"
  else
    rm -rf "$AUTH_E2E_DATA_DIR"
  fi
}
trap cleanup EXIT
if [[ ! -x "$AUTH_V1_PYTHON" ]]; then
  python3 -m venv "$ROOT_DIR/.venv_auth_v1"
  "$AUTH_V1_PYTHON" -m pip install -r "$ROOT_DIR/backend/requirements-web.txt"
fi
if [[ ! -x "$AUTH_V2_PYTHON" ]]; then
  python3 -m venv "$ROOT_DIR/.venv_auth_v2"
  "$AUTH_V2_PYTHON" -m pip install -r "$ROOT_DIR/backend/requirements-v2.txt"
fi
"$AUTH_V1_PYTHON" "$ROOT_DIR/backend/tests/run_auth_fixture.py" >"$AUTH_E2E_DATA_DIR/v1.log" 2>&1 &
pids+=("$!")
AUTH_SERVICE_URL=http://127.0.0.1:5103 V2_PORT=8103 V2_DATABASE_URL="sqlite+pysqlite:///$AUTH_E2E_DATA_DIR/v2.sqlite" \
  "$AUTH_V2_PYTHON" "$ROOT_DIR/backend/run_v2.py" >"$AUTH_E2E_DATA_DIR/v2.log" 2>&1 &
pids+=("$!")
for url in http://127.0.0.1:5103/api/v1/health http://127.0.0.1:8103/health; do
  ready=0
  for attempt in {1..40}; do
    if curl -fsS --max-time 2 "$url" >/dev/null; then ready=1; break; fi
    sleep 0.5
  done
  if [[ "$ready" != 1 ]]; then
    cat "$AUTH_E2E_DATA_DIR/v1.log" "$AUTH_E2E_DATA_DIR/v2.log"
    exit 1
  fi
done
cd "$ROOT_DIR/frontend"
npx playwright test --config playwright.auth.config.ts "$@"
