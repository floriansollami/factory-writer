# Script texte normal - Factory Writer

## Slide 1 - Contexte

**Temps de lecture estimé : 1 min à 1 min 10 à débit naturel.**

Bonjour à tous. Je me présente, Florian, consultant GenAI chez SFEIR.

Vous avez missionné SFEIR pour réfléchir avec vous à Factory Writer, votre projet de génération automatisée de fiches produit. L’idée aujourd’hui, c’est de poser le problème, puis de vous proposer une solution cible pour y répondre.

Je commence par le contexte. Vous êtes une marque B2C premium dans l’univers du jardin, avec du mobilier extérieur haut de gamme et des outils de jardin ergonomiques.

Vos produits sont conçus en interne. La fiche produit doit donc refléter à la fois la réalité technique du produit et le ton Axolotl.

Aujourd’hui, les équipes partent de dossiers techniques usine, puis doivent vérifier les données et les reformuler en fiche e-commerce. Ce processus prend environ trois semaines.

C’est ce contexte qui crée le besoin Factory Writer : réduire un goulot d’étranglement éditorial, sans banaliser la fiche produit ni perdre la confiance dans les informations utilisées.

## Slide 2 - Objectifs client

**Temps de lecture estimé : 1 min à 1 min 10 à débit naturel.**

À partir de ce contexte, il y a quatre objectifs à garder en tête.

Le premier, c’est la productivité : passer d’un cycle autour de trois semaines à une fiche prête à relire en moins de deux minutes après l’import des documents.

Le deuxième, c’est la fiabilité technique. Une dimension, une matière ou une certification fausse peut directement nuire à la marque. Donc l’IA ne doit pas inventer ou corriger seule les données techniques.

Le troisième, c’est la scalabilité. La solution doit fonctionner sur un produit, mais aussi sur plusieurs centaines de références lors d’un lancement Spring/Summer.

Et le quatrième, c’est l’approche context-first. L’idée n’est pas d’entraîner un modèle qui ferait tout, mais de construire un contexte propre, validé, versionné, puis de générer à partir de ce contexte.

Ces quatre objectifs donnent la direction : on veut aller vite, mais sans perdre le contrôle.

## Slide 3 - Principe directeur

**Temps de lecture estimé : 1 min à 1 min 10 à débit naturel.**

La conséquence directe des objectifs précédents, c’est qu’on ne peut pas générer une fiche produit directement depuis des PDFs bruts.

Si on donne simplement les documents à un LLM en lui demandant d’écrire la fiche, on gagne du temps, mais on perd le contrôle. On ne sait pas toujours quelle information a été utilisée, si une valeur a été mal lue, ou si le modèle a complété une information absente.

Le principe directeur que je propose est donc simple : avant de générer, on construit un contexte produit fiable.

Ce contexte contient les faits techniques validés, les règles du guide de style actif et les signaux commerciaux utiles.

Ensuite seulement, le modèle peut rédiger. Il ne part pas d’un PDF brut ; il part d’un contexte clair, versionné, sourcé et contrôlé.

C’est ce principe qui permet d’aller vite, tout en gardant une vraie barrière contre l’hallucination.

## Slide 4 - Vue globale cible

**Temps de lecture estimé : 1 min 20 à 1 min 30 à débit naturel.**

Maintenant qu’on a posé le principe du contexte contrôlé, voici la vue globale de l’architecture cible.

L’idée, c’est d’avoir une chaîne event-driven : les informations arrivent depuis les systèmes existants, puis un orchestrateur durable les capte sous forme d’événements et déclenche la bonne étape quand les bons prérequis sont disponibles. On va le détailler juste après.

Chaque étape produit ou met à jour une donnée interne : un document source, un fact technique, un pack de style, un signal commercial, puis un snapshot de contexte.

La génération arrive seulement à la fin de cette chaîne.

Donc à ce niveau, il faut surtout retenir le flux : sources, événements, orchestration, contexte produit, génération contrôlée.

## Slide 5 - Architecture technique cible

**Temps de lecture estimé : 1 min 15 à 1 min 25 à débit naturel.**

Sur cette slide, on zoome d’un cran. Le schéma est un C4 Container Diagram : il ne montre pas le code, il montre les grandes briques applicatives qui s’exécutent ou qui stockent les données.

La lecture se fait de gauche à droite. Les systèmes externes et le back-office envoient des événements ou des commandes à l’API / Event Gateway. C’est le point d’entrée unique.

Ensuite, l’orchestrateur durable suit le cycle de vie d’une référence produit. Il ne fait pas les appels externes lui-même ; il planifie le travail dans des files de tâches, puis délègue aux workers d’exécution.

Ces workers sont séparés par responsabilité. Document Processing appelle Document Intelligence pour classifier et extraire. Style Guide gère les règles de marque. Commercial Signals prépare les signaux issus des ventes et des retours clients. Product Sheet Generation arrive à la fin, pour générer la fiche.

À droite, les stores gardent les traces importantes : les PDFs et preuves, les facts et snapshots, les signaux analytics, et l’audit. L’Operational DB matérialise ensuite le Product Context Snapshot.

Le point clé du schéma, c’est celui-là : le LLM Gateway ne lit ni les PDFs, ni les stores bruts. Il est appelé uniquement par le worker de génération, à partir d’un Product Context Snapshot déjà validé.

## Slide 6 - Pourquoi un orchestrateur durable

**Temps de lecture estimé : 1 min 20 à 1 min 30 à débit naturel.**

Le cycle de vie d’une fiche produit n’est pas un simple appel API.

Pour une référence produit, on peut recevoir les dossiers techniques maintenant, valider le guide de style plus tard, recalculer les signaux commerciaux ensuite, et parfois attendre une correction humaine.

Sans un système d’orchestration durable, ça devient vite compliqué : il faut savoir ce qui est déjà prêt, ce qui manque encore, et où reprendre le traitement.

Avec un orchestrateur durable, chaque référence produit a un suivi durable. L’orchestrateur garde l’état, attend des signaux métier, et reprend quand un prérequis arrive.

Les signaux typiques sont : `TechnicalFactsReady`, `StylePackActivated`, et `CommercialSnapshotAvailable`.

Si tout est prêt, l’orchestrateur crée le Product Context Snapshot. Si quelque chose manque, il attend. Si une revue humaine est nécessaire, il attend la décision puis reprend au bon endroit.

Le point important, c’est qu’on évite les scripts fragiles, les cron jobs qui repassent en boucle, ou les états perdus entre deux services. L’orchestrateur durable devient la mémoire fiable du cycle de vie produit.

## Slide 7 - Ingestion technique et zéro hallucination

**Temps de lecture estimé : 1 min 20 à 1 min 30 à débit naturel.**

Ici, on zoome sur la chaîne technique.

L’idée est simple : on ne demande pas au LLM de lire les PDFs et de se débrouiller tout seul.

D’abord, on classe chaque document. Est-ce que c’est une fiche technique ? Une fiche matière ? Une notice de montage ? Ou est-ce que le document est hors périmètre ?

Ensuite, selon le type détecté, on envoie le PDF vers le bon modèle d’extraction.

Et là, point important : le modèle d’extraction ne produit pas directement une vérité finale. Il propose des candidats, avec une valeur, une source, une page, et un score de confiance quand il est disponible.

Après ça, le backend reprend la main avec des contrôles déterministes. Est-ce que le champ est requis ? Est-ce que l’unité est lisible ? Est-ce que la valeur est réaliste ? Est-ce qu’une autre source dit autre chose ?

Si tout est cohérent, la donnée devient un fact technique validé.

Sinon, elle part en revue humaine.

Et c’est seulement cette couche de facts techniques validés qui pourra ensuite être utilisée pour générer la fiche.

## Slide 8 - Style guide

**Temps de lecture estimé : 1 min à 1 min 10 à débit naturel.**

Après la partie technique, il y a un autre sujet important : la voix de marque.

Une fiche Axolotl doit être juste, mais elle doit aussi avoir le bon ton. Elle doit rester premium, claire, cohérente, et éviter les formulations qui ne correspondent pas à la marque.

Donc on ne veut pas simplement écrire dans le prompt : “écris comme Axolotl”, et espérer que le modèle comprenne toujours la même chose.

L’approche cible, c’est de traiter le style guide comme une vraie source. On en extrait des règles de ton, de vocabulaire et de structure. Ces règles sont relues, validées, puis activées dans un style pack.

Une fois actif, ce style pack peut être réutilisé pour toutes les fiches produit.

Comme pour les facts techniques, on ne laisse pas tout au modèle. On transforme la voix de marque en règles contrôlées, versionnées et réutilisables.

## Slide 9 - Signaux commerciaux

**Temps de lecture estimé : 1 min à 1 min 10 à débit naturel.**

On a maintenant deux briques contrôlées : les facts techniques pour la vérité produit, et le style pack pour la voix de marque.

La troisième brique, ce sont les signaux commerciaux.

Par exemple : les ventes, les retours clients, les questions fréquentes, les objections, ou les arguments qui fonctionnent bien sur une famille de produits.

Ces signaux sont utiles pour orienter la fiche. Ils peuvent aider à choisir quel bénéfice mettre en avant, quel vocabulaire utiliser, ou quelle objection traiter dans la description.

Mais ils ne doivent jamais devenir une source de vérité technique.

Si un retour client dit qu’une table est légère, mais que le dossier technique indique 58 kilos, c’est le dossier technique qui gagne.

Donc on injecte ces signaux dans le contexte produit comme des signaux d’orientation commerciale, pas comme des facts.

La séparation est simple : les facts techniques disent ce qui est vrai, le style guide dit comment parler, et les signaux commerciaux aident à choisir l’angle.

## Slide 10 - Contexte produit

**Temps de lecture estimé : 1 min à 1 min 10 à débit naturel.**

On arrive maintenant au point de jonction : le contexte produit.

Les facts techniques, le style pack et les signaux commerciaux ne partent pas séparément vers la génération. On les assemble d’abord dans un snapshot.

Ce snapshot est figé, versionné et sourcé.

Ça veut dire que pour une fiche générée, on peut retrouver quelles données techniques ont été utilisées, quel style pack était actif, et quels signaux commerciaux ont orienté la rédaction.

C’est important, parce que la génération ne doit pas dépendre d’un état flou ou d’un prompt qui va chercher un peu partout.

Le modèle reçoit un contexte clair : ce qui est vrai, comment parler, et quel angle commercial privilégier.

Donc le Product Context Snapshot devient la frontière d’entrée de la génération. Avant lui, on collecte et on contrôle. Après lui, on peut générer.

## Slide 11 - Génération contrôlée

**Temps de lecture estimé : 1 min 15 à 1 min 25 à débit naturel.**

Une fois le contexte produit prêt, on peut générer la fiche.

Mais la génération reste contrôlée. On ne fait pas un appel libre au modèle avec un prompt improvisé.

On part du Product Context Snapshot, puis on utilise une recette de prompt versionnée. Cette recette définit le rôle du modèle, le format attendu, les contraintes, et la manière d’utiliser les données du contexte.

Ensuite, l’appel passe par une LLM Gateway. L’intérêt, c’est de garder une interface stable avec les providers et les modèles : on peut router, tracer, limiter, ou changer de modèle sans réécrire toute l’application.

Le modèle renvoie ensuite une sortie structurée. Ce n’est pas juste un texte libre : le backend attend des champs précis, comme un titre, une description, des bénéfices, des spécifications et des raisons de relecture si besoin.

Enfin, le backend applique un post-check déterministe. Il vérifie par exemple les sections obligatoires, les claims interdits, les champs vides, ou les signaux de relecture.

Donc le LLM rédige, mais le système garde le contrôle du contexte, du format et du statut final.

## Slide 12 - Human-on-the-loop

**Temps de lecture estimé : 1 min 10 à 1 min 20 à débit naturel.**

Je fais une distinction importante ici : on n’utilise pas l’humain de la même manière partout.

Pour le style guide, on est plutôt sur du human-in-the-loop. Avant d’activer des règles de marque qui vont être réutilisées sur toutes les fiches, on veut une validation humaine explicite.

En revanche, pour les fiches produit, on vise du human-on-the-loop.

Le système avance automatiquement quand les contrôles passent. L’humain n’intervient que si un contrôle bloque : confiance faible, contradiction, champ requis absent, valeur incohérente, ou document hors périmètre.

Dans ce cas, il ne réécrit pas tout le processus. Il prend une décision ciblée : confirmer, corriger, rejeter ou demander un nouveau document.

Ensuite, le flow reprend automatiquement au bon endroit.

C’est cette différence qui permet de garder le contrôle, sans transformer chaque fiche produit en validation manuelle complète.

## Slide 13 - LLMOps et offline lab

**Temps de lecture estimé : 1 min 20 à 1 min 30 à débit naturel.**

Après les contrôles et les décisions humaines ciblées, il reste une question : comment améliorer la qualité de génération dans le temps.

Une recette de génération peut très bien fonctionner sur quelques produits, puis montrer ses limites sur une autre famille, une certification sensible, ou un document plus ambigu.

Donc la cible, c’est d’avoir une boucle d’amélioration contrôlée.

On versionne d’abord la recette : le prompt, le modèle, les paramètres, et les exemples éventuellement injectés.

Ensuite, on la teste sur un jeu de cas représentatifs : un produit simple, un produit avec certification, un document ambigu, une contradiction, un champ manquant.

Puis on regarde les résultats à plusieurs niveaux.

Le premier niveau, ce sont les règles déterministes : JSON valide, champs obligatoires présents, claims interdits absents, dimensions cohérentes. Là, il n’y a pas d’interprétation.

Le deuxième niveau, ce sont les rubriques métier : ton premium, clarté, fidélité aux facts, absence de survente.

Ces rubriques peuvent être notées par un juge LLM sur beaucoup de cas. Le juge ne décide pas de la vérité technique ; il sert à mesurer la qualité rédactionnelle et à comparer les versions plus vite.

Enfin, on compare les recettes : version actuelle contre version candidate, prompt A contre prompt B, modèle A contre modèle B.

Et une recette ne devient active que si elle progresse sur le jeu de tests, pas juste parce qu’un exemple isolé est convaincant.
