# Document AI Custom Extractor : fine-tuning avec corrections humaines

Voici la version propre, appuyée sur la documentation Google officielle.

Le point clé :

```text
Fine-tuned foundation model Document AI
= une nouvelle version de processor Custom Extractor
= spécialisée sur tes documents corrigés
= créée à partir d’un modèle fondation Google
```

Ce n’est pas :

```text
du fine-tuning LiteLLM
du prompt engineering
une mise à jour automatique en temps réel
une correction qui modifie immédiatement le modèle
```

C’est un cycle batch :

```text
corrections humaines
-> dataset labellisé
-> entraînement / fine-tuning
-> nouvelle processor version
-> évaluation
-> déploiement contrôlé
```

## 1. Ce que Google appelle “fine-tuning”

Dans Document AI, un `Custom Extractor` sert à extraire des **entités métier personnalisées** dans des documents pour lesquels il n’existe pas de processor pré-entraîné adapté.

Exemple Axolotl :

```text
dimension_width_cm
dimension_depth_cm
dimension_height_cm
net_weight_kg
primary_material
wood_species
metal_grade
eco_certification_type
eco_certification_id
assembly_constraint
maintenance_constraint
```

Au départ, tu peux utiliser un **Foundation model**.

Ensuite, quand tu as des documents corrigés par des humains, tu peux créer une nouvelle version fine-tuned :

```text
base version Google
+ dataset Axolotl corrigé
= processorVersions/fine-tuned-axolotl-technical-sheet-v1
```

Google documente bien que les processors peuvent avoir plusieurs versions, que ces versions peuvent être entraînées/uptrainées, évaluées, déployées et appelées explicitement.

## 2. Le flow exact recommandé

```text
1. Créer un Custom Extractor.
2. Définir le schéma des champs.
3. Importer des documents réels.
4. Auto-labeler avec un foundation model.
5. Vérifier et corriger humainement les labels.
6. Marquer les documents comme labeled.
7. Séparer train set et test set.
8. Lancer le fine-tuning pour créer une nouvelle processor version.
9. Évaluer precision / recall / F1.
10. Déployer la version si elle est meilleure.
11. Appeler explicitement cette version dans Factory Writer.
12. Réinjecter périodiquement les nouvelles corrections humaines.
```

## 3. Créer le Custom Extractor

Dans Google Cloud Console :

```text
Document AI
-> Workbench
-> Custom Extractor
-> Create processor
```

Exemple :

```text
processor_name = axolotl-technical-sheet-extractor
location = eu
type = Custom Extractor
```

Le processor est le conteneur.

Dedans, tu peux avoir plusieurs versions :

```text
foundation-baseline
fine-tuned-v1
fine-tuned-v2
fine-tuned-v3
```

Côté Factory Writer, on stockera toujours :

```text
processor_id
processor_version
base_processor_version
schema_version
```

## 4. Définir le schéma

Tu définis les champs à extraire.

Exemple :

```text
product_reference
dimension_width_cm
dimension_depth_cm
dimension_height_cm
net_weight_kg
primary_material
wood_species
metal_grade
eco_certification_type
eco_certification_id
assembly_constraint
maintenance_constraint
```

Google insiste sur un point important : les noms de champs et les descriptions influencent la qualité des modèles foundation.

Donc il ne faut pas écrire :

```text
width
```

Il vaut mieux écrire :

```text
dimension_width_cm
```

Avec une description claire :

```text
Extract the explicit product width from the technical specification.
Only extract values directly stated in the document.
Do not infer width from product name, image, or marketing text.
If both product and package dimensions are present, prefer product dimensions.
```

Pour Axolotl, je recommande :

| Champ | Mode logique |
| --- | --- |
| Dimensions | `Extract` |
| Poids | `Extract` |
| Matériaux | `Extract` |
| Certifications | `Extract` |
| Contraintes d’assemblage explicites | `Extract` |
| Catégorie documentaire | `Derive` possible, mais pas comme fact publiable |

Principe :

```text
Facts critiques publiables = Extract uniquement
```

`Derive` est utile pour classifier ou enrichir, mais pas pour certifier une dimension, un poids ou une matière.

## 5. Importer les documents

Google demande un dataset de documents pour entraîner, up-trainer ou évaluer une processor version.

Tu importes donc des PDFs réels dans le dataset.

Google propose deux stockages :

```text
Google-managed storage
Custom Cloud Storage location
```

Pour Axolotl, sauf contrainte forte, je choisirais :

```text
Google-managed storage
```

Pourquoi : Google le recommande comme option simple et moins risquée pour éviter de casser le dataset par manipulation manuelle du bucket.

Il faut séparer :

```text
train set
test set
```

Le test set est critique : il sert à mesurer si `fine-tuned-v2` est vraiment meilleure que `fine-tuned-v1`.

## 6. Auto-labeling

Google permet d’utiliser une processor version existante pour pré-remplir les labels.

Flow :

```text
Importer documents
-> Import with auto-labeling
-> choisir une version foundation ou existante
-> Document AI pré-remplit les entités
```

Exemple :

```text
Document AI propose :
dimension_width_cm = 190 cm
dimension_depth_cm = 90 cm
dimension_height_cm = 74 cm
primary_material = teck FSC
```

Mais Google précise un point important :

```text
Les documents auto-labelés ne peuvent pas être utilisés pour training/test
tant qu’ils n’ont pas été vérifiés et marqués comme labeled.
```

Donc :

```text
auto-label
-> humain vérifie
-> humain corrige
-> Mark as labeled
```

## 7. Correction humaine

C’est ici que les corrections deviennent utiles pour le fine-tuning.

Exemple :

```text
Document source :
L/P/H : 1900 / 900 / 740 mm
```

Extraction initiale :

```text
width = 900 mm
depth = 1900 mm
height = 740 mm
```

Correction humaine :

```text
width = 1900 mm
depth = 900 mm
height = 740 mm
```

Cette correction devient de la **ground truth**.

Autre exemple :

```text
Document AI propose :
net_weight_kg = 150 kg

Humain corrige :
net_weight_kg = 15.0 kg
```

Autre exemple :

```text
Document AI oublie :
eco_certification_id

Humain ajoute :
eco_certification_id = FSC-C123456
```

Ce sont ces corrections qui nourrissent le prochain fine-tuning.

## 8. Corrections depuis Factory Writer ou depuis Google Console

Il y a deux trajectoires.

### POC+

Le plus simple :

```text
Google Document AI Console
-> labeling tool
-> correction humaine
-> Mark as labeled
-> training
```

C’est suffisant pour prouver la boucle.

### Production

Plus propre :

```text
review humaine dans Factory Writer
-> stockage corrections en DB
-> job offline exporte des Document JSON avec entities corrigées
-> import pre-labeled documents dans Document AI dataset
-> fine-tune nouvelle version
```

Google documente l’import de documents pré-labelés au format `Document` JSON, à condition que les `entities` correspondent au schéma du processor.

Donc l’admin Factory Writer peut devenir la vraie interface métier, puis alimenter Document AI offline.

## 9. Lancer le fine-tuning

Dans la console :

```text
Processor
-> Build / Train
-> Create new version / Train new version
```

Tu choisis :

```text
base processor version
training set
test set
display name
training parameters si besoin
```

Exemple de version :

```text
fine-tuned-axolotl-technical-sheet-v1
```

Google expose aussi des paramètres avancés comme :

```text
training_steps
learning_rate_multiplier
```

Mais je ne les toucherais pas au début.

Règle pragmatique :

```text
d’abord améliorer le dataset
ensuite seulement jouer avec les hyperparamètres
```

Une mauvaise ground truth donnera un mauvais modèle, même avec les meilleurs paramètres.

## 10. Évaluer la nouvelle version

Google évalue les processor versions avec :

```text
precision
recall
F1
```

Ces métriques sont calculées en comparant :

```text
prédictions du processor
vs
annotations humaines du test set
```

Exemple :

| Champ | Precision | Recall | F1 | Décision |
| --- | --- | --- | --- | --- |
| `dimension_width_cm` | 0.98 | 0.96 | 0.97 | OK |
| `dimension_depth_cm` | 0.97 | 0.95 | 0.96 | OK |
| `net_weight_kg` | 0.86 | 0.78 | 0.82 | Trop faible |
| `eco_certification_id` | 0.74 | 0.62 | 0.67 | Review obligatoire |

Lecture :

```text
precision = quand le modèle extrait une valeur, est-ce correct ?
recall = est-ce qu’il retrouve tout ce qu’il devrait retrouver ?
F1 = équilibre precision / recall
```

Pour Axolotl, seuils recommandés :

| Fact | Seuil minimal |
| --- | --- |
| Dimensions | F1 >= 0.95 |
| Poids | F1 >= 0.95 |
| Matériaux | F1 >= 0.90 |
| Certification | F1 >= 0.95 |
| Assemblage | F1 >= 0.85 |

Si un champ reste faible :

```text
pas d’auto-publication
review obligatoire
```

## 11. Déployer la version

Quand la version est acceptable :

```text
Manage versions
-> Deploy version
-> éventuellement Set as default
```

Mais dans Factory Writer, je recommande de ne pas dépendre du `default`.

Il vaut mieux appeler explicitement :

```text
processorVersions/fine-tuned-axolotl-technical-sheet-v1
```

Pourquoi : reproductibilité.

Tu dois pouvoir dire :

```text
Cette fiche produit a été générée avec :
processor_id = axolotl-technical-sheet-extractor
processor_version = fine-tuned-axolotl-technical-sheet-v1
base_processor_version = pretrained-foundation-model-...
```

Google documente trois façons d’appeler un processor :

```text
sans version -> utilise default
avec version explicite -> utilise cette version
avec channel stable/rc -> utilise le channel
```

Pour Factory Writer :

```text
prod = version explicite
```

## 12. Boucle d’amélioration continue

La boucle complète devient :

```text
1. Le modèle extrait.
2. Python valide.
3. Les cas douteux vont en review.
4. L’humain corrige.
5. Les corrections sont stockées.
6. Périodiquement, on ajoute ces corrections au dataset.
7. On fine-tune une nouvelle version.
8. On compare v1 vs v2 sur le même test set.
9. Si v2 est meilleure, on la déploie.
10. Sinon, on garde v1.
```

C’est exactement le pattern cible pour Axolotl :

```text
le runtime reste rapide
les erreurs enrichissent le dataset
le modèle s’améliore par versions
chaque version est mesurée avant déploiement
```

## 13. Ce qu’il faut stocker côté Factory Writer

Pour chaque extraction :

```text
extraction_run_id
document_id
document_type
processor_id
processor_version
base_processor_version
schema_version
confidence_by_field
validation_status
review_reason
created_at
```

Pour chaque fact candidat :

```text
fact_candidate_id
fact_type
field_name
raw_value
normalized_value
unit
confidence
source_text
source_page
source_bbox
validation_status
review_reason
```

Pour chaque correction humaine :

```text
human_correction_id
fact_candidate_id
old_value
corrected_value
corrected_by
corrected_at
correction_reason
source_page
source_bbox
exported_to_docai_dataset_at
```

Pour chaque dataset/fine-tune :

```text
dataset_version
train_set_uri
test_set_uri
processor_version_created
evaluation_precision
evaluation_recall
evaluation_f1
deployed_at
rollback_from_version
```

## 14. POC vs Prod

### POC

```text
Custom Extractor Foundation model
+ validation Python
+ review par exception
+ stockage corrections
```

Pas besoin de fine-tuning immédiatement.

### POC+

```text
20 à 50 documents corrigés
dataset Document AI
fine-tuned-v1
comparaison foundation baseline vs fine-tuned-v1
```

### Production

```text
dataset versionné
test set figé
fine-tuning périodique
déploiement contrôlé
appel explicite de processor version
rollback possible
métriques par fournisseur et type documentaire
```

## Résumé

Pour faire un **Fine-tuned foundation model** avec les corrections humaines :

```text
1. Créer un Custom Extractor.
2. Définir un schéma clair avec descriptions.
3. Importer des documents réels.
4. Auto-labeler avec le foundation model.
5. Corriger les labels humainement.
6. Marquer les documents comme labeled.
7. Assigner train/test.
8. Créer une nouvelle processor version via fine-tuning.
9. Évaluer precision / recall / F1.
10. Déployer seulement si les métriques passent.
11. Appeler explicitement cette processor version dans Factory Writer.
12. Réinjecter périodiquement les nouvelles corrections humaines.
```

Le point clé :

```text
Les corrections humaines ne modifient pas magiquement le modèle en temps réel.
Elles deviennent une ground truth dataset.
Ensuite, on lance un nouveau fine-tuning.
Ce fine-tuning produit une nouvelle processor version.
```

## Sources Google utilisées

1. [Custom Extractor overview](https://docs.cloud.google.com/document-ai/docs/custom-extractor-overview)
2. [Custom Extractor with generative AI](https://docs.cloud.google.com/document-ai/docs/ce-with-genai)
3. [Custom Extractor mechanisms](https://docs.cloud.google.com/document-ai/docs/ce-mechanisms)
4. [Train and evaluate](https://docs.cloud.google.com/document-ai/docs/training-overview)
5. [Create dataset](https://docs.cloud.google.com/document-ai/docs/create-dataset)
6. [Label documents](https://docs.cloud.google.com/document-ai/docs/label-documents)
7. [Evaluate performance](https://docs.cloud.google.com/document-ai/docs/evaluate)
8. [Managing processor versions](https://docs.cloud.google.com/document-ai/docs/manage-processor-versions)
9. [Custom-based extraction](https://docs.cloud.google.com/document-ai/docs/custom-based-extraction)
10. [Handle processing response](https://docs.cloud.google.com/document-ai/docs/handle-response)
