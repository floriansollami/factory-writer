set dotenv-load := true

# Affiche par défaut la liste des commandes et leur documentation
default:
    @just --list --justfile {{justfile()}}

# --- 🚀 Développement ---

# [Backend] Démarre le serveur FastAPI en local (Hot-Reload)
dev-backend:
    cd backend && uv run uvicorn api.main:app --reload --port 8000

# [Frontend] Démarre le client Web (Placeholder)
dev-frontend:
    @echo "Frontend non initialisé pour le moment."

# [Monorepo] Démarre l'intégralité de la stack (Back + Front)
dev: dev-backend dev-frontend

# --- 📦 Base de données (PostgreSQL & Alembic) ---

# Démarre la base de données de développement locale (Docker)
db-up:
    cd backend && docker compose up -d

# --- ☁️ Automatisation Cloud (GCP Sandbox SOTA 2026) ---

# Déploie dynamiquement l'infrastructure Sandbox sur le Google Cloud Actif
setup-sandbox project_id=$(gcloud config get-value project):
    @echo "🚀 Provisionnement du POC sur GCP : {{project_id}}..."
    @# 1. Bucket GCS
    gcloud storage buckets create gs://{{project_id}}-brand-styles --location=europe-west1 --uniform-bucket-level-access || true
    @# 2. Document AI
    gcloud alpha document-ai processors create --display-name="factory-writer-style-parser" --type="LAYOUT_PARSER_PROCESSOR" --location="eu" --project="{{project_id}}" || true
    @echo "⚠️ Pense à copier l'ID du Processor retourné ci-dessus dans ton .env !"
    @# 3. IAM (Service Account pour Eventarc)
    gcloud iam service-accounts create eventarc-style-trigger --display-name="Eventarc Trigger" || true
    gcloud projects add-iam-policy-binding {{project_id}} --member="serviceAccount:eventarc-style-trigger@{{project_id}}.iam.gserviceaccount.com" --role="roles/eventarc.eventReceiver" || true
    gcloud projects add-iam-policy-binding {{project_id}} --member="serviceAccount:eventarc-style-trigger@{{project_id}}.iam.gserviceaccount.com" --role="roles/run.invoker" || true
    @# 4. Trigger Eventarc
    gcloud eventarc triggers create trigger-upload-style-guide --location=europe-west1 --destination-run-service=factory-writer-backend --destination-run-region=europe-west1 --event-filters="type=google.cloud.storage.object.v1.finalized" --event-filters="bucket={{project_id}}-brand-styles" --service-account="eventarc-style-trigger@{{project_id}}.iam.gserviceaccount.com" || true
    @echo "✅ Infrastructure déployée !"

# Génère une nouvelle migration (si tu as modifié les modèles)
db-makemigrations message="Schema update":
    cd backend && uv run alembic revision --autogenerate -m "{{message}}"

# Applique les migrations en attente
db-migrate:
    cd backend && uv run alembic upgrade head

# Injecte la taxonomie de base (Seed)
db-seed:
    cd backend/src && PYTHONPATH=. uv run python -m api.scripts.seed_taxonomie

# --- 🛠️ Qualité de Code SOTA 2026 ---

# Formate l'ensemble du code Python via Ruff
format:
    cd backend && uv run ruff format .

# Vérifie le linting Python (Conventions, Imports) via Ruff 
lint:
    cd backend && uv run ruff check .

# Auto-corrige les problèmes de syntaxe et imports
fix:
    cd backend && uv run ruff check . --fix

# Vérifie le typage statique strict via Mypy
typecheck:
    cd backend && uv run mypy .

# Exécute l'ensemble du pipeline de vérification (Format -> Lint -> Typecheck)
check-all: format lint typecheck
