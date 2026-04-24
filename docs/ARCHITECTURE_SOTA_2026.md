# Architecture SOTA Avril 2026 : Factory Writer Axolotl

Ce document remplace la version précédente et reformule l'architecture cible avec les recommandations les plus solides au 15 avril 2026, en s'appuyant sur :

- les patterns officiels **Temporal**
- les patterns officiels **Google Cloud**
- les contraintes métier décrites dans [CLIENT_REQUEST.md](/Users/floriansollami/Documents/GitHub/factory-writer/docs/CLIENT_REQUEST.md)
- la vision d'ensemble décrite dans [FINAL_ARCHITECTURE.md](/Users/floriansollami/Documents/GitHub/factory-writer/docs/FINAL_ARCHITECTURE.md)

## 0. Position d'architecture

La bonne architecture pour Axolotl n'est pas :

- un seul pipeline GenAI monolithique
- ni un seul workflow Temporal qui fait tout
- ni des appels LLM à la volée sur chaque source dans le hot path

La bonne architecture est une architecture en **4 flux séparés** :

1. **runtime produit online**
2. **ingestion admin du style guide**
3. **signal factory data** pour ventes et reviews
4. **offline lab** pour évaluer et optimiser

Le principe clé est :

**Temporal orchestre les cycles de vie métier et les attentes événementielles.
BigQuery + Dataform préparent les données analytiques réutilisables.
Langfuse porte le LLMOps : prompts, traces, datasets, experiments et scores.
Le runtime ne consomme que des contextes déjà structurés, validés et versionnés.**

## 1. Les décisions structurantes

| Sujet | Décision recommandée |
| --- | --- |
| Synchronisation produit | `1 workflow Temporal par SKU` |
| Attente d'événements tardifs | `Signals Temporal` |
| Traitements lourds | `activities routées vers des task queues spécialisées` |
| Extraction facts usine | `Document AI + validation déterministe + evidence` |
| Style guide | `workflow admin séparé + style pack versionné` |
| Signaux ventes/reviews | `pipeline BigQuery/Dataform batch + snapshots matérialisés` |
| Extraction GenAI des reviews | `AI.GENERATE_TABLE ou équivalent batch, jamais en hot path` |
| Génération produit | `LiteLLM + recette de génération active promue offline` |
| Prompt registry / traces / datasets | `Langfuse` |
| Évaluations simples / experiments | `Langfuse + custom metrics` |
| Évaluations avancées / optimizers | `Vertex AI dans le offline lab, optionnel et encadré` |
| Décision de production | `Postgres generation_recipe_active` |
| Déploiement workers | `Cloud Run worker pools pour le POC, malgré leur maturité plus faible` |
| Gouvernance Temporal | `Worker Versioning + Replay Testing + Continue-As-New` |

## 1 bis. Prompt governance cible

Le point important avec Langfuse est de ne pas confondre quatre niveaux :

| Niveau | Source de vérité | Rôle |
| --- | --- | --- |
| Prompt individuel | `Langfuse` | Texte du prompt, version, labels, diffs, rollback, lien avec traces. |
| Recette de génération | `Postgres` | Combinaison exacte autorisée en production : prompt version, model profile, paramètres, schéma, politique de validation. |
| Catalogue modèle | `LiteLLM` | Alias modèle autorisés, routing vers le vrai provider, fallback, tokens, coûts. |
| Exécution modèle | `LiteLLM` | Appel effectif du modèle choisi et production de la trace runtime. |
| Evaluation avancée | `Vertex AI` | Scores offline avancés et propositions d'optimisation. |

Le runtime ne charge jamais `latest`. Il charge une version exacte décidée par Postgres :

```text
generation_recipe_version
-> prompt_name
-> prompt_version
-> model_profile
-> temperature
-> max_tokens
-> response_format / output_schema
-> validation_policy
```

Langfuse peut avoir un label `production`, mais ce label ne remplace pas la `generation_recipe_active` côté Factory Writer. Il sert au pilotage LLMOps, pas à court-circuiter la gouvernance métier.

### Pourquoi parler de recette et pas seulement de prompt

Un résultat LLM change si tu modifies :

- le prompt
- le modèle
- la température
- le schéma de sortie
- les few-shots
- la politique de rewrite

Donc l'offline lab ne doit pas promouvoir “un prompt”. Il doit promouvoir une **recette de génération**.

Exemple :

| Recette | Prompt Langfuse | Model profile LiteLLM | Paramètres | Statut |
| --- | --- | --- | --- | --- |
| `style_pack_recipe_v1` | `style_guide_extract_rules:v12` | `style-guide-extractor-gemini25flash-eu-v1` | `temperature=0`, `schema=style_pack_candidate_v1` | active |
| `style_pack_recipe_v2` | `style_guide_extract_rules:v13` | `style-guide-extractor-claude-sonnet-eu-v1` | `temperature=0`, `schema=style_pack_candidate_v1` | candidate |

```mermaid
flowchart LR
    LF["Langfuse<br/>prompt versions"] --> REC["Generation recipe"]
    LLM["LiteLLM<br/>model_profile catalog"] --> REC
    REC --> PG["Postgres<br/>active recipe"]
    PG --> ON["Online workflow"]
    ON --> GW["LiteLLM execution"]
    GW --> PROV["Resolved provider model"]
```

### Modèle : alias stable vs provider réel

En cible prod, Factory Writer appelle un `model_profile`, pas directement un provider model.

| Niveau | Exemple | Pourquoi |
| --- | --- | --- |
| `model_profile` | `product-sheet-writer-gemini25pro-eu-v1` | Alias stable testé et autorisé par le lab. |
| `resolved_provider_model` | `vertex_ai/gemini-2.5-pro` | Vrai modèle exécuté, stocké dans les traces. |

Cette séparation permet de changer le routing LiteLLM sans changer le use case, tout en gardant l'audit exact du modèle réellement appelé.

## 2. Pourquoi cette séparation est la meilleure approche

Le besoin client combine quatre réalités différentes :

- un produit peut être créé **avant** que le dossier technique n'arrive
- le guide de style change rarement, mais il est **très critique**
- les signaux ventes/reviews demandent une logique **batch analytique**
- l'optimisation des prompts et des modèles n'a rien à faire dans le SLA `< 2 min`

Donc :

- **Temporal** doit posséder le cycle de vie du SKU
- **Dataform + BigQuery** doivent posséder la fabrication des signaux marketing
- **un workflow admin séparé** doit posséder l'ingestion du style guide
- **un lab offline séparé** doit posséder les évaluations et promotions de variantes

## 3. Le schéma global cible

```mermaid
flowchart LR
    subgraph IN["Entrées"]
        EV1["Eventarc: product_created"]
        EV2["Eventarc: zip_usine_upload"]
        EV3["Admin UI: style guide upload + start"]
        EV4["Cron: offline evaluations"]
    end

    subgraph API["Cloud Run HTTP"]
        ROUTER["api-router"]
    end

    subgraph TEMP["Temporal"]
        WF1["ProductLifecycleWorkflow"]
        WF2["StyleGuideIngestionWorkflow"]
        WF3["OfflineEvaluationWorkflow"]

        Q1["queue: product-lifecycle"]
        Q2["queue: docai-activities"]
        Q3["queue: llm-generation"]
        Q4["queue: style-ingestion"]
        Q5["queue: offline-eval"]
    end

    subgraph WRK["Cloud Run Worker Pools"]
        W1["worker-orchestrator"]
        W2["worker-docai"]
        W3["worker-llm"]
        W4["worker-style-admin"]
        W5["worker-offline-lab"]
    end

    subgraph DATA["Données / APIs"]
        GCS["GCS: sealed archives + style source"]
        DOC["Document AI"]
        BQ["BigQuery raw + marts + signal snapshots"]
        DF["Dataform schedules"]
        PG["Cloud SQL PostgreSQL"]
        LLM["LiteLLM / model providers"]
        LF["Langfuse prompt registry + traces + datasets"]
        VX["Vertex AI eval + prompt optimizer optional"]
        CMS["PIM / CMS / Product Content API"]
    end

    EV1 --> ROUTER
    EV2 --> ROUTER
    EV3 --> ROUTER
    EV4 --> ROUTER

    ROUTER -->|"start / signal"| WF1
    ROUTER -->|"start"| WF2
    ROUTER -->|"start"| WF3

    WF1 --> Q1 --> W1
    W1 --> Q2 --> W2
    W1 --> Q3 --> W3

    WF2 --> Q4 --> W4
    WF3 --> Q5 --> W5

    W2 --> GCS
    W2 --> DOC
    W2 --> PG

    W1 --> BQ
    W1 --> PG

    W3 --> LLM
    W3 --> LF
    W3 --> PG
    W3 --> BQ
    W3 --> CMS

    W4 --> GCS
    W4 --> DOC
    W4 --> LLM
    W4 --> LF
    W4 --> PG

    DF --> BQ
    W5 --> BQ
    W5 --> PG
    W5 --> LLM
    W5 --> LF
    W5 --> VX
    W5 --> PG
```

## 4. Comment lire ce schéma

Il faut le lire comme quatre couloirs indépendants.

### Couloir 1. Runtime produit

Il commence avec :

- `product_created`
- `zip_usine_upload`

Le rôle de ce couloir est :

- attendre les prérequis
- extraire les facts
- récupérer les signaux déjà préparés
- charger le style pack actif
- lancer la génération
- publier ou envoyer en review

Le cœur de ce couloir est `ProductLifecycleWorkflow`.

### Couloir 2. Style guide admin

Il commence avec :

- `style guide upload`
- `start style guide ingestion`

Le rôle de ce couloir est :

- lire un PDF source
- le découper proprement
- en extraire des règles structurées
- faire valider par l'humain métier
- publier un `style_pack` versionné

Le cœur de ce couloir est `StyleGuideIngestionWorkflow`.

### Couloir 3. Signal factory data

Il ne dépend pas d'un SKU unique.

Son rôle est de produire en continu :

- des agrégats de ventes
- des extractions structurées sur reviews
- des signaux marketing comparables
- des snapshots prêts à consommer par le runtime

Ce couloir est possédé par :

- **BigQuery**
- **Dataform**

et non par Temporal.

### Couloir 4. Offline lab

Il sert à :

- relire les traces de production
- construire des datasets Langfuse versionnés
- évaluer les variantes
- utiliser Langfuse pour les experiments et scores
- utiliser Vertex AI pour comparer et optimiser quand le niveau de maturité le justifie
- promouvoir une nouvelle `generation_recipe_active`

Le cœur de ce couloir est `OfflineEvaluationWorkflow`.

La règle de production est :

```text
Langfuse stocke les prompts et les traces.
Vertex peut scorer ou proposer un candidat.
Postgres décide la generation_recipe active.
Temporal orchestre la promotion.
```

## 5. Le runtime produit : la vraie logique Temporal

Le vrai pattern Temporal recommandé ici est :

- `1 workflow durable par SKU`
- `Signals` pour les événements externes tardifs
- `activities` routées vers des queues spécialisées
- pas de child workflows partout par défaut

### Schéma du flux SKU

```mermaid
flowchart TD
    A["Start: product_created"] --> B["Workflow: ProductLifecycleWorkflow"]
    B --> C["wait_condition(): sources techniques disponibles"]

    C -->|"signal technical_sources_uploaded"| D["Child workflow: TechnicalDossierIngestionWorkflow"]
    D --> E["facts_valides_json + evidence + validation status"]

    E --> F["Activity: load_signal_snapshot<br/>queue product-lifecycle<br/>worker-orchestrator"]
    E --> G["Activity: load_style_pack_actif<br/>queue product-lifecycle<br/>worker-orchestrator"]
    E --> H["Activity: load_generation_recipe_active<br/>queue product-lifecycle<br/>worker-orchestrator"]
    H --> H2["Activity: fetch_exact_prompts_from_langfuse<br/>queue llm-generation<br/>worker-llm"]

    F --> I["context_snapshot complet"]
    G --> I
    H2 --> I

    I --> J["Activity: generate_structured_candidate<br/>queue llm-generation<br/>worker-llm"]
    J --> J2["Activity: validate_candidate_with_python<br/>queue product-lifecycle<br/>worker-orchestrator"]
    J2 -->|"needs correction"| J3["Activity: rewrite_with_validator_feedback<br/>queue llm-generation<br/>worker-llm"]
    J3 --> J2
    J2 -->|"pass"| K["publish gate"]
    K -->|"pass"| L["publish content"]
    K -->|"fail"| M["pending_editor_review"]
```

### Pourquoi cette forme est meilleure

- le workflow garde l'état métier
- les activities font le vrai travail
- les queues spécialisées isolent les profils de charge
- on évite de transformer chaque étape en child workflow sans vraie raison
- on évite 5 à 6 appels LLM séquentiels dans le runtime
- on garde `claim_plan` et `redaction_plan` comme objets structurés dans la sortie, pas forcément comme appels LLM séparés

## 6. Où mettre les signaux ventes et reviews

C'est ici que l'ancienne version n'était pas assez claire.

### La bonne réponse concrète

Pour Axolotl, je recommande :

- **Dataform + BigQuery** pour produire les signaux en batch
- **Temporal runtime** pour consommer les snapshots déjà calculés

Je **ne recommande pas** :

- de recalculer les signaux reviews à la volée dans le workflow produit
- ni de faire tourner `AI.GENERATE_TABLE` dans le hot path

### Pourquoi

Le sujet ventes/reviews est un sujet de **produit de données**, pas de synchronisation d'événements SKU.

Il faut :

- lire beaucoup de données historiques
- calculer des cohortes
- agréger
- classifier des reviews
- republier des tables propres

Ça correspond exactement à ce que Google documente pour :

- **BigQuery**
- **Dataform**
- **scheduled pipelines**

Temporal n'est pas le meilleur moteur pour ce travail récurrent de transformation analytique.

Temporal doit plutôt :

- attendre le bon moment pour un SKU
- aller lire le snapshot final
- fallback si le snapshot manque

## 7. Architecture recommandée pour la signal factory

```mermaid
flowchart LR
    subgraph RAW["Sources brutes dans BigQuery"]
        S1["sales_history_raw"]
        S2["customer_reviews_raw"]
        S3["product_catalog_snapshot"]
    end

    subgraph DF["Dataform schedules"]
        D1["sales_aggregates_daily"]
        D2["review_prompt_input_daily"]
        D3["review_signal_candidates_daily"]
        D4["review_signal_aggregates_daily"]
        D5["cohort_signal_snapshot_daily"]
    end

    subgraph BQ["BigQuery curated"]
        C1["sales_signal_mart"]
        C2["review_signal_candidates"]
        C3["review_signal_mart"]
        C4["signal_snapshot_latest"]
    end

    S1 --> D1 --> C1
    S2 --> D2 --> D3 --> C2
    C2 --> D4 --> C3
    C1 --> D5 --> C4
    C3 --> D5 --> C4
    S3 --> D5
```

### Comment fonctionne ce pipeline

#### Étape 1. Ventes

On calcule de manière déterministe :

- top performances
- taux de conversion
- ventes par famille / sous-famille / segment
- signaux forts par cohorte comparable

Ici, il faut privilégier :

- SQL
- agrégations déterministes
- tests Dataform

#### Étape 2. Reviews

On prépare des entrées structurées review par review :

- review brute
- SKU source
- langue
- contexte produit

Puis on utilise une extraction GenAI **en batch**, pas au runtime.

#### Étape 3. Extraction GenAI des reviews

Ici, oui, tu peux utiliser :

- `AI.GENERATE_TABLE` dans BigQuery

mais dans un rôle précis :

- extraire des `review_signal_candidates`
- avec un schéma strict
- avec un output structuré
- avec échantillonnage QA offline

Donc on n'utilise pas `AI.GENERATE_TABLE` comme fondation critique du runtime.  
On l'utilise comme **étape de fabrication batch** du produit de données reviews.

#### Étape 4. Agrégation finale

Après l'extraction review par review, on repasse en SQL déterministe pour :

- agréger les signaux
- fusionner avec les ventes
- produire un `signal_snapshot_latest`

Ce snapshot est ensuite lu par le runtime produit.

## 8. Ce que je recommande concrètement pour `AI.GENERATE_TABLE`

### Oui, je le garde

Parce que dans ton cas :

- les reviews sont déjà en BigQuery
- tu veux des signaux structurés
- tu veux un pipeline analytique batch

Donc `AI.GENERATE_TABLE` est cohérent pour un POC.

### Mais je l'encadre fortement

Je recommande de l'utiliser avec :

- schéma de sortie strict
- température faible
- prompts versionnés
- statut et traces de génération conservés
- benchmark offline sur échantillons annotés
- agrégation SQL après extraction

### Sortie cible recommandée

Par review, la sortie doit ressembler à quelque chose comme :

```json
{
  "signaux_detectes": [
    {
      "code_signal": "stabilite",
      "polarite": "positive",
      "confiance": 0.87,
      "extrait_preuve": "la table reste tres stable meme sur terrasse"
    }
  ],
  "resume_structured": "review principalement positive sur la stabilite",
  "statut_extraction": "ok"
}
```

Ensuite seulement, tu agrèges.

### Pourquoi ce cadrage est important

Parce que le contrat stable de ton architecture n'est pas :

- la fonction BigQuery GenAI elle-même

Le contrat stable, c'est :

- la table `review_signal_candidates`
- la table `signal_snapshot_latest`

Si un jour tu remplaces `AI.GENERATE_TABLE` par :

- un worker batch LiteLLM orchestré par Temporal
- un autre moteur d'inférence

le runtime ne change pas.

## 9. Dataform ou Temporal pour les signaux ?

### Réponse courte

- **Dataform** pour le pipeline régulier
- **Temporal** seulement pour les cas exceptionnels

### Répartition recommandée

| Sujet | Outil principal |
| --- | --- |
| agrégats de ventes quotidiens | `Dataform + BigQuery` |
| extraction batch des reviews | `Dataform + BigQuery AI.GENERATE_TABLE` |
| fusion et snapshots de cohortes | `Dataform + BigQuery` |
| lecture du snapshot par SKU | `Temporal runtime` |
| backfill exceptionnel / rerun manuel | `Temporal admin workflow` optionnel |

### Pourquoi cette répartition est la meilleure

Parce que :

- Dataform est fait pour les transformations planifiées, testées et versionnées sur BigQuery
- Temporal est fait pour les workflows durables, pilotés par événements, sur des entités métier

Le bon design 2026 consiste à **ne pas faire faire à Temporal le travail de Dataform**, et inversement.

## 10. Le style guide : flux séparé et versionné

Le style guide ne doit pas vivre dans l'offline lab.

Il doit avoir son propre workflow :

- `StyleGuideIngestionWorkflow`

son propre worker :

- `worker-style-admin`

sa propre queue :

- `queue: style-ingestion`

### Pourquoi

Parce que le style guide est :

- rare
- métier critique
- validé par humain
- utilisé directement en production

Donc ce n'est pas une expérience de lab.

### Flux style guide recommandé

1. upload du PDF dans GCS
2. start du workflow admin
3. parse via Document AI Layout Parser
4. fetch du prompt d'extraction depuis Langfuse ou prompt local POC
5. structured extraction via LiteLLM
6. trace Langfuse de l'appel LLM
7. validation déterministe
8. review humaine
9. publication d'un `style_pack_version`
10. activation d'un seul pack à la fois

Pour le POC, les prompts peuvent rester en fichiers versionnés dans Git. En cible prod, Langfuse devient le registry des prompts individuels, tandis que Postgres conserve la preuve d'audit du `style_pack` produit : prompt name, prompt version, modèle, température, hashes et trace Langfuse.

## 11. Offline lab : ce qu'il doit faire exactement

L'offline lab doit être séparé et posséder :

- les traces de production Langfuse
- les datasets d'évaluation Langfuse versionnés
- les variantes de prompts
- les experiments Langfuse
- les scores et feedbacks humains
- les appels Vertex AI Eval quand on veut un benchmark plus robuste
- les prompt optimizers, seulement comme générateurs de candidats
- la promotion de la `generation_recipe_active`

### Ce qu'il lit

- traces runtime Langfuse
- sorties humaines corrigées
- cas gold annotés
- datasets Langfuse versionnés

### Ce qu'il produit

- `generation_recipe_v2`, `v3`, etc.
- métriques comparatives
- statut baseline / candidate / active
- nouvelles versions de prompts dans Langfuse
- décision de promotion dans Postgres

### Boucle recommandée

L'unité de test est une **recette complète** :

```text
prompt version + model_profile + température + max_tokens + response_format + validation policy
```

Le lab teste donc aussi les modèles. Il ne compare pas uniquement des prompts.

```mermaid
flowchart TD
    A["Langfuse prod traces"] --> B["Trace mining + curation"]
    B --> C["Langfuse dataset versionné"]
    C --> D["OfflineEvaluationWorkflow"]
    D --> E["Recipe A<br/>prompt v12 + Gemini Flash"]
    D --> F["Recipe B<br/>prompt v13 + Gemini Flash"]
    D --> G["Recipe C<br/>prompt v13 + Claude Sonnet"]
    D --> H["Recipe D<br/>prompt v13 + Gemini Pro"]
    E --> I["Runs via LiteLLM<br/>same dataset"]
    F --> I
    G --> I
    H --> I
    I --> J["Deterministic metrics<br/>schema + grounding + forbidden claims"]
    I --> K["Langfuse experiment scores<br/>human feedback + custom scores"]
    I --> L["Vertex AI Eval optional<br/>pointwise / pairwise / AutoSxS"]
    J --> M["Scorecard"]
    K --> M
    L --> M
    M --> N["Promotion gate"]
    N --> O["Postgres generation_recipe_active"]
    N --> P["Langfuse labels candidate/staging/production"]
```

Les traces de production ne doivent pas être optimisées directement. Elles doivent être transformées en dataset stable, filtré et éventuellement annoté. Sinon, le lab optimise sur du bruit.

### Comment on change de prompt ou de modèle

| Changement | Où il se fait | Exemple |
| --- | --- | --- |
| Nouveau texte de prompt | `Langfuse` | `style_guide_extract_rules:v12 -> v13` |
| Nouveau modèle testé | `generation_recipe candidate` + `LiteLLM model_profile` | `gemini25flash -> claude-sonnet` |
| Routing infra transparent | `LiteLLM` | même `model_profile`, autre région ou provider équivalent |
| Passage en production | `PromptPromotionWorkflow` + `Postgres` | `generation_recipe_v8` devient active |

Le code applicatif ne change pas. Le use case dépend de ports :

```text
PromptRegistryPort -> récupère la version exacte de prompt
LLMGatewayPort -> appelle le model_profile via LiteLLM
RepositoryPort -> lit la generation_recipe active
```

## 12. Worker pools Cloud Run : position pragmatique pour le POC

Le choix de **Cloud Run worker pools** est maintenu ici volontairement pour le POC.

### Position honnête

Ce n'est pas la brique la plus conservatrice de toute l'architecture.

Mais pour un POC, ce choix reste acceptable si tu assumes trois choses :

- tu privilégies la simplicité de déploiement GCP-native
- tu acceptes une surface produit encore moins mature que les services Cloud Run HTTP classiques
- tu pilotes explicitement le nombre d'instances

### Reco pratique

Pour le POC :

- `worker-orchestrator` : faible volumétrie, toujours vivant
- `worker-docai` : capacité modérée, pilotée manuellement
- `worker-llm` : capacité plus large, pilotée manuellement
- `worker-style-admin` : très faible capacité
- `worker-offline-lab` : très faible capacité

Le point important est :

**dans ce POC, les worker pools servent à isoler les rôles et les ressources, pas à démontrer un autoscaling parfait.**

## 13. Les garde-fous SOTA qu'il faut absolument ajouter

### Côté Temporal

- `Worker Versioning`
- `Replay Testing`
- `Continue-As-New` sur les workflows longs
- idempotence sur les signaux d'événements

### Côté extraction facts

- evidence / provenance par fact
- validation déterministe forte
- review si facts critiques manquants

### Côté signaux marketing

- snapshots versionnés
- fallback de cohorte si exact match absent
- QA sur extraction review

### Côté génération

- generation recipe active versionnée
- prompt registry Langfuse pour les prompts individuels
- Postgres comme source de vérité de la recette runtime promue
- structured outputs obligatoires
- validation Python pure obligatoire
- style pack actif versionné
- traces Langfuse corrélées aux workflows Temporal
- publish gate avant publication storefront

## 14. Le fallback si un signal snapshot manque

Le runtime produit ne doit pas casser si le `signal_snapshot_latest` exact n'existe pas encore.

Il faut une stratégie de fallback :

1. cohorte exacte : `famille + sous_famille + segment + matériau`
2. cohorte élargie : `famille + sous_famille + segment`
3. cohorte large : `famille + segment`
4. pas de signal fiable : génération facts + style uniquement, puis `pending_editor_review`

Cette logique est importante pour respecter :

- le SLA
- la robustesse
- le principe "context-first"

## 15. La phrase simple à dire au client

Tu peux résumer l'architecture comme ça :

> Nous séparons Factory Writer en quatre flux complémentaires. Temporal orchestre le cycle de vie de chaque SKU et attend les événements métier tardifs. Dataform et BigQuery fabriquent à l'avance les signaux marketing à partir des ventes et des reviews, y compris la partie GenAI sur les reviews, mais toujours hors du hot path. Le style guide est ingéré et validé dans un flux admin distinct pour publier un style pack versionné. Enfin, un lab offline séparé utilise Langfuse pour les prompts, traces, datasets et scores, et Vertex AI comme moteur avancé optionnel d'évaluation/optimisation, sans impacter le SLA de production.

## 16. Conclusion

La version la plus solide de l'architecture Axolotl en avril 2026 est donc :

- **Temporal** pour le cycle de vie produit et les workflows métiers durables
- **Cloud Run worker pools** pour exécuter des workers spécialisés dans le POC
- **Document AI** pour les facts usine et le parsing structurel du style guide
- **BigQuery + Dataform** pour la fabrication récurrente des signaux ventes/reviews
- **AI.GENERATE_TABLE** uniquement comme brique batch d'enrichissement review, jamais comme dépendance runtime
- **LiteLLM** pour la chaîne de génération
- **Langfuse** pour le prompt registry, les traces, datasets, experiments et scores
- **Vertex AI** pour l'évaluation et l'optimisation offline avancée, optionnelle et encadrée
- **Postgres** pour la `generation_recipe_active` et les promotions

Ce n'est pas une architecture "LLM partout".  
C'est une architecture où chaque brique a un rôle précis, stable et justifiable.

## Sources

- [Temporal Workers](https://docs.temporal.io/workers)
- [Temporal Task Queues](https://docs.temporal.io/task-queue)
- [Temporal Workflow message passing](https://docs.temporal.io/encyclopedia/workflow-message-passing)
- [Temporal Child Workflows](https://docs.temporal.io/child-workflows)
- [Temporal Worker performance](https://docs.temporal.io/develop/worker-performance)
- [Temporal Safe deployments](https://docs.temporal.io/develop/safe-deployments)
- [Cloud Run worker pools](https://docs.cloud.google.com/run/docs/deploy-worker-pools)
- [Manage Cloud Run worker pools](https://docs.cloud.google.com/run/docs/managing/workerpools)
- [BigQuery orchestrate workloads](https://docs.cloud.google.com/bigquery/docs/orchestrate-workloads)
- [BigQuery schedule pipelines](https://cloud.google.com/bigquery/docs/schedule-pipelines)
- [BigQuery AI.GENERATE_TABLE](https://docs.cloud.google.com/bigquery/docs/generate-table)
- [Document AI Gemini layout parser](https://docs.cloud.google.com/document-ai/docs/layout-parse-chunk)
- [Vertex AI evaluation overview](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/evaluation-overview)
- [Vertex AI prompt optimizer](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/prompt-optimizer)
- [Langfuse prompt management overview](https://langfuse.com/docs/prompt-management/overview)
- [Langfuse prompt version control](https://langfuse.com/docs/prompt-management/features/prompt-version-control)
- [Langfuse link prompts to traces](https://langfuse.com/docs/prompt-management/features/link-to-traces)
- [Langfuse datasets](https://langfuse.com/docs/evaluation/experiments/datasets)
- [Langfuse experiments via SDK](https://langfuse.com/docs/evaluation/experiments/experiments-via-sdk)
- [Langfuse scores via SDK/API](https://langfuse.com/docs/evaluation/evaluation-methods/scores-via-sdk)
- [Langfuse LiteLLM integration](https://langfuse.com/integrations/frameworks/litellm-sdk)
- [Langfuse OpenTelemetry SDK](https://langfuse.com/docs/observability/sdk/overview)
