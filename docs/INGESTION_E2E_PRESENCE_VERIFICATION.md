# Verification de presence e2e du pipeline d'ingestion sur le nouvel ERD

Date de verification : 2026-04-21

Reference schema :
- [ERD_POC_FINAL_SIMPLIFIED.md](/Users/floriansollami/Documents/GitHub/factory-writer/docs/ERD_POC_FINAL_SIMPLIFIED.md)

Hypotheses de cette verification :
- aucune execution provider reelle ;
- aucun test unitaire ou e2e ajoute ;
- verification basee uniquement sur la presence du code et la continuite des chemins d'execution ;
- un pipeline est `present` seulement si la chaine complete existe de l'API a la persistance finale ;
- un pipeline est `partiel` seulement si une chaine executable est entamee mais incomplete ;
- un pipeline est `absent` si seuls le schema ou des briques isolees existent.

## Verdict global

| Domaine | Verdict |
| --- | --- |
| ERD POC simplifie | Conforme |
| Pipeline style guide | e2e present |
| Pipeline dossiers techniques | absent |

## 1. Verdict ERD

Verdict : `schema conforme`

Tables presentes dans le code runtime :
- `taxonomie_produit`
- `product`
- `document_collection`
- `document_source`
- `document_ingestion_run`
- `style_pack`
- `style_rule`
- `technical_fact_candidate`
- `technical_review_case`
- `technical_fact`

Preuves :
- modeles POC : [backend/src/factory_writer/infrastructure/database/models/poc_ingestion.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/infrastructure/database/models/poc_ingestion.py)
- taxonomie partagee : [backend/src/factory_writer/infrastructure/database/models/taxonomy.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/infrastructure/database/models/taxonomy.py)
- export metadata : [backend/src/factory_writer/infrastructure/database/models/__init__.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/infrastructure/database/models/__init__.py)
- migration nouveau schema : [backend/alembic/versions/20260421_0002_add_poc_ingestion_schema.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/alembic/versions/20260421_0002_add_poc_ingestion_schema.py)
- migration drop legacy : [backend/alembic/versions/20260421_0003_drop_legacy_style_guide_schema.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/alembic/versions/20260421_0003_drop_legacy_style_guide_schema.py)

Relations et contraintes confirmees :
- `product.taxonomie_produit_id -> taxonomie_produit.id`
- `document_collection.product_id -> product.id`
- `document_source.collection_id -> document_collection.id`
- `document_ingestion_run.collection_id -> document_collection.id`
- `style_pack.ingestion_run_id -> document_ingestion_run.id`
- `style_rule.pack_id -> style_pack.id`
- `style_rule.taxonomie_produit_id -> taxonomie_produit.id`
- `technical_fact_candidate.ingestion_run_id -> document_ingestion_run.id`
- `technical_fact_candidate.source_id -> document_source.id`
- `technical_review_case.ingestion_run_id -> document_ingestion_run.id`
- `technical_review_case.source_id -> document_source.id` nullable
- `technical_review_case.fact_candidate_id -> technical_fact_candidate.id` nullable
- `technical_fact.product_id -> product.id`
- `technical_fact.source_candidate_id -> technical_fact_candidate.id`
- unicite `technical_fact(product_id, field_name)`
- unicite `technical_fact(source_candidate_id)`
- unicite version GCS sur `document_source(storage_bucket, storage_object_name, storage_generation)`
- unicite workflow sur `document_ingestion_run.temporal_workflow_id`
- unicite pack actif via index partiel `style_pack.est_actif = true`

Statuts verifies au bon endroit :
- `document_collection.statut`
- `document_source.statut`
- `document_ingestion_run.statut`
- `document_ingestion_run.current_step`
- `style_pack.statut`
- `style_rule.decision_editoriale`
- `technical_fact_candidate.validation_status`
- `technical_review_case.status`

Ancien ERD :
- aucune ancienne table legacy n'est encore exposee dans le code runtime ;
- les references restantes vivent seulement dans l'historique Alembic, ce qui est attendu.

Ecart releve :
- aucun ecart bloquant entre le schema runtime et l'ERD POC final simplifie.

## 2. Verdict style guide

Verdict : `e2e present`

### Chaine complete trouvee

| Maillon | Verdict | Preuve |
| --- | --- | --- |
| 1. Endpoint upload | present | [backend/src/factory_writer/api/routes/style_guide_admin_router.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/api/routes/style_guide_admin_router.py) |
| 2. Service upload | present | [backend/src/factory_writer/application/services/style_guide_ingestion_service.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/application/services/style_guide_ingestion_service.py) |
| 3. Port storage | present | [backend/src/factory_writer/application/ports/style_guide_ingestion/storage.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/application/ports/style_guide_ingestion/storage.py) |
| 4. Repository cree `document_collection` + `document_source` | present | [backend/src/factory_writer/infrastructure/database/repositories/style_guide_repository.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/infrastructure/database/repositories/style_guide_repository.py) |
| 5. Endpoint start-ingestion | present | [backend/src/factory_writer/api/routes/style_guide_admin_router.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/api/routes/style_guide_admin_router.py) |
| 6. Service cree `document_ingestion_run` | present | [backend/src/factory_writer/application/services/style_guide_ingestion_service.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/application/services/style_guide_ingestion_service.py) |
| 7. Starter Temporal | present | [backend/src/factory_writer/temporal/style_guide_ingestion/starter.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/temporal/style_guide_ingestion/starter.py) |
| 8. Workflow Temporal | present | [backend/src/factory_writer/temporal/style_guide_ingestion/workflow.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/temporal/style_guide_ingestion/workflow.py) |
| 9. Worker enregistre workflow + activities | present | [backend/src/factory_writer/temporal/style_guide_ingestion/worker.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/temporal/style_guide_ingestion/worker.py), [backend/src/factory_writer/temporal/worker.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/temporal/worker.py) |
| 10. Activity lancement Document AI | present | [backend/src/factory_writer/temporal/style_guide_ingestion/activities.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/temporal/style_guide_ingestion/activities.py) |
| 11. Activity polling / recuperation Document AI | present | [backend/src/factory_writer/temporal/style_guide_ingestion/activities.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/temporal/style_guide_ingestion/activities.py) |
| 12. Client Document AI chunks + provenance | present | [backend/src/factory_writer/infrastructure/gcp/document_ai_client.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/infrastructure/gcp/document_ai_client.py) |
| 13. Generation draft pack | present | [backend/src/factory_writer/application/services/style_guide_ingestion_service.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/application/services/style_guide_ingestion_service.py) |
| 14. Persistance `style_pack` + `style_rule` | present | [backend/src/factory_writer/infrastructure/database/repositories/style_guide_repository.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/infrastructure/database/repositories/style_guide_repository.py) |
| 15. Review humaine admin | partiel | la revue existe dans le frontend, mais n'est pas encore branchee a des endpoints backend dedies |
| 16. Activation via signal / workflow / repository | partiel | la logique service/workflow/repository existe, mais n'est plus exposee par HTTP dans le router admin minimal |
| 17. Promotion finale et maj des tables | present | [backend/src/factory_writer/infrastructure/database/repositories/style_guide_repository.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/infrastructure/database/repositories/style_guide_repository.py) |

### Ce qui est explicitement present

- le workflow utilise les statuts du nouvel ERD, pas ceux de l'ancien schema ;
- `document_ingestion_run.extraction_steps_json` est alimente lors du parse Layout Parser et du draft LLM ;
- `style_rule.source_evidence_text`, `source_evidence_provider_id`, `source_evidence_page_start`, `source_evidence_page_end`, `source_evidence_json` sont renseignes a la creation du draft pack ;
- l'unicite du pack actif est assuree au niveau DB et respectee dans la promotion ;
- l'activation est bloquee tant qu'une regle reste `A_VALIDER` au niveau service ;
- la revue humaine complete existe dans le code, mais n'est pas encore exposee par HTTP dans le router admin minimal.

### Entrées admin exposees

Routes presentes :
- `GET /api/style-guide/overview`
- `POST /api/style-guide/upload`
- `POST /api/style-guide/document-sources/{document_source_id}/start-ingestion`

### Trous eventuels

Le pipeline backend style guide reste complet sous les couches service/workflow/repository, mais la surface HTTP admin a ete volontairement reduite au strict minimum utilise par le frontend actuel.

Reserve non bloquante :
- la verification ne prouve pas l'execution reelle provider-to-provider ; elle conclut uniquement que la chaine de code complete existe et pointe vers les bonnes tables.

## 3. Verdict dossiers techniques

Verdict : `absent`

### Matrice de presence

| Maillon | Verdict | Constat |
| --- | --- | --- |
| 1. Endpoint upload dossier technique | absent | aucun router technique dedie trouve |
| 2. Service d'ingestion technique | absent | aucun service applicatif dedie trouve |
| 3. Creation `document_collection(TECHNICAL_DOSSIER)` + multi-`document_source` | absent | supportee par le schema, mais aucun use case/service ne la cree |
| 4. Creation `document_ingestion_run(TECHNICAL_DOSSIER_EXTRACTION)` | absent | aucun code applicatif ne le fait |
| 5. Orchestrateur / workflow Temporal technique | absent | aucun workflow technique dedie trouve |
| 6. Etape classifier | absent | aucun adapter/use case branche sur le pipeline technique |
| 7. Etape OCR / qualite | absent | aucun pipeline technique branche |
| 8. Etape extractor foundation model | absent | aucun pipeline technique branche |
| 9. Persistance `technical_fact_candidate` | absent | modeles presents, aucun repository/use case technique dedie |
| 10. Persistance `technical_review_case` | absent | modeles presents, aucun use case technique dedie |
| 11. Promotion `technical_fact` | absent | modele present, aucun flux de promotion technique |
| 12. Surface admin review technique | absent | aucun endpoint admin technique dedie |

### Ce qui existe reellement

Present :
- les tables SQLAlchemy du volet technique existent dans [backend/src/factory_writer/infrastructure/database/models/poc_ingestion.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/infrastructure/database/models/poc_ingestion.py) ;
- l'ERD supporte bien les facts candidats, review cases et facts valides.

Absent :
- aucune route FastAPI dediee ;
- aucun service applicatif dedie ;
- aucun repository technique dedie ;
- aucun workflow Temporal technique dedie ;
- aucun worker dedie ;
- aucun adaptateur classifier / OCR / extractor branche au pipeline technique.

Conclusion :
- le schema permet le pipeline dossiers techniques ;
- la feature e2e dossiers techniques n'est pas presente dans le repo actuel.

## 4. Integrations transverses

### Routes FastAPI

Verdict : `coherent pour le style guide, absent pour les dossiers techniques`

Preuves :
- inclusion routeur style guide : [backend/src/factory_writer/main.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/main.py)
- aucune inclusion de routeur technique dedie trouvee.

### Repositories et nouvelles tables

Verdict : `coherent`

Constat :
- le repository actif du style guide ecrit uniquement dans les nouvelles tables du POC ;
- aucune ecriture runtime vers les anciennes tables n'a ete trouvee.

Preuve :
- [backend/src/factory_writer/infrastructure/database/repositories/style_guide_repository.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/infrastructure/database/repositories/style_guide_repository.py)

### Ports applicatifs et clean architecture

Verdict : `coherent`

Constat :
- le service applicatif depend de ports `Protocol` et de snapshots applicatifs ;
- les types infra restent dans les adapters GCP / DB / Temporal / LLM ;
- aucune fuite infra directe n'a ete relevee dans les signatures du service style guide.

Preuves :
- ports applicatifs : [backend/src/factory_writer/application/ports/style_guide_ingestion/document_parser.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/application/ports/style_guide_ingestion/document_parser.py), [backend/src/factory_writer/application/ports/style_guide_ingestion/storage.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/application/ports/style_guide_ingestion/storage.py), [backend/src/factory_writer/application/ports/style_guide_ingestion/workflow_starter.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/application/ports/style_guide_ingestion/workflow_starter.py), [backend/src/factory_writer/application/ports/style_guide_ingestion/draft_pack_generator.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/application/ports/style_guide_ingestion/draft_pack_generator.py), [backend/src/factory_writer/application/ports/style_guide_ingestion/repository.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/application/ports/style_guide_ingestion/repository.py)
- service : [backend/src/factory_writer/application/services/style_guide_ingestion_service.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/application/services/style_guide_ingestion_service.py)

### Worker Temporal principal

Verdict : `coherent`

Constat :
- le dispatcher principal reference bien le worker style guide ;
- aucun worker technique d'ingestion documentaire n'est reference.

Preuves :
- [backend/src/factory_writer/temporal/worker.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/temporal/worker.py)
- [backend/src/factory_writer/temporal/style_guide_ingestion/worker.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/temporal/style_guide_ingestion/worker.py)

### Configs requises

Verdict : `suffisant pour le style guide, insuffisant pour un pipeline technique`

Present pour le style guide :
- GCS bucket
- GCP project/location/processor Document AI
- Temporal address/namespace/worker role
- LLM prompt name/version

Preuves :
- [backend/src/factory_writer/core/config.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/core/config.py)
- [backend/src/factory_writer/infrastructure/gcp/storage_client.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/infrastructure/gcp/storage_client.py)
- [backend/src/factory_writer/infrastructure/gcp/document_ai_client.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/infrastructure/gcp/document_ai_client.py)

Absent pour un pipeline technique :
- aucune config technique distincte pour classifier, OCR, extractor et pipeline dossier technique.

### Legacy et code orphelin

Verdict : `pas de dependance legacy bloqueuse dans le runtime`

Constat :
- le runtime ne depend plus de l'ancien schema style guide ;
- les references restantes a l'ancien ERD survivent seulement dans l'historique Alembic ;
- aucune route legacy style guide n'a ete conservee dans le backend actif.

## Conclusion finale

- `ERD` : conforme au document de reference.
- `Style guide` : la feature e2e est presente dans le code, de l'API jusqu'au remplissage final des tables du nouvel ERD.
- `Dossiers techniques` : la feature e2e n'est pas presente ; seul le schema cible est en place.

Formulation courte defendable :

> Le repo contient bien un pipeline style guide complet branche sur le nouvel ERD. En revanche, le volet dossiers techniques n'est pas encore implemente en e2e : le schema existe, mais la chaine API -> service -> workflow -> persistance -> review n'existe pas encore.
