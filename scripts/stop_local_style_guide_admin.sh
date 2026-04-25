#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$ROOT_DIR/.tmp/style-guide-admin"
BACKEND_PID_FILE="$STATE_DIR/backend.pid"
LEGACY_WORKER_PID_FILE="$STATE_DIR/worker.pid"
STYLE_WORKER_PID_FILE="$STATE_DIR/worker-style.pid"
PRODUCT_WORKER_PID_FILE="$STATE_DIR/worker-product.pid"
FRONTEND_PID_FILE="$STATE_DIR/frontend.pid"
LOG_STREAM_PID_FILE="$STATE_DIR/log-stream.pid"
ROOT_ENV_FILE="${LOCAL_ENV_FILE:-$ROOT_DIR/.env.local}"
BACKEND_ENV_FILE="$ROOT_DIR/backend/.env"
FAKE_GCS_CONTAINER_NAME="factory-writer-fake-gcs"
BACKEND_PORT="${BACKEND_PORT:-8080}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
STYLE_GUIDE_RESET_ON_STOP="${STYLE_GUIDE_RESET_ON_STOP:-true}"
DB_URL="${DB__URL:-postgresql+psycopg://postgres:postgres@127.0.0.1:${POSTGRES_PORT}/factory_writer}"

load_env_file_if_present() {
  local file_path="$1"
  if [[ -f "$file_path" ]]; then
    set -a
    source "$file_path"
    set +a
  fi
}

stop_managed_process() {
  local pid_file="$1"

  if [[ ! -f "$pid_file" ]]; then
    return
  fi

  local pid
  pid="$(cat "$pid_file")"
  if kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid" >/dev/null 2>&1 || true
    for _ in {1..20}; do
      if ! kill -0 "$pid" >/dev/null 2>&1; then
        break
      fi
      sleep 0.2
    done
  fi
  rm -f "$pid_file"
}

terminate_port_process_if_matches() {
  local port="$1"
  local expected_pattern="$2"
  local listener_pids

  listener_pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -z "$listener_pids" ]]; then
    return
  fi

  while IFS= read -r pid; do
    [[ -z "$pid" ]] && continue
    local command_line
    command_line="$(ps -p "$pid" -o command= 2>/dev/null || true)"
    if [[ "$command_line" == *"$expected_pattern"* ]]; then
      kill "$pid" >/dev/null 2>&1 || true
      for _ in {1..20}; do
        if ! kill -0 "$pid" >/dev/null 2>&1; then
          break
        fi
        sleep 0.2
      done
    fi
  done <<<"$listener_pids"
}

reset_style_guide_state() {
  if [[ "$STYLE_GUIDE_RESET_ON_STOP" != "true" ]]; then
    return 2
  fi

  if ! command -v uv >/dev/null 2>&1; then
    echo "Nettoyage local ignoré: commande 'uv' introuvable." >&2
    return 1
  fi

  if (
    cd "$ROOT_DIR/backend"
    DB__URL="$DB_URL" uv run python - <<'PY'
import os

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

TABLES = [
    "product_context_snapshot",
    "style_rule",
    "style_pack",
    "technical_review_case",
    "technical_fact_candidate",
    "technical_fact",
    "document_ingestion_run",
    "document_source",
    "document_collection",
    "product",
]

url = make_url(os.environ["DB__URL"]).set(drivername="postgresql")
dsn = url.render_as_string(hide_password=False)

with psycopg.connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
              AND tablename = ANY(%s)
            ORDER BY array_position(%s::text[], tablename)
            """,
            (TABLES, TABLES),
        )
        existing_tables = [row[0] for row in cur.fetchall()]

        if existing_tables:
            cur.execute(
                sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE").format(
                    sql.SQL(", ").join(sql.Identifier(table) for table in existing_tables)
                )
            )
    conn.commit()
PY
  ) >/dev/null 2>&1; then
    return 0
  fi

  echo "Nettoyage local ignoré: impossible de joindre la base locale." >&2
  return 1
}

load_env_file_if_present "$BACKEND_ENV_FILE"
load_env_file_if_present "$ROOT_ENV_FILE"
DB_URL="${DB__URL:-$DB_URL}"

stop_managed_process "$BACKEND_PID_FILE"
stop_managed_process "$LEGACY_WORKER_PID_FILE"
stop_managed_process "$STYLE_WORKER_PID_FILE"
stop_managed_process "$PRODUCT_WORKER_PID_FILE"
stop_managed_process "$FRONTEND_PID_FILE"
stop_managed_process "$LOG_STREAM_PID_FILE"
terminate_port_process_if_matches \
  "$BACKEND_PORT" \
  "uvicorn factory_writer.main:app --app-dir src --host 127.0.0.1 --port ${BACKEND_PORT}"
terminate_port_process_if_matches \
  "$FRONTEND_PORT" \
  "vite --host 127.0.0.1 --port ${FRONTEND_PORT}"

cleanup_status=0
if reset_style_guide_state; then
  cleanup_status=0
else
  cleanup_status=$?
fi

docker rm -f "$FAKE_GCS_CONTAINER_NAME" >/dev/null 2>&1 || true

cd "$ROOT_DIR"
docker compose stop postgres temporal >/dev/null || true

rm -rf "$STATE_DIR"

if [[ "$cleanup_status" -eq 0 ]]; then
  echo "Stack locale arrêtée et état POC nettoyé."
elif [[ "$cleanup_status" -eq 2 ]]; then
  echo "Stack locale arrêtée."
else
  echo "Stack locale arrêtée (nettoyage local ignoré)."
fi
