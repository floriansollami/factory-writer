# Architecture des Événements : Push (Webhook) vs Pull (Subscribe)

Ce document détaille les choix architecturaux concernant la messagerie asynchrone (Event-Driven Architecture) pour le projet **Factory Writer**, en s'appuyant sur les standards de l'industrie technologique de la Silicon Valley en 2026.

---

## 1. Les Notions de Base : Pull vs Push

Dans un système asynchrone, un service "producteur" (ex: l'ERP ou un Bucket GCS) émet des événements, et un "consommateur" (notre API Cloud Run) doit les traiter. Il existe deux grandes manières d'organiser cette communication.

### Le Modèle "Pull" (Subscribe classique)
* **Comment ça marche :** Le consommateur ouvre une connexion permanente vers la file d'attente (Pub/Sub, Kafka, RabbitMQ) et demande en boucle : *"Y a-t-il un nouveau message ?"*.
* **Contrainte :** Le serveur consommateur doit être allumé 24h/24 et 7j/7 pour observer la file, même s'il n'y a aucun événement pendant des semaines.

### Le Modèle "Push" (Webhook Serverless)
* **Comment ça marche :** Le consommateur se met en veille. C'est l'infrastructure Cloud (le "Router", ex: Eventarc ou EventBridge) qui surveille l'arrivée des données. Quand un événement arrive, l'infrastructure "frappe à la porte" du consommateur en lui envoyant une requête **HTTP POST**.
* **Avantage originel :** Le consommateur n'a pas besoin de surveiller ; il est réveillé à la demande.

---

## 2. Le Standard Silicon Valley 2026

Dans les architectures Cloud-Native de 2026, **le modèle "Push via HTTP" combiné au Serverless est devenu la recommandation principale pour la majorité des workloads**.

### Le rôle crucial et universel de la norme CloudEvents (CNCF)

En 2026, pour lutter contre le "Vendor Lock-in" (la dépendance toxique aux SDKs d'un seul fournisseur Cloud), l'industrie s'est unifiée autour d'un standard appelé **CloudEvents**, géré par la Cloud Native Computing Foundation (CNCF).

* **Qu'est-ce que c'est ?** Il s'agit d'une spécification universelle de formatage d'événements. Un message "CloudEvents" possède une structure garantie et immuable constituée de métadonnées de routage (`id`, `source`, `type`, `time`) et d'une charge utile (`data`).
* **Est-ce limité au mode "Push" ? Absolument pas !** La puissance de CloudEvents est d'être **agnostique au transport**. La sémantique reste identique, seul le vecteur change :
  * **En modèle "Pull" (ex: Kafka, MQTT) :** Les attributs CloudEvents sont encodés nativement dans l'enveloppe binaire du message (les Kafka Headers par exemple). 
  * **En modèle "Push" (ex: Eventarc, AWS EventBridge) :** Les attributs CloudEvents sont injectés sous forme de simples en-têtes HTTP (ex: `ce-id`, `ce-type`), et le corps du message loge dans le body HTTP.
* **L'avantage massif pour Factory Writer** : Utilisé ici en mode "Push", notre code d'API (FastAPI) n'a besoin d'importer **aucun SDK Google**. L'API se contente de lire les Headers HTTP. Si demain matin The Outdoor Axolotl migre toute son informatique vers Amazon Web Services, **absolument 0% du code de réception métier ne devra être modifié**. 

* **Le Rôle d'Eventarc (Pourquoi pas Pub/Sub "pur" ?)** : 
  Bien qu'Eventarc s'appuie secretly sur le moteur Pub/Sub de Google pour transporter ses données, la philosophie d'architecture de 2026 exige d'interagir avec **Eventarc**, le "traducteur universel", plutôt que de faire de la plomberie manuelle sur Pub/Sub.
  * **Exemple "À l'ancienne" (Pub/Sub Pur)** : Brancher Cloud Storage vers une API via Pub/Sub exige de gérer manuellement `Topics` et `Push Subscriptions`. Surtout, l'API reçoit un format propriétaire Google (`{"message": {"data": "base64_encoded", "messageId": "..."}}`). Cela crée un **Vendor Lock-in** mortel, forçant le développeur à coder un désérialiseur Base64 lié très spécifiquement à la grammaire interne de Google.
  * **La philosophie "Modern Cloud-Native" (Eventarc)** : En utilisant Eventarc, le hub masque les tuyaux Pub/Sub. Il intercepte les signaux (ex: "nouveau PDF sur Storage"), les aseptise, et **mue le payload brut de Google vers le standard inter-opérable CloudEvents**. L'application Python n'a même pas idée qu'elle s'exécute sur un cloud Google ; elle se contente de lire une requête Web standard. C'est la garantie de portabilité ultime.
  * **L'interopérabilité avec les systèmes externes (Exemple : Apache Kafka ERP)** : Si l'ERP d'entreprise publie ses événements sur un cluster Apache Kafka existant, l'architecture reste préservée sans écrire de code d'intégration. Deux patterns d'infrastructure (No-Code) s'offrent aux DevOps :
    1. **Le Pub/Sub Bridge Pattern (Recommandé)** : L'IT déploie un plugin officiel `Google Cloud Pub/Sub Sink Connector` sur son cluster Kafka Connect. Ce connecteur aspire les événements et les déverse dans Pub/Sub. Eventarc prend alors le relais nativement pour les formater en CloudEvents et appeler Cloud Run en Push.
    2. **Google Integration Connectors** : Google Cloud peut se brancher directement à un cluster Kafka externe via son connecteur managé, servant de pont pour déclencher les workflows. Dans les deux cas, le code applicatif backend reste préservé d'une intégration Kafka directe.

### Pourquoi utiliser CloudEvents en mode Pull si le SDK (ex: Kafka) reste obligatoire ?

Même si l'utilisation d'une file d'attente Kafka ou RabbitMQ nécessite invariablement d'importer leur SDK de transport (pour établir la connexion TCP et gérer les acquittements), le format CloudEvents apporte 3 fonctionnalités révolutionnaires ("Le standard de l'enveloppe") :

1. **La fin de "l'Enfer des Formats Custom" :** Avant CloudEvents, chaque équipe inventait sa propre structure JSON (`{"action": "create"}`, `{"event_name": "new_file"}`, etc.). Il était impossible de brancher un outil de monitoring global sur le cluster Kafka sans coder des analyseurs spécifiques pour chaque équipe. En standardisant les formats, l'outillage DevOps moderne sait lire nativement les événements de toute la société.
2. **Le Routage sans Désérialisation :** Des routeurs événementiels ou outils d'infrastructure peuvent "scroller" les millions de messages Kafka à la vitesse de la lumière. Ils regardent uniquement les "Kafka Headers" standards (comme `ce-type`) pour trier et rediriger la donnée, **sans jamais avoir besoin de parser ou lire la charge binaire** (le gros fichier) cachée dans le message.
3. **La Traçabilité Cross-Transport (Le Graal) :** Si un événement démarre en Push HTTP sur Google Cloud, qu'il est envoyé dans un cluster TCP Kafka pour l'analyse Data, et atterrit enfin sur une file AWS SQS ; l'identifiant originel `ce-id` et son origine `ce-source` restent **strictement les mêmes** de bout en bout. Tracer l'origine d'une anomalie transversale devient trivial là où c'était impossible auparavant.

---

## 3. Pourquoi l'API Cloud Run est-elle "Serverless" ?

Pour qu'un modèle "Push HTTP" soit intéressant économiquement, il faut que l'API qui reçoit le coup de fil soit "Serverless". **Cloud Run** est l'incarnation de ce principe :

1. **Le "Scale-to-Zero" (Coût à vide)** : S'il n'y a pas d'événements (par exemple le dimanche ou hors période de nouvelle collection), le nombre de conteneurs hébergeant ton code tombe mathématiquement à **0**. L'entreprise paie 0$.
2. **L'Autoscaling géré par l'infrastructure** : Cloud Run gère la *Concurrency* (la simultanéité). Un seul conteneur Cloud Run peut traiter jusqu'à 80 (voire 1000) requêtes HTTP Push simultanément. Si Eventarc pousse subitement 5 000 requêtes HTTP à la seconde, Google détectera le pic et allumera instantanément (en quelques millisecondes / "Cold Start" réduit) autant de conteneurs que nécessaire pour encaisser le choc.
3. **Le développeur déchargé de l'Ops** : Tu n'as pas à gérer les serveurs virtuels, le load-balancing, ou les courbes CPU. Ton code se comporte comme une simple fonction pure.

---

## 4. Le High-Throughput Streaming : L'exception où le "Pull" règne encore

Bien que le "Push Serverless" soit la norme, la Silicon Valley réserve le modèle "Pull" pour des cas qualifiés de **High-Throughput Streaming** :

* **Qu'est-ce que c'est ?** Des flux gigantestes et incessants de données. Exemples :
  * Ingestion des clics web en direct d'Amazon (1 million de clics par seconde).
  * Signaux télémétriques de flottes de véhicules autonomes.
* **Pourquoi pas du "Push" ici ?** Effectuer 1 million de requêtes `HTTP POST` par seconde créerait un Overhead HTTP (latence réseau, headers TCP) catastrophique, appelé DDoS par accident.
* **Le Pattern recommandé :** Dans ce cas, et UNIQUEMENT dans ce cas, on utilise un modèle "Pull" (Apache Kafka ou Pub/Sub Stream) avec des serveurs dédiés (GKE, Dataflow) allumés en continu, "tirant" les messages par très grosses grappes optimisées.

---

## 5. Application à The Outdoor Axolotl : Pourquoi le Push est parfait

Dans le cadre de **Factory Writer**, la charge de l'entreprise Axolotl s'apparente à des "Bursts" (pics très concentrés) asynchrones.

### Simulation de charge (Le "Bursty Workload")
Imaginons un lancement majeur, une nouvelle collection "Spring-Summer 2026" contenant 400 nouveaux produits (SKUs).
1. **Événements ERP (Eventarc Push)** : L'ERP d'Axolotl pousse 400 messages métier `ProductCreated`.
2. **Archives Usines (Eventarc Push)** : L'usine uploade une archive qui génère, disons, 3 fichiers PDF par produit. Cela génère 1 200 événements de type `google.cloud.storage.object.v1.finalized`.

**Bilan d'exécution :**
Le système va recevoir environ **1 600 événements HTTP Push** concentrés sur une fenêtre d'environ 5 à 10 minutes, puis plus rien pendant 6 mois (jusqu'à la collection "Autumn-Winter").

### Verdict Architectural et l'Impact FinOps (Financial Operations)

Dans la réalité du Retail (que ce soit un géant de la distribution ou une marque Premium comme Axolotl), **la création de produits n'est pas un flux continu lissé sur l'année, c'est un flux "haché" dicté par les Saisons (Collections).** 
Le service d'Ingénierie Produit prépare les nouvelles gammes d'été pendant des mois en brouillon, et le jour du "Gel de la Collection", l'ERP valide tout d'un seul bloc.

* **Le Désastre du modèle "Pull" (Le serveur permanent) :** Si Axolotl utilisait un serveur "Pull" allumé en permanence (24/7) pour surveiller la file d'attente ou un broker Kafka, l'entreprise paierait **8 760 heures d'infrastructure Cloud par an** pour un système qui enregistre **0 activité pendant 360 jours**, juste pour être sûr de capter les deux rafales de 10 minutes liées au Printemps et à l'Automne. 
* **Le Miracle FinOps du "Push Serverless" :**
  1. **À l'instant T0 (Jours creux)**: 0 conteneur, coût d'hébergement API à **0$**.
  2. **À T0 + 1s (Activation de la collection)**: Les 1 600 Webhooks Eventarc s'abattent simultanément sur l'API Cloud Run.
  3. **À T0 + 5s**: Cloud Run "Scale" instantanément et démarre une dizaine d'instances (chacune gérant ~160 requêtes concurrentes ultra-rapides grâce à ASGI/FastAPI).
  4. **À T0 + 10s**: L'API a dépilé les 1 600 CloudEvents, inscrit l'existence des produits, lancé les 400 Workflows asynchrones sur **Temporal**, et répondu `HTTP 200` à l'infrastructure Google.
  5. **À T0 + 2 minutes**: Cloud Run coupe les conteneurs et redescend l'API à un coût de 0$. (En tâche de fond, le Worker Temporal prend le relais à son rythme lissé pour l'extraction OCR et LiteLLM).

Ce comportement est exactement ce qui fait du "Webhook Push + Cloud Run" un coup de maître technologique en 2026 : un alignement absolu entre la modernité logicielle de l'Event-Driven et l'efficience économique maximale (FinOps) exigée pour les flux Data irréguliers des e-commerçants.
