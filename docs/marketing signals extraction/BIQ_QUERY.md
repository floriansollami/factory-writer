Oui. Voici la **réponse globale refaite jusqu’au point 9**, avec les 3 améliorations demandées :

- j’explique **qui produit le score** et ce que dit réellement la doc BigQuery ;
- j’explique pourquoi j’utilise parfois du **JSON comme exemple**, alors qu’en vrai on parle bien de **tables BigQuery** ;
- je refais le **point 7** pour que `mart.review_signal_by_segment` soit vraiment clair.

## 1. Les 3 tables brutes de départ

### `raw.sales_history`

| Field (EN)         | Champ (FR)                    | Description                             | Exemple                   |
| ------------------ | ----------------------------- | --------------------------------------- | ------------------------- |
| `order_line_id`    | identifiant ligne de commande | Identifiant unique de la ligne de vente | `OL_20260409_000184`      |
| `order_date`       | date de commande              | Date/heure de la commande               | `2026-04-09 14:32:11 UTC` |
| `product_sku`      | SKU produit                   | Identifiant produit vendu               | `TABLE-TEAK-210`          |
| `country_code`     | pays                          | Pays de vente                           | `FR`                      |
| `sales_channel`    | canal de vente                | Site web, marketplace, retail, etc.     | `ecommerce_web`           |
| `quantity`         | quantité                      | Nombre d’unités vendues                 | `1`                       |
| `unit_price_gross` | prix unitaire brut            | Prix catalogue avant remise             | `1299.00`                 |
| `discount_amount`  | montant remise                | Remise appliquée                        | `100.00`                  |
| `net_revenue`      | revenu net                    | Revenu net de la ligne                  | `1199.00`                 |
| `currency`         | devise                        | Devise de la vente                      | `EUR`                     |
| `order_status`     | statut commande               | Confirmée, annulée, remboursée          | `confirmed`               |
| `returned_flag`    | retour produit                | Indique si l’article a été retourné     | `false`                   |

### `raw.customer_reviews`

| Field (EN)          | Champ (FR)        | Description                          | Exemple                                       |
| ------------------- | ----------------- | ------------------------------------ | --------------------------------------------- |
| `review_id`         | identifiant avis  | Identifiant unique de l’avis         | `REV_887421`                                  |
| `product_sku`       | SKU produit       | Produit concerné par l’avis          | `TABLE-TEAK-210`                              |
| `review_date`       | date avis         | Date de publication                  | `2026-03-18`                                  |
| `rating`            | note              | Note donnée par le client            | `5`                                           |
| `review_title`      | titre avis        | Titre de l’avis                      | `Beautiful finish`                            |
| `review_body`       | texte avis        | Corps complet de l’avis              | `Beautiful teak finish, feels very stable...` |
| `locale`            | langue/locale     | Langue de l’avis                     | `en_GB`                                       |
| `verified_purchase` | achat vérifié     | Si l’avis est rattaché à un achat    | `true`                                        |
| `source`            | source            | Source de collecte                   | `site_reviews`                                |
| `helpful_votes`     | votes utiles      | Nombre de votes utiles               | `12`                                          |
| `reviewer_hash`     | hash client       | Identifiant pseudonymisé du reviewer | `a91f...`                                     |
| `moderation_status` | statut modération | Validé, rejeté, suspect              | `approved`                                    |

### `raw.product_catalog`

| Field (EN)            | Champ (FR)          | Description                           | Exemple                                        |
| --------------------- | ------------------- | ------------------------------------- | ---------------------------------------------- |
| `product_sku`         | SKU produit         | Clé produit maître                    | `TABLE-TEAK-210`                               |
| `product_name`        | nom produit         | Nom commercial courant                | `Aldebaran Teak Garden Table 210`              |
| `category`            | catégorie           | Famille principale                    | `garden_table`                                 |
| `product_line`        | gamme               | Ligne/gamme produit                   | `premium_teak`                                 |
| `season`              | saison              | Collection ou saison                  | `SPRING_SUMMER`                                |
| `price_positioning`   | positionnement prix | Segment prix                          | `PREMIUM`                                      |
| `primary_material`    | matériau principal  | Matériau dominant                     | `teak`                                         |
| `secondary_material`  | matériau secondaire | Matériau secondaire                   | `powder_coated_steel`                          |
| `attribute_tags_json` | tags attributs      | Tags/attributs exploitables plus tard | `["outdoor","premium_finish","fsc_certified"]` |
| `certifications_json` | certifications      | Certifications portées par le produit | `["FSC"]`                                      |
| `launch_date`         | date lancement      | Date de mise sur le marché            | `2026-02-15`                                   |
| `is_active`           | actif               | Produit actif ou non                  | `true`                                         |

## 2. Pourquoi cette approche est SOTA 2026

Au 9 avril 2026, le pattern le plus propre pour ce besoin reste :

- **BigQuery** comme couche analytique.
- **Dataform** pour construire et tester les transformations SQL.
- **extraction structurée** pour transformer les reviews en signaux.
- **validation** après extraction.
- **tables `mart.*`** pour exposer des signaux finaux à l’app.
- **snapshot runtime** pour figer ce qui a vraiment été utilisé par un job.

En version simple, on ne fait pas :

- `raw reviews -> prompt`

On fait :

- `raw -> clean -> derived -> validated -> mart -> runtime context`

C’est ce qui permet d’avoir :

- de la traçabilité
- de la stabilité
- un pipeline rejouable
- et moins d’hallucinations dans la fiche finale

## 3. Le chemin complet : de brut à signal

### Vue d’ensemble

| Couche              | But                                | Exemple de table                    | Ce qu’on y fait               |
| ------------------- | ---------------------------------- | ----------------------------------- | ----------------------------- |
| `raw`               | stocker le brut                    | `raw.customer_reviews`              | ingestion sans logique métier |
| `stg`               | nettoyer/normaliser                | `stg.customer_reviews_clean`        | dédup, langue, SKU, spam      |
| `derived candidate` | proposer une extraction structurée | `derived.review_enriched_candidate` | extraction avec schéma        |
| `derived validated` | garder seulement le fiable         | `derived.review_enriched_validated` | validation SQL + taxonomie    |
| `mart`              | agréger pour le métier             | `mart.review_signal_by_segment`     | top thèmes, language cues     |
| runtime snapshot    | figer ce qui a été consommé        | `ANALYTICS_SNAPSHOT`                | snapshot par job              |

Ce qu’il faut retenir :

- `raw` = données brutes
- `stg` = données propres
- `derived` = enrichissement review par review
- `mart` = signaux finaux prêts pour l’app

**Important sur les exemples JSON** :  
quand je mets un JSON plus bas, il faut le lire comme :

- soit **le contenu d’une ligne** d’une table BigQuery,
- soit **une représentation compacte** d’une colonne `STRUCT`/`JSON`,
- soit **un exemple pédagogique** pour rendre la ligne plus lisible.

Donc oui, on parle toujours bien de **tables BigQuery**.  
Le JSON n’est qu’une façon simple de montrer le contenu d’une ligne.

## 4. Étape 1 : nettoyer les tables brutes

### `stg.customer_reviews_clean`

| Contrôle                       | Pourquoi                        | Exemple                                  |
| ------------------------------ | ------------------------------- | ---------------------------------------- |
| `review_body IS NOT NULL`      | éviter les avis vides           | avis sans texte rejeté                   |
| `LENGTH(review_body) >= 20`    | éviter le bruit                 | `good` rejeté                            |
| `locale LIKE 'en%'`            | cohérence du POC                | `fr_FR` mis de côté                      |
| SKU valide                     | joindre au catalogue            | `UNKNOWN123` rejeté                      |
| dédup par hash                 | éviter copies/reposts           | 2 avis identiques -> 1 conservé          |
| filtre anti-spam               | limiter faux avis               | burst de 50 avis quasi identiques rejeté |
| `moderation_status = approved` | ne garder que le contenu fiable | avis suspect exclu                       |

### `stg.sales_history_clean`

| Contrôle                 | Pourquoi                 | Exemple                                       |
| ------------------------ | ------------------------ | --------------------------------------------- |
| SKU normalisé            | joindre partout          | `table-teak-210` -> `TABLE-TEAK-210`          |
| devise harmonisée        | comparer correctement    | USD converti ou gardé avec devise             |
| statuts invalides exclus | éviter bruit business    | annulé/remboursé exclus des perfs             |
| dates propres            | agrégation fiable        | timezone unifiée                              |
| enrichissement catalogue | récupérer segment métier | ajout de `category`, `product_line`, `season` |

Ici, il y a déjà une idée importante :

- **si la donnée brute est sale, le signal final sera mauvais**
- donc le nettoyage n’est pas accessoire, c’est une vraie étape du pipeline

## 5. Étape 2 : enrichir chaque review

Ici, on veut transformer une review brute en structure exploitable.

### Exemple de review source

> “Beautiful teak finish, feels very stable, and assembly was easier than expected.”

On veut arriver à une **ligne enrichie** qui ressemble à ça :

| Champ                  | Exemple                                                         |
| ---------------------- | --------------------------------------------------------------- |
| `strength_theme_codes` | `["premium_finish", "stability", "easy_assembly"]`              |
| `pain_theme_codes`     | `[]`                                                            |
| `language_cues`        | `["beautiful finish", "feels very stable", "easy to assemble"]` |
| `verbatim_snippets`    | `["Beautiful teak finish", "feels very stable"]`                |
| `confidence_score`     | `0.93`                                                          |

Encore une fois : ceci représente **le contenu d’une ligne** de `derived.review_enriched_candidate`.

Mais pour comprendre comment on y arrive, il faut expliquer 4 notions.

### 5.1 Qu’est-ce qu’une taxonomie ?

Une **taxonomie**, c’est une **liste officielle de catégories autorisées**.

Exemple de taxonomie pour Axolotl :

| `theme_code` autorisé | Signification                             |
| --------------------- | ----------------------------------------- |
| `premium_finish`      | le client perçoit une belle finition      |
| `stability`           | le client perçoit le produit comme stable |
| `easy_assembly`       | le client trouve l’assemblage facile      |
| `comfort`             | le client parle du confort                |
| `durability`          | le client parle de robustesse             |
| `hard_assembly`       | le client trouve l’assemblage difficile   |
| `instability`         | le client perçoit un manque de stabilité  |

Donc :

- la **taxonomie** = la liste complète des thèmes autorisés
- un **`theme_code`** = un élément de cette taxonomie

Exemple :

- `stability` est un `theme_code`
- l’ensemble de tous les `theme_code` forme la taxonomie

Le but est simple :

- empêcher le système d’inventer des catégories libres
- garder un vocabulaire métier contrôlé

### 5.2 Qu’est-ce qu’un `snippet verbatim` ?

Un **snippet verbatim**, c’est un **petit extrait exact du texte source**.

Dans la review :

> “Beautiful teak finish, feels very stable, and assembly was easier than expected.”

Des snippets verbatim possibles sont :

- `Beautiful teak finish`
- `feels very stable`

Pourquoi on les garde ?
Parce qu’ils servent de **preuve** :

- on peut vérifier qu’ils existent vraiment dans la review
- on peut vérifier que le thème choisi est bien relié au texte

Donc :

- `verbatim_snippet` = extrait recopié tel quel depuis la review

### 5.3 Qu’est-ce qu’un `confidence_score` ?

C’est ici qu’il faut être très précis.

Le `confidence_score` **n’est pas un score natif garanti par BigQuery**.  
Dans la doc officielle `AI.GENERATE_TABLE`, Google documente surtout :

- les colonnes d’entrée,
- les colonnes de sortie définies par ton `output_schema`,
- `full_response`,
- `status`.

Autrement dit :

- **BigQuery ne fournit pas automatiquement un “confidence score standard”** pour ce cas.

Donc si tu mets `confidence_score` dans ton `output_schema`, il y a 2 possibilités :

1. **le modèle lui-même remplit ce champ**  
   Dans ce cas, c’est en pratique un **self-score du modèle**.  
   C’est utile comme signal faible, mais ce n’est **pas suffisant** pour prendre une décision seul.

2. **le pipeline calcule ou ajuste un score après coup**  
   C’est beaucoup plus robuste.

### Ce que je recommande

Pour être SOTA et rigoureux, je ferais la différence entre :

- `model_self_score`
  - score proposé par le modèle dans la sortie structurée
- `validation_score`
  - score calculé par le pipeline après validation

Exemple de logique de `validation_score` :

- `+0.4` si tous les `theme_code` sont valides
- `+0.3` si tous les `verbatim_snippets` existent vraiment dans le texte
- `+0.2` si la review n’est pas suspecte
- `+0.1` si `verified_purchase = true`

Donc, dans une version très propre :

- le modèle peut proposer un score
- mais **le score final exploité par le pipeline doit être recalculé ou ajusté côté système**

### 5.4 Comment fonctionne `AI.GENERATE_TABLE` ?

`AI.GENERATE_TABLE` permet à BigQuery de :

1. prendre une table ou une requête comme entrée
2. envoyer chaque ligne à un modèle Vertex/Gemini via un remote model
3. demander une sortie **structurée** selon un `output_schema`
4. écrire directement le résultat sous forme tabulaire

Dans notre cas, on ne lui demande pas :

> “Résume-moi librement cette review.”

On lui demande plutôt :

> “Lis cette review. Trouve uniquement les thèmes présents explicitement dans le texte. Choisis les thèmes uniquement dans la taxonomie autorisée. Retourne aussi des extraits exacts du texte.”

### Ce qu’on impose à `AI.GENERATE_TABLE`

On impose :

- un **`output_schema`**
- une **liste fermée de `theme_code`**
- des **snippets verbatim**
- éventuellement un **model self-score**

#### `output_schema`

C’est le format de sortie attendu.

Exemple :

```sql
strength_theme_codes ARRAY<STRING>,
pain_theme_codes ARRAY<STRING>,
language_cues ARRAY<STRING>,
verbatim_snippets ARRAY<STRING>,
model_self_score FLOAT64
```

Le modèle n’a donc pas le droit d’écrire un paragraphe libre.

#### Liste fermée de `theme_code`

Le modèle doit choisir seulement parmi la taxonomie :

- `premium_finish`
- `stability`
- `easy_assembly`
- etc.

Il n’a pas le droit d’inventer :

- `luxury_feeling`
- `premium_outdoor_magic`

#### `verbatim_snippets`

Le modèle doit fournir des extraits exacts qui justifient les thèmes.

#### `model_self_score`

S’il est demandé, c’est un champ généré par le modèle lui-même.  
Il faut donc le traiter comme un **signal**, pas comme une vérité.

### 5.5 Comment on arrive concrètement au résultat

Review :

> “Beautiful teak finish, feels very stable, and assembly was easier than expected.”

#### Étape A : le modèle repère des spans utiles

Il repère par exemple :

- `Beautiful teak finish`
- `feels very stable`
- `assembly was easier than expected`

#### Étape B : il mappe ces spans à la taxonomie

- `Beautiful teak finish` -> `premium_finish`
- `feels very stable` -> `stability`
- `assembly was easier than expected` -> `easy_assembly`

#### Étape C : il remplit la ligne candidate

Exemple de ligne candidate :

| Champ                  | Valeur                                                          |
| ---------------------- | --------------------------------------------------------------- |
| `strength_theme_codes` | `["premium_finish", "stability", "easy_assembly"]`              |
| `pain_theme_codes`     | `[]`                                                            |
| `language_cues`        | `["beautiful finish", "feels very stable", "easy to assemble"]` |
| `verbatim_snippets`    | `["Beautiful teak finish", "feels very stable"]`                |
| `model_self_score`     | `0.93`                                                          |

### 5.6 Différence entre `verbatim_snippets` et `language_cues`

C’est important :

| Champ               | Rôle                                                  |
| ------------------- | ----------------------------------------------------- |
| `verbatim_snippets` | preuve exacte issue du texte                          |
| `language_cues`     | formulation courte réutilisable pour le ton marketing |

Exemple :

- `verbatim_snippet` : `Beautiful teak finish`
- `language_cue` : `beautiful finish`

Donc :

- `verbatim_snippets` = preuve
- `language_cues` = inspiration de vocabulaire

## 6. Étape 3 : séparer `candidate` et `validated`

### `derived.review_enriched_candidate`

C’est la sortie directe de l’extraction structurée.  
Ici, le système dit :

> “voilà ce que le modèle propose”

Exemple de **ligne candidate** :

| Champ                  | Valeur                                                          |
| ---------------------- | --------------------------------------------------------------- |
| `review_id`            | `REV_887421`                                                    |
| `strength_theme_codes` | `["premium_finish", "stability", "easy_assembly"]`              |
| `pain_theme_codes`     | `[]`                                                            |
| `language_cues`        | `["beautiful finish", "feels very stable", "easy to assemble"]` |
| `verbatim_snippets`    | `["Beautiful teak finish", "feels very stable"]`                |
| `model_self_score`     | `0.93`                                                          |
| `status`               | `""`                                                            |

### `derived.review_enriched_validated`

Ici, on garde seulement ce qui passe les contrôles.

| Validation          | Règle                                                |
| ------------------- | ---------------------------------------------------- |
| statut OK           | la ligne n’a pas échoué                              |
| code autorisé       | chaque `theme_code` est dans la taxonomie            |
| snippet réel        | chaque `verbatim_snippet` existe dans `review_body`  |
| score final minimal | ex. `validation_score >= 0.80`                       |
| source propre       | la review vient bien de `stg.customer_reviews_clean` |

Exemple de **ligne validée** :

| Champ                  | Valeur                                                          |
| ---------------------- | --------------------------------------------------------------- |
| `review_id`            | `REV_887421`                                                    |
| `strength_theme_codes` | `["premium_finish", "stability", "easy_assembly"]`              |
| `pain_theme_codes`     | `[]`                                                            |
| `language_cues`        | `["beautiful finish", "feels very stable", "easy to assemble"]` |
| `verbatim_snippets`    | `["Beautiful teak finish", "feels very stable"]`                |
| `model_self_score`     | `0.93`                                                          |
| `validation_score`     | `0.90`                                                          |
| `validation_status`    | `accepted`                                                      |

Donc :

- `candidate` = le modèle propose
- `validated` = le pipeline accepte

## 7. Étape 4 : construire les signaux `mart.*`

C’est ici que beaucoup de gens se trompent.

`mart.review_signal_by_segment` **n’est pas une table pour une seule catégorie**.  
Ce n’est pas “la table des garden tables”.  
C’est **une seule table BigQuery** qui contient **une ligne par segment métier**.

### Qu’est-ce qu’un segment métier ?

Un segment métier, c’est une combinaison de dimensions, par exemple :

- `category`
- `product_line`
- `price_positioning`
- `season`
- `locale`

Donc une ligne peut représenter :

- `garden_table / premium_teak / PREMIUM / SPRING_SUMMER / en_GB`

et une autre ligne peut représenter :

- `garden_chair / ergonomic_tools / MID / ALL_YEAR / en_US`

### Donc `mart.review_signal_by_segment`, c’est quoi exactement ?

C’est une table du type :

| category       | product_line      | price_positioning | season          | locale  | top_feedback_strengths                           | top_language_cues                                             | review_count |
| -------------- | ----------------- | ----------------- | --------------- | ------- | ------------------------------------------------ | ------------------------------------------------------------- | ------------ |
| `garden_table` | `premium_teak`    | `PREMIUM`         | `SPRING_SUMMER` | `en_GB` | `["stability","easy_assembly","premium_finish"]` | `["feels very stable","beautiful finish","easy to assemble"]` | `100`        |
| `garden_chair` | `comfort_lounge`  | `PREMIUM`         | `SPRING_SUMMER` | `en_GB` | `["comfort","premium_finish"]`                   | `["very comfortable","beautiful finish"]`                     | `74`         |
| `garden_tool`  | `ergonomic_tools` | `MID`             | `ALL_YEAR`      | `en_US` | `["comfort","durability"]`                       | `["easy on the wrist","feels solid"]`                         | `212`        |

Donc :

- **une seule table**
- **beaucoup de lignes**
- **chaque ligne = un segment produit**

### Comment on construit cette table ?

On part de `derived.review_enriched_validated`.

Puis on regroupe les reviews par segment.

Exemple : sur le segment  
`garden_table / premium_teak / PREMIUM / SPRING_SUMMER / en_GB`

on compte les occurrences :

| Thème            | Nombre d’occurrences |
| ---------------- | -------------------- |
| `stability`      | 38                   |
| `easy_assembly`  | 31                   |
| `premium_finish` | 27                   |

On garde alors les plus fréquents comme signal final pour **ce segment**.

C’est ça qu’on met dans la ligne correspondante de `mart.review_signal_by_segment`.

### Même logique côté ventes

`mart.sales_signal_by_segment` suit le même principe :

| category       | product_line     | price_positioning | season          | locale  | top_sales_angles                                      | top_performing_attributes                        | orders_count |
| -------------- | ---------------- | ----------------- | --------------- | ------- | ----------------------------------------------------- | ------------------------------------------------ | ------------ |
| `garden_table` | `premium_teak`   | `PREMIUM`         | `SPRING_SUMMER` | `en_GB` | `["durability","premium_finish","outdoor_stability"]` | `["teak","fsc_certified","powder_coated_steel"]` | `1842`       |
| `garden_chair` | `comfort_lounge` | `PREMIUM`         | `SPRING_SUMMER` | `en_GB` | `["comfort","premium_finish"]`                        | `["teak","weather_resistant_fabric"]`            | `991`        |

L’idée est simple :

- `candidate` = review individuelle enrichie
- `validated` = review individuelle acceptée
- `mart` = **table unique de signaux agrégés par segment**

## 8. Materialized view ou table `mart` ?

| Objet             | Ce que c’est                                                       | Quand l’utiliser                            |
| ----------------- | ------------------------------------------------------------------ | ------------------------------------------- |
| table classique   | données stockées physiquement                                      | étapes intermédiaires, audit, logique riche |
| materialized view | résultat SQL pré-calculé et rafraîchi automatiquement par BigQuery | agrégats simples et fréquents               |
| table `mart`      | table métier finale prête pour l’app                               | logique métier finale, souvent plus riche   |

### Reco Axolotl

- `derived.review_enriched_candidate` -> **table**
- `derived.review_enriched_validated` -> **table**
- `mart.sales_signal_by_segment` -> **materialized view ou table** selon complexité
- `mart.review_signal_by_segment` -> **plutôt table `mart`** recalculée par Dataform

Pourquoi `review_signal_by_segment` est souvent une vraie table `mart` ?
Parce qu’il y a plus de logique :

- nettoyage
- taxonomie
- validation
- agrégation
- filtres sur seuils
- qualité des reviews

## 9. Fréquence de mise à jour

| Objet                           | Fréquence réaliste         |
| ------------------------------- | -------------------------- |
| `raw.sales_history`             | continu ou batch fréquent  |
| `raw.customer_reviews`          | continu ou batch fréquent  |
| `stg.*`                         | horaire ou après ingestion |
| `derived.review_enriched_*`     | horaire ou quotidien       |
| `mart.sales_signal_by_segment`  | horaire ou quotidien       |
| `mart.review_signal_by_segment` | quotidien, parfois horaire |

En 2026, ce n’est pas manuel.  
Le pattern normal est :

- **Dataform workflows** pour orchestrer
- **assertions** pour la qualité
- **Scheduled Queries** ou workflows planifiés pour les refreshs
- **materialized views** auto-refresh seulement si la logique est assez simple

## Point clé à retenir

Le chemin complet, jusqu’ici, est :

1. tables brutes `raw.*`
2. nettoyage en `stg.*`
3. extraction structurée par review dans `derived.review_enriched_candidate`
4. validation dans `derived.review_enriched_validated`
5. agrégation par segment dans :
   - `mart.review_signal_by_segment`
   - `mart.sales_signal_by_segment`

Et surtout :

- `theme_code` = code autorisé d’un thème
- taxonomie = la liste complète de ces codes
- `verbatim_snippet` = preuve textuelle exacte
- `model_self_score` = score proposé par le modèle, non suffisant à lui seul
- `validation_score` = score plus robuste calculé par le pipeline

**Sources**

- [AI.GENERATE_TABLE](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-generate-table)
- [Generate structured data in BigQuery](https://cloud.google.com/bigquery/docs/generate-table)
- [Dataform overview](https://docs.cloud.google.com/dataform/docs/overview)
- [Dataform assertions](https://docs.cloud.google.com/dataform/docs/assertions)
- [Materialized views intro](https://docs.cloud.google.com/bigquery/docs/materialized-views-intro)
- [Scheduled queries](https://cloud.google.com/bigquery/docs/scheduling-queries)

Si tu veux, je peux maintenant écrire cette version telle quelle dans [BIQ_QUERY.md](/Users/floriansollami/Documents/GitHub/factory-writer/BIQ_QUERY.md).

---

# Orchestration du pipeline BigQuery

> On ne va pas mélanger 15 mécanismes. On choisit **un orchestrateur principal** pour le pipeline BigQuery.

Pour **Axolotl**, la recommandation la plus claire est :

- **Dataform** = orchestrateur principal des transformations BigQuery
- **Assertions Dataform** = tests qualité automatiques
- **Materialized views** = seulement pour quelques agrégats simples, si utile
- **Scheduled Queries** = option simple pour un POC très léger, ou pour un cas isolé
- **Pas de mise à jour manuelle**

## La version simple

Il faut imaginer 2 pipelines différents :

1. **pipeline data BigQuery**
   - prépare les signaux sales/reviews
2. **pipeline runtime Factory Writer**
   - lit les signaux et génère la fiche

Le point qui te bloquait concerne surtout le **pipeline data BigQuery**.

---

## 1. C’est quoi Dataform ?

Dataform, c’est un outil Google pour **écrire, organiser et exécuter les transformations SQL BigQuery**.

En version très simple, Dataform sert à dire :

- d’abord construire `stg.customer_reviews_clean`
- puis construire `derived.review_enriched_candidate`
- puis construire `derived.review_enriched_validated`
- puis construire `mart.review_signal_by_segment`

Donc Dataform gère :

- **l’ordre d’exécution**
- **les dépendances**
- **le versioning Git**
- **les tests qualité**

Tu peux le voir comme un “chef d’orchestre SQL” pour BigQuery.

## 2. C’est quoi un Dataform workflow ?

Un **workflow Dataform**, c’est simplement une **exécution planifiée ou déclenchée** de ton pipeline Dataform.

Exemple :

- tous les jours à 2h du matin
- on lance le workflow `reviews_signals_pipeline`

Ce workflow va exécuter automatiquement, dans le bon ordre :

1. `stg.customer_reviews_clean`
2. `stg.sales_history_clean`
3. `derived.review_enriched_candidate`
4. `derived.review_enriched_validated`
5. `mart.review_signal_by_segment`
6. `mart.sales_signal_by_segment`

Donc :

- **Dataform** = l’outil
- **workflow Dataform** = un run planifié de cet outil

---

## 3. C’est quoi une assertion ?

Une **assertion**, c’est un **test qualité sur les données**.

Le principe est simple :

- si le test échoue, le pipeline doit alerter ou échouer

Exemples d’assertions utiles :

### Sur `stg.customer_reviews_clean`

- `review_body` ne doit pas être nul
- `locale` doit être en anglais
- `product_sku` doit exister dans le catalogue
- pas de doublons sur `review_id`

### Sur `derived.review_enriched_validated`

- tous les `theme_code` doivent être dans la taxonomie
- tous les `verbatim_snippets` doivent exister dans `review_body`
- `validation_score` doit être entre `0` et `1`

### Sur `mart.review_signal_by_segment`

- `review_count` doit être supérieur à un seuil minimal
- pas de ligne sans `category`
- pas de ligne sans `product_line`

Donc une assertion, c’est juste :

> “je vérifie automatiquement que la table produite est cohérente”

---

## 4. C’est quoi une Scheduled Query ?

Une **Scheduled Query**, c’est simplement une requête BigQuery qui s’exécute automatiquement selon un planning.

Exemple :

- tous les jours à 1h
- exécuter :
  - `CREATE OR REPLACE TABLE stg.customer_reviews_clean AS ...`

C’est très simple, mais plus limité que Dataform.

### Différence entre Dataform et Scheduled Query

- **Scheduled Query**
  - bien pour une requête isolée
  - simple
  - peu de logique de dépendances

- **Dataform**
  - bien pour un vrai pipeline multi-étapes
  - dépendances
  - assertions
  - versioning
  - plus propre à long terme

Donc pour Axolotl :

- **je recommande Dataform comme base**
- les Scheduled Queries restent une option si tu veux un mini POC ultra simple

---

## 5. C’est quoi une materialized view dans ce contexte ?

Une **materialized view**, c’est une vue que BigQuery **pré-calcule et rafraîchit automatiquement**.

C’est utile si ton calcul est simple.

Exemple :

- somme des ventes par `category`, `season`, `price_positioning`

Dans ce cas, BigQuery peut maintenir ça automatiquement.

Mais si la logique est plus riche, avec :

- taxonomie
- validation
- filtres qualité
- agrégations complexes

alors on préfère une **table construite par Dataform**.

Donc :

- calcul simple = possible en `materialized view`
- logique plus riche = table `mart` recalculée par pipeline

---

## 6. Comment j’orchestrerais concrètement tout ça pour Axolotl

Le plus clair est de choisir **un seul chemin principal** :

### Orchestration recommandée

- **Ingestion** remplit `raw.sales_history`, `raw.customer_reviews`, `raw.product_catalog`
- **Dataform workflow planifié** lance le pipeline data
- **Assertions Dataform** vérifient la qualité
- **Tables `mart.*`** sont mises à jour automatiquement
- **Runtime Factory Writer** lit ensuite les tables `mart.*`

---

## 7. Le pipeline complet, étape par étape

### Étape A. Ingestion des données brutes

Des connecteurs, imports ou batchs remplissent :

- `raw.sales_history`
- `raw.customer_reviews`
- `raw.product_catalog`

### Étape B. Lancement du workflow Dataform

Par exemple :

- toutes les nuits à 2h
- ou toutes les heures si besoin

### Étape C. Dataform construit `stg.*`

- nettoyage des reviews
- nettoyage des ventes
- normalisation des SKU
- enrichissement avec le catalogue

### Étape D. Dataform lance l’enrichissement des reviews

Ici, Dataform peut exécuter une **operation SQL** qui appelle `AI.GENERATE_TABLE`.

Ça produit :

- `derived.review_enriched_candidate`

### Étape E. Dataform construit la table validée

Une requête SQL prend `derived.review_enriched_candidate` et crée :

- `derived.review_enriched_validated`

avec :

- filtres sur la taxonomie
- filtres sur les snippets
- filtres sur les scores
- rejet des reviews douteuses

### Étape F. Dataform construit les tables `mart.*`

- `mart.review_signal_by_segment`
- `mart.sales_signal_by_segment`

### Étape G. Assertions finales

Dataform vérifie que :

- pas de champs critiques manquants
- pas de codes invalides
- pas de segments absurdes
- pas de volumes trop faibles

### Étape H. Le runtime Axolotl lit `mart.*`

Quand un job produit démarre :

- le worker Temporal appelle BigQuery
- récupère la ligne du bon segment
- fige ça dans `ANALYTICS_SNAPSHOT`

---

## 8. Exemple très concret de planning

### Tous les jours à 1h

- ingestion des nouvelles reviews et ventes dans `raw.*`

### Tous les jours à 2h

- workflow Dataform :
  - `stg.sales_history_clean`
  - `stg.customer_reviews_clean`
  - `derived.review_enriched_candidate`
  - `derived.review_enriched_validated`
  - `mart.review_signal_by_segment`
  - `mart.sales_signal_by_segment`

### Toute la journée

- les jobs Factory Writer lisent les tables `mart.*`
- puis écrivent `ANALYTICS_SNAPSHOT`

Donc le pipeline data et le pipeline runtime sont bien séparés.

---

## 9. Ce que je te recommande de retenir

Si tu veux une version simple et propre :

- **Dataform** orchestre presque tout le pipeline BigQuery
- **Assertions** = tests qualité automatiques sur les tables
- **Scheduled Queries** = solution simple si tu ne veux pas encore tout passer dans Dataform
- **Materialized views** = optimisation technique pour des agrégats simples, pas le cœur du pipeline
- **L’app Axolotl ne construit pas les signaux**
- **L’app Axolotl consomme les signaux déjà préparés**

## 10. La phrase la plus claire

Si je devais le résumer en une phrase :

> BigQuery + Dataform préparent automatiquement les signaux marketing en amont; ensuite le workflow Axolotl lit ces signaux déjà prêts et les fige dans `ANALYTICS_SNAPSHOT` avant la génération.

**Sources**

- [Dataform overview](https://docs.cloud.google.com/dataform/docs/overview)
- [Dataform assertions](https://docs.cloud.google.com/dataform/docs/assertions)
- [BigQuery Scheduled Queries](https://cloud.google.com/bigquery/docs/scheduling-queries)
- [BigQuery Materialized Views](https://docs.cloud.google.com/bigquery/docs/materialized-views-intro)
- [AI.GENERATE_TABLE](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-generate-table)

Si tu veux, je peux maintenant te faire un **schéma ultra simple “qui lance quoi, à quel moment”** pour que tu voies visuellement comment `Dataform`, `BigQuery`, `Temporal` et `ANALYTICS_SNAPSHOT` s’enchaînent.

---

# Les équivalents de AI.GENERATE_TABLE dans les autres produits

Le point important, c’est que **BigQuery a deux niveaux** :
**AI.GENERATE** peut déjà produire une sortie structurée selon un schéma personnalisé et renvoie un `STRUCT`, alors que **AI.GENERATE_TABLE** va plus loin en tant que **fonction SQL table-valued** qui génère directement une table avec ton schéma à partir de tables BigQuery et de données non structurées. ([Google Cloud Documentation][1])

Sur les principaux produits, voilà la réalité :

- **Snowflake** : **oui, très proche**. `AI_EXTRACT` fait de l’extraction structurée depuis du texte ou des fichiers, y compris de l’extraction de **tables**, à partir d’un schéma, et renvoie un objet JSON. `AI_COMPLETE` supporte aussi des sorties structurées via **JSON schema** ou **SQL type literal**. Donc fonctionnellement c’est proche de `AI.GENERATE_TABLE`, mais ce n’est pas la même forme “fonction table-valued native”. ([docs.snowflake.com][2])

- **Databricks** : **oui, assez proche**. `ai_extract` extrait des données structurées depuis du texte et des documents selon un schéma, et `ai_query` peut imposer un format de sortie en **DDL**, **json_object** ou **json_schema**. Là aussi, on est proche en usage, mais plus en mode **VARIANT / STRUCT / JSON** qu’en “table générée directement” comme BigQuery. ([docs.databricks.com][3])

- **Microsoft Fabric Data Warehouse** : **partiellement, oui**. En T-SQL, Microsoft documente des fonctions IA intégrées en preview, dont `ai_extract`, qui renvoie des propriétés JSON, puis `OPENJSON` sert à les transformer en colonnes. Donc l’idée est là, mais la forme documentée aujourd’hui ressemble plus à **JSON + parsing SQL** qu’à un clone exact de `AI.GENERATE_TABLE`. ([Microsoft Learn][4])

- **Azure Synapse Dedicated SQL Pool** : **pas au même niveau d’équivalence dans les docs que j’ai vérifiées**. Les docs Synapse mettent surtout en avant `PREDICT` pour le scoring ML, tandis que les nouvelles fonctions IA texte documentées côté Microsoft sont dans **Fabric Warehouse**. Donc sur Azure, le vrai rapprochement se fait aujourd’hui avec **Fabric**, pas Synapse. ([Microsoft Learn][5])

- **Amazon Redshift** : **partiel**. Redshift peut créer une fonction d’inférence SQL via `CREATE EXTERNAL MODEL` avec Bedrock, et le retour peut être du `VARCHAR` ou du `SUPER` JSON ; Amazon Q dans Query Editor v2 peut aussi générer du SQL à partir d’un prompt. C’est puissant, mais ce n’est pas le même produit “clé en main” qu’une fonction dédiée type `AI.GENERATE_TABLE`. ([AWS Documentation][6])

- **Oracle Autonomous AI Database** : **partiel mais différent**. `DBMS_CLOUD_AI.GENERATE` sert surtout à `runsql`, `showsql`, `explainsql`, `narrate`, `summarize`, `chat`, `translate`, et `DBMS_CLOUD_AI.GENERATE_SYNTHETIC_DATA` peut générer des données conformes au schéma. C’est fort, mais ce n’est pas le même usage que “prendre des lignes/documents et produire directement une table structurée”. ([Oracle Docs][7])

- **Teradata VantageCloud** : **il y a bien de l’IA en SQL**, avec des fonctions intégrées comme sentiment, ask LLM, reconnaissance d’entités, résumé, traduction, etc. En revanche, dans les docs officielles que j’ai consultées, je n’ai pas vu un équivalent nommé et documenté exactement comme `AI.GENERATE_TABLE`. ([docs.teradata.com][8])

Donc, en résumé :

**Les plus proches de BigQuery `AI.GENERATE_TABLE` aujourd’hui sont surtout `Snowflake` et `Databricks`.**
**Fabric** s’en rapproche aussi, mais en mode **JSON + OPENJSON**.
**Redshift**, **Oracle** et **Teradata** ont bien de la GenAI dans SQL, mais pas le même niveau de fonction “table-valued structurée prête à l’emploi”. ([docs.snowflake.com][9])

Je peux te faire juste après un **tableau complet** : plateforme par plateforme, avec colonnes **équivalent direct / équivalent partiel / pas trouvé**.

[1]: https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-generate "The AI.GENERATE function  |  BigQuery  |  Google Cloud Documentation"
[2]: https://docs.snowflake.com/en/user-guide/snowflake-cortex/ai-documents "Cortex AI Functions: Documents | Snowflake Documentation"
[3]: https://docs.databricks.com/aws/en/sql/language-manual/functions/ai_extract "ai_extract function | Databricks on AWS"
[4]: https://learn.microsoft.com/en-us/fabric/data-warehouse/ai-functions "AI Functions (Preview) - Microsoft Fabric | Microsoft Learn"
[5]: https://learn.microsoft.com/en-us/azure/synapse-analytics/machine-learning/what-is-machine-learning?utm_source=chatgpt.com "Machine Learning capabilities in Azure Synapse Analytics"
[6]: https://docs.aws.amazon.com/redshift/latest/dg/r_create_external_model.html "CREATE EXTERNAL MODEL - Amazon Redshift"
[7]: https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/sql-generation-ai-autonomous.html "Use Select AI for Natural Language Interaction with your Database"
[8]: https://docs.teradata.com/r/Lake-Analyze-Your-Data-with-ClearScape-AnalyticsTM/Text-Analytics-AI-Functions "Text Analytics AI Functions | Teradata Vantage - Text Analytics AI Functions - Teradata VantageCloud Lake"
[9]: https://docs.snowflake.com/en/sql-reference/functions/ai_extract "AI_EXTRACT | Snowflake Documentation"
