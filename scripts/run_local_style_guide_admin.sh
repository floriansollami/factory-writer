#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$ROOT_DIR/.tmp/style-guide-admin"
LOG_DIR="$STATE_DIR/logs"
BACKEND_PID_FILE="$STATE_DIR/backend.pid"
WORKER_PID_FILE="$STATE_DIR/worker.pid"
FRONTEND_PID_FILE="$STATE_DIR/frontend.pid"
ROOT_ENV_FILE="${LOCAL_ENV_FILE:-$ROOT_DIR/.env.local}"
BACKEND_ENV_FILE="$ROOT_DIR/backend/.env"

POSTGRES_PORT="${POSTGRES_PORT:-5432}"
TEMPORAL_PORT="${TEMPORAL_PORT:-7233}"
TEMPORAL_UI_PORT="${TEMPORAL_UI_PORT:-8233}"
FAKE_GCS_PORT="${FAKE_GCS_PORT:-4443}"
BACKEND_PORT="${BACKEND_PORT:-8080}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

DB_URL="${DB__URL:-postgresql+psycopg://postgres:postgres@127.0.0.1:${POSTGRES_PORT}/factory_writer}"
TEMPORAL_ADDRESS="${TEMPORAL__ADDRESS:-127.0.0.1:${TEMPORAL_PORT}}"
TEMPORAL_NAMESPACE="${TEMPORAL__NAMESPACE:-default}"
TEMPORAL_WORKER_ROLE="${TEMPORAL__WORKER_ROLE:-style-guide-ingestion}"
TEMPORAL_DEPLOYMENT_NAME="${TEMPORAL__DEPLOYMENT_NAME:-factory-writer-local}"
STYLE_GUIDE_STORAGE_MODE="${STYLE_GUIDE_STORAGE_MODE:-real}"
GCP_PROJECT_ID="${GCP__PROJECT_ID:-}"
DOCUMENT_AI_PROCESSOR_ID="${GCP__DOCUMENT_AI_PROCESSOR_ID:-}"
STYLE_GUIDE_BUCKET_NAME="${GCP__STYLE_GUIDE_BUCKET_NAME:-}"
STORAGE_EMULATOR_HOST="${GCP__STORAGE_EMULATOR_HOST:-}"

# real = frontend branché au vrai backend sans MSW.
FRONTEND_MODE="${FRONTEND_MODE:-real}"

FAKE_GCS_CONTAINER_NAME="factory-writer-fake-gcs"
FAKE_GCS_DATA_DIR="$STATE_DIR/fake-gcs-data"

mkdir -p "$LOG_DIR" "$FAKE_GCS_DATA_DIR"

script_log() {
  local step="$1"
  shift
  printf '[local-style-guide][%s] %s\n' "$step" "$*"
}

load_env_file_if_present() {
  local file_path="$1"
  if [[ -f "$file_path" ]]; then
    set -a
    source "$file_path"
    set +a
  fi
}

require_command() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Commande requise manquante: $command_name" >&2
    exit 1
  fi
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

require_nonempty_env() {
  local var_name="$1"
  local value="${!var_name:-}"
  if [[ -z "$value" ]]; then
    echo "Variable requise manquante: $var_name" >&2
    exit 1
  fi
}

ensure_gcp_auth() {
  if [[ -n "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]]; then
    return
  fi

  if command -v gcloud >/dev/null 2>&1; then
    if gcloud auth application-default print-access-token >/dev/null 2>&1; then
      return
    fi
  fi

  echo "Authentification GCP absente. Configure GOOGLE_APPLICATION_CREDENTIALS ou lance 'gcloud auth application-default login'." >&2
  exit 1
}

assert_port_available() {
  local port="$1"
  local pid_file="$2"
  local label="$3"
  local expected_pattern="$4"

  if [[ -f "$pid_file" ]]; then
    local known_pid
    known_pid="$(cat "$pid_file")"
    if kill -0 "$known_pid" >/dev/null 2>&1; then
      return
    fi
    rm -f "$pid_file"
  fi

  terminate_port_process_if_matches "$port" "$expected_pattern"

  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Le port $port est déjà occupé. Libère-le avant de lancer $label." >&2
    exit 1
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

wait_for_url() {
  local url="$1"
  local label="$2"
  local timeout_seconds="${3:-30}"
  local deadline=$((SECONDS + timeout_seconds))

  until curl -fsS "$url" >/dev/null 2>&1; do
    if (( SECONDS >= deadline )); then
      echo "$label n'est pas devenu disponible à temps: $url" >&2
      exit 1
    fi
    sleep 0.5
  done
}

wait_for_postgres() {
  local postgres_container_id
  postgres_container_id="$(cd "$ROOT_DIR" && docker compose ps -q postgres)"

  if [[ -z "$postgres_container_id" ]]; then
    echo "Impossible de trouver le conteneur postgres dans docker compose." >&2
    exit 1
  fi

  for _ in {1..60}; do
    local health_status
    health_status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$postgres_container_id")"
    if [[ "$health_status" == "healthy" || "$health_status" == "running" ]]; then
      return
    fi
    sleep 1
  done

  echo "Postgres n'est pas devenu prêt dans le délai imparti." >&2
  exit 1
}

wait_for_temporal() {
  local ui_url="http://127.0.0.1:${TEMPORAL_UI_PORT}"
  local deadline=$((SECONDS + 60))

  until curl -fsS "$ui_url" >/dev/null 2>&1; do
    if (( SECONDS >= deadline )); then
      echo "Temporal UI n'est pas devenue prête dans le délai imparti: $ui_url" >&2
      exit 1
    fi
    sleep 1
  done
}

reset_local_database_schema() {
  cd "$ROOT_DIR/backend"
  DB__URL="$DB_URL" uv run python - <<'PY'
import os

from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DB__URL"], isolation_level="AUTOCOMMIT")
with engine.connect() as connection:
    connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
    connection.execute(text("CREATE SCHEMA public"))
    connection.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
    connection.execute(text("GRANT ALL ON SCHEMA public TO public"))
engine.dispose()
PY
}

run_migrations() {
  local migration_log="$LOG_DIR/alembic.log"

  if (
    cd "$ROOT_DIR/backend" &&
    DB__URL="$DB_URL" uv run alembic upgrade head >"$migration_log" 2>&1
  ); then
    return
  fi

  if grep -q "Can't locate revision identified by" "$migration_log"; then
    echo "Base locale avec historique Alembic obsolète détecté, reset du schéma public..."
    reset_local_database_schema
    (
      cd "$ROOT_DIR/backend" &&
      DB__URL="$DB_URL" uv run alembic upgrade head >"$migration_log" 2>&1
    )
    return
  fi

  cat "$migration_log" >&2
  exit 1
}

ensure_fake_gcs() {
  local container_state=""

  if docker inspect "$FAKE_GCS_CONTAINER_NAME" >/dev/null 2>&1; then
    container_state="$(docker inspect --format '{{.State.Status}}' "$FAKE_GCS_CONTAINER_NAME")"
  fi

  if [[ "$container_state" == "running" ]]; then
    return
  fi

  if [[ -n "$container_state" ]]; then
    docker rm -f "$FAKE_GCS_CONTAINER_NAME" >/dev/null 2>&1 || true
  fi

  docker run -d \
    --rm \
    --name "$FAKE_GCS_CONTAINER_NAME" \
    -p "${FAKE_GCS_PORT}:${FAKE_GCS_PORT}" \
    -v "$FAKE_GCS_DATA_DIR:/data" \
    fsouza/fake-gcs-server:1.54.0 \
    -scheme http \
    -port "$FAKE_GCS_PORT" >/dev/null

  cd "$ROOT_DIR/backend"
  GCP__PROJECT_ID="$GCP_PROJECT_ID" \
  GCP__STYLE_GUIDE_BUCKET_NAME="$STYLE_GUIDE_BUCKET_NAME" \
  GCP__STORAGE_EMULATOR_HOST="$STORAGE_EMULATOR_HOST" \
  uv run python - <<'PY'
from time import monotonic, sleep
import os

from google.cloud.storage import Client

host = os.environ["GCP__STORAGE_EMULATOR_HOST"]
bucket_name = os.environ["GCP__STYLE_GUIDE_BUCKET_NAME"]
project_id = os.environ["GCP__PROJECT_ID"]

client = Client(
    project=project_id,
    client_options={"api_endpoint": host},
    use_auth_w_custom_endpoint=False,
)

deadline = monotonic() + 15
while monotonic() < deadline:
    try:
        list(client.list_buckets())
        break
    except Exception:
        sleep(0.2)
else:
    raise SystemExit("fake-gcs-server n'est pas devenu prêt dans le délai imparti.")

bucket = client.bucket(bucket_name)
if not bucket.exists():
    client.create_bucket(bucket)
PY
}

start_backend() {
  stop_managed_process "$BACKEND_PID_FILE"
  assert_port_available \
    "$BACKEND_PORT" \
    "$BACKEND_PID_FILE" \
    "le backend" \
    "uvicorn factory_writer.main:app --app-dir src --host 127.0.0.1 --port ${BACKEND_PORT}"

  (
    cd "$ROOT_DIR/backend"
    nohup env \
      DEBUG=true \
      DB__URL="$DB_URL" \
      TEMPORAL__ADDRESS="$TEMPORAL_ADDRESS" \
      TEMPORAL__NAMESPACE="$TEMPORAL_NAMESPACE" \
      TEMPORAL__API_KEY="" \
      TEMPORAL__WORKER_ROLE="$TEMPORAL_WORKER_ROLE" \
      TEMPORAL__DEPLOYMENT_NAME="$TEMPORAL_DEPLOYMENT_NAME" \
      GCP__PROJECT_ID="$GCP_PROJECT_ID" \
      GCP__DOCUMENT_AI_PROCESSOR_ID="$DOCUMENT_AI_PROCESSOR_ID" \
      GCP__STYLE_GUIDE_BUCKET_NAME="$STYLE_GUIDE_BUCKET_NAME" \
      GCP__STORAGE_EMULATOR_HOST="$STORAGE_EMULATOR_HOST" \
      bash -lc "exec uv run uvicorn factory_writer.main:app --app-dir src --host 127.0.0.1 --port ${BACKEND_PORT}" \
      >"$LOG_DIR/backend.log" 2>&1 &
    echo $! >"$BACKEND_PID_FILE"
  )

  wait_for_url "http://127.0.0.1:${BACKEND_PORT}/health" "Le backend" 30
}

start_worker() {
  stop_managed_process "$WORKER_PID_FILE"

  (
    cd "$ROOT_DIR/backend"
    nohup env \
      DEBUG=true \
      DB__URL="$DB_URL" \
      TEMPORAL__ADDRESS="$TEMPORAL_ADDRESS" \
      TEMPORAL__NAMESPACE="$TEMPORAL_NAMESPACE" \
      TEMPORAL__API_KEY="" \
      TEMPORAL__WORKER_ROLE="$TEMPORAL_WORKER_ROLE" \
      TEMPORAL__DEPLOYMENT_NAME="$TEMPORAL_DEPLOYMENT_NAME" \
      GCP__PROJECT_ID="$GCP_PROJECT_ID" \
      GCP__DOCUMENT_AI_PROCESSOR_ID="$DOCUMENT_AI_PROCESSOR_ID" \
      GCP__STYLE_GUIDE_BUCKET_NAME="$STYLE_GUIDE_BUCKET_NAME" \
      GCP__STORAGE_EMULATOR_HOST="$STORAGE_EMULATOR_HOST" \
      bash -lc "exec uv run python -m factory_writer.temporal.worker" \
      >"$LOG_DIR/worker.log" 2>&1 &
    echo $! >"$WORKER_PID_FILE"
  )

  sleep 2
  if ! kill -0 "$(cat "$WORKER_PID_FILE")" >/dev/null 2>&1; then
    echo "Le worker style guide s'est arrêté au démarrage. Voir $LOG_DIR/worker.log" >&2
    exit 1
  fi
}

start_frontend() {
  stop_managed_process "$FRONTEND_PID_FILE"
  assert_port_available \
    "$FRONTEND_PORT" \
    "$FRONTEND_PID_FILE" \
    "le frontend" \
    "vite --host 127.0.0.1 --port ${FRONTEND_PORT}"

  local msw_env=""
  if [[ "$FRONTEND_MODE" == "real" ]]; then
    msw_env="VITE_USE_MSW=false"
  elif [[ "$FRONTEND_MODE" != "mixed" ]]; then
    echo "FRONTEND_MODE invalide: $FRONTEND_MODE (valeurs acceptées: mixed, real)" >&2
    exit 1
  fi

  if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
    (cd "$ROOT_DIR/frontend" && npm ci)
  fi

  (
    cd "$ROOT_DIR/frontend"
    if [[ -n "$msw_env" ]]; then
      nohup env VITE_API_BASE_URL="http://127.0.0.1:${BACKEND_PORT}" "$msw_env" \
        bash -lc "exec npm run dev -- --host 127.0.0.1 --port ${FRONTEND_PORT}" \
        >"$LOG_DIR/frontend.log" 2>&1 &
    else
      nohup env VITE_API_BASE_URL="http://127.0.0.1:${BACKEND_PORT}" \
        bash -lc "exec npm run dev -- --host 127.0.0.1 --port ${FRONTEND_PORT}" \
        >"$LOG_DIR/frontend.log" 2>&1 &
    fi
    echo $! >"$FRONTEND_PID_FILE"
  )

  wait_for_url "http://127.0.0.1:${FRONTEND_PORT}" "Le frontend" 45
}

require_command docker
require_command curl
require_command lsof
require_command uv
require_command npm

script_log setup "Chargement des variables d'environnement..."
load_env_file_if_present "$BACKEND_ENV_FILE"
load_env_file_if_present "$ROOT_ENV_FILE"

if [[ "$STYLE_GUIDE_STORAGE_MODE" == "real" ]]; then
  require_nonempty_env GCP__PROJECT_ID
  require_nonempty_env GCP__DOCUMENT_AI_PROCESSOR_ID
  require_nonempty_env GCP__STYLE_GUIDE_BUCKET_NAME
  ensure_gcp_auth
  STORAGE_EMULATOR_HOST=""
elif [[ "$STYLE_GUIDE_STORAGE_MODE" == "fake" ]]; then
  GCP_PROJECT_ID="${GCP__PROJECT_ID:-factory-writer-local}"
  STYLE_GUIDE_BUCKET_NAME="${GCP__STYLE_GUIDE_BUCKET_NAME:-factory-writer-style-guide-local}"
  STORAGE_EMULATOR_HOST="${GCP__STORAGE_EMULATOR_HOST:-http://127.0.0.1:${FAKE_GCS_PORT}}"
else
  echo "STYLE_GUIDE_STORAGE_MODE invalide: $STYLE_GUIDE_STORAGE_MODE (valeurs acceptées: real, fake)" >&2
  exit 1
fi

GCP_PROJECT_ID="${GCP__PROJECT_ID:-$GCP_PROJECT_ID}"
DOCUMENT_AI_PROCESSOR_ID="${GCP__DOCUMENT_AI_PROCESSOR_ID:-$DOCUMENT_AI_PROCESSOR_ID}"
STYLE_GUIDE_BUCKET_NAME="${GCP__STYLE_GUIDE_BUCKET_NAME:-$STYLE_GUIDE_BUCKET_NAME}"

mkdir -p "$STATE_DIR"

script_log infra "Démarrage de Postgres et Temporal..."
cd "$ROOT_DIR"
docker compose up -d postgres temporal >/dev/null
wait_for_postgres
wait_for_temporal
if [[ "$STYLE_GUIDE_STORAGE_MODE" == "fake" ]]; then
  script_log infra "Préparation du fake GCS..."
  ensure_fake_gcs
else
  docker rm -f "$FAKE_GCS_CONTAINER_NAME" >/dev/null 2>&1 || true
fi

script_log db "Synchronisation de l'environnement Python, migrations et seed taxonomie..."
(
  cd "$ROOT_DIR/backend"
  uv sync --extra dev >/dev/null
  run_migrations
  DB__URL="$DB_URL" uv run python -m factory_writer.scripts.seed_taxonomie >/dev/null
)

script_log backend "Démarrage de l'API locale..."
start_backend
script_log worker "Démarrage du worker style-guide-ingestion..."
start_worker
script_log frontend "Démarrage du frontend local..."
start_frontend

cat <<EOF
Stack locale prête.

Frontend: http://127.0.0.1:${FRONTEND_PORT}
Backend:  http://127.0.0.1:${BACKEND_PORT}
Health:   http://127.0.0.1:${BACKEND_PORT}/health
Temporal: http://127.0.0.1:${TEMPORAL_UI_PORT}
Worker:   style-guide-ingestion (local)
Bucket:   ${STYLE_GUIDE_BUCKET_NAME}
Storage:  ${STYLE_GUIDE_STORAGE_MODE}
Processor: ${DOCUMENT_AI_PROCESSOR_ID}
Mode frontend: ${FRONTEND_MODE}

Logs:
- $LOG_DIR/backend.log
- $LOG_DIR/worker.log
- $LOG_DIR/frontend.log

Stop:
- bash "$ROOT_DIR/scripts/stop_local_style_guide_admin.sh"
EOF
