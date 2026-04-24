# Architecture de gestion des erreurs

Ce document fixe une approche simple, lisible et compatible `clean architecture` pour Factory Writer.

L'objectif est d'avoir :

- des erreurs métier compréhensibles
- des frontières explicites
- des retries Temporal cohérents
- des réponses HTTP propres
- un code facile à lire pour un POC

---

## 1. Principe directeur

Chaque couche a un rôle précis :

- **domaine / application** : exprime les erreurs métier et les règles du produit
- **infrastructure** : capte les erreurs techniques fournisseurs et les traduit
- **API** : transforme les erreurs applicatives en réponses HTTP
- **Temporal activities** : transforme les erreurs applicatives en `ApplicationError`
- **Temporal workflows** : orchestrent, mais ne décident pas de la logique fine d’erreur technique

Donc :

- pas de `HTTPException` dans les services
- pas de `ApplicationError` dans le domaine
- pas de `ValueError` / `RuntimeError` pour des cas métier connus
- pas de `except Exception: return 200`

---

## 2. Hiérarchie recommandée

Il faut une hiérarchie courte.

### Base

| Classe | Rôle | Retryable | HTTP par défaut |
| --- | --- | --- | --- |
| `FactoryWriterError` | erreur applicative racine | non | `500` |
| `ValidationError` | entrée invalide ou contrat violé | non | `400` ou `422` |
| `ConflictError` | conflit métier / idempotence | non | `409` |
| `NotFoundError` | ressource absente | non | `404` |
| `ConfigurationError` | config serveur invalide | non | `500` |
| `TransientDependencyError` | dépendance temporairement indisponible | oui | `503` |
| `PermanentDependencyError` | dépendance en échec définitif | non | `502` ou `500` |

### Spécialisations projet utiles

| Classe | Hérite de | Quand l’utiliser | Retryable |
| --- | --- | --- | --- |
| `WrongBucketError` | `ValidationError` | un event GCS arrive d’un bucket non attendu | non |
| `NotAPdfError` | `ValidationError` | le fichier reçu n’est pas un PDF | non |
| `InvalidGcsUriError` | `ValidationError` | URI `gs://` mal formée | non |
| `InvalidStyleGuideDocumentSourceIdError` | `ValidationError` | `document_source_id` invalide | non |
| `StyleGuideAlreadyExistsError` | `ConflictError` | ingestion déjà en cours ou déjà faite | non |
| `StyleGuideObjectNotFoundError` | `NotFoundError` | objet GCS introuvable | non |
| `WorkflowStartError` | `TransientDependencyError` | impossible de démarrer un workflow Temporal | oui |
| `DocumentAIOutputMissingError` | `TransientDependencyError` | sortie Document AI attendue mais absente | oui |

---

## 3. Matrice par couche

| Couche | Ce qu’elle peut lever | Ce qu’elle ne doit pas lever |
| --- | --- | --- |
| `domain` / `application` | `FactoryWriterError` et sous-classes | `HTTPException`, `ApplicationError`, `GoogleAPICallError`, `IntegrityError` |
| `infrastructure` | traduit une erreur technique en `FactoryWriterError` | laisse remonter brute une erreur fournisseur connue |
| `api` | presque rien, elle mappe surtout | erreurs SQLAlchemy / GCP / Temporal brutes |
| `temporal activities` | `ApplicationError` à partir de `FactoryWriterError` | erreurs métier silencieuses non mappées |
| `temporal workflows` | `ActivityError` ou erreurs d’orchestration | logique détaillée de classification technique |

---

## 4. Mapping HTTP

L’API doit renvoyer des réponses `application/problem+json`.

### Règle

- erreur applicative connue : réponse HTTP standardisée
- erreur inattendue : `500`
- événement volontairement ignoré : `200`

### Tableau

| Erreur | HTTP | Comportement API |
| --- | --- | --- |
| `ValidationError` | `400` ou `422` | retourne une erreur client claire |
| `ConflictError` | `409` | explique qu’un traitement existe déjà |
| `NotFoundError` | `404` | ressource absente |
| `ConfigurationError` | `500` | erreur serveur non retryable |
| `TransientDependencyError` | `503` | erreur serveur temporaire, retry externe possible |
| erreur inconnue | `500` | log `exception`, réponse générique |

### Cas upload admin guide de style

Pour les endpoints admin :

- fichier non PDF : `400`
- PDF vide ou trop volumineux : `400` ou `413`
- source introuvable au démarrage : `404`
- ingestion déjà terminée : `409`
- panne DB / Temporal / GCS / config : `500` ou `503`

Le point important :

- l'import du PDF ne démarre pas Temporal
- seul `POST /api/style-guide/document-sources/{document_source_id}/start-ingestion` démarre le workflow
- `500/503` veut dire "échec réel, retry externe possible"

---

## 5. Mapping Temporal

Les retries doivent être décidés à la frontière des **activities**.

### Règle

- erreur métier définitive : `ApplicationError(non_retryable=True)`
- erreur transitoire : `ApplicationError(non_retryable=False)`
- erreur inconnue : laisser remonter, avec retry policy bornée

### Tableau

| Erreur applicative | Mapping Temporal | Effet |
| --- | --- | --- |
| `ValidationError` | `ApplicationError(..., non_retryable=True)` | stop immédiat |
| `ConflictError` | `ApplicationError(..., non_retryable=True)` | stop immédiat |
| `NotFoundError` | `ApplicationError(..., non_retryable=True)` | stop immédiat |
| `ConfigurationError` | `ApplicationError(..., non_retryable=True)` | stop immédiat |
| `TransientDependencyError` | `ApplicationError(..., non_retryable=False)` | retry activité |
| `PermanentDependencyError` | `ApplicationError(..., non_retryable=True)` | stop immédiat |

### Exemple concret

| Cas | Décision |
| --- | --- |
| mauvais bucket | non retryable |
| fichier non PDF | non retryable |
| `source_id` invalide | non retryable |
| Document AI indisponible temporairement | retryable |
| Temporal indisponible au démarrage | retryable |
| sortie Document AI absente alors qu’elle devrait exister | retryable au début, puis borné par `schedule_to_close_timeout` |

---

## 6. Timeouts et retry policy

Le pattern recommandé :

- **workflow** : pas de retry global par défaut
- **activities** : retries explicites, bornés, par type de dépendance

### Rôle des timeouts

| Timeout | Sert à quoi |
| --- | --- |
| `start_to_close_timeout` | durée max d’une tentative |
| `schedule_to_close_timeout` | budget total d’exécution avec retries |
| `heartbeat_timeout` | détecter une activity longue bloquée |

### Reco simple pour le POC

| Type d’activity | `start_to_close` | `schedule_to_close` | Retry |
| --- | --- | --- | --- |
| DB courte | 10 à 30 sec | 1 à 2 min | faible |
| GCS lecture métadonnées | 15 à 30 sec | 2 à 3 min | faible |
| Document AI LRO | 2 à 5 min | 10 à 15 min | borné |
| LLM rédaction | 30 à 90 sec | 3 à 5 min | borné |
| attente humaine | pas un retry, mais `workflow.wait_condition` | selon besoin métier | aucun |

### Règle pratique

- pas de retries infinis
- `maximum_attempts` borné
- `non_retryable_error_types` explicites

---

## 7. Matrice orientée projet

### 7.1 API admin style guide

| Étape | Si ça échoue | Type d’erreur attendu | HTTP |
| --- | --- | --- | --- |
| upload fichier | fichier non PDF | `ValidationError` | `400` |
| upload fichier | fichier trop volumineux | `ValidationError` | `413` |
| création source | GCS ou DB indisponible | `TransientDependencyError` | `503` |
| démarrage ingestion | source absente | `NotFoundError` | `404` |
| démarrage ingestion | source déjà terminée | `ConflictError` | `409` |
| démarrage Temporal | Temporal indisponible | `WorkflowStartError` | `503` |

### 7.2 Service d’ingestion style guide

| Étape | Erreur recommandée | Pourquoi |
| --- | --- | --- |
| URI GCS invalide | `InvalidGcsUriError` | contrat violé |
| `document_source_id` invalide | `InvalidStyleGuideDocumentSourceIdError` | contrat violé |
| storage adapter absent | `ConfigurationError` | bug de wiring |
| parser Document AI absent | `ConfigurationError` | bug de wiring |
| objet GCS introuvable | `StyleGuideObjectNotFoundError` | état réel du fichier |
| sortie DocAI absente | `DocumentAIOutputMissingError` | dépendance incomplète / transitoire |

### 7.3 Activities Temporal

| Activity | Si erreur applicative | Action |
| --- | --- | --- |
| `mark_source_in_progress` | map vers `ApplicationError` | stop ou retry selon type |
| `parse_layout` | map vers `ApplicationError` | retry si dépendance transitoire |
| `persist_fragments` | map vers `ApplicationError` | souvent retryable si DB |
| `generate_draft_pack` | map vers `ApplicationError` | retry borné si LLM |
| `promote_pack` | map vers `ApplicationError` | stop si conflit définitif |

### 7.4 Workflow

| Cas | Ce que fait le workflow |
| --- | --- |
| une activity échoue définitivement | marque la source en erreur, termine |
| une activity est retryable | laisse Temporal rejouer selon la policy |
| signal humain `approve=false` | termine proprement avec statut rejeté |
| signal humain absent | timeout métier, pas un retry technique |

---

## 8. Logging

### Règle

Une erreur doit être loggée **une seule fois** avec stack trace, à la frontière qui la traite vraiment.

### Recommandation

| Endroit | Niveau de log recommandé |
| --- | --- |
| traduction d’une erreur métier attendue | `warning` |
| erreur inattendue dans API | `exception` |
| erreur inattendue dans activity | `exception` |
| domaine / application | pas de stack trace par défaut |

### Règle de code

- utiliser `raise NouveauType(...) from exc`
- ne pas perdre la cause
- ne pas logger puis ré-emballer puis re-logger partout

---

## 9. Règles SQLAlchemy

Pour toute opération transactionnelle :

- `commit` sur le chemin nominal
- `rollback` dans le repository ou l’unité transactionnelle si l’écriture échoue
- traduire l’erreur SQLAlchemy utile
- relancer une erreur applicative explicite

Exemples :

- contrainte unique cassée : `ConflictError`
- connexion DB temporairement indisponible : `TransientDependencyError`

---

## 10. Ce qu’il faut faire maintenant dans le code

Ordre recommandé :

1. créer `FactoryWriterError` et les sous-classes principales
2. remplacer les `ValueError` / `RuntimeError` métier dans les services
3. ajouter un handler FastAPI global `problem+json`
4. ajouter un mapper `FactoryWriterError -> ApplicationError` côté Temporal
5. revoir les routes admin pour distinguer clairement validation, conflit et dépendance indisponible
6. revoir les retry policies des activities

---

## 11. Résumé exécutable

La règle la plus importante du projet est :

- **le domaine parle métier**
- **l’infra traduit la technique**
- **l’API parle HTTP**
- **Temporal parle retry**

Si cette séparation est respectée, le projet reste simple à lire même avec plusieurs workflows et plusieurs activities.
