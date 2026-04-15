# --- Étape 1 : Build stage pour les dépendances ultra-rapide avec uv ---
FROM python:3.12-slim AS builder

# Installation de uv depuis l'image officielle, épinglée par digest pour un build reproductible
COPY --from=ghcr.io/astral-sh/uv@sha256:b1e699368d24c57cda93c338a57a8c5a119009ba809305cc8e86986d4a006754 /uv /uvx /bin/

# Paramètres de uv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Installation des dépendances stricte selon le lockfile
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project --no-dev

# Copie du code applicatif puis installation explicite du package projet
COPY src/ /app/src/
RUN uv pip install --python /app/.venv/bin/python --no-deps .

# --- Étape 2 : Image finale (Distroless / Slim) ---
FROM python:3.12-slim

# Sécurité SOTA 2026 : Privilege Drop (Zero Root Allowed)
RUN groupadd -r appgroup && useradd -r -g appgroup -u 1000 appuser

WORKDIR /app

# Copie l'environnement virtuel compilé (chown restrictif)
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copie Alembic (chown restrictif)
COPY --chown=appuser:appgroup alembic.ini /app/alembic.ini
COPY --chown=appuser:appgroup alembic/ /app/alembic/

# Variable d'environnement Cloud Run (port 8080)
ENV PORT="8080"
ENV PYTHONUNBUFFERED="1"

# Verrouillage final du runtime sur l'UID numérique strict (Security check: CKV_DOCKER_3)
USER 1000

# Comportement par défaut : API HTTP.
# Les workers et les migrations surchargent la commande au déploiement.
CMD ["uvicorn", "factory_writer.main:app", "--host", "0.0.0.0", "--port", "8080"]
