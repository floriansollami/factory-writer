# Squelette Temporal Factory Writer

Ce dossier porte le squelette vide de l'orchestration Temporal pour l'architecture cible décrite dans [ARCHITECTURE_SOTA_2026.md](/Users/floriansollami/Documents/GitHub/factory-writer/docs/ARCHITECTURE_SOTA_2026.md).

## Structure

- `task_queues.py` : noms canoniques des task queues Temporal.
- `worker_roles.py` : rôles de workers Cloud Run et mapping depuis la config.
- `activity_options.py` : retry policies et timeouts partagés.
- `client.py` : création du client Temporal avec le converter Pydantic.
- `registry.py` : registre central `role -> queue -> workflows -> activities`.
- `starter.py` : helpers de démarrage et de signal des workflows.
- `worker.py` : bootstrap générique d'un worker selon son rôle.
- `workflows/sku_lifecycle.py` : workflow durable principal par SKU.
- `workflows/style_guide_ingestion.py` : workflow admin pour le style guide.
- `workflows/offline_evaluation.py` : workflow du lab offline.
- `activities/docai_activities.py` : extraction facts / archives techniques.
- `activities/context_activities.py` : chargement des snapshots et publish gate.
- `activities/llm_generation_activities.py` : chaîne claim plan -> redaction plan -> final draft -> review.
- `activities/style_guide_activities.py` : ingestion et promotion du style pack.
- `activities/offline_eval_activities.py` : chargement batch offline, eval Vertex, promotion prompt.

## Règles d'implémentation

- Les workflows restent déterministes et ne parlent à aucun système externe.
- Les appels réseau, SQL, BigQuery, Vertex, Document AI et LiteLLM vivent dans les activities.
- Le runtime produit repose sur `1 workflow par SKU`.
- Le style guide et le lab offline ont leurs propres workflows séparés.
- Les workers sont spécialisés par rôle et par task queue.
- Le worker versioning peut être activé via `TEMPORAL__BUILD_ID`.

## Ordre d'implémentation recommandé

1. Brancher les vraies integrations dans `docai_activities.py`.
2. Brancher les loaders de contexte et le publish gate dans `context_activities.py`.
3. Brancher la chaîne LiteLLM dans `llm_generation_activities.py`.
4. Brancher le workflow admin du style guide.
5. Brancher le workflow offline Vertex.
6. Ajouter replay tests, tests d'activities et tests d'intégration workflow.

## Rôles Cloud Run visés

- `orchestrator` : queue `sku-lifecycle`
- `docai` : queue `docai-activities`
- `llm` : queue `llm-generation`
- `style-admin` : queue `style-ingestion`
- `offline-lab` : queue `offline-eval`
