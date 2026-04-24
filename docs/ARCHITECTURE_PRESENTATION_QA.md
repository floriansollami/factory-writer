# Architecture Presentation Q&A

Ce document regroupe les questions probables pendant la présentation Factory Writer et les réponses défendables côté architecture.

## Positionnement général

L'architecture Factory Writer n'est pas une architecture de chatbot agentique. C'est une chaîne industrielle de génération contrôlée :

```text
events -> extraction fiable -> contexte structuré -> génération contrainte -> review -> publication
```

On privilégie donc :

| Besoin client | Choix architectural |
| --- | --- |
| SLA < 2 min | pipeline déterministe, workers séparés, prompts déjà promus |
| zéro hallucination technique | Document AI + validations déterministes + facts structurés |
| scalabilité collection SS26 | Temporal + Cloud Run workers + BigQuery pré-calculé |
| pas de vendor lock-in modèle | LiteLLM pour l'appel modèle |
| ton de marque strict | style pack structuré, versionné, approuvé humainement |
| amélioration continue | Langfuse pour prompts/traces/datasets + offline lab + évaluations |
| gouvernance prompt | Postgres décide du package actif, Langfuse stocke les versions de prompts |

## 1. Pourquoi pas LangGraph ?

Réponse courte : LangGraph est très bon pour des agents et workflows LLM dynamiques, mais notre pipeline est principalement un workflow métier long-running, event-driven, durable et auditable. Temporal est plus adapté comme colonne vertébrale d'orchestration.

LangGraph documente bien deux notions : les workflows ont des chemins prédéfinis, les agents décident dynamiquement de leurs outils et étapes. Notre cas est beaucoup plus proche d'un workflow prédéfini que d'un agent autonome.

Pour Factory Writer, le workflow est connu :

```text
product_created
-> attendre dossier technique
-> parser Document AI
-> extraire facts
-> charger signaux
-> charger style pack
-> charger la generation recipe active
-> générer un candidat structuré
-> valider déterministiquement
-> rewrite si nécessaire
-> publication
```

Ce n'est pas un agent qui explore librement. On ne veut pas que le système décide s'il doit appeler Document AI, BigQuery ou publier. Ces étapes sont métier, imposées et auditables.

| Critère | Temporal | LangGraph |
| --- | --- | --- |
| Durable execution sur plusieurs minutes/heures/jours | Très fort | Possible via persistence/checkpointing, mais moins orienté infra métier long-running |
| Reprise après crash worker | Natif | Possible mais dépend du setup |
| Retry policies par activité | Natif | Moins central |
| Human-in-the-loop durable | Signals / updates / timers natifs | Très bon aussi, mais plus agent/workflow LLM |
| Orchestration de jobs GCP LRO | Très adapté | Possible, mais pas son cœur |
| Lecture métier par un backend engineer | Très claire : workflow + activities | Peut devenir plus abstrait avec graph state |
| Architecture hexagonale Python | Très propre | Possible, mais souvent plus couplé au framework LangChain |

Réponse présentation :

> Nous n'avons pas choisi LangGraph comme orchestrateur principal parce que Factory Writer n'est pas un agent conversationnel autonome. C'est un pipeline métier contrôlé, déclenché par événements, avec des étapes imposées, des retries, des attentes longues, de la validation humaine et des garanties d'idempotence. Temporal est plus naturel pour cette responsabilité. LangGraph pourrait être ajouté plus tard pour un sous-module agentique, par exemple un assistant interne de diagnostic ou d'exploration éditoriale, mais pas comme colonne vertébrale du workflow produit.

## 2. Pourquoi Langfuse, et pourquoi pas LangSmith ?

Réponse courte : la proposition cible ajoute Langfuse comme couche LLMOps légère pour le prompt registry, le tracing LLM, les datasets, les expériences et les scores. LangSmith reste un bon outil, mais il est plus naturel quand l'architecture est déjà centrée sur LangChain/LangGraph. Ici, le cœur est Temporal + LiteLLM, donc Langfuse s'intègre plus simplement sans déplacer l'orchestration métier.

Langfuse prend cette responsabilité :

| Fonction Langfuse | Rôle dans Factory Writer |
| --- | --- |
| Prompt registry | Stocker les versions de prompts, labels, configs et diffs |
| Prompt-to-trace | Relier chaque génération au prompt exact utilisé |
| Tracing LLM | Capturer modèle, latence, tokens, coût, erreurs, input/output |
| Datasets | Construire des jeux de test depuis les traces de production |
| Experiments | Comparer plusieurs prompts ou modèles sur les mêmes exemples |
| Scores | Stocker métriques automatiques, feedback humain et juges LLM |

Ce que Langfuse ne remplace pas :

```text
Temporal = orchestration durable
LiteLLM = exécution modèle et abstraction provider
Postgres = vérité opérationnelle Factory Writer
Vertex AI Eval = évaluation avancée optionnelle
validations Python = contrôle déterministe
```

La règle importante est la suivante :

```text
Langfuse peut héberger les prompts et les traces.
Postgres reste le control plane qui dit quelle generation recipe est active.
Le runtime ne charge jamais "latest" implicitement.
Il charge une version explicite promue.
```

Différence avec LangSmith :

| Critère | Langfuse | LangSmith |
| --- | --- | --- |
| Intégration LiteLLM | Très directe via callbacks / OpenTelemetry | Possible, mais moins centrale |
| Stack Temporal + LiteLLM | Très aligné | Possible, mais plus orienté LangChain |
| Prompt registry autonome | Oui | Oui |
| Traces + datasets + scores | Oui | Oui |
| Debug graph/agent LangChain | Moins central | Très fort |
| Adoption dans notre architecture | Couche LLMOps indépendante | Alternative crédible si le client standardise LangChain |

Pour le POC strict, on peut encore garder les prompts dans Git pour éviter la dépendance externe. Pour la cible production, Langfuse devient la couche propre de prompt management et d'observabilité LLM.

Réponse présentation :

> Nous ajoutons Langfuse pour ce qu'il fait le mieux : versionner les prompts, tracer les appels LLM, construire des datasets depuis la production et comparer les variantes. Il ne remplace ni Temporal, ni LiteLLM, ni Postgres. LangSmith aurait aussi été défendable, surtout dans une stack LangChain/LangGraph. Comme notre architecture est centrée sur Temporal et LiteLLM, Langfuse est le choix LLMOps le plus léger et le moins intrusif.

## 3. Pourquoi Document AI plutôt qu'un LLM direct ?

Réponse courte : parce que Document AI est fait pour l'extraction documentaire fiable, layout-aware, traçable et industrialisable. Un LLM direct est bon pour comprendre, mais moins bon comme source primaire d'extraction vérifiable.

Document AI Layout Parser ne fait pas juste lire un PDF. Il extrait :

| Élément | Pourquoi c'est utile |
| --- | --- |
| texte OCR | base factuelle lisible |
| tables | essentiel pour dimensions, matériaux, specs |
| listes | utile pour règles de style, contraintes, certifications |
| ordre de lecture | évite les mélanges de colonnes |
| chunks contextuels | garde le contexte de section |
| sortie JSON GCS | traçable, rejouable, auditable |

Google indique que le Layout Parser Gemini améliore la qualité sur les tableaux, l'ordre de lecture et le chunking contextuel. La doc précise aussi qu'il réduit les hallucinations par rapport aux parsers purement LLM, car l'extraction reste ancrée dans le contenu réel du document.

| Critère | Document AI | LLM direct |
| --- | --- | --- |
| Extraction OCR/layout | Spécialisé | Possible, mais plus opaque |
| Tables complexes | Meilleur choix | Risque de confusion |
| Traçabilité page/blocs/chunks | Forte | Moins structurée |
| Sortie batch GCS | Native | À construire soi-même |
| Idempotence workflow | Bonne avec output_uri et operation_id | Plus manuel |
| Coût/latence maîtrisable | Oui, batch processor | Dépend du contexte multimodal |
| Risque hallucination extraction | Plus faible | Plus élevé |

Réponse présentation :

> Nous utilisons Document AI comme couche "extract", et LiteLLM comme couche "understand". Document AI transforme le PDF en contenu structuré et traçable. Ensuite seulement, le LLM interprète ce contenu pour produire des facts, règles de style ou signaux. Cette séparation évite de demander au LLM de faire à la fois OCR, parsing, compréhension métier et génération, ce qui augmenterait le risque d'erreur.

## 4. Pourquoi pas du RAG ?

Réponse courte : parce que le besoin principal n'est pas de répondre à une question ouverte sur une grande base documentaire. Le besoin est de générer une fiche produit à partir d'un contexte fermé, contrôlé et déjà sélectionné.

Le RAG est très utile quand :

```text
l'utilisateur pose une question variable
la base documentaire est grande
on ne sait pas à l'avance quels documents sont pertinents
on doit retrouver les meilleurs passages par similarité
```

Notre cas est différent :

```text
le SKU est connu
le dossier technique du SKU est connu
le style pack actif est connu
les signaux BigQuery sont pré-calculés
les facts valides sont explicitement injectés
```

On ne veut pas que le modèle aille chercher approximativement des passages proches. On veut lui donner le contexte exact.

| Risque | Exemple |
| --- | --- |
| mauvais voisin sémantique | récupérer une table similaire mais pas le bon SKU |
| hallucination par analogie | reprendre une dimension d'un ancien modèle |
| non-déterminisme | deux requêtes proches ne récupèrent pas toujours les mêmes passages |
| complexité inutile | embeddings, index, chunking, retrieval, reranking, monitoring |
| conflit avec zéro hallucination | le retrieval peut introduire des informations non autorisées |

Réponse présentation :

> Nous avons choisi une approche context-first plutôt qu'un RAG générique. Le contexte est construit explicitement : facts validés, signaux marketing, style pack actif. Pour garantir zéro hallucination technique, nous préférons injecter uniquement les faits autorisés plutôt que récupérer dynamiquement des passages proches via embeddings.

## 5. Pourquoi pas PostgreSQL + pgvector + embeddings ?

Réponse courte : pgvector est utile pour de la recherche sémantique, mais le POC n'en a pas besoin pour générer une fiche fiable. On utilise Postgres pour la vérité opérationnelle structurée, pas comme moteur de retrieval sémantique.

Cloud SQL PostgreSQL supporte `pgvector` et l'intégration Vertex AI embeddings. Google décrit ce pattern pour construire des applications RAG et faire de la recherche sémantique. Ce n'est donc pas une mauvaise technologie. Ce n'est juste pas le bon niveau de complexité pour notre use case initial.

Ce qu'on fait à la place :

| Besoin | Choix actuel |
| --- | --- |
| Stocker les produits | Postgres structuré |
| Stocker les sources style guide | Postgres structuré |
| Stocker les fragments Document AI | Postgres structuré |
| Stocker les packs style | Postgres structuré |
| Stocker les règles | Postgres relationnel + foreign keys |
| Stocker les signaux marketing | BigQuery + snapshot |
| Comparables ventes/reviews | BigQuery par cohortes déterministes |

Quand pgvector deviendrait pertinent :

| Cas futur | Pourquoi pgvector serait utile |
| --- | --- |
| retrouver des fiches similaires pour few-shot | similarité sémantique entre anciennes fiches |
| proposer des exemples de style | recherche dans corpus éditorial validé |
| assistant interne marketing | questions libres sur guides et anciennes fiches |
| matching de produits comparables | complément sémantique aux cohortes BigQuery |
| détection de doublons | similarité entre descriptions |

Réponse présentation :

> Nous n'avons pas mis pgvector dans le POC parce que la génération doit être pilotée par des faits exacts et des règles explicites. pgvector est pertinent pour retrouver des exemples ou construire un assistant sémantique, mais pas comme source de vérité technique. Nous pourrons l'ajouter plus tard pour le lab offline, les few-shots ou la recherche de contenus similaires.

## 6. Pourquoi pas fine-tuning ?

Réponse courte : le client demande explicitement une approche context-first, sans cycles de training coûteux. Le fine-tuning n'est pas le bon outil pour garantir des dimensions exactes ou respecter un guide de style qui évolue.

Le fine-tuning est utile quand :

```text
on a beaucoup d'exemples annotés
le comportement attendu est stable
on veut réduire la taille du prompt
on veut apprendre un style ou format récurrent
```

Mais ici :

```text
les données produit changent à chaque SKU
les facts techniques doivent venir du dossier courant
le guide de style peut évoluer
les signaux marketing changent avec les ventes/reviews
le POC doit rester multi-provider via LiteLLM
```

Réponse présentation :

> Nous ne fine-tunons pas le modèle parce que le problème n'est pas d'apprendre une connaissance fixe. Le problème est d'injecter le bon contexte au bon moment, avec des facts validés et des règles de style versionnées. Le fine-tuning pourrait améliorer le ton à maturité, mais il ne remplace pas la validation factuelle ni la gestion dynamique du contexte.

## 7. Pourquoi LiteLLM ?

Réponse courte : LiteLLM sert de couche d'abstraction modèle. Il permet d'éviter que tout le code métier dépende directement de Vertex, OpenAI, Anthropic ou autre.

| Besoin | Apport |
| --- | --- |
| éviter vendor lock-in | changer de provider plus facilement |
| standardiser les appels | interface unique |
| tester plusieurs modèles | même contrat applicatif |
| séparer prompt et provider | clean architecture plus propre |
| garder Vertex AI possible | tout en restant remplaçable |

Réponse présentation :

> LiteLLM est utilisé comme adapter modèle, pas comme cœur métier. Notre application dépend d'un port `StyleGuideDraftPackGeneratorPort`, pas directement d'un SDK fournisseur. Cela respecte l'exigence context-first et évite de verrouiller l'architecture sur un seul provider.

### Comment changer de modèle proprement ?

Le runtime ne doit pas dépendre directement de `vertex_ai/gemini-3-pro-preview` ou `claude-sonnet`. Il doit dépendre d'un `model_profile` validé, par exemple :

```text
style-guide-extractor-gemini25flash-eu-v1
product-sheet-writer-claude-sonnet-eu-v1
```

L'offline lab teste plusieurs **recettes de génération** :

```text
prompt version + model_profile + temperature + max_tokens + response_format
```

Puis `PromptPromotionWorkflow` active la recette gagnante dans Postgres. Langfuse garde les versions de prompts et LiteLLM garde le catalogue/routing des modèles. Le code métier ne change pas.

## 8. Pourquoi Temporal plutôt que Cloud Workflows ou juste Pub/Sub ?

Réponse courte : Pub/Sub transporte des événements, mais n'orchestre pas l'état métier. Cloud Workflows peut orchestrer, mais Temporal est plus adapté pour des workflows longs, typés, testables en code Python, avec activités, retries, signals et human-in-the-loop.

Factory Writer a besoin de :

```text
attendre plusieurs événements
relancer des étapes en erreur transitoire
suivre des LRO Document AI
attendre une validation humaine
reprendre après crash worker
éviter les états orphelins
avoir une vue d'exécution par SKU
```

Réponse présentation :

> Pub/Sub et Eventarc déclenchent le système, mais ne sont pas l'orchestrateur métier. Temporal garde la mémoire du workflow, des retries, des timers et des validations humaines. C'est ce qui permet de rendre robuste un pipeline qui dépend de GCS, Document AI, BigQuery, LLM et Postgres.

## 9. Pourquoi un offline lab alors que le client veut < 2 min ?

Réponse courte : parce que l'optimisation ne doit pas être faite dans le hot path. Le hot path doit utiliser des prompts déjà promus.

Le online doit faire :

```text
charger generation_recipe_active
charger style_pack_actif
générer
valider
publier/review
```

L'offline doit faire :

```text
tester variantes
comparer modèles
évaluer qualité
optimiser prompts
promouvoir une version
```

Réponse présentation :

> Le SLA < 2 min concerne la génération d'une fiche pour un nouveau produit. Il ne doit pas inclure l'optimisation des prompts. Les prompts sont optimisés en offline, puis promus. Le online utilise uniquement les versions actives validées.

## 10. Pourquoi review humaine pour le style guide ?

Réponse courte : parce que le guide de style est un artefact rare, stratégique, et validé par Sophie. L'humain reste le meilleur validateur final.

Le LLM peut aider à extraire :

```text
règles de voix
règles de ton
claims interdits
lexique préféré
contraintes de format
```

Mais il ne doit pas décider seul de l'identité de marque.

Réponse présentation :

> Pour le guide de style, le bon pattern est : le LLM prépare, les validations déterministes filtrent, Sophie approuve. Comme le style guide change peu souvent et a une forte valeur métier, la review humaine est plus fiable et moins coûteuse qu'un système complexe de judge model dès le POC.

## 11. Pourquoi BigQuery pour les signaux marketing ?

Réponse courte : parce que les ventes et reviews sont analytiques, volumineuses et historisées. BigQuery est le bon endroit pour calculer des signaux par cohortes.

Les signaux ne sont pas des facts techniques. Ce sont des indices de priorisation :

```text
finition_premium score 0.84
durabilite score 0.81
stabilite score 0.79
assemblage_facile score 0.72
```

Réponse présentation :

> BigQuery ne sert pas à inventer des claims. Il sert à calculer quels angles marketing résonnent sur des produits comparables. Ces signaux priorisent le message, mais ne deviennent jamais des vérités techniques.

## 12. Pourquoi ne pas publier directement au frontend ?

Réponse courte : dans une architecture e-commerce propre, le frontend ne devrait pas être la source de vérité du contenu produit. Il consomme le contenu depuis un CMS, PIM, commerce backend ou API de contenu.

Pour le POC :

```text
Factory Writer génère la fiche
Postgres stocke le draft et son statut
un endpoint API expose le résultat
plus tard on pousse vers PIM/CMS/composable commerce
```

Réponse présentation :

> Le frontend ne doit pas recevoir directement un texte non gouverné. Factory Writer produit un contenu versionné avec statut : draft, pending review, approved, published. Le canal final peut être une API, un CMS ou un PIM selon l'écosystème du client.

## 13. Pourquoi une architecture aussi structurée pour un POC ?

Réponse courte : parce que le POC doit démontrer l'architecture cible sans tout industrialiser. On garde les bons patterns, mais on limite ce qui doit être branché dès le premier jour.

On garde simple sur :

```text
pas de pgvector
pas de fine-tuning
pas de RAG complet
pas de Vertex Eval dans le runtime
pas d'optimisation automatique de prompt en production
```

On garde sérieux sur :

```text
Temporal
Document AI
LiteLLM
Langfuse
Postgres
BigQuery
GCS
versioning
validation déterministe
human review
```

Le découpage de maturité est volontaire :

| Niveau | Choix |
| --- | --- |
| POC strict | prompts Git, metadata Postgres, validations déterministes |
| POC+ | Langfuse pour prompt registry, traces et datasets |
| cible production | Langfuse + offline lab + Vertex Eval optionnel + promotion contrôlée |

Réponse présentation :

> Le POC n'est pas un script jetable. Il doit prouver que la cible est réaliste. On garde donc les décisions structurantes : Temporal, Document AI, LiteLLM, Langfuse, Postgres, BigQuery, validations déterministes et review humaine. En revanche, on ne met pas tout dans le chemin critique : les évaluations lourdes, l'optimisation de prompts et les comparaisons avancées restent offline.

## Questions bonus probables

| Question | Réponse courte |
| --- | --- |
| Pourquoi pas tout faire avec un prompt libre non structuré ? | Parce que ça mélange extraction, raisonnement, rédaction et validation. C'est plus fragile et moins auditable. |
| Pourquoi garder claim plan, redaction plan, draft et review comme objets ? | Parce que chaque objet a une responsabilité claire. En runtime, ils peuvent être produits dans un seul appel LLM structuré pour préserver le SLA. |
| Pourquoi stocker les facts plutôt que juste le PDF ? | Parce que la génération doit utiliser des facts validés, pas relire un PDF à chaque fois. |
| Pourquoi les signaux marketing ne sont pas des facts ? | Parce qu'ils viennent de tendances ventes/reviews et servent à prioriser le message, pas à affirmer une vérité technique. |
| Pourquoi Postgres et BigQuery ? | Postgres pour l'état opérationnel et relationnel, BigQuery pour l'analytique historique. |
| Pourquoi Cloud Run ? | Simple, scalable, serverless, compatible API et workers containerisés. |
| Pourquoi GCS ? | Source documentaire durable, versionnable, compatible Document AI batch. |
| Pourquoi prompt templates en code pour le POC strict ? | Plus simple pour démarrer. La cible propre est Langfuse comme prompt registry. |
| Pourquoi Postgres garde la recette active si Langfuse a des labels ? | Parce que Langfuse versionne les prompts, mais la production doit promouvoir une recette complète : prompt, modèle, paramètres, schéma et politique de validation. |
| Pourquoi stocker les hashes de prompts dans `style_pack` ? | Pour tracer le prompt exact sans stocker tout le prompt rendu dans la table métier. En cible Langfuse, on pourra ajouter un lien vers la trace LLMOps. |
| Pourquoi ne pas tout évaluer en online ? | Parce que l'évaluation lourde coûte du temps et casserait le SLA. Elle doit être offline. |
| Pourquoi pas Vertex Prompt Optimizer en automatique ? | Parce qu'un optimizer peut maximiser une métrique tout en abîmant le ton premium. Il peut proposer, mais un humain ou une promotion contrôlée décide. |
| Comment tester un autre modèle sans casser le code ? | L'offline lab crée une recette candidate avec un autre `model_profile`, la teste via LiteLLM sur le même dataset, puis promeut seulement si les métriques gagnent. |

## Formulation défendable en présentation

> Notre architecture n'est pas construite comme un chatbot agentique. Elle est construite comme une factory de contenu contrôlée. On ne cherche pas à donner de l'autonomie au modèle, mais à lui fournir le bon contexte, au bon moment, avec des validations strictes. Document AI extrait, BigQuery priorise, Postgres gouverne les états et les promotions, Temporal orchestre, LiteLLM abstrait les modèles, Langfuse trace et versionne les prompts, et le LLM génère sous contraintes. Les outils comme LangGraph, RAG ou pgvector sont pertinents dans d'autres parties du cycle de maturité, mais ils ne doivent pas remplacer le cœur du pipeline si l'objectif prioritaire est zéro hallucination technique, SLA court et architecture compréhensible.

## Sources

- [LangGraph Workflows and Agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents)
- [LangSmith Observability Concepts](https://docs.langchain.com/langsmith/observability-concepts)
- [LangSmith Prompt Engineering Quickstart](https://docs.langchain.com/langsmith/prompt-engineering-quickstart)
- [Langfuse Prompt Management](https://langfuse.com/docs/prompt-management/overview)
- [Langfuse Prompt Version Control](https://langfuse.com/docs/prompt-management/features/prompt-version-control)
- [Langfuse Link Prompts to Traces](https://langfuse.com/docs/prompt-management/features/link-to-traces)
- [Langfuse Datasets](https://langfuse.com/docs/evaluation/experiments/datasets)
- [Langfuse LiteLLM Integration](https://langfuse.com/integrations/frameworks/litellm-sdk)
- [Google Document AI Layout Parser](https://docs.cloud.google.com/document-ai/docs/layout-parse-chunk)
- [Google Cloud RAG Architecture with Vertex AI and Vector Search](https://docs.cloud.google.com/architecture/gen-ai-rag-vertex-ai-vector-search)
- [Vertex AI RAG Engine Embeddings](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/rag-engine/use-embedding-models)
- [Cloud SQL PostgreSQL Vector Embeddings](https://docs.cloud.google.com/sql/docs/postgres/generate-manage-vector-embeddings)
- [Cloud SQL GenAI Applications](https://docs.cloud.google.com/sql/docs/postgres/ai-overview)
- [pgvector Official Repository](https://github.com/pgvector/pgvector)
- [Temporal Durable Execution](https://temporal.io/)
