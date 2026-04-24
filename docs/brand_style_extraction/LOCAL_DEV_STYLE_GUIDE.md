# Local Dev Style Guide

Ce setup local est celui recommandé pour le POC :

- `Postgres` local via Docker
- `Temporal` local via Docker
- `API FastAPI` sur le host
- `worker Temporal` sur le host
- `Cloud Storage` réel
- `Document AI` réel
- déclenchement explicite de l'ingestion via l'API locale

L'objectif est simple :

1. uploader un vrai PDF via l'API locale
2. laisser l'API stocker le PDF dans Cloud Storage
3. lancer explicitement l'ingestion depuis l'API locale
4. laisser le worker local exécuter les activities
5. observer l'exécution dans les logs locaux et dans Temporal UI

## 1. Pré-requis

- Docker Desktop
- `uv`
- `gcloud`
- accès au projet GCP
- accès au bucket de style guide
- accès au processor Document AI

Authentification GCP locale :

```bash
gcloud auth application-default login
```

## 2. Variables d'environnement

Copier le fichier exemple :

```bash
cp .env.local.example .env.local
```

Puis renseigner au minimum :

- `GCP__PROJECT_ID`
- `GCP__DOCUMENT_AI_PROCESSOR_ID`
- `GCP__STYLE_GUIDE_BUCKET_NAME`

Le reste fonctionne avec les defaults du POC local.

Pour ce repo, le fichier `.env.local` peut déjà être prérempli ainsi :

- `GCP__PROJECT_ID=factory-writer-poc-1776097019`
- `GCP__STYLE_GUIDE_BUCKET_NAME=factory-writer-poc-1776097019-brand-styles`

Il reste surtout à renseigner :

- `GCP__DOCUMENT_AI_PROCESSOR_ID`

Selon la doc officielle Google Cloud Document AI :

- la page **Processors** de la console liste tous les processors du projet
- l'onglet **Overview** d'un processor affiche notamment **Name**, **ID**, **Type** et **Prediction endpoint**

Donc ici, le plus simple est :

1. ouvrir la console GCP
2. aller dans `Document AI > Processors`
3. cliquer sur le processor utilisé pour le style guide
4. copier le champ **ID**
5. le coller dans `GCP__DOCUMENT_AI_PROCESSOR_ID`

Référence officielle :

- `Creating and managing processors` : la doc décrit explicitement la page **Processors** et l'onglet **Overview** du processor.

## 3. Démarrer l'infrastructure locale

```bash
make infra-up
```

Services démarrés :

- Postgres sur `localhost:5432`
- Temporal gRPC sur `localhost:7233`
- Temporal UI sur `http://localhost:8233`

Suivre les logs si besoin :

```bash
make infra-logs
```

## 4. Migrer la base

```bash
make db-migrate
```

## 5. Lancer l'API locale

Dans un terminal :

```bash
make api
```

L'API écoute sur `http://localhost:8080`.

## 6. Lancer le worker local

Dans un second terminal :

```bash
make worker-style
```

Le worker local poll la task queue `style-guide-ingestion` sur le Temporal local.

## 7. Déclencher le flow depuis l'admin

Ouvrez l'admin local, importez le PDF, puis lancez l'analyse depuis l'écran de vérification.

```bash
make frontend-real
```

Ce mode reflète le flow admin POC : l'import du PDF et le démarrage de l'ingestion restent deux actions explicites.

## 8. Ce que tu dois observer

### Logs API

Tu dois voir l'upload traité puis le workflow démarré après l'appel `start-ingestion`.

### Logs worker

Tu dois voir les étapes :

- `start_docai_job`
- `check_docai_job`
- `generate_draft_pack`

### Temporal UI

Tu dois voir un workflow `StyleGuideIngestionWorkflow` dans `http://localhost:8233`.

## 9. Important : pourquoi ça s'arrête ensuite

Le workflow style guide attend un signal humain `approve_pack`.

C'est normal si l'exécution se met en attente après `generate_draft_pack`.

Pour terminer le workflow :

1. ouvrir Temporal UI
2. ouvrir le workflow
3. envoyer le signal `approve_pack`
4. utiliser un payload du type :

```json
{
  "approved": true
}
```

## 10. Pourquoi on ne branche pas un vrai Eventarc vers localhost

Pour ce POC, on ne cherche pas à faire :

- `Cloud Storage -> Eventarc -> localhost`

On fait :

- `Cloud Storage réel`
- `Document AI réel`
- `API locale explicite`

C'est le bon compromis :

- plus simple
- plus rapide
- suffisamment réaliste
- adapté au dev local

## 11. Arrêter l'infra locale

```bash
make infra-down
```
