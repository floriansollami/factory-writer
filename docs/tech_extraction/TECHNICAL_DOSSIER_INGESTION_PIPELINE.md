# Pipeline d'ingestion des dossiers techniques usine

Ce document décrit le flow cible pour transformer un dossier technique usine en facts techniques validés, utilisables par LiteLLM pour générer des fiches produit sans hallucination technique.

Le flow cible :

```text
PDF usine
-> OCR
-> Split / classification
-> extraction de facts
-> validation déterministe
-> review si doute
-> facts validés
-> génération produit
```

## 1. Enterprise OCR v2.1 : lire le document et créer la preuve

Objectif : transformer le PDF en **preuve documentaire exploitable**.

Si l’usine envoie un PDF, on commence par le lire avec Enterprise OCR v2.1.

Il renvoie :

| Élément | Exemple | Utilité |
| --- | --- | --- |
| Texte brut | `Dimensions: 190 x 90 x 74 cm` | Source vérifiable. |
| Tokens | `190`, `90`, `74`, `cm` | Contrôle fin. |
| Confidence | `0.97` sur `190` | Savoir si la lecture est fiable. |
| Page | `page 2` | Retrouver la source. |
| Bounding box | Coordonnées sur le PDF | Surligner dans l’UI. |
| Quality score | `0.84` | Détecter un scan flou, coupé ou difficile à lire. |
| Défauts image | `defect_glare`, `defect_text_cutoff` | Expliquer pourquoi une review est nécessaire. |

À ce stade, on ne comprend pas encore le métier. On sait seulement :

```text
voici ce qui est écrit dans le document
voici où c’est écrit
voici avec quel niveau de confiance
```

Exemple de preuve stockée :

```json
{
  "page": 2,
  "text": "Dimensions: 190 x 90 x 74 cm",
  "confidence": 0.97,
  "bbox": {
    "left": 0.32,
    "top": 0.41,
    "width": 0.25,
    "height": 0.03
  }
}
```

## 2. Custom Splitter / Classifier : comprendre le type de document

Objectif : savoir **ce qu’on est en train de traiter**.

Un dossier usine peut contenir plusieurs types de documents :

```text
pages 1-2 : fiche technique produit
page 3 : certificat FSC
pages 4-8 : notice d’assemblage
page 9 : plan technique
```

Le `Custom Splitter` découpe le PDF en sous-documents logiques.

Le `Custom Classifier` dit de quel type il s’agit :

```json
[
  {
    "pages": [1, 2],
    "document_type": "TECHNICAL_SHEET",
    "confidence": 0.96
  },
  {
    "pages": [3],
    "document_type": "ECO_CERTIFICATE",
    "confidence": 0.91
  },
  {
    "pages": [4, 5, 6, 7, 8],
    "document_type": "ASSEMBLY_NOTICE",
    "confidence": 0.88
  },
  {
    "pages": [9],
    "document_type": "BLUEPRINT",
    "confidence": 0.81
  }
]
```

Pourquoi c’est important : on n’extrait pas les mêmes informations dans une fiche technique, un certificat ou une notice.

```text
TECHNICAL_SHEET -> dimensions, poids, matériaux
ECO_CERTIFICATE -> certificat, organisme, validité
ASSEMBLY_NOTICE -> contraintes d’assemblage
BLUEPRINT -> cotes, plan, zones visuelles
```

Si le dossier est simple, on peut sauter cette étape.

## 3. Custom Extractor : transformer le document en facts métier

Objectif : extraire des **facts typés**, pas seulement du texte.

À partir des pages classées, le Custom Extractor cherche les champs définis dans notre schéma.

Exemple de sortie :

```json
[
  {
    "fact_type": "DIMENSION",
    "field": "width_cm",
    "raw_value": "190 cm",
    "normalized_value": 190,
    "unit": "cm",
    "confidence": 0.96,
    "source_text": "Dimensions: 190 x 90 x 74 cm",
    "source_page": 2
  },
  {
    "fact_type": "MATERIAL",
    "field": "wood_type",
    "raw_value": "teck certifié FSC",
    "normalized_value": "teck",
    "confidence": 0.91,
    "source_text": "Structure: teck certifié FSC",
    "source_page": 2
  },
  {
    "fact_type": "CERTIFICATION",
    "field": "eco_certification",
    "raw_value": "FSC",
    "normalized_value": "FSC",
    "confidence": 0.93,
    "source_text": "FSC certified wood",
    "source_page": 3
  }
]
```

À ce stade, ce sont des **fact candidates**.

Ils ne sont pas encore utilisables pour générer la fiche produit, car même Document AI peut se tromper. Il faut valider.

### Mode Custom Extractor recommandé pour Axolotl

Il faut voir le **Custom Extractor** comme une machine Document AI que tu configures pour extraire **tes propres champs métier**.

Exemple Axolotl :

```text
Je veux récupérer :
- largeur
- profondeur
- hauteur
- poids
- matériau
- certification
- contrainte d’assemblage
```

Google te donne trois façons d’apprendre à cette machine où trouver ces champs.

#### L’idée simple

Imagine que tu donnes des dossiers techniques à un stagiaire.

Il y a trois situations possibles :

| Situation | Analogie humaine | Mode Google |
| --- | --- | --- |
| Les documents changent souvent de forme | Tu donnes au stagiaire une définition claire des champs, il comprend grâce au contexte | Foundation model |
| Les documents se ressemblent globalement, mais pas parfaitement | Tu entraînes le stagiaire avec beaucoup d’exemples corrigés | Custom model |
| Les documents sont toujours exactement identiques | Tu lui dis “regarde toujours dans cette case” | Template |

#### Les trois modes

##### 1. Foundation model

C’est le mode moderne, basé sur un modèle fondation Google.

Tu dis à Google :

```text
Voici les champs que je veux extraire.
Voici ce que chaque champ veut dire.
Débrouille-toi pour les trouver dans le document.
```

Exemple :

```text
Champ : dimension_width_cm

Description :
Extraire la largeur du produit exactement comme elle est écrite dans la fiche technique.
Ne pas inventer. Ne pas déduire depuis le nom du produit.
```

Le modèle va chercher dans le document :

```text
Dimensions : 190 x 90 x 74 cm
```

Et proposer :

```json
{
  "dimension_width_cm": "190 cm"
}
```

Pourquoi c’est puissant : il peut fonctionner même si le champ n’est pas toujours au même endroit.

Exemple :

```text
Fournisseur A :
Dimensions : 190 x 90 x 74 cm

Fournisseur B :
Width: 190 cm
Depth: 90 cm
Height: 74 cm

Fournisseur C :
L 190 / P 90 / H 74
```

Le Foundation model peut comprendre que ces trois écritures parlent de la même chose.

C’est le mode recommandé pour Axolotl au départ, parce que les fournisseurs auront probablement des formats différents.

##### 2. Custom model

C’est un modèle entraîné avec tes propres documents, mais moins orienté “GenAI”.

Tu donnes beaucoup d’exemples labellisés :

```text
Dans ce document, ça c’est la largeur.
Dans celui-là, ça c’est le matériau.
Dans celui-là, ça c’est la certification.
```

Google entraîne un modèle spécialisé sur tes documents.

Il est adapté quand :

```text
les documents se ressemblent assez,
mais changent un peu selon fournisseur, année, version ou template.
```

Exemple :

```text
Tous les fournisseurs ont une fiche technique proche :
- bloc produit en haut
- tableau dimensions au milieu
- matériaux en bas
```

Mais :

```text
le fournisseur A met les dimensions à gauche,
le fournisseur B les met à droite,
le fournisseur C ajoute une colonne.
```

Là, le Custom model peut être utile.

Mais il demande plus de données labellisées que le Foundation model.

##### 3. Template

C’est le mode le plus rigide.

Tu l’utilises quand le document est toujours exactement pareil.

Exemple :

```text
Fournisseur A envoie toujours le même formulaire PDF.
La largeur est toujours dans la case 4B.
Le poids est toujours dans la case 5C.
Le matériau est toujours dans la case 6A.
```

Dans ce cas, Document AI apprend surtout :

```text
où regarder sur la page
```

C’est très efficace si le formulaire ne bouge jamais.

Mais si le fournisseur change la mise en page, ajoute une colonne ou déplace une section, ça devient fragile.

Pour Axolotl, ce mode ne doit être utilisé que pour un fournisseur ultra-standardisé.

#### Tableau réexpliqué simplement

| Mode | Ce que tu donnes à Google | Comment Google apprend | Quand c’est bon | Quand c’est mauvais |
| --- | --- | --- | --- | --- |
| Foundation model | Les noms des champs, leurs descriptions, parfois quelques exemples | Il utilise un modèle pré-entraîné capable de comprendre des documents variés | Formats différents, peu d’exemples, besoin de démarrer vite | Si tu veux zéro GenAI ou un comportement très rigide |
| Custom model | Beaucoup de documents labellisés | Il entraîne un modèle spécialisé sur tes documents | Formats assez réguliers, beaucoup d’exemples corrigés | Si tu as peu de données ou trop de formats différents |
| Template | Quelques documents au layout identique | Il apprend où sont les zones fixes | Formulaire toujours identique | Si les documents changent de structure |

#### Exemple concret Axolotl

Supposons qu’Axolotl reçoit trois dossiers.

Dossier fournisseur A :

```text
Dimensions : 190 x 90 x 74 cm
Structure : teck certifié FSC
Poids net : 32 kg
```

Dossier fournisseur B :

```text
Width: 190 cm
Depth: 90 cm
Height: 74 cm
Material: FSC teak
Net weight: 32 kg
```

Dossier fournisseur C :

```text
L/P/H : 1900 / 900 / 740 mm
Essence : Teck
Certification : FSC
Masse nette : 32 kg
```

Ces documents ne sont pas identiques, mais ils disent la même chose.

Le mode le plus adapté est :

```text
Foundation model
```

Parce qu’il peut comprendre :

```text
Width = largeur = L
Depth = profondeur = P
Height = hauteur = H
1900 mm = 190 cm
FSC teak = teck certifié FSC
```

Mais il ne faut pas lui faire confiance aveuglément. Derrière, notre code Python valide.

#### Comment le mettre en place pour Axolotl

Étape 1 : POC+.

On crée un Custom Extractor en mode :

```text
Foundation model
```

Avec un schéma simple :

```text
product_reference
dimension_width
dimension_depth
dimension_height
dimension_unit
net_weight
primary_material
wood_species
metal_grade
eco_certification
assembly_constraint
```

On écrit de bonnes descriptions pour chaque champ.

Exemple :

```text
dimension_width:
Extract the explicit product width from the technical specification.
Do not infer it from the product name.
If multiple dimensions are present, prefer product dimensions over package dimensions.
```

Étape 2 : review des résultats.

Pour chaque document traité, Document AI sort des valeurs avec confidence.

Exemple :

```json
{
  "dimension_width": "190 cm",
  "confidence": 0.96
}
```

Si la confidence est basse ou si la valeur est bizarre :

```text
review humaine
```

Étape 3 : corrections humaines.

Quand un humain corrige :

```text
Document AI a extrait 150 kg
Humain corrige : 15.0 kg
```

On garde cette correction.

Ces corrections deviennent un dataset.

Étape 4 : fine-tuning.

Quand on a assez de corrections et d’exemples, on améliore le modèle :

```text
Foundation model
-> fine-tuned foundation model
```

Donc le système apprend progressivement les formats Axolotl.

#### La vraie recommandation

Pour Axolotl :

```text
Départ : Foundation model
Ensuite : Fine-tuned foundation model
Exception : Template pour un fournisseur avec formulaire fixe
Exception : Custom model si on ne veut pas de GenAI ou si les documents sont très réguliers
```

#### Pourquoi pas Template directement ?

Parce que les fournisseurs ne vont probablement pas tous envoyer le même document.

Avec 10 usines, tu risques d’avoir :

```text
10 structures différentes
10 vocabulaires différents
10 façons d’écrire les dimensions
10 formats de certificats
```

Un Template marche si tout est au même endroit.

Mais dans ton cas, tu veux plutôt une extraction capable de comprendre :

```text
où est la largeur, même si elle change de place
où est la certification, même si elle est écrite différemment
où est le matériau, même si c’est dans un tableau ou un paragraphe
```

Donc :

```text
Foundation model
```

#### Phrase à retenir

Le choix du mode dépend du niveau de variation des documents :

```text
Documents très variables -> Foundation model
Documents assez similaires + beaucoup d’exemples -> Custom model
Documents identiques -> Template
```

Pour Axolotl, comme les dossiers viennent probablement de plusieurs usines avec des formats différents :

```text
Foundation model est le bon choix par défaut.
```

Puis, avec les corrections humaines :

```text
fine-tuned foundation model devient la cible production.
```

## 4. Validation Python : décider sans IA

Objectif : appliquer des règles déterministes, non probabilistes.

Ici, pas de LLM. Pas de “je pense que”. Seulement du code.

Exemples de validations :

| Validation | Exemple | Résultat |
| --- | --- | --- |
| Exact match | `190 cm` doit exister dans le texte OCR | Bloque si le LLM ou l’extractor invente. |
| Parsing numérique | `1S0 cm` n’est pas un nombre valide | Review. |
| Unités | `1.9 m` devient `190 cm` | Normalisation. |
| Bornes physiques | Une chaise de `150 kg` est suspecte | Review. |
| Required fields | Pas de matériau principal | Review. |
| Contradiction interne | Tableau dit `190 cm`, plan dit `180 cm` | Review. |
| Confidence threshold | Confidence `0.52` sur une dimension | Review. |
| Quality score | Page floue ou coupée | Review. |
| Certification proof | `FSC` mentionné sans certificat | Review. |

Exemple validé :

```json
{
  "fact": "width_cm",
  "raw_value": "190 cm",
  "status": "VALIDATED"
}
```

Exemple à revoir :

```json
{
  "fact": "weight_kg",
  "raw_value": "150 kg",
  "status": "NEEDS_REVIEW",
  "reason": "OUT_OF_RANGE_FOR_PRODUCT_FAMILY"
}
```

Autre exemple à revoir :

```json
{
  "fact": "width_cm",
  "raw_value": "1S0 cm",
  "status": "NEEDS_REVIEW",
  "reason": "OCR_AMBIGUOUS_NUMERIC_VALUE"
}
```

C’est cette étape qui fait la différence entre :

```text
IA qui extrait
```

et :

```text
système fiable qui décide ce qui est publiable
```

## 5. Review par exception : l’humain ne voit que les doutes

Objectif : ne pas ralentir 250 produits avec une revue manuelle complète.

L’humain ne relit pas tout. Il traite uniquement les facts douteux.

Exemple UI :

```text
Produit : Table Axolotl 190
Fact douteux : weight_kg
Valeur extraite : 150 kg
Raison : hors bornes pour mobilier_jardin/table_repas
Source : page 2, zone surlignée
Action :
- corriger à 15.0 kg
- confirmer 150 kg
- rejeter le document
```

Grâce aux bounding boxes OCR, l’interface peut afficher :

```text
le PDF
+ la zone exacte surlignée
+ la valeur extraite
+ la raison du doute
```

Donc l’humain ne cherche pas dans 15 pages. Il tranche un point précis.

## 6. Facts validés : seule source autorisée pour LiteLLM

Objectif : empêcher le LLM de puiser directement dans les PDF.

Une fois validés, les facts deviennent la source officielle :

```json
{
  "sku": "AX-TABLE-190",
  "validated_facts": {
    "width_cm": 190,
    "depth_cm": 90,
    "height_cm": 74,
    "wood_type": "teck",
    "certification": "FSC",
    "assembly": "piètement à fixer"
  }
}
```

LiteLLM ne reçoit pas :

```text
le PDF complet
```

Il reçoit :

```text
les facts validés
+ le style pack validé
+ les signaux marketing
```

Exemple de contexte runtime :

```json
{
  "product_facts": {
    "dimensions": "190 x 90 x 74 cm",
    "material": "teck",
    "certification": "FSC",
    "assembly_constraint": "piètement à fixer"
  },
  "style_rules": {
    "voice": "vouvoiement constant, élégance calme",
    "forbidden_claims": ["résiste à vie", "sans entretien pour toujours"]
  },
  "marketing_signals": {
    "top_customer_feedback": ["stable", "élégant", "facile à installer"]
  }
}
```

Le LLM peut rédiger :

```text
Cette table en teck certifié FSC installe une présence extérieure sobre, avec un format 190 x 90 cm pensé pour les repas en plein air.
```

Mais il n’a pas le droit d’inventer :

```text
résiste aux intempéries à vie
```

car ce claim est interdit par le style pack.

Il n’a pas non plus le droit d’inventer :

```text
200 x 100 cm
```

car la validation finale vérifie que toutes les dimensions mentionnées viennent des facts validés.

## 7. Fine-tuning avec les corrections humaines

Un **Fine-tuned foundation model** Document AI signifie :

```text
1. On part d’un modèle fondation Google déjà pré-entraîné.
2. On lui fournit des documents Axolotl corrigés par des humains.
3. Google crée une nouvelle processor version spécialisée.
```

Ce n’est pas du fine-tuning LiteLLM et ce n’est pas du prompt engineering. C’est une **nouvelle version de processor Document AI**.

### Boucle de fine-tuning

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

### Exemple concret

Version initiale :

```text
foundation-technical-sheet-v0
```

Erreur observée :

```text
Fournisseur A écrit :
L/P/H : 1900 / 900 / 740 mm

Le modèle extrait :
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

Après plusieurs corrections similaires, on fine-tune :

```text
fine-tuned-technical-sheet-v1
```

La nouvelle version apprend mieux les notations fournisseur comme `L/P/H`, ce qui réduit le taux de review.

### Où vont les corrections humaines ?

Les corrections humaines ne modifient pas le modèle en temps réel.

Elles deviennent une **ground truth dataset** :

```text
review humaine dans Factory Writer
-> stockage corrections en DB
-> job offline crée des Document JSON avec entities corrigées
-> import pre-labeled documents dans Document AI dataset
-> fine-tune nouvelle version
```

Pour le POC, la correction peut rester dans la console Google Document AI.

Pour la prod, la correction doit venir de l’admin Factory Writer pour garder un historique métier complet.

### Évaluation de la version fine-tuned

Google évalue une processor version sur un test set avec :

```text
precision
recall
F1
```

Lecture :

| Métrique | Sens |
| --- | --- |
| Precision | Quand le modèle extrait une valeur, est-ce correct ? |
| Recall | Le modèle retrouve-t-il toutes les valeurs attendues ? |
| F1 | Équilibre entre precision et recall. |

Pour Axolotl, les seuils doivent dépendre de la criticité :

| Fact | Seuil minimal recommandé |
| --- | --- |
| Dimensions | F1 >= 0.95 |
| Poids | F1 >= 0.95 |
| Matériaux | F1 >= 0.90 |
| Certification | F1 >= 0.95 |
| Assemblage | F1 >= 0.85 |

Si un champ n’atteint pas le seuil, il ne doit pas être publié automatiquement. Il doit rester soumis à review.

### Version explicite dans Factory Writer

En production, Factory Writer ne doit pas dépendre aveuglément du processor `default`.

L’application doit appeler explicitement :

```text
processorVersions/fine-tuned-axolotl-technical-sheet-v1
```

Et stocker pour chaque extraction :

```text
processor_id
processor_version
base_processor_version
document_type
schema_version
extraction_run_id
confidence_by_field
validation_status
review_reason
human_correction_id
```

Cette trace permet de répondre à une question d’audit :

```text
Quelle version exacte du processor a produit les facts utilisés dans cette fiche produit ?
```

## Résumé du rôle de chaque étape

| Étape | Question à laquelle elle répond |
| --- | --- |
| Enterprise OCR | Qu’est-ce qui est réellement écrit dans le document, où, et avec quelle confiance ? |
| Splitter / Classifier | Quel type de document ou de page suis-je en train de traiter ? |
| Custom Extractor | Quels facts métier peut-on extraire de ce document ? |
| Validation Python | Ces facts sont-ils cohérents, prouvés et publiables ? |
| Review par exception | Quels facts nécessitent une décision humaine ? |
| Facts validés | Quelles données le LLM a-t-il le droit d’utiliser pour rédiger ? |
| Fine-tuning | Comment réduire progressivement les erreurs grâce aux corrections humaines ? |

## Exemple complet

Document usine :

```text
Table repas extérieur AX-T190
Dimensions : 190 x 90 x 74 cm
Structure : teck certifié FSC
Poids net : 32 kg
Assemblage : piètement à fixer
```

Pipeline :

```text
OCR lit le texte et localise chaque ligne.
Classifier dit : TECHNICAL_SHEET.
Custom Extractor sort width=190, depth=90, height=74, material=teck, certification=FSC.
Python vérifie exact match, unités, bornes physiques et champs requis.
Tout est cohérent.
Les facts passent en VALIDATED.
LiteLLM génère la fiche produit à partir de ces facts validés.
```

Cas problématique :

```text
OCR lit : Poids net : 150 kg
```

Validation :

```text
150 kg pour une table de jardin = hors borne réaliste
=> NEEDS_REVIEW
=> pas de génération automatique tant que ce fact critique n’est pas corrigé ou confirmé
```

## Conclusion

Le design cible repose sur une règle simple :

```text
automatisation massive quand les preuves sont propres,
blocage ciblé quand un fait critique est douteux.
```

Le LLM ne rédige jamais depuis un document brut. Il rédige depuis des facts validés.
