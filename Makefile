SHELL := /bin/bash
ROOT_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
LOCAL_ENV_FILE := $(ROOT_DIR).env.local

.PHONY: help infra-up infra-down infra-logs db-migrate db-seed api worker-style worker-product frontend frontend-real backend-check local-style-guide local-style-guide-logs local-style-guide-down

help:
	@printf "Targets disponibles:\\n"
	@printf "  make infra-up                Démarre Postgres et Temporal local\\n"
	@printf "  make infra-down              Arrête l'infra locale\\n"
	@printf "  make infra-logs              Suit les logs Docker locaux\\n"
	@printf "  make db-migrate              Lance alembic upgrade head\\n"
	@printf "  make db-seed                 Injecte la taxonomie POC\\n"
	@printf "  make api                     Lance l'API locale\\n"
	@printf "  make worker-style            Lance le worker style guide local\\n"
	@printf "  make worker-product          Lance le worker product lifecycle local\\n"
	@printf "  make frontend                Lance l'admin frontend avec upload mocké\\n"
	@printf "  make frontend-real           Lance l'admin frontend contre l'API locale réelle\\n"
	@printf "  make local-style-guide       Démarre la stack locale style guide réelle puis suit les logs backend/worker/frontend\\n"
	@printf "  make local-style-guide-logs  Suit uniquement les logs backend/worker/frontend déjà démarrés\\n"
	@printf "  make local-style-guide-down  Arrête la stack locale style guide\\n"
	@printf "  make backend-check           Lance les checks backend standards (lint, format, mypy, tests, compile)\\n"

infra-up:
	docker compose up -d

infra-down:
	docker compose down

infra-logs:
	docker compose logs -f postgres temporal

db-migrate:
	bash -lc 'set -a; [ -f "$(LOCAL_ENV_FILE)" ] && source "$(LOCAL_ENV_FILE)"; set +a; cd "$(ROOT_DIR)backend" && uv run alembic upgrade head'

db-seed:
	bash -lc 'set -a; [ -f "$(LOCAL_ENV_FILE)" ] && source "$(LOCAL_ENV_FILE)"; set +a; cd "$(ROOT_DIR)backend" && uv run python -m factory_writer.scripts.seed_taxonomie'

api:
	bash -lc 'set -a; [ -f "$(LOCAL_ENV_FILE)" ] && source "$(LOCAL_ENV_FILE)"; set +a; cd "$(ROOT_DIR)backend" && uv run uvicorn factory_writer.main:app --app-dir src --reload --port 8080'

worker-style:
	bash -lc 'set -a; [ -f "$(LOCAL_ENV_FILE)" ] && source "$(LOCAL_ENV_FILE)"; set +a; export TEMPORAL__WORKER_ROLE=style-guide-ingestion; cd "$(ROOT_DIR)backend" && uv run python -m factory_writer.temporal.worker'

worker-product:
	bash -lc 'set -a; [ -f "$(LOCAL_ENV_FILE)" ] && source "$(LOCAL_ENV_FILE)"; set +a; export TEMPORAL__WORKER_ROLE=product-lifecycle; cd "$(ROOT_DIR)backend" && uv run python -m factory_writer.temporal.worker'

frontend:
	cd "$(ROOT_DIR)frontend" && VITE_API_BASE_URL=http://127.0.0.1:8080 npm run dev -- --host 127.0.0.1 --port 5173

frontend-real:
	cd "$(ROOT_DIR)frontend" && VITE_API_BASE_URL=http://127.0.0.1:8080 VITE_USE_MSW=false npm run dev -- --host 127.0.0.1 --port 5173

local-style-guide:
	bash -lc 'set -euo pipefail; cleaned=0; cleanup(){ if [[ "$$cleaned" -eq 1 ]]; then return; fi; cleaned=1; bash "$(ROOT_DIR)scripts/stop_local_style_guide_admin.sh" >/dev/null 2>&1 || true; }; trap cleanup EXIT; trap "cleanup; exit 0" INT TERM; bash "$(ROOT_DIR)scripts/run_local_style_guide_admin.sh"; bash "$(ROOT_DIR)scripts/stream_local_style_guide_logs.sh"'

local-style-guide-logs:
	bash "$(ROOT_DIR)scripts/stream_local_style_guide_logs.sh"

local-style-guide-down:
	bash "$(ROOT_DIR)scripts/stop_local_style_guide_admin.sh"

backend-check:
	cd "$(ROOT_DIR)backend" && uv run --extra dev ruff check src/factory_writer alembic tests
	cd "$(ROOT_DIR)backend" && uv run --extra dev ruff format --check src/factory_writer alembic tests
	cd "$(ROOT_DIR)backend" && uv run mypy --explicit-package-bases src/factory_writer alembic tests
	cd "$(ROOT_DIR)backend" && uv run --extra dev pytest
	cd "$(ROOT_DIR)backend" && uv run python -m compileall -q src/factory_writer alembic tests
