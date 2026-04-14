Oui. Voici la version claire.

Le point le plus important à retenir est celui-ci :

**`foundation model` / `custom model based` / `custom template based` ne sont pas trois extracteurs différents de Google Document AI. Ce sont trois modes du seul `Custom Extractor`.**
Les autres extracteurs, comme **Form Parser** ou **Layout Parser**, n’ont pas ces trois options. Google le dit explicitement dans sa vue d’ensemble de l’extraction. ([Google Cloud Documentation][1])

## 1) Les différents types d’extracteurs

### A. Form Parser

**À quoi il sert**
Il sert à extraire des **paires clé/valeur**, des **tableaux** et des éléments de formulaires structurés. C’est le bon choix quand tes documents ressemblent à des formulaires ou à des fiches assez standard, et que tu veux surtout récupérer les champs visibles tels quels. ([Google Cloud Documentation][1])

**Quand l’utiliser**
Utilise-le si tes documents sont des **formulaires structurés** avec des libellés bien visibles, par exemple des champs du style `Material: Oak`, `Width: 1200 mm`, `Certification: FSC`, tous présentés de façon assez régulière. ([Google Cloud Documentation][2])

**Options foundation / model based / template based ?**
**Aucune.** Ces trois options n’existent pas pour le Form Parser. Elles existent seulement pour le **Custom Extractor**. ([Google Cloud Documentation][1])

---

### B. Custom Extractor

**À quoi il sert**
C’est l’extracteur à utiliser quand **tu connais les champs métier que tu veux sortir** et qu’il n’existe pas de processeur préentraîné adapté. Google dit que le Custom Extractor sert à extraire les **entités que tu définis toi-même dans le schéma**. ([Google Cloud Documentation][1])

**Quand l’utiliser**
Utilise-le quand tu veux extraire des champs comme :

* `type_de_bois`
* `nuance_acier`
* `epaisseur`
* `contrainte_assemblage`
* `eco_certification`

Autrement dit : quand tu ne veux pas juste lire un formulaire générique, mais **sortir tes propres champs métier**. ([Google Cloud Documentation][1])

**Options disponibles**
C’est **le seul** extracteur qui propose ces trois modes : **foundation model**, **custom model based**, **custom template based**. Google recommande de **commencer par le foundation model** comme premier choix, puis d’essayer les autres si nécessaire. ([Google Cloud Documentation][1])

#### B1. Foundation model

**Quand l’utiliser**
C’est le bon choix quand les documents ont une **forte variation de mise en page** et beaucoup de **texte libre / paragraphes**. Google le recommande comme **première option pour les layouts variables**. ([Google Cloud Documentation][3])

**Exemple concret**
Une usine met la nuance d’acier dans un tableau, une autre dans un paragraphe, une troisième dans une note technique : c’est typiquement un cas **foundation model**. ([Google Cloud Documentation][3])

**Données nécessaires**
Google indique qu’on peut viser une qualité de production avec environ **0 à 50+ documents** selon la variabilité, et que ces modèles demandent **peu de données supplémentaires** par rapport aux autres approches. ([Google Cloud Documentation][3])

#### B2. Custom model based

**Quand l’utiliser**
C’est le bon choix si tu **ne veux pas utiliser de generative AI**, ou si tes documents ont une **variation faible à moyenne** et peu de texte libre. Google le présente comme un modèle entraîné avec tes données, sans generative AI. ([Google Cloud Documentation][4])

**Exemple concret**
Tes fiches techniques changent un peu selon les fournisseurs ou les années, mais restent proches : même type de sections, mêmes zones, peu de paragraphes libres. Là, le **custom model based** peut convenir. ([Google Cloud Documentation][3])

**Données nécessaires**
Google indique un besoin plus élevé en données annotées, typiquement **10 à 100+ documents** pour une qualité de production, et au minimum **10 documents d’entraînement** et **10 de test** pour entraîner ce type de modèle. ([Google Cloud Documentation][3])

#### B3. Custom template based

**Quand l’utiliser**
C’est le bon choix pour des documents à **mise en page fixe**, presque identiques d’un fichier à l’autre. Google le réserve aux documents avec **layout fixe** et peu de texte libre. ([Google Cloud Documentation][3])

**Exemple concret**
Toutes les usines d’un même groupe envoient exactement la même fiche PDF avec les mêmes cases au même endroit : là, le **template based** est souvent le plus simple. ([Google Cloud Documentation][3])

**Données nécessaires**
Google indique qu’il faut au minimum **3 documents d’entraînement**, **3 de test** et **3 labels de schéma**, et précise qu’ajouter beaucoup plus de documents n’améliore pas forcément ce mode ; il faut surtout annoter très précisément. ([Google Cloud Documentation][5])

---

### C. Layout Parser

**À quoi il sert**
Il sert à extraire la **structure du document** : texte, tableaux, listes, blocs, et à renvoyer des **chunks contextualisés**. Ce n’est pas, en premier lieu, un extracteur métier pour tes champs comme `nuance_acier` ou `certification`. ([Google Cloud Documentation][2])

**Quand l’utiliser**
Utilise-le si ton besoin est surtout de **structurer le contenu**, faire de la **recherche** dans les documents, ou préparer un pipeline RAG / QA. Pas comme extracteur principal de tes valeurs métier. ([Google Cloud Documentation][2])

**Options foundation / model based / template based ?**
**Aucune.** ([Google Cloud Documentation][1])

---

### D. Parsers préentraînés

**À quoi ils servent**
Ils servent à extraire des champs dans des **types de documents spécialisés** déjà couverts par Google. La doc les distingue du Custom Extractor. ([Google Cloud Documentation][2])

**Quand l’utiliser**
Utilise-les uniquement si ton document correspond déjà à un type métier reconnu par Google. Sinon, reviens au **Custom Extractor**. ([Google Cloud Documentation][3])

**Options foundation / model based / template based ?**
**Aucune.** Ces trois modes ne concernent pas les parsers préentraînés. ([Google Cloud Documentation][1])

---

## 2) Résumé ultra simple

Tu peux retenir ça :

* **Form Parser** = formulaires structurés
* **Custom Extractor** = tes champs métier
* **Layout Parser** = structure du document
* **Pretrained parser** = document métier déjà prévu par Google

Et à l’intérieur de **Custom Extractor seulement** :

* **foundation model** = documents variables
* **custom model based** = variation faible à moyenne, sans GenAI
* **custom template based** = documents fixes ([Google Cloud Documentation][1])

---

## 3) Mon explication de l’architecture que je te propose

### L’idée générale

Quand je t’ai dit :

**“classification par catégorie produit + Custom Extractor par famille documentaire”**

je voulais dire :

1. **identifier quel type de document tu as reçu**
2. **envoyer ce document vers le bon extracteur**
3. **ne pas essayer de tout faire avec un seul extracteur géant** ([Google Cloud Documentation][6])

### Pourquoi je propose ça

Google indique que le **Custom Classifier** sert à reconnaître des classes de documents, puis à **passer le document au processeur d’extraction approprié**. C’est exactement le principe de routage dont je parlais. ([Google Cloud Documentation][6])

### Ce que ça donne en pratique

Imaginons que tu reçoives un gros dossier technique d’usine. Dedans, tu peux avoir :

* une fiche matière
* une instruction d’assemblage
* un certificat environnemental
* une fiche de dimensions

Dans ce cas, l’architecture logique est :

**Étape 1 : OCR si le PDF est scanné**
Document AI distingue bien la phase de **digitization/OCR** de la phase d’extraction. ([Google Cloud Documentation][2])

**Étape 2 : Splitter si un PDF contient plusieurs sous-documents**
Document AI prévoit aussi des processeurs de **split** pour découper un paquet documentaire en unités plus propres. ([Google Cloud Documentation][2])

**Étape 3 : Classifier**
Tu classes chaque morceau en catégories, par exemple :

* `fiche_matiere`
* `assemblage`
* `certificat`
* `dimensions` ([Google Cloud Documentation][6])

**Étape 4 : Routage vers le bon extracteur**
Ensuite tu envoies :

* `fiche_matiere` → extracteur matière
* `assemblage` → extracteur assemblage
* `certificat` → extracteur certification
* `dimensions` → extracteur dimensions ([Google Cloud Documentation][6])

### Pourquoi plusieurs extracteurs et pas un seul ?

Parce qu’un seul extracteur peut devenir trop large, trop ambigu et trop difficile à maintenir. La doc indique d’ailleurs qu’un schéma de Custom Extractor supporte jusqu’à **150 labels**, et recommande plusieurs processeurs si la logique métier exige davantage d’entités. Même sans atteindre 150, c’est déjà un bon signal d’architecture : séparer quand les familles documentaires sont différentes. ([Google Cloud Documentation][7])

### Ce que je te conseille pour ton cas

Pour toi, je ne ferais **pas** un extracteur par usine.
Je ferais plutôt un extracteur par **famille documentaire** ou par **catégorie produit si la structure change vraiment**.

Exemple :

* **Extracteur Matières**
  champs : type de bois, essence, nuance acier, traitement, revêtement
* **Extracteur Dimensions**
  champs : longueur, largeur, épaisseur, tolérances
* **Extracteur Assemblage**
  champs : type de fixation, ordre de montage, couple, contrainte
* **Extracteur Certifications**
  champs : type de certification, identifiant, organisme, date d’expiration

Ça, c’est ma recommandation d’architecture à partir de la logique Document AI. Elle est cohérente avec le fait que Google prévoit le **classifier** pour router vers le bon extracteur, et que le **foundation model** est recommandé pour les layouts variables. ([Google Cloud Documentation][6])

### Quel mode mettre dans ces extracteurs ?

Mon conseil par défaut :

* **Extracteur Matières** → **Custom Extractor / foundation model**
* **Extracteur Dimensions** → **foundation model**, sauf si les fiches sont strictement identiques, auquel cas **template based**
* **Extracteur Assemblage** → **foundation model** car il y a souvent du texte libre
* **Extracteur Certifications** → foundation model ou template based selon la régularité des certificats ([Google Cloud Documentation][3])

### Et le fine-tuning dans tout ça ?

Le **foundation model** est le point de départ. Ensuite, si les résultats ne sont pas assez bons, tu **fine-tunes** ce Custom Extractor avec plus de documents annotés. Google dit que le foundation model est recommandé en premier, et que les descriptions de propriétés aident la qualité d’extraction. ([Google Cloud Documentation][1])

### Dernier point important : contrôle qualité

Le Custom Extractor renvoie un **confidence score** par entité. Google explique que ce score sert justement à déclencher une **revue manuelle** quand la confiance est faible. Donc dans l’architecture, il faut prévoir une file de contrôle humain pour les champs incertains. ([Google Cloud Documentation][3])

## Conclusion

La réponse simple est :

**Les 3 modes `foundation model / custom model based / custom template based` ne concernent que le `Custom Extractor`.** ([Google Cloud Documentation][1])

Et pour ton cas, l’architecture la plus logique est :

**OCR si besoin → split du dossier → classification du type de document → routage vers un ou plusieurs Custom Extractors → revue humaine des champs à faible confiance.** ([Google Cloud Documentation][2])

La plupart du temps, pour des dossiers venant de nombreuses usines, je commencerais par :

**plusieurs `Custom Extractors` en mode `foundation model`, organisés par famille documentaire.** ([Google Cloud Documentation][3])

Je peux maintenant te faire la suite la plus utile : **un schéma concret de 4 extracteurs pour ton projet, avec les champs exacts à créer dans chacun**.

[1]: https://docs.cloud.google.com/document-ai/docs/extracting-overview "Extraction overview  |  Document AI  |  Google Cloud Documentation"
[2]: https://docs.cloud.google.com/document-ai/docs/overview "Document AI overview  |  Google Cloud Documentation"
[3]: https://docs.cloud.google.com/document-ai/docs/custom-extractor-overview "Custom extractor overview  |  Document AI  |  Google Cloud Documentation"
[4]: https://docs.cloud.google.com/document-ai/docs/custom-based-extraction "Custom-based extraction  |  Document AI  |  Google Cloud Documentation"
[5]: https://docs.cloud.google.com/document-ai/docs/ce-template-based "Template-based extraction  |  Document AI  |  Google Cloud Documentation"
[6]: https://docs.cloud.google.com/document-ai/docs/custom-classifier "Create, use, and manage a custom document classifier  |  Document AI  |  Google Cloud Documentation"
[7]: https://docs.cloud.google.com/document-ai/docs/training-overview "Train and evaluate  |  Document AI  |  Google Cloud Documentation"
