#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_DIR="$ROOT_DIR/.runtime_pids"
LOG_DIR="$ROOT_DIR/.runtime_logs"
mkdir -p "$PID_DIR" "$LOG_DIR"

V1_PID_FILE="$PID_DIR/backend_v1.pid"
V2_PID_FILE="$PID_DIR/backend_v2.pid"
FE_PID_FILE="$PID_DIR/frontend.pid"

V1_LOG_FILE="$LOG_DIR/backend_v1.log"
V2_LOG_FILE="$LOG_DIR/backend_v2.log"
FE_LOG_FILE="$LOG_DIR/frontend.log"

V1_ENV="$ROOT_DIR/backend_env"
V2_ENV="$ROOT_DIR/.venv_v2"

V1_PY="$V1_ENV/bin/python"
V2_PY="$V2_ENV/bin/python"

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

http_ok() {
  local url="$1"
  curl -fsS --max-time 3 "$url" >/dev/null 2>&1
}

is_running() {
  local pid_file="$1"
  if [[ ! -f "$pid_file" ]]; then
    return 1
  fi
  local pid
  pid="$(cat "$pid_file")"
  if [[ -z "$pid" ]]; then
    rm -f "$pid_file"
    return 1
  fi
  if kill -0 "$pid" >/dev/null 2>&1; then
    return 0
  fi
  rm -f "$pid_file"
  return 1
}

wait_http() {
  local url="$1"
  local timeout="${2:-60}"
  local waited=0
  while (( waited < timeout )); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    ((waited+=1))
  done
  echo "Timed out waiting for: $url"
  return 1
}

ensure_v1_env() {
  if [[ ! -x "$V1_PY" ]]; then
    echo "Creating backend v1 env: $V1_ENV"
    python3 -m venv "$V1_ENV"
    "$V1_PY" -m pip install --upgrade pip
    "$V1_PY" -m pip install -r "$ROOT_DIR/backend/requirements.txt"
  fi
}

ensure_v2_env() {
  if [[ ! -x "$V2_PY" ]]; then
    echo "Creating backend v2 env: $V2_ENV"
    python3 -m venv "$V2_ENV"
    "$V2_PY" -m pip install --upgrade pip
    "$V2_PY" -m pip install -r "$ROOT_DIR/backend/requirements-v2.txt"
  fi
}

start_v1() {
  if is_running "$V1_PID_FILE"; then
    echo "backend v1 already running (pid $(cat "$V1_PID_FILE"))"
    return
  fi
  ensure_v1_env
  echo "Starting backend v1 on :5003"
  (
    cd "$ROOT_DIR/backend"
    nohup env FLASK_CONFIG=production FLASK_ENV=production FLASK_DEBUG=0 "$V1_PY" run.py >"$V1_LOG_FILE" 2>&1 &
    echo $! > "$V1_PID_FILE"
  )
  if ! wait_http "http://127.0.0.1:5003/api/v1/health" 90; then
    echo "backend v1 failed to become healthy, last logs:"
    tail -n 80 "$V1_LOG_FILE" || true
    stop_one "$V1_PID_FILE" "backend v1"
    return 1
  fi
  if ! is_running "$V1_PID_FILE"; then
    echo "backend v1 health is reachable but managed process exited; port 5003 may be occupied by another process"
    tail -n 80 "$V1_LOG_FILE" || true
    return 1
  fi
}

start_v2() {
  if is_running "$V2_PID_FILE"; then
    echo "backend v2 already running (pid $(cat "$V2_PID_FILE"))"
    return
  fi
  ensure_v2_env
  echo "Starting backend v2 on :8003"
  (
    cd "$ROOT_DIR/backend"
    nohup env V2_PORT=8003 "$V2_PY" run_v2.py >"$V2_LOG_FILE" 2>&1 &
    echo $! > "$V2_PID_FILE"
  )
  if ! wait_http "http://127.0.0.1:8003/health" 90; then
    echo "backend v2 failed to become healthy, last logs:"
    tail -n 80 "$V2_LOG_FILE" || true
    stop_one "$V2_PID_FILE" "backend v2"
    return 1
  fi
  if ! is_running "$V2_PID_FILE"; then
    echo "backend v2 health is reachable but managed process exited; port 8003 may be occupied by another process"
    tail -n 80 "$V2_LOG_FILE" || true
    return 1
  fi
}

start_frontend() {
  if is_running "$FE_PID_FILE"; then
    echo "frontend already running (pid $(cat "$FE_PID_FILE"))"
    return
  fi
  echo "Starting frontend dev server on :5173"
  (
    cd "$ROOT_DIR/frontend"
    if [[ ! -d node_modules ]]; then
      npm install
    fi
    nohup npm run dev -- --host 0.0.0.0 --port 5173 >"$FE_LOG_FILE" 2>&1 &
    echo $! > "$FE_PID_FILE"
  )
  wait_http "http://127.0.0.1:5173" 120
}

stop_one() {
  local pid_file="$1"
  local name="$2"
  if ! is_running "$pid_file"; then
    echo "$name not running"
    rm -f "$pid_file"
    return
  fi
  local pid
  pid="$(cat "$pid_file")"
  echo "Stopping $name (pid $pid)"
  kill "$pid" >/dev/null 2>&1 || true
  sleep 1
  if kill -0 "$pid" >/dev/null 2>&1; then
    kill -9 "$pid" >/dev/null 2>&1 || true
  fi
  rm -f "$pid_file"
}

status() {
  local v1_health='down'
  local v2_health='down'
  local fe_health='down'
  if http_ok "http://127.0.0.1:5003/api/v1/health"; then
    v1_health='up'
  fi
  if http_ok "http://127.0.0.1:8003/health"; then
    v2_health='up'
  fi
  if http_ok "http://127.0.0.1:5173"; then
    fe_health='up'
  fi

  if is_running "$V1_PID_FILE"; then
    echo "backend v1: running (pid $(cat "$V1_PID_FILE"), health=$v1_health)"
  elif [[ "$v1_health" == "up" ]]; then
    echo "backend v1: unmanaged process detected on port 5003 (health=up)"
  else
    echo "backend v1: stopped"
  fi
  if is_running "$V2_PID_FILE"; then
    echo "backend v2: running (pid $(cat "$V2_PID_FILE"), health=$v2_health)"
  elif [[ "$v2_health" == "up" ]]; then
    echo "backend v2: unmanaged process detected on port 8003 (health=up)"
  else
    echo "backend v2: stopped"
  fi
  if is_running "$FE_PID_FILE"; then
    echo "frontend: running (pid $(cat "$FE_PID_FILE"), health=$fe_health)"
  elif [[ "$fe_health" == "up" ]]; then
    echo "frontend: unmanaged process detected on port 5173 (health=up)"
  else
    echo "frontend: stopped"
  fi
}

check() {
  local failed=0
  echo "Checking health endpoints..."
  if curl -fsS "http://127.0.0.1:5003/api/v1/health" | sed -e 's/^/v1: /'; then
    echo
  else
    echo "v1: health check failed"
    failed=1
  fi
  if curl -fsS "http://127.0.0.1:8003/health" | sed -e 's/^/v2: /'; then
    echo
  else
    echo "v2: health check failed"
    failed=1
  fi
  if curl -fsS "http://127.0.0.1:8003/api/v2/interview/architecture" | sed -e 's/^/v2-arch: /'; then
    echo
  else
    echo "v2-arch: endpoint check failed"
    failed=1
  fi
  return "$failed"
}

usage() {
  cat <<'EOF'
Usage: scripts/stack.sh <start|stop|restart|status|check> [--frontend]
  start       Start backend v1 and v2, optional frontend
  stop        Stop frontend, backend v2, backend v1
  restart     Stop then start
  status      Show process status from pid files
  check       Run HTTP health checks

Examples:
  ./scripts/stack.sh start
  ./scripts/stack.sh start --frontend
  ./scripts/stack.sh check
  ./scripts/stack.sh stop
EOF
}

ACTION="${1:-}"
WITH_FRONTEND="${2:-}"

case "$ACTION" in
  start)
    start_v1
    start_v2
    if [[ "$WITH_FRONTEND" == "--frontend" ]]; then
      start_frontend
    fi
    status
    ;;
  stop)
    stop_one "$FE_PID_FILE" "frontend"
    stop_one "$V2_PID_FILE" "backend v2"
    stop_one "$V1_PID_FILE" "backend v1"
    ;;
  restart)
    "$0" stop
    "$0" start "$WITH_FRONTEND"
    ;;
  status)
    status
    ;;
  check)
    check
    ;;
  *)
    usage
    exit 2
    ;;
esac
