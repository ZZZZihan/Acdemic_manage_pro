#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT_DIR="$(cd "$FRONTEND_DIR/.." && pwd)"
STARTED_BY_RUNNER=0
E2E_TMP_DIR=""

cleanup() {
  if [[ "$STARTED_BY_RUNNER" -eq 1 ]]; then
    "$ROOT_DIR/scripts/stack.sh" stop >/dev/null 2>&1 || true
  fi
  if [[ -n "$E2E_TMP_DIR" && -d "$E2E_TMP_DIR" ]]; then
    rm -rf "$E2E_TMP_DIR"
  fi
}
trap cleanup EXIT

status_output="$("$ROOT_DIR/scripts/stack.sh" status)"
if echo "$status_output" | grep -Eq '(running|unmanaged process detected)'; then
  if [[ "${E2E_ALLOW_REUSE:-0}" != "1" ]]; then
    echo "Detected existing runtime stack; refusing to run non-hermetic E2E."
    echo "Stop existing services first, or set E2E_ALLOW_REUSE=1 to reuse current stack."
    echo "$status_output"
    exit 2
  fi
else
  E2E_TMP_DIR="$(mktemp -d "$ROOT_DIR/.runtime_e2e_db.XXXXXX")"
  export DATABASE_URL="sqlite:///$E2E_TMP_DIR/data-v1-e2e.sqlite"
  export V2_DATABASE_URL="sqlite+pysqlite:///$E2E_TMP_DIR/data-v2-e2e.sqlite"
  "$ROOT_DIR/scripts/stack.sh" start --frontend
  STARTED_BY_RUNNER=1
fi

cd "$FRONTEND_DIR"

resolved_channel="${PW_CHANNEL:-}"
if [[ -z "$resolved_channel" ]]; then
  if command -v google-chrome >/dev/null 2>&1 || command -v google-chrome-stable >/dev/null 2>&1; then
    resolved_channel="chrome"
  elif [[ -d "/Applications/Google Chrome.app" ]]; then
    resolved_channel="chrome"
  fi
fi

if [[ -n "$resolved_channel" ]]; then
  PW_CHANNEL="$resolved_channel" npx playwright test "$@"
else
  npx playwright test "$@"
fi
