#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${APP_DIR:-$SCRIPT_DIR}"
PYTHON_EXECUTABLE="${PYTHON_EXECUTABLE:-$APP_DIR/.venv/bin/python}"

if [[ -z "${DATA_DIR:-}" ]] && [[ -x "$PYTHON_EXECUTABLE" ]]; then
  cd "$APP_DIR"
  DATA_DIR="$(PYTHONPATH="$APP_DIR/backend" "$PYTHON_EXECUTABLE" -c \
    'from app.core.config import settings; print(settings.DATA_DIR)')"
fi
DATA_DIR="${DATA_DIR:-data}"
case "$DATA_DIR" in
  /*) ;;
  *) DATA_DIR="$APP_DIR/${DATA_DIR#./}" ;;
esac

PID_FILE="$DATA_DIR/app.pid"
PORT_FILE="$DATA_DIR/app.port"

if [[ ! -f "$PID_FILE" ]]; then
  echo "Application is not running."
  exit 0
fi

PID="$(cat "$PID_FILE")"
if kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  for _ in $(seq 1 15); do
    kill -0 "$PID" 2>/dev/null || break
    sleep 1
  done
  kill -0 "$PID" 2>/dev/null && kill -9 "$PID"
fi

rm -f "$PID_FILE" "$PORT_FILE"
echo "Application stopped."
