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
if [[ -z "${APP_PORT:-}" ]] && [[ -f "$PORT_FILE" ]]; then
  APP_PORT="$(cat "$PORT_FILE")"
fi
if [[ -z "${APP_PORT:-}" ]] && [[ -n "${PORT:-}" ]]; then
  APP_PORT="$PORT"
fi
if [[ -z "${APP_PORT:-}" ]] && [[ -x "$PYTHON_EXECUTABLE" ]]; then
  cd "$APP_DIR"
  APP_PORT="$(PYTHONPATH="$APP_DIR/backend" "$PYTHON_EXECUTABLE" -c \
    'from app.core.config import settings; print(settings.APP_PORT)')"
fi
: "${APP_PORT:?Set APP_PORT when the saved port and Python configuration are unavailable}"

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  curl --silent --fail "http://127.0.0.1:$APP_PORT/api/health"
  echo
  echo "Application is running on port $APP_PORT (PID $(cat "$PID_FILE"))."
  exit 0
fi

echo "Application is not running."
exit 1
