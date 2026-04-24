#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$ROOT_DIR/.tmp/style-guide-admin"
LOG_DIR="$ROOT_DIR/.tmp/style-guide-admin/logs"
STREAMER_PID_FILE="$STATE_DIR/log-stream.pid"

mkdir -p "$STATE_DIR" "$LOG_DIR"
touch "$LOG_DIR/backend.log" "$LOG_DIR/worker.log" "$LOG_DIR/frontend.log"

TAIL_FROM_START="${TAIL_FROM_START:-false}"

stop_pid_if_running() {
  local pid="$1"
  if [[ -z "$pid" ]]; then
    return
  fi

  if kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid" >/dev/null 2>&1 || true
    for _ in {1..20}; do
      if ! kill -0 "$pid" >/dev/null 2>&1; then
        break
      fi
      sleep 0.1
    done
  fi
}

terminate_existing_streamers() {
  if [[ -f "$STREAMER_PID_FILE" ]]; then
    stop_pid_if_running "$(cat "$STREAMER_PID_FILE")"
    rm -f "$STREAMER_PID_FILE"
  fi

  while IFS= read -r pid; do
    [[ -z "$pid" ]] && continue
    if [[ "$pid" != "$$" ]]; then
      stop_pid_if_running "$pid"
    fi
  done < <(pgrep -f "$ROOT_DIR/scripts/stream_local_style_guide_logs.sh" || true)
}

terminate_existing_streamers
echo "$$" >"$STREAMER_PID_FILE"

if [[ -t 1 ]]; then
  COLOR_BACKEND=$'\033[1;34m'
  COLOR_WORKER=$'\033[1;32m'
  COLOR_FRONTEND=$'\033[1;35m'
  COLOR_RESET=$'\033[0m'
else
  COLOR_BACKEND=""
  COLOR_WORKER=""
  COLOR_FRONTEND=""
  COLOR_RESET=""
fi

stream_file() {
  local label="$1"
  local color="$2"
  local file_path="$3"

  local tail_args=()
  if [[ "$TAIL_FROM_START" == "true" ]]; then
    tail_args=(-n +1 -F)
  else
    tail_args=(-n 0 -F)
  fi

  tail "${tail_args[@]}" "$file_path" 2>/dev/null | while IFS= read -r line; do
    local formatted_line="$line"
    formatted_line="$(printf '%s\n' "$formatted_line" | sed -E 's/ \(\{.*\}\) \[[^][]+\]$//')"
    formatted_line="$(printf '%s\n' "$formatted_line" | sed -E 's/ \[[^][]+\]$//')"
    printf '%b[%-8s]%b %s\n' "$color" "$label" "$COLOR_RESET" "$formatted_line"
  done
}

stream_file "backend" "$COLOR_BACKEND" "$LOG_DIR/backend.log" &
BACKEND_STREAM_PID=$!
stream_file "worker" "$COLOR_WORKER" "$LOG_DIR/worker.log" &
WORKER_STREAM_PID=$!
stream_file "frontend" "$COLOR_FRONTEND" "$LOG_DIR/frontend.log" &
FRONTEND_STREAM_PID=$!

cleanup() {
  kill "$BACKEND_STREAM_PID" "$WORKER_STREAM_PID" "$FRONTEND_STREAM_PID" >/dev/null 2>&1 || true
  if [[ -f "$STREAMER_PID_FILE" ]] && [[ "$(cat "$STREAMER_PID_FILE")" == "$$" ]]; then
    rm -f "$STREAMER_PID_FILE"
  fi
}

trap cleanup EXIT INT TERM

wait "$BACKEND_STREAM_PID" "$WORKER_STREAM_PID" "$FRONTEND_STREAM_PID"
