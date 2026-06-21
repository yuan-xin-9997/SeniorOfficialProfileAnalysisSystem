#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${APP_DIR:-$SCRIPT_DIR}"
PYTHON_EXECUTABLE="${PYTHON_EXECUTABLE:-$APP_DIR/.venv/bin/python}"

cd "$APP_DIR"
test -x "$PYTHON_EXECUTABLE"

read_setting() {
  PYTHONPATH="$APP_DIR/backend" "$PYTHON_EXECUTABLE" -c \
    "from app.core.config import settings; print(settings.$1)"
}

resolve_path() {
  case "$1" in
    /*) printf '%s\n' "$1" ;;
    *) printf '%s\n' "$APP_DIR/${1#./}" ;;
  esac
}

APP_HOST="${APP_HOST:-$(read_setting APP_HOST)}"
APP_PORT="${APP_PORT:-${PORT:-$(read_setting APP_PORT)}}"
DATA_DIR="$(resolve_path "${DATA_DIR:-$(read_setting DATA_DIR)}")"
LOG_DIR="$(resolve_path "${LOG_DIR:-$(read_setting LOG_DIR)}")"
FRONTEND_DIST_DIR="$(resolve_path "${FRONTEND_DIST_DIR:-$(read_setting FRONTEND_DIST_DIR)}")"
PID_FILE="$DATA_DIR/app.pid"
PORT_FILE="$DATA_DIR/app.port"

mkdir -p "$DATA_DIR" "$LOG_DIR"

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Application is already running (PID $(cat "$PID_FILE"))."
  exit 0
fi

test -f "$FRONTEND_DIST_DIR/index.html"

export APP_HOST APP_PORT DATA_DIR LOG_DIR FRONTEND_DIST_DIR
nohup "$PYTHON_EXECUTABLE" "$APP_DIR/backend/run.py" >/dev/null 2>&1 &

PID=$!
echo "$PID" > "$PID_FILE"
echo "$APP_PORT" > "$PORT_FILE"

for _ in $(seq 1 30); do
  if curl --silent --fail "http://127.0.0.1:$APP_PORT/api/health" >/dev/null; then
    echo "Application started on $APP_HOST:$APP_PORT (PID $PID)."
    exit 0
  fi
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "Application exited during startup. Check $LOG_DIR/app.log."
    rm -f "$PID_FILE" "$PORT_FILE"
    exit 1
  fi
  sleep 1
done

echo "Application did not become healthy. Check $LOG_DIR/app.log."
kill "$PID" 2>/dev/null || true
rm -f "$PID_FILE" "$PORT_FILE"
exit 1
