SHELL := /bin/bash
ROOT_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
LOCAL_ENV_FILE := $(ROOT_DIR).env.local

.PHONY: help infra-up infra-down infra-logs db-migrate db-seed api worker-style demo-style-upload demo-style-replay

help:
	@printf "Targets disponibles:\\n"
	@printf "  make infra-up                Démarre Postgres et Temporal local\\n"
	@printf "  make infra-down              Arrête l'infra locale\\n"
	@printf "  make infra-logs              Suit les logs Docker locaux\\n"
	@printf "  make db-migrate              Lance alembic upgrade head\\n"
	@printf "  make db-seed                 Injecte la taxonomie POC\\n"
	@printf "  make api                     Lance l'API locale\\n"
	@printf "  make worker-style            Lance le worker style guide local\\n"
	@printf "  make demo-style-upload PDF=./guide.pdf   Upload réel GCS + webhook local\\n"
	@printf "  make demo-style-replay OBJECT=AXOLOTL_STYLE_GUIDE_V4.pdf   Rejoue un objet déjà présent dans GCS\\n"

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

demo-style-upload:
	@[ -n "$(PDF)" ] || (echo "Usage: make demo-style-upload PDF=./guide-style.pdf" && exit 1)
	bash "$(ROOT_DIR)backend/scripts/demo_style_guide_upload.sh" "$(PDF)"

demo-style-replay:
	@[ -n "$(OBJECT)" ] || (echo "Usage: make demo-style-replay OBJECT=AXOLOTL_STYLE_GUIDE_V4.pdf" && exit 1)
	bash "$(ROOT_DIR)backend/scripts/replay_style_guide_event.sh" "$(OBJECT)"
