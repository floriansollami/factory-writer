# Plan de mise à jour du déploiement : API + workers Temporal

Ce document explique comment mettre à jour le déploiement pour que le nouveau squelette Temporal soit cohérent avec l'architecture cible et réellement déployable.

Il part de l'existant du repo :

- [backend/Dockerfile](/Users/floriansollami/Documents/GitHub/factory-writer/backend/Dockerfile)
- [.github/workflows/deploy.yml](/Users/floriansollami/Documents/GitHub/factory-writer/.github/workflows/deploy.yml)
- [backend/src/main.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/main.py)
- [backend/src/temporal/worker.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/temporal/worker.py)
- [backend/src/temporal/registry.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/temporal/registry.py)
- [docs/ARCHITECTURE_SOTA_2026.md](/Users/floriansollami/Documents/GitHub/factory-writer/docs/ARCHITECTURE_SOTA_2026.md)

## 1. Constat actuel

Le code Temporal a changé, mais le déploiement ne suit pas encore.

### Ce qui est bien

- on a maintenant un vrai `main()` worker dans [worker.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/temporal/worker.py)
- le code supporte plusieurs rôles de workers via [worker_roles.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/temporal/worker_roles.py)
- le registre route déjà correctement `role -> queue -> workflows -> activities` via [registry.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/temporal/registry.py)
- le Dockerfile est déjà pensé pour être surchargé par Cloud Run

### Ce qui ne colle plus

| Sujet | Situation actuelle | Problème |
| --- | --- | --- |
| Worker pools | un seul worker pool `factory-writer-worker` | le squelette Temporal attend plusieurs rôles |
| Variable `TEMPORAL__WORKER_ROLE` | non passée dans le déploiement worker | le worker démarre par défaut en `style-admin`, ce qui est implicite et fragile |
| Commandes de lancement | `uvicorn src.main:app` et `python -m src.temporal.worker` | le packaging fonctionne, mais ce n'est pas le chemin le plus propre avec `PYTHONPATH=/app/src` |
| Worker versioning | le code le supporte | la CI/CD ne passe pas encore de `build_id` ni de stratégie de rollout |
| Migrations DB | pas de step dédié | dangereux dès que le schéma Temporal/style guide bouge |
| Docker image | copie seulement `src/` | impossible d'exécuter Alembic depuis l'image telle quelle |
| Local dev | `docker-compose.yml` ne démarre que Postgres | il manque au minimum un Temporal dev server ou une convention claire vers Temporal Cloud |

## 2. Décision cible recommandée

Pour rester simple et propre, je recommande :

- **une seule image Docker**
- **un service Cloud Run pour l'API**
- **un worker pool Cloud Run par rôle Temporal**
- **un job de migration séparé**
- **une CI/CD avec matrix pour les workers**

### Topologie cible

| Composant | Type | Nom recommandé | Commande |
| --- | --- | --- | --- |
| API HTTP | Cloud Run service | `factory-writer-api` | `uvicorn main:app --host 0.0.0.0 --port 8080` |
| Worker orchestrator | Cloud Run worker pool | `factory-writer-orchestrator` | `python -m temporal.worker` |
| Worker docai | Cloud Run worker pool | `factory-writer-docai` | `python -m temporal.worker` |
| Worker llm | Cloud Run worker pool | `factory-writer-llm` | `python -m temporal.worker` |
| Worker style-admin | Cloud Run worker pool | `factory-writer-style-admin` | `python -m temporal.worker` |
| Worker offline-lab | Cloud Run worker pool | `factory-writer-offline-lab` | `python -m temporal.worker` |
| Migration DB | Cloud Run Job ou step CI dédié | `factory-writer-db-migrate` | `alembic upgrade head` |

La différence entre les workers ne vient pas de la commande, mais de :

- `TEMPORAL__WORKER_ROLE`
- leur nom
- leur scaling
- éventuellement leurs secrets / IAM

## 3. Recommandation POC

Pour le POC, il ne faut pas tout déployer tout de suite.

### POC minimal aujourd'hui

Déployer seulement :

- `factory-writer-api`
- `factory-writer-style-admin`

Parce que :

- c'est la seule chaîne Temporal déjà engagée fonctionnellement
- `orchestrator`, `docai`, `llm` et `offline-lab` existent surtout comme squelette

### POC extensible demain

La CI/CD doit être conçue dès maintenant pour supporter tous les rôles, mais avec un système `enabled: true/false` par worker.

## 4. Ce qu'il faut changer

## 4.1. Dockerfile

### Objectif

Avoir une image unique capable de :

- lancer l'API
- lancer n'importe quel worker
- lancer les migrations

### Changements recommandés

| Ordre | Changement | Pourquoi |
| --- | --- | --- |
| 1 | garder `PYTHONPATH=/app/src` | permet des imports simples |
| 2 | standardiser les commandes sur `main:app` et `temporal.worker` | plus propre que `src.main` / `src.temporal.worker` |
| 3 | copier `alembic.ini` et `alembic/` dans l'image | nécessaire pour exécuter les migrations depuis l'image |
| 4 | définir un `CMD` par défaut pour l'API | le service HTTP devient le comportement standard |

### Commandes recommandées

- API : `uvicorn main:app --host 0.0.0.0 --port 8080`
- Worker : `python -m temporal.worker`
- Migration : `alembic upgrade head`

## 4.2. GitHub Actions

### Objectif

Passer de :

- un build
- un déploiement API
- un seul worker pool

à :

- un build
- une migration DB
- un déploiement API
- un déploiement matrix des worker pools

### Structure recommandée

| Étape | Action |
| --- | --- |
| 1 | build + push de l'image unique |
| 2 | exécution des migrations |
| 3 | déploiement de l'API |
| 4 | déploiement des worker pools activés |

### Recommandation de matrix workers

| role | worker_pool | enabled_poc |
| --- | --- | --- |
| `style-admin` | `factory-writer-style-admin` | `true` |
| `orchestrator` | `factory-writer-orchestrator` | `false` |
| `docai` | `factory-writer-docai` | `false` |
| `llm` | `factory-writer-llm` | `false` |
| `offline-lab` | `factory-writer-offline-lab` | `false` |

Chaque worker reçoit au minimum :

- `TEMPORAL__ADDRESS`
- `TEMPORAL__NAMESPACE`
- `TEMPORAL__WORKER_ROLE`
- `TEMPORAL__DEPLOYMENT_NAME`
- secrets nécessaires

## 4.3. Worker role explicite

Aujourd'hui, le code peut démarrer sans `TEMPORAL__WORKER_ROLE` parce que la config a un défaut `style-admin`.

Pour le déploiement, ce n'est **pas** une bonne idée.

### Recommandation

- en CI/CD, toujours définir explicitement `TEMPORAL__WORKER_ROLE`
- ne jamais dépendre du défaut pour la prod

Sinon :

- on déploie un worker qui a l'air générique
- mais qui poll en réalité uniquement `style-ingestion`

## 4.4. Worker Versioning

Le code supporte déjà le `build_id`, mais il faut éviter de le brancher à moitié.

### Recommandation POC

Pour l'instant :

- **laisser `TEMPORAL__BUILD_ID` non défini**
- donc **désactiver de fait le Worker Versioning**

Pourquoi :

- le code est prêt
- mais la CI/CD ne gère pas encore un rollout versionné Temporal propre

### Recommandation plus tard

Quand la chaîne sera stable :

- passer `TEMPORAL__BUILD_ID=${{ github.sha }}`
- gérer explicitement le rollout des nouvelles versions de workers

Donc :

- **code prêt**
- **ops pas encore prêtes**

Pour un POC, il vaut mieux assumer ça clairement.

## 4.5. Migrations DB

Aujourd'hui, c'est le plus gros angle mort du déploiement.

### Problème

- le schéma va bouger
- il n'y a pas de step de migration
- l'image ne contient pas encore Alembic

### Recommandation

Ajouter un vrai bloc migration avant le déploiement API/workers.

### Option recommandée

- **Cloud Run Job** de migration, depuis la même image

### Option acceptable POC

- step GitHub Actions dédié qui exécute `alembic upgrade head`

Mais dans tous les cas :

- migration **avant** API
- migration **avant** workers

## 4.6. docker-compose local

Le `docker-compose.yml` n'est plus aligné avec le code.

### Problème

Il démarre uniquement :

- Postgres

alors que le code a maintenant besoin aussi de :

- Temporal

### Recommandation

Pour le dev local, choisir une stratégie claire :

### Option A

- utiliser **Temporal Cloud** aussi en local via `.env`

### Option B

- ajouter un **Temporal dev server** local au `docker-compose`

Pour un POC équipe, l'option B est souvent plus simple.

## 5. Scaling recommandé par rôle

Comme les worker pools Cloud Run sont encore en preview et à scaling manuel, il faut garder un plan simple.

| Rôle | Scaling POC recommandé |
| --- | --- |
| API | autoscaling Cloud Run normal |
| style-admin | `1` instance |
| orchestrator | `0` tant que non utilisé |
| docai | `0` tant que non utilisé |
| llm | `0` tant que non utilisé |
| offline-lab | `0` tant que non utilisé |

Quand le runtime SKU sera branché :

- `orchestrator = 1`
- `docai = 1`
- `llm = 1`

## 6. Ordre de mise à jour recommandé

| Ordre | Tâche |
| --- | --- |
| 1 | standardiser les commandes de lancement API et worker |
| 2 | mettre à jour le Dockerfile pour inclure Alembic |
| 3 | ajouter la stratégie de migration DB |
| 4 | refactorer la GitHub Action en `build -> migrate -> deploy api -> deploy workers` |
| 5 | déployer le worker `style-admin` avec `TEMPORAL__WORKER_ROLE=style-admin` |
| 6 | vérifier le scénario POC style guide de bout en bout |
| 7 | ensuite seulement ouvrir les rôles `orchestrator`, `docai`, `llm` |

## 7. Résumé exécutif

La bonne mise à jour n'est pas de bricoler le worker existant.

La bonne mise à jour est :

- garder **une seule image**
- déployer **plusieurs worker pools spécialisés**
- rendre le rôle worker **explicite**
- **ne pas activer tout de suite** le Worker Versioning en prod
- ajouter une vraie étape de **migration DB**
- limiter le POC déployé aujourd'hui à :
  - API
  - style-admin

Comme ça :

- le squelette Temporal reste cohérent
- le déploiement reste simple
- on ne déploie pas des rôles pas encore utilisés
