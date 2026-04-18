# SOTA 2026 Python Architecture - Factory Writer

Ce document sert de source de vérité pour les choix architecturaux et l'outillage de l'application Python sous-jacente au projet "Factory Writer". Il garantit le respect des standards SOTA (State of the Art) de la Silicon Valley en 2026.

---

## 1. Outillage & Gestion de Projet

### `uv` : Le Gestionnaire de Dépendances
- **Équivalent Node.js** : `pnpm` ou `npm` (gère la résolution des paquets, et remplace le dossier `node_modules` par `.venv`).
- **Rôle** : Remplace l'intégralité de la chaîne obsolète (`pip`, `poetry`, `virtualenv`, `pip-tools`).
- **Standardisation** : Intégration stricte du PEP au travers du `pyproject.toml`.
- **Performance** : Les résolutions (`uv lock`) s'exécutent en quelques millisecondes grâce au moteur écrit en Rust.
- **Isolant** : Les environnements (`.venv`) sont gérés nativement et les installations `uv sync` verrouillent parfaitement les versions pour la production.

### `Make` : Le Task Runner POC
- **Équivalent Node.js** : La section `"scripts"` du `package.json` (`npm run ...`).
- **Rôle** : centralise les commandes locales du POC.
- **Implémentation** : fichier central `Makefile` à la racine.
- **Vision long terme** : si un frontend est ajouté, on pourra migrer vers un task runner monorepo plus riche. Pour le POC, `make` évite de maintenir deux systèmes de commandes concurrents.

---

## 2. Qualité de Code & Clean Architecture

### Hexagonal Architecture (Domain-Driven Design)
Le code n'est pas monolithique, il suit un découpage stratégique pour les workflows temporels :
- **`src/domain/`** : Les entités métier "Pures" (Pydantic Models) et exceptions. **Interdiction stricte d'importer des éléments réseau, base de données ou FastAPI.**
- **`src/application/`** : Les "Use Cases" métier et logiques de routage des Workflows (ex: Temporal Activities).
- **`src/infrastructure/`** : Les points d'entrée vers l'extérieur : l'I/O. C'est ici que l'on implémente la base de données SQL (`psycopg`, `SQLAlchemy`), Google Document AI, GCS et les appels aux LLMs (`LiteLLM`).
- **`src/presentation/`** : Les Routeurs HTTP de `FastAPI`.
- **`src/core/`** : L'amorçage système (Configuration, DI, Logs).

### Mypy (Mode Strict)
Typage statique fort pour interdire l'échec au runtime :
- Configuration `strict = true` et `disallow_untyped_defs = true`.
- Équivaut au `tsc --strict` de TypeScript. Protège contre la donnée JSON instable générée par les LLMs.

### Ruff (Le "God-Linter")
- **Équivalent Node.js** : La fusion ultime de `ESLint` et `Prettier`.
- **Rôle** : Formateur et Analyseur Statique écrit en Rust.
- **Règles Actives** : Syntaxe pure (`E`), Pyflakes/Import errors (`F`), tri asynchrone des imports (`I`), modernisation et mise à jour de code py312 (`UP`), détection de bugs critiques (`B`), simplification structurelle (`SIM`).

### Pytest (Testing Framework)
- **Équivalent Node.js** : `Jest` ou `Vitest`.
- **Rôle** : L'outil SOTA incontournable pour l'exécution des tests (unitaires, intégration, e2e) en Python. S'utilise avec des "fixtures" pour injecter les dépendances proprement.

---

## 3. Web & Connectivité

### FastAPI + Uvicorn (ASGI)
- **Équivalent Node.js** : `NestJS` (ou Express) tournant sur la boucle d'événements native de Node.js.
- Exécution I/O non bloquante. Le serveur utilise `uvicorn` (surcouche à `uvloop` qui émule la libuv de Node.js avec les mêmes performances de concurrence).

### Pydantic (Data Validation) + Settings
- **Équivalent Node.js** : `Zod` (pour la validation) ou `class-validator` couplé aux DTOs.
- Cast, parsing et validation du JSON d'entrée via des modèles stricts.
- Chargement des variables d'environnement (`.env`) parsées, typées et validées automatiquement par `pydantic-settings` dans `src/core/config.py`.

### HTTPX (Client Réseau)
- **Équivalent Node.js** : `Axios` ou le `Fetch API` natif.
- **Rôle** : Bibliothèque Python standard pour effectuer de vrais appels HTTP(s) asynchrones. Remplace le vieillissant module `requests` qui était bloquant.

---

## 4. Data & Persistance

### SQLAlchemy 2.0 (ORM)
- **Équivalent Node.js** : `Prisma` ou `TypeORM`.
- **Rôle** : L'ORM SOTA de Python. Gère les requêtes métier, les modèles typés stricts et les transactions. Attention : en version 2.0 c'est de l'asynchrone natif, le code ressemble beaucoup plus au monde Node.

### Alembic (Migrations)
- **Équivalent Node.js** : Les commandes de migration (`npx prisma migrate` ou TypeORM Migrations).
- **Rôle** : Scanne les modèles Python pour générer dynamiquement l'évolution (les deltas) de l'architecture SQL et l'appliquer en production.

### Psycopg 3 (Driver BDD)
- **Équivalent Node.js** : Le célèbre paquet `pg` (node-postgres).
- **Rôle** : Le traducteur de très bas niveau (écrit en C) qui envoie physiquement les octets TCP asynchrones au port PostgreSQL 5432.

---

## 5. Stack IA Embarquée (`pyproject.toml`)

- **Orchestration** : `temporalio` (pour router et garantir les workflows de validation du claim et du style guide).
- **Generative AI Gateway** : `litellm` (proxy universel).
- **Extraction** : `google-cloud-documentai` & `google-cloud-storage`.

---

## 5. DevOps / Déploiement
- **Dockerfile Multi-Stage** : 
  - Compilation d'un environnement `.venv` virtuel hyper-léger via `uv pip` dans un extracteur `builder`.
  - Copie isolée sur une image base distroless (Slim).
  - Optimisé drastiquement pour les "Cold Starts" ultra exigeants des modules Google Cloud Run.
