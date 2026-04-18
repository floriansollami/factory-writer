# Plan d'implémentation POC : ingestion du guide de style

Ce document donne le plan concret pour finir la feature d'ingestion du guide de style dans le POC Factory Writer.

Il est aligné avec :

- [ARCHITECTURE_SOTA_2026.md](/Users/floriansollami/Documents/GitHub/factory-writer/docs/ARCHITECTURE_SOTA_2026.md)
- [FINAL_ARCHITECTURE.md](/Users/floriansollami/Documents/GitHub/factory-writer/docs/FINAL_ARCHITECTURE.md)
- [ARCHITECTURE_STYLE_GUIDE_INGESTION.md](/Users/floriansollami/Documents/GitHub/factory-writer/docs/brand_style_extraction/ARCHITECTURE_STYLE_GUIDE_INGESTION.md)

## Objectif POC

Le scénario cible est le suivant :

1. un PDF de guide de style arrive dans GCS
2. Eventarc appelle l'API Cloud Run
3. l'API crée ou réutilise une source de guide de style
4. l'API démarre `StyleGuideIngestionWorkflow`
5. le workflow parse le PDF avec Document AI
6. le workflow persiste les fragments utiles
7. le workflow génère un draft pack structuré
8. un humain approuve ou rejette
9. le draft approuvé devient le pack actif utilisé au runtime

## Ce qui existe déjà dans le code

- route Eventarc : [eventarc_router.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/api/routes/eventarc_router.py)
- service applicatif : [style_guide_ingestion_service.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/application/services/style_guide_ingestion_service.py)
- workflow Temporal : [workflow.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/temporal/style_guide_ingestion/workflow.py)
- activities Temporal : [activities.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/temporal/style_guide_ingestion/activities.py)
- modèles DB : [style_guide.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/infrastructure/database/models/style_guide.py)

Aujourd'hui, le workflow et les activities style guide sont câblés pour le POC.

## Recommandation SOTA 2026 pour ce cas

Pour un guide de style de marque, la bonne approche n'est pas de faire une chaîne full-LLM non gouvernée.

Le pattern sérieux est :

- source versionnée
- parsing déterministe du document
- fragments avec provenance
- draft structuré par LLM en JSON strict
- validations déterministes
- review humaine
- promotion transactionnelle d'un seul pack actif

Autrement dit :

- le LLM prépare
- les validateurs filtrent
- l'humain approuve

## Roadmap unique

| Ordre | Tâche | Ce qu'on implémente | Résultat attendu |
| --- | --- | --- | --- |
| 1 | Stabiliser les statuts DB | implémenter `mark_style_source_in_progress_activity` et `mark_style_source_failed_activity` avec vraie persistance | le workflow reflète correctement `EN_COURS` et `ERREUR` |
| 2 | Ajouter la provenance minimale | compléter les modèles et la migration avec génération GCS, métadonnées Document AI et erreur minimale | le POC sait d'où vient exactement un pack |
| 3 | Brancher Document AI Layout Parser | remplacer `trigger_style_layout_parse_activity` par un vrai appel Document AI | le PDF produit une sortie de parsing exploitable |
| 4 | Persister les fragments | remplacer `persist_style_fragments_activity` par une vraie normalisation des sections/chunks | les fragments du guide sont stockés en base |
| 5 | Générer le draft pack | remplacer `generate_style_pack_draft_activity` par un appel LiteLLM avec structured output | un `PackStyle` brouillon et ses règles sont créés |
| 6 | Valider le draft | ajouter validation déterministe du JSON produit avant persistance | seules les sorties valides passent |
| 7 | Gérer l'approbation humaine | attendre un signal `approve_pack` avec `approved: true/false` | le pack n'est activé qu'après validation humaine |
| 8 | Promouvoir le pack actif | remplacer `promote_style_pack_activity` par une vraie transaction | un seul pack actif existe au runtime |
| 9 | Brancher la lecture runtime | faire lire le pack actif par le runtime produit | la génération de fiches n'utilise plus le PDF brut |
| 10 | Ajouter les tests critiques | tests d'activities, tests de workflow, tests d'idempotence | le flux est fiable pour le POC |

## Plan détaillé par activity

### 1. `mark_style_source_in_progress_activity`

**But**

Passer la source du guide de style à `EN_COURS` au démarrage du workflow.

**À faire**

- charger `SourceGuideStyle` par `source_id`
- si la source est déjà `EN_COURS`, ne rien faire
- si la source est `EN_ATTENTE` ou `ERREUR`, la passer à `EN_COURS`
- ne jamais écraser une source déjà terminée

**Pourquoi**

Cette activity doit être idempotente. En Temporal, une activity peut être rejouée ou retentée.

**Résultat**

- statut fiable
- reprise propre en cas de retry

### 2. `mark_style_source_failed_activity`

**But**

Passer la source à `ERREUR` quand le workflow échoue.

**À faire**

- charger la source
- si la source est déjà `TERMINE`, ne pas la dégrader
- sinon passer à `ERREUR`
- persister un message d'erreur minimal si le modèle le permet

**Pourquoi**

Il faut pouvoir relancer proprement un guide échoué sans perdre la visibilité métier.

### 3. `trigger_style_layout_parse_activity`

**But**

Appeler Document AI Layout Parser sur le PDF du guide de style.

**À faire**

- lire l'URI GCS de la source
- capturer les métadonnées minimales du fichier
  - bucket
  - object name
  - generation GCS
  - metageneration
- appeler Document AI avec une version explicite de processor
- stocker au minimum
  - `docai_operation_id`
  - `docai_output_uri`
  - `docai_processor_version`

**À prévoir**

- output URI déterministe par `source_id` et génération GCS
- heartbeat si l'appel est long
- réutilisation si le même document exact a déjà été parsé avec la même config

**Résultat**

Le workflow obtient un `StyleGuideLayoutParseResult` réel, pas un placeholder.

### 4. `persist_style_fragments_activity`

**But**

Transformer la sortie Document AI en fragments persistés en base.

**À faire**

- relire le JSON produit par Document AI
- extraire les sections utiles
- normaliser les fragments
  - index stable
  - titre de section
  - contenu textuel
- supprimer puis recréer les fragments de la source dans une même transaction pour le POC

**Pourquoi**

Le runtime d'extraction LLM ne doit jamais dépendre directement du PDF brut. Il doit travailler sur des fragments propres et rejouables.

**Validation minimale**

- au moins un fragment
- pas de fragment vide
- index monotone

### 5. `generate_style_pack_draft_activity`

**But**

Créer un draft pack structuré à partir des fragments.

**À faire**

- charger les fragments persistés
- appeler LiteLLM avec structured output
- demander une sortie atomique et gouvernable
  - voix de marque
  - profils de ton
  - règles hard
  - règles soft
  - promesses interdites
  - provenance fragment par règle
- valider le JSON avant insertion
- créer `PackStyle` en `BROUILLON`
- créer les `RegleStyle` associées

**Pourquoi**

Le bon niveau de sortie n'est pas un texte libre. C'est un pack structuré, versionnable et injecté ensuite dans les prompts runtime.

### 6. Validation déterministe du draft

Cette validation peut être codée dans `generate_style_pack_draft_activity` au début du POC.

**À vérifier**

- enums valides
- niveaux de contrainte valides
- texte de règle non vide
- `fragment_source_id` existant
- absence de doublons évidents
- cohérence minimale entre portée et règle

**Important**

Pour le POC, cette validation déterministe + review humaine suffit. Il n'est pas nécessaire d'ajouter toute une chaîne de prompt optimization et de judge-based evaluation sur ce flux d'ingestion rare.

### 7. `promote_style_pack_activity`

**But**

Promouvoir un brouillon approuvé en pack actif.

**À faire**

- charger le draft pack
- désactiver l'ancien pack actif
- activer le nouveau pack
- marquer la source comme `TERMINE`
- stocker la date d'approbation

**Pourquoi**

La promotion doit être transactionnelle. Le runtime ne doit jamais voir deux packs actifs simultanément.

### 8. Signal d'approbation

Le workflow supporte déjà le signal `approve_pack`, mais il faut mieux l'exploiter.

**À faire**

- attendre `approved: true/false`
- refuser proprement si le signal vaut `false`
- promouvoir le pack si le signal vaut `true`

**Résultat**

La validation humaine reste simple pour le POC. Les métadonnées avancées de review sont un ajout POC+.

## Ajustements de modèle recommandés pour le POC

Il ne faut pas surmodéliser, mais quelques champs manquent pour un POC propre.

### `SourceGuideStyle`

Ajouter au minimum :

- `storage_uri`
- `storage_generation`
- `storage_metageneration`
- `parser_resource_id`
- `parser_operation_id`
- `parser_output_uri`
- `dernier_message_erreur`

### `FragmentStyle`

Ajouter si simple à faire :

- `page_debut`
- `page_fin`
- `chemin_section`

### `PackStyle`

Ajouter au minimum :

- `prompt_registry_provider`
- `prompt_name`
- `prompt_version`
- `llm_model`
- `llm_temperature`
- `llm_max_tokens`
- `llm_response_format`
- `system_prompt_hash`
- `user_prompt_hash`
- `approuve_le`

## Ordre d'implémentation recommandé

Il faut coder dans cet ordre, sinon le flux reste cassé ou difficile à tester.

1. activités DB de statut
2. migration légère de provenance
3. activity Document AI
4. activity de persistance des fragments
5. activity de génération du draft pack
6. propagation de l'approbation humaine
7. activity de promotion
8. lecture runtime du pack actif
9. tests

## Tests minimums à prévoir

| Niveau | Test | But |
| --- | --- | --- |
| unit | activity `mark_style_source_in_progress_activity` | vérifier idempotence et transitions de statut |
| unit | activity `mark_style_source_failed_activity` | vérifier qu'on ne dégrade pas une source terminée |
| unit | parsing fragments | vérifier la normalisation du résultat Document AI |
| unit | validation draft pack | vérifier enums, provenance, règles vides |
| workflow | happy path | source -> parse -> fragments -> draft -> approve -> promote |
| workflow | reject path | vérifier retour `rejected` |
| workflow | failure path | vérifier passage à `ERREUR` |

## Definition of done du POC

Le POC est terminé quand on peut :

1. déposer un PDF de guide de style dans le bucket GCS
2. voir Eventarc appeler l'API
3. voir le workflow Temporal démarrer
4. voir la source passer à `EN_COURS`
5. voir Document AI parser le PDF
6. voir les fragments stockés en base
7. voir un pack brouillon créé en base
8. approuver le draft
9. voir un seul `PackStyle` actif
10. charger ce pack actif depuis le runtime produit

## Ce qu'il ne faut pas faire maintenant

Pour ce POC, il ne faut pas complexifier trop tôt avec :

- un judge LLM complet sur l'ingestion du style guide
- des métriques pairwise Vertex sur chaque draft de style
- une calibration avancée du judge
- une optimisation continue du prompt du style guide

Ce sera utile plus tard seulement si Axolotl commence à ingérer fréquemment plusieurs guides, plusieurs langues ou plusieurs variantes de voice pack.
