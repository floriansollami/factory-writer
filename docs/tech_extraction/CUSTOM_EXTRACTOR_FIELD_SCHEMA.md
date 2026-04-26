# Schéma des 3 Custom Extractors Document AI

Objectif : définir les labels à créer dans les trois Custom Extractors du POC Axolotl.

Ces schémas ne doivent pas être spécifiques à la table Rivage 220. Ils doivent rester transverses pour les futurs produits Axolotl : tables, chaises, bancs, parasols, mobilier modulaire et, plus tard, outils de jardin.

Les prompts sont volontairement courts pour rester compatibles avec la limite Document AI de 512 caractères par description de champ. Les labels `core` alimentent déjà la validation POC actuelle. Les labels `extended` sont utiles pour améliorer la future fiche produit, mais devront être mappés côté backend avant promotion automatique.

## Stratégie de découpage prod-ready

La bonne granularité n’est pas “un extractor par produit”. Ce serait trop coûteux à maintenir, difficile à évaluer et trop pauvre en exemples par produit.

La bonne approche est :

1. `Custom Classifier` : identifier le type documentaire.
2. Routage backend déterministe : choisir l’extractor selon `document_type`, puis éventuellement `famille_code` ou `sous_famille_code`.
3. `Custom Extractor` transverse : extraire les facts communs à une famille documentaire.
4. Extension progressive : créer un extractor spécialisé seulement si une famille produit introduit des champs critiques très différents.

Découpage recommandé :

| Niveau | Quand l’utiliser | Exemple Axolotl |
| --- | --- | --- |
| Extractor par type documentaire | Par défaut POC et première prod | `technical_sheet`, `material_specification`, `assembly_notice` |
| Extractor par famille produit + type documentaire | Si les champs critiques divergent fortement | `garden_tools_technical_sheet` |
| Extractor par fournisseur/template | Si gros volume avec format stable | `supplier_x_template_extractor` |
| Extractor par produit | À éviter presque toujours | Anti-pattern sauf cas très stratégique avec énorme volume |

Règles de décision :

- Garder le même extractor si les nouveaux champs sont optionnels et ne dégradent pas la qualité.
- Créer un nouvel extractor si plus de 20 à 30 % des champs critiques sont propres à une famille produit.
- Créer un nouvel extractor si le même label devient ambigu selon la famille, par exemple `capacity` pour une table, un parasol ou un outil.
- Créer un nouvel extractor si les métriques F1/confidence baissent sur une famille produit.
- Créer un nouvel extractor si les règles de validation déterministe changent fortement.
- Éviter les schémas trop larges : même si Document AI supporte beaucoup de labels, un schéma illisible devient difficile à corriger, versionner et expliquer.

Pour le POC, les trois extractors ci-dessous sont donc des extractors **transverses par type documentaire**, pas des extractors de table.

## Architecture cible Axolotl

L'architecture cible doit séparer deux sujets :

- le **modèle canonique de facts techniques**, stable côté backend ;
- les **extractors Document AI**, qui peuvent évoluer, se spécialiser ou être remplacés.

Le modèle canonique est la source durable pour la génération produit : `product_name`, `sku`, dimensions, poids, matériaux, finitions, certifications, contraintes d'assemblage, limites de claims, preuves, confidence, source, page et bounding box. Les processors Document AI ne doivent jamais devenir le modèle métier final. Ils alimentent des facts candidats qui sont ensuite normalisés et validés.

Flow cible :

```text
Upload PDFs usine
-> stockage GCS
-> Custom Classifier Document AI
-> document_type détecté
-> routage backend
-> Custom Extractor adapté
-> facts candidats
-> validation déterministe
-> revue humaine si doute
-> facts validés
-> contexte produit
-> génération fiche produit
```

Routage cible :

```text
document_type + famille_code + sous_famille_code optionnel
-> processor_id
-> processor_version
-> schema_version
```

Exemple :

| document_type | famille_code | sous_famille_code | extractor cible | schema_version |
| --- | --- | --- | --- | --- |
| `TECHNICAL_SHEET` | `mobilier_jardin` | `*` | `fw-technical-sheet-extractor` | `technical_sheet_v1` |
| `TECHNICAL_SHEET` | `outils_jardin` | `*` | `fw-garden-tools-technical-sheet-extractor` | `garden_tools_sheet_v1` |
| `MATERIAL_SPECIFICATION` | `*` | `*` | `fw-material-spec-extractor` | `material_spec_v1` |
| `ASSEMBLY_NOTICE` | `*` | `*` | `fw-assembly-notice-extractor` | `assembly_notice_v1` |

Lecture fonctionnelle :

- Le classifier répond à la question : **quel type de document est-ce ?**
- La taxonomie produit aide à répondre : **quel extractor exact faut-il utiliser ?**
- L'extractor répond : **quels facts techniques sont écrits dans ce document ?**
- Le backend normalise et valide : **quels facts sont fiables et utilisables pour générer ?**

Au départ, Axolotl peut garder trois extractors transverses :

```text
TECHNICAL_SHEET
-> dimensions, poids, matériaux, finitions, capacité, specs produit

MATERIAL_SPECIFICATION
-> matériaux, origine, FSC, SVLK, FLEGT, REACH, composants couverts/exclus

ASSEMBLY_NOTICE
-> outils, pièces, étapes, contraintes, restrictions, contrôles finaux
```

Ensuite, on spécialise seulement si les métriques ou le métier l'exigent. Par exemple, si les outils de jardin ajoutent des champs critiques comme `blade_length_cm`, `cutting_diameter_mm`, `handle_material`, `battery_voltage_v`, `motor_power_w` ou `safety_standard`, il devient pertinent de créer `fw-garden-tools-technical-sheet-extractor`.

Principe de gouvernance :

- pas un extractor par produit ;
- pas un extractor géant pour toute l'entreprise ;
- un portefeuille d'extractors par type documentaire ;
- spécialisation par famille produit quand les facts critiques divergent ;
- mapping obligatoire vers un modèle canonique backend ;
- génération LLM uniquement depuis des facts validés, jamais directement depuis les PDFs.

## Recommandation de routage pour Axolotl

Pour Axolotl, le routage conseillé est progressif.

Au départ, y compris en première prod, il faut utiliser **un extractor par type documentaire**, pas par famille ni par sous-famille :

```text
TECHNICAL_SHEET -> fw-technical-sheet-extractor
MATERIAL_SPECIFICATION -> fw-material-spec-extractor
ASSEMBLY_NOTICE -> fw-assembly-notice-extractor
```

Cela signifie que le même `fw-technical-sheet-extractor` doit couvrir les fiches techniques de tables, chaises, bancs, parasols ou mobilier modulaire, tant que les champs restent suffisamment communs.

Il ne faut pas partir directement sur un extractor par sous-famille. C'est trop fin trop tôt : cela multiplierait les processors, réduirait le nombre d'exemples par extractor, compliquerait les versions et augmenterait la maintenance.

Implémentation POC : le routage reste **config-driven** dans le backend. Il est résolu par un resolver applicatif à partir du `document_type` et des variables GCP, sans table DB. Une table de routage devient utile plus tard seulement si Axolotl spécialise par famille, sous-famille, fournisseur ou version active.

Ordre de spécialisation recommandé :

| Niveau | Décision | Exemple |
| --- | --- | --- |
| 1 | Type documentaire seul, par défaut | `TECHNICAL_SHEET + * + *` |
| 2 | Type documentaire + famille produit, si divergence métier forte | `TECHNICAL_SHEET + outils_jardin + *` |
| 3 | Type documentaire + sous-famille, seulement si très spécifique et volumique | `TECHNICAL_SHEET + outils_jardin + tondeuse_batterie` |
| À éviter | Extractor par produit | `TECHNICAL_SHEET + Table Rivage 220` |

Table de routage de départ :

| document_type | famille_code | sous_famille_code | extractor cible |
| --- | --- | --- | --- |
| `TECHNICAL_SHEET` | `*` | `*` | `fw-technical-sheet-extractor` |
| `MATERIAL_SPECIFICATION` | `*` | `*` | `fw-material-spec-extractor` |
| `ASSEMBLY_NOTICE` | `*` | `*` | `fw-assembly-notice-extractor` |

Évolution typique si Axolotl ajoute des outils de jardin :

| document_type | famille_code | sous_famille_code | extractor cible |
| --- | --- | --- | --- |
| `TECHNICAL_SHEET` | `outils_jardin` | `*` | `fw-garden-tools-technical-sheet-extractor` |
| `TECHNICAL_SHEET` | `*` | `*` | `fw-technical-sheet-extractor` |

La règle de priorité doit prendre la ligne la plus spécifique :

1. `document_type + famille_code + sous_famille_code`
2. `document_type + famille_code + *`
3. `document_type + * + *`

Il faut donc créer un extractor spécialisé uniquement avec des preuves terrain : confidence faible, erreurs répétées, review humaine fréquente, champs critiques absents ou règles de validation très différentes.

## Options Document AI pour les labels

Dans l'UI Document AI, chaque label demande plusieurs choix structurants :

| Paramètre | Valeurs possibles | Explication |
| --- | --- | --- |
| `Name` | Texte libre, unique par extractor | Nom technique du label, par exemple `sku`, `material_primary`, `assembly_steps`. C'est le champ qui revient dans la réponse JSON Document AI. |
| `This is a parent label` | `Oui`, `Non` | `Oui` sert à créer un label parent qui regroupe des sous-labels. Utile pour des structures complexes. Pour notre POC, on utilise surtout des labels simples, donc `Non`. |
| `Method` | `Extract`, `Derive` | `Extract` extrait une valeur présente dans le document. `Derive` produit une valeur calculée ou déduite à partir d'autres informations. Pour le POC zero-hallucination, on privilégie `Extract`. |
| `Data type` | `Plain text`, `Number`, `Currency`, `Money`, `Datetime`, `Address`, `Checkbox` | Type attendu pour la valeur extraite. `Plain text` est le plus robuste pour garder unités, codes, certifications et formulations source. |
| `Occurrence` | `Optional once`, `Optional multiple`, `Required once`, `Required multiple` | Définit si le champ est obligatoire et s'il peut apparaître plusieurs fois. Pour le POC, `Optional multiple` est le plus robuste avec des PDFs hétérogènes. |
| `Description - Prompt for label` | Texte libre, max 512 caractères | Prompt qui explique à Document AI quoi extraire et quoi éviter. C'est le levier principal de qualité pour le zero-shot. |

Pour le POC Axolotl, tous les labels ci-dessous sont configurés ainsi :

| Option | Valeur retenue | Raison |
| --- | --- | --- |
| `Method` | `Extract` | On extrait uniquement ce qui est écrit dans les PDFs. `Derive` introduirait une logique d'inférence ou de calcul, moins adaptée à notre objectif zero-hallucination. |
| `Data type` | `Plain text` | On préserve les unités, tolérances, codes, noms de certifications et formulations source : `220 cm`, `11 N·m`, `FSC Mix Credit`, `2 adultes`, `30 à 40 min`. Le backend normalise ensuite. |
| `Occurrence` | `Optional multiple` | Les documents industriels sont hétérogènes : un champ peut être absent, présent une fois ou répété. Cela évite de forcer un champ manquant et permet plusieurs matériaux, certifications, pièces, étapes ou contraintes. |

Ce choix est volontairement conservateur. Quand on aura assez de résultats terrain, on pourra durcir certains labels :

- `Optional once` pour `sku`, `product_name` ou `supplier_name` si les documents sont stables.
- `Number` pour les dimensions, poids, temps, couple ou nombre de personnes si l'extraction texte est fiable.
- `Datetime` pour `certificate_valid_until` si les formats de dates sont suffisamment homogènes.

## Garantir les facts requis avant génération

`Required once` ou `Required multiple` dans Document AI ne suffit pas à garantir qu'une fiche produit peut être générée. Ces options guident l'extractor, mais la garantie métier doit être portée par le backend.

Google recommande de définir soigneusement les champs, leurs noms et leurs descriptions, car ils impactent fortement la qualité d'extraction, surtout avec les modèles foundation et zero-shot. Google recommande aussi d'évaluer les performances avec F1, precision et recall, puis de vérifier les labels prédits et les champs manquants. Le HITL natif Document AI est déprécié : la revue humaine doit donc être implémentée dans l'admin Axolotl.

La séparation cible est la suivante :

| Niveau | Rôle | Exemple |
| --- | --- | --- |
| Schema Document AI | Dire à l'extractor quoi chercher | `material_primary`, `dimension_width`, `assembly_steps` |
| Modèle canonique backend | Normaliser les facts extraits | `field_name`, `normalized_value`, `unit`, `confidence`, `source`, `page`, `bbox_json` |
| Contrat de génération | Dire quels facts sont obligatoires pour générer | `sku`, dimensions, matière principale, finition, limites de claims |

Pipeline de contrôle :

```text
PDF
-> classifier
-> extractor
-> facts candidats
-> normalisation backend
-> validation du contrat de génération
-> review humaine si manque ou doute
-> génération seulement si contrat satisfait
```

Le contrat de génération doit dépendre du contexte produit :

```text
famille_code + sous_famille_code + type de fiche + canal
```

Exemple pour une table de jardin :

| Fact canonique | Niveau | Pourquoi |
| --- | --- | --- |
| `sku` | requis | Identifier le produit et éviter de mélanger les PDFs |
| `product_name` | requis ou déjà fourni par DB | Produire un titre cohérent |
| `dimension_width` | requis | Fiche incomplète sans dimensions |
| `dimension_depth` | requis | Fiche incomplète sans dimensions |
| `dimension_height` | requis | Fiche incomplète sans dimensions |
| `material_primary` | requis | Argument produit central |
| `finish_primary` | requis | Description produit et conseils d'entretien |
| `usage_capacity` | conditionnel | Requis pour table ou assise, pas forcément pour tous les produits |
| `eco_certifications` | optionnel mais contrôlé | Ne s'écrit que si une preuve valide est présente |
| `technical_claim_limits` | requis si claims sensibles | Empêche les promesses interdites ou non prouvées |
| `assembly_constraints` | conditionnel | Requis si la fiche parle de montage ou de contraintes d'assemblage |

Le backend doit produire une matrice de readiness avant génération :

```json
{
  "generation_contract": "mobilier_jardin_table_v1",
  "required_missing": ["dimension_height"],
  "low_confidence": ["material_primary"],
  "conflicts": ["sku"],
  "ready_for_generation": false
}
```

Si `ready_for_generation=false`, la génération est bloquée et des `technical_review_case` sont créés. L'utilisateur peut alors corriger une valeur, ajouter un fact manquant depuis le PDF, marquer un champ comme non applicable, demander un nouveau PDF ou remplacer le lot.

Recommandation POC : garder Document AI en `Optional multiple` pour extraire large, puis appliquer le vrai contrat de génération côté backend. La règle métier doit être :

```text
Pas de facts requis validés
= pas de génération
= contrôle qualité humain
```

## Labels de mesure sans unité

Les labels Document AI ne doivent pas encoder l’unité quand la source peut écrire `mm`, `cm`, `m`, `kg`, `g`, `min`, `h` ou `N·m`. Le label décrit le concept métier, pas l’unité canonique du backend.

Exemples appliqués dans les extractors GCP :

| Ancien label | Nouveau label | Règle |
| --- | --- | --- |
| `dimension_width_cm` | `dimension_width` | Extraire la valeur source, conserver l’unité si visible. |
| `dimension_depth_cm` | `dimension_depth` | Extraire la valeur source, conserver l’unité si visible. |
| `dimension_height_cm` | `dimension_height` | Extraire la valeur source, conserver l’unité si visible. |
| `weight_kg` | `weight` | Extraire le poids source, ne pas convertir côté GCP. |
| `assembly_time_minutes` | `assembly_time` | Extraire la durée source, ne pas additionner ni convertir côté GCP. |
| `max_torque_nm` | `max_torque` | Extraire le couple source, conserver `N·m` si écrit. |

Le backend normalise ensuite de façon déterministe. Pour les dimensions groupées, `dimension_set_raw` sert de preuve de contexte, par exemple `Dimensions L/P/H (mm) : 2 200 / 950 / 740`. Si aucune unité explicite ou contextuelle n’est disponible, le fact ne doit pas être promu automatiquement.

## 1. `fw-technical-sheet-extractor`

Type de document routé : `TECHNICAL_SHEET`.

| Priorité | Label | Method | Data type | Occurrence | Prompt Document AI |
| --- | --- | --- | --- | --- | --- |
| core | `product_name` | Extract | Plain text | Optional multiple | Extraire le nom ou la désignation produit exacte couverte par la fiche technique. Prendre le nom le plus spécifique. Ne pas extraire une famille générique ni un autre produit cité. |
| core | `sku` | Extract | Plain text | Optional multiple | Extraire la référence produit, SKU ou code article exact. Conserver lettres, chiffres et tirets. Ne pas confondre avec lot, révision ou tampon documentaire. |
| core | `dimension_set_raw` | Extract | Plain text | Optional multiple | Extraire la ligne ou cellule complète qui donne les dimensions du produit fini avec ordre et unité : L/P/H, L x P x H, largeur/profondeur/hauteur, mm, cm ou m. Ne pas convertir. Ne pas extraire dimensions colis ou composant. |
| core | `dimension_width` | Extract | Plain text | Optional multiple | Extraire la largeur ou longueur principale du produit fini exactement comme écrite. Si les dimensions sont groupées (L/P/H, L x P x H), prendre la première valeur selon l’ordre annoncé. Conserver l’unité source si visible. Ne pas convertir. Ne pas extraire une dimension de colis ou composant. |
| core | `dimension_depth` | Extract | Plain text | Optional multiple | Extraire la profondeur du produit fini exactement comme écrite. Si les dimensions sont groupées (L/P/H, L x P x H), prendre la deuxième valeur selon l’ordre annoncé. Conserver l’unité source si visible. Ne pas convertir. Ne pas extraire une dimension de colis ou composant. |
| core | `dimension_height` | Extract | Plain text | Optional multiple | Extraire la hauteur du produit fini exactement comme écrite. Si les dimensions sont groupées (L/P/H, L x P x H), prendre la troisième valeur selon l’ordre annoncé. Conserver l’unité source si visible. Ne pas convertir. Ne pas extraire la hauteur de colis. |
| core | `material_primary` | Extract | Plain text | Optional multiple | Extraire la matière principale du produit ou de la partie dominante. Inclure essence, grade, alliage ou nom scientifique si présents. Ne rien inventer. |
| core | `material_secondary` | Extract | Plain text | Optional multiple | Extraire les matières secondaires structurantes : piètement, cadre, visserie, manche, lame, textile, batterie. Inclure grade ou finition si écrit. |
| core | `finish_primary` | Extract | Plain text | Optional multiple | Extraire la finition principale : huile, peinture, poudre, couleur, RAL, traitement de surface ou aspect. Ne pas transformer en promesse de durabilité. |
| core | `weight` | Extract | Plain text | Optional multiple | Extraire le poids du produit hors emballage exactement comme écrit. Conserver l’unité source, la tolérance ou la plage si présentes. Ne pas convertir. Ne pas extraire le poids du colis, de la palette ou de l’emballage. |
| extended | `usage_capacity` | Extract | Plain text | Optional multiple | Extraire la capacité d’usage explicitement indiquée : nombre de places, charge, volume, surface couverte ou cadence recommandée. Ne pas déduire depuis les dimensions. |
| extended | `feature_or_accessory` | Extract | Plain text | Optional multiple | Extraire les fonctionnalités ou accessoires techniques écrits : passage parasol, patins, poignée, lame, housse, verrouillage, batterie, réglage. |
| extended | `component_dimensions` | Extract | Plain text | Optional multiple | Extraire les dimensions d’un composant important : plateau, piètement, cadre, assise, manche, lame, toile, roue ou bac. Conserver unités et tolérances. Ne pas extraire les dimensions globales du produit fini ni du colis. |
| core | `quality_control_points` | Extract | Plain text | Optional multiple | Extraire les critères de contrôle qualité explicitement listés : stabilité, jeu, tolérance, nettoyage, conformité atelier. Garder les formulations techniques. |
| core | `technical_claim_limits` | Extract | Plain text | Optional multiple | Extraire les notes qui limitent l’usage marketing des données techniques : absence de garantie permanente, entretien limité, usage non absolu. Ne pas créer de restriction absente. |

## 2. `fw-material-spec-extractor`

Type de document routé : `MATERIAL_SPECIFICATION`.

| Priorité | Label | Method | Data type | Occurrence | Prompt Document AI |
| --- | --- | --- | --- | --- | --- |
| core | `product_name` | Extract | Plain text | Optional multiple | Extraire le produit couvert par l’attestation matière ou conformité. Ne pas extraire un produit mentionné comme exemple, exclusion ou référence secondaire. |
| core | `sku` | Extract | Plain text | Optional multiple | Extraire le SKU, référence article ou code produit concerné par l’attestation. Conserver le format exact. Ne pas confondre avec lot ou certificat. |
| extended | `supplier_name` | Extract | Plain text | Optional multiple | Extraire le fournisseur, fabricant, site ou organisme émetteur de la déclaration. Ne pas extraire la marque commerciale si elle n’est pas l’émetteur. |
| extended | `assembly_site` | Extract | Plain text | Optional multiple | Extraire le site d’assemblage, fabrication ou pays d’origine s’il est explicitement écrit. Ne pas déduire depuis une langue ou un code. |
| core | `material_primary` | Extract | Plain text | Optional multiple | Extraire la matière, essence, alliage ou composition principale déclarée. Inclure nom scientifique, grade ou origine si présents. |
| core | `material_origin` | Extract | Plain text | Optional multiple | Extraire l’origine déclarée de la matière : pays, plantation, provenance, lot ou légalité export. Ne pas inventer depuis le fournisseur. |
| core | `eco_certifications` | Extract | Plain text | Optional multiple | Extraire les certifications ou preuves environnementales explicitement valides : FSC, PEFC, SVLK, FLEGT, REACH, RoHS, recyclé, origine contrôlée. |
| core | `certification_claim_type` | Extract | Plain text | Optional multiple | Extraire le type exact de revendication certifiée, par exemple FSC Mix Credit. Ne jamais transformer en claim plus fort comme 100 % FSC. |
| core | `license_or_certificate_code` | Extract | Plain text | Optional multiple | Extraire les codes de licence, certificat, audit ou conformité. Conserver lettres, tirets et chiffres. Ne pas fusionner plusieurs codes. |
| extended | `chain_of_custody_code` | Extract | Plain text | Optional multiple | Extraire le code de chaîne de contrôle, CoC ou audit associé. Conserver le format exact et ne pas le confondre avec une licence de marque. |
| extended | `legality_export_reference` | Extract | Plain text | Optional multiple | Extraire les références de légalité export ou traçabilité, par exemple SVLK, FLEGT ou batch export. Conserver le code complet. |
| core | `covered_component` | Extract | Plain text | Optional multiple | Extraire les composants explicitement couverts par la preuve ou certification. Ne pas inclure les composants seulement listés ou exclus. |
| core | `excluded_component` | Extract | Plain text | Optional multiple | Extraire les composants explicitement exclus du périmètre de certification ou d’attestation. Garder la formulation précise. |
| core | `unsupported_claims` | Extract | Plain text | Optional multiple | Extraire les mentions que le document interdit ou ne permet pas d’affirmer : 100 % FSC, zéro entretien, garantie permanente, matériau certifié à tort. |
| extended | `certificate_valid_until` | Extract | Plain text | Optional multiple | Extraire la date de validité, expiration ou prochaine vérification. Ne pas extraire la date d’émission si aucune validité n’est indiquée. |

## 3. `fw-assembly-notice-extractor`

Type de document routé : `ASSEMBLY_NOTICE`.

| Priorité | Label | Method | Data type | Occurrence | Prompt Document AI |
| --- | --- | --- | --- | --- | --- |
| core | `product_name` | Extract | Plain text | Optional multiple | Extraire le nom, article ou référence du produit concerné par la notice. Ne pas extraire le nom d’une pièce ou d’un composant isolé. |
| extended | `assembly_product_ref` | Extract | Plain text | Optional multiple | Extraire la référence de colis, article, notice ou version de montage. Conserver le format exact. Ne pas confondre avec le SKU commercial. |
| core | `assembly_people_required` | Extract | Plain text | Optional multiple | Extraire le nombre de personnes ou opérateurs nécessaires au montage. Conserver la formulation source, par exemple 2 adultes. |
| core | `assembly_time` | Extract | Plain text | Optional multiple | Extraire le temps de montage indiqué ou constaté exactement comme écrit. Conserver l’unité source et la plage si présentes. Ne pas convertir. Ne pas additionner des étapes si aucun total n’est écrit. |
| core | `required_tool` | Extract | Plain text | Optional multiple | Extraire les outils nécessaires ou fournis : clé Allen, tournevis, maillet, gabarit, niveau. Ne pas extraire la visserie comme outil. |
| core | `max_torque` | Extract | Plain text | Optional multiple | Extraire le couple de serrage maximum ou recommandé exactement comme écrit. Conserver l’unité source, par exemple N·m. Ne pas convertir. Ne pas extraire un diamètre, une taille ou une référence de vis. |
| extended | `parts_list` | Extract | Plain text | Optional multiple | Extraire la liste des pièces principales à assembler : structure, cadre, pieds, assise, manche, lame, toile, roues, bac ou modules. Inclure quantités si écrites. Ne pas inclure les étapes. |
| extended | `hardware_list` | Extract | Plain text | Optional multiple | Extraire la quincaillerie : vis, rondelles, inserts, patins, sachets. Inclure dimensions et quantités si disponibles. Ne pas extraire les outils. |
| core | `assembly_steps` | Extract | Plain text | Optional multiple | Extraire la séquence opératoire dans l’ordre : préparer, présenter, équerrer, serrer, régler, contrôler. Garder verbes et contraintes clés. |
| core | `assembly_constraints` | Extract | Plain text | Optional multiple | Extraire les contraintes de montage qui conditionnent la qualité ou la sécurité : support, ordre, jeu, serrage progressif, interdictions, tolérances. |
| core | `prohibited_actions` | Extract | Plain text | Optional multiple | Extraire les actions explicitement interdites : visseuse à choc, reperçage, collage, levage incorrect, usage abrasif. Ne pas reformuler en bénéfice. |
| extended | `clearance_or_tolerance` | Extract | Plain text | Optional multiple | Extraire les jeux, tolérances ou écarts acceptés : diagonales, jeu bois/métal, écart de montage, distance minimale. Conserver unités et tolérances. Ne pas convertir. |
| core | `final_quality_check` | Extract | Plain text | Optional multiple | Extraire les contrôles finaux demandés après montage : stabilité, hauteur finie, patins, serrage, alignement, surface plane. |
| extended | `use_or_safety_warning` | Extract | Plain text | Optional multiple | Extraire les avertissements d’usage ou sécurité après montage. Ne pas transformer en argument marketing ni inventer de risque absent. |
