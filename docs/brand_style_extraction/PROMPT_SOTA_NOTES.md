# Prompt SOTA Notes

## Revue SOTA Avril 2026

Oui. Au **22 avril 2026**, après revue sur **15 sources officielles/primaires**, je dirais ceci :

**Verdict**
Le couple [system.mustache](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/application/prompts/style_guide_extract_rules/v1/system.mustache) + [user.mustache](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/factory_writer/application/prompts/style_guide_extract_rules/v1/user.mustache) est maintenant **proche du top SOTA pour du prompt-only** sur ce use case d’extraction structurée.  
Il est **bien mieux découpé qu’avant** :
- `system` porte maintenant le **rôle**, les **invariants stables**, et la **sémantique durable des types**
- `user` porte la **mission du run**, les **données injectées**, le **protocole de couverture/classification**, et les **exemples**

J’ai aussi nettoyé ce qui n’était pas optimal SOTA :
- suppression d’une partie de la redondance entre `system` et `user`
- remplacement du wording `chunks` par `extraits source` dans le prompt
- conservation des règles de classification ambiguës dans le `user` seulement quand elles sont spécifiques au task
- compilation revérifiée après refactor

**Ce qui est maintenant aligné SOTA**
- séparation correcte `system` / `user`
- prompt structuré avec tags explicites
- sortie contrainte par schéma au niveau API, sans recopier le schéma JSON dans le prompt
- consignes de couverture explicites sans hardcoder un nombre de règles
- exemples courts et ciblés pour les cas ambigus
- pas de dépendance au terme technique Document AI “chunk” dans le wording métier

**Ce qui n’est pas “top absolu”**
- pour des PDFs plus longs et plus variés, le vrai SOTA n’est plus seulement le prompt : c’est **prompt + eval harness + éventuellement multi-pass extraction**
- il reste une tension classique entre :
  - prompts statiques au début pour le caching / stabilité
  - données longues au début pour certains modèles long-context  
  Comme ton pipeline envoie déjà des extraits découpés, le compromis actuel est raisonnable.
- le prompt est maintenant bon, mais **la vraie preuve de niveau SOTA** sera un bench sur plusieurs PDFs, pas une seule réussite

**Mon jugement net**
- **prompt-only** : oui, on est maintenant **dans une très bonne zone SOTA**
- **système d’extraction complet** : non, pas encore, tant qu’on n’a pas un petit banc d’évaluation multi-documents

**Sources revues**
1. [OpenAI Prompting](https://developers.openai.com/api/docs/guides/prompting)
2. [OpenAI Reasoning Best Practices](https://developers.openai.com/api/docs/guides/reasoning-best-practices)
3. [OpenAI Safety Best Practices](https://developers.openai.com/api/docs/guides/safety-best-practices)
4. [OpenAI Prompt Optimizer](https://developers.openai.com/api/docs/guides/prompt-optimizer)
5. [OpenAI Prompt Caching](https://developers.openai.com/api/docs/guides/prompt-caching)
6. [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
7. [Google Vertex AI System Instructions Introduction](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/system-instruction-introduction)
8. [Google Vertex AI Use System Instructions](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/system-instructions)
9. [Google Vertex AI Prompt Design Strategies](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/prompt-design-strategies)
10. [Google Vertex AI Break Down Prompts](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/break-down-prompts)
11. [Google Vertex AI Structured Output](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/control-generated-output)
12. [Google Vertex AI Structure Prompts](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/structure-prompts)
13. [Anthropic Prompting Best Practices / Give Claude a Role](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/system-prompts)
14. [Anthropic XML Tags](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/use-xml-tags)
15. [Anthropic Prompt Improver](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompt-improver)

La prochaine étape sérieuse, si tu veux, c’est que je te construise un **mini eval harness** local qui lance 5 à 10 runs sur plusieurs PDFs de référence et compare :
- couverture des citations source
- stabilité des types
- stabilité du nombre de règles
- dérives entre runs

## Explication Des Limites Restantes

Il y a 2 idées distinctes.

**1. Pourquoi le prompt seul ne suffit plus dès que les PDFs deviennent variés**
Sur un PDF simple comme Axolotl, un bon prompt peut suffire.
Mais dès que tu passes à des documents plus longs, plus sales, plus ambigus, avec des structures différentes, le problème n’est plus seulement :
- “le prompt est-il bien écrit ?”

Le problème devient aussi :
- est-ce qu’il reste stable sur 20 documents différents ?
- est-ce qu’il dérive selon la mise en page ?
- est-ce qu’il oublie des familles de règles sur certains cas ?
- est-ce qu’il reclassifie différemment des cas ambigus selon les runs ?

C’est pour ça que le vrai SOTA en prod, ce n’est pas juste un “bon prompt”. C’est :
- **prompt**
- **eval harness**
- parfois **multi-pass extraction**

### `eval harness`
C’est un banc de test reproductible.
Tu prends un petit corpus de PDFs de référence, avec un attendu métier ou au moins des assertions de couverture, puis tu mesures :
- citations attendues présentes ou non
- types stables ou non
- nombre de règles trop bas / trop haut
- dérive entre plusieurs runs du même document

Sans ça, tu peux avoir un prompt qui “a l’air bon” sur un doc, mais qui casse discrètement sur les suivants.

### `multi-pass extraction`
Au lieu de demander au modèle de tout faire d’un coup :
- détecter tous les fragments
- les classer
- les dédupliquer
- les transformer en JSON final

tu découpes.

Exemple :
1. pass 1 : inventorier les fragments normatifs explicites
2. pass 2 : classer chaque fragment
3. pass 3 : convertir en règles finales

Pourquoi c’est plus SOTA sur les cas durs :
- chaque étape est plus simple
- moins de fusion accidentelle
- debug beaucoup plus facile
- meilleure contrôlabilité

En contrepartie :
- plus de coût
- plus de latence
- plus de code orchestration

Donc sur ton POC actuel, je ne dis pas “il faut absolument le faire maintenant”.  
Je dis :
```text
si demain tu veux tenir sur des PDFs réellement variés,
le prompt seul finira par plafonner.
```

**2. La tension entre “instructions statiques au début” et “données longues au début”**
Il y a deux bonnes pratiques qui tirent dans des directions différentes.

### Bonne pratique A : mettre le contenu statique au début
Les docs OpenAI sur le prompt caching recommandent de mettre :
- instructions stables
- exemples stables

au début du prompt, pour maximiser le cache et la stabilité de préfixe.

Idée :
```text
même préfixe = meilleur cache = moins de coût/latence
```

### Bonne pratique B : mettre les longs documents tôt dans le contexte
Les docs Anthropic long-context disent que, pour de très gros documents, mettre les documents longs en haut peut améliorer la performance.

Idée :
```text
quand le contexte est énorme, le modèle “voit” mieux le document si tu le mets tôt
```

### Pourquoi il y a tension
Si tu mets :
- d’abord tout le gros document
- puis les instructions

tu perds une partie du bénéfice “préfixe statique identique”.

Si tu mets :
- d’abord le prompt fixe
- puis les données variables

tu gagnes en cache / stabilité de préfixe, mais pour certains très longs contextes tu n’es pas forcément dans l’ordre le plus performant du point de vue lecture-document.

### Pourquoi chez toi c’est acceptable
Ton pipeline n’envoie pas :
- un PDF brut de 200 pages

Il envoie :
- des **extraits déjà découpés**
- beaucoup plus petits
- déjà orientés extraction

Donc tu n’es pas dans un vrai scénario “long-context monstrueux”.  
Du coup, le compromis actuel est raisonnable :
- `system` + instructions stables
- puis `user` avec mission + extraits source
- sans renverser toute la structure pour optimiser un cas long-context extrême

Autrement dit :
```text
comme les données envoyées au modèle sont déjà compressées et structurées,
la tension existe théoriquement,
mais elle est beaucoup moins critique dans ton pipeline actuel.
```

**Résumé net**
- pour un seul PDF simple, un bon prompt peut suffire
- pour un produit robuste sur beaucoup de PDFs, il faut mesurer avec un eval harness
- si les cas deviennent vraiment difficiles, il faut parfois passer en multi-pass
- la question “où mettre les données dans le prompt” dépend aussi du volume de contexte
- dans ton cas, comme on envoie des extraits déjà découpés, le design actuel reste défendable

Si tu veux, je peux te faire juste après un exemple concret de :
- **single-pass actuel**
vs
- **multi-pass minimal réaliste** pour votre flow.
