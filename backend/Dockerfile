# --- Étape 1 : Build stage pour les dépendances ultra-rapide avec uv ---
FROM python:3.12-slim AS builder

# Installation de uv depuis l'image officielle (latest garantit Support SOTA)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Paramètres de uv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Installation des dépendances stricte selon le lockfile
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# --- Étape 2 : Image finale (Distroless / Slim) ---
FROM python:3.12-slim

# Sécurité SOTA 2026 : Privilege Drop (Zero Root Allowed)
RUN groupadd -r appgroup && useradd -r -g appgroup -u 1000 appuser

WORKDIR /app

# Copie l'environnement virtuel compilé (chown restrictif)
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copie le code source (chown restrictif)
COPY --chown=appuser:appgroup src/ /app/src/

# Variable d'environnement Cloud Run (port 8080)
ENV PORT="8080"
ENV PYTHONPATH="/app/src"

# Verrouillage final du runtime sur l'UID numérique strict (Security check: CKV_DOCKER_3)
USER 1000

# Lancement de l'application
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
