# Masterclass 2026 : Comprendre "Brand Voice" vs "Brand Tone"

Face à la multiplication des contenus générés par l'IA dans l'e-commerce, l'industrie du retail a dû rationaliser sa manière de définir l'identité d'une marque.
Voici ce qu'il faut absolument retenir : **La Voix est une identité, le Ton est une attitude.**

---

## 1. Les concepts pour les débutants absolus

Imaginez que The Outdoor Axolotl est une vraie personne : Sophie.

### A. La Brand Voice (La Voix de la Marque)

C'est la personnalité viscérale de Sophie. Qu'elle soit heureuse, en colère, au travail ou en vacances, **Sophie reste toujours la même personne au fond**.

- _Règles de Voix d'Axolotl_ : Experte, Élégante, Naturelle, Polie.
- _Dans la vraie vie_ : La Voix ne change **jamais**. Elle ancre la marque dans l'esprit du client.

### B. Le Brand Tone (Le Ton de la Marque)

C'est la manière dont Sophie **adapte son discours selon la situation**.

- Sophie ne va pas parler à son banquier de la même manière qu'elle parle à son enfant. Sa _Voix_ reste polie et élégante, mais son _Ton_ s'adapte.
- _Dans le Retail d'Axolotl_ : On ne vend pas un **Canapé de décoration à 8000€** (Ton inspirant et premium) avec la même attitude qu'on vend un **Sécateur technique** (Ton éducationnel, précis et sécuritaire).

**En résumé : La Voix (Voice) est constante. Le Ton (Tone) est le curseur fluide qui s'adapte à la catégorie de produit.**

---

## 2. Le Framework "Tone Spectrum" de 2026

Dans la Silicon Valley et le retail haut de gamme, on utilise désormais des "Sliders" (curseurs) pour définir les dimensions d'un Ton.

| Catégorie Produit        | Curseur Formalité    | Curseur Humour       | Curseur Émotion      | Résultat "Target Tone"    |
| ------------------------ | -------------------- | -------------------- | -------------------- | ------------------------- |
| **Mobilier Ultra-Luxe**  | Très Formel          | Sérieux (0 Humour)   | Très Inspirant       | _Premium & Architectural_ |
| **Outillage de Jardin**  | Décontracté mais Pro | Pragmatique direct   | Rassurant (Sécurité) | _Expert & Pédagogue_      |
| **SAV / Service Client** | Strictement Formel   | Sérieux & Empathique | Calme & Présent      | _Service Empathique_      |

---

## 3. Application à l'Architecture Factory Writer (ERD)

Pour modéliser cela dans notre base de données PostgreSQL de façon brillante sans tout réinventer, nous utilisons une astuce d'architecture élégante : **Le `tone_id` nullable**.

Dans notre table `STYLE_RULES` (les règles qui créent le Logic Firewall) :

- Si une règle a une colonne `tone_id` vide (**NULL**), alors c'est une règle de **VOICE**. Elle s'applique **obligatoirement à absolument tous les produits du site**.
- Si une règle a un `tone_id` assigné (ex: UUID du ton "Premium & Architectural"), alors c'est une règle de **TONE**. Elle s'ajuste dynamiquement.

---

## 4. Visualisation des Tables (Comme dans la vraie BDD)

Pour comprendre l'impact colossal de cette stratégie, voici à quoi ressemblent vos deux tables SQL en production.

### Table : `TARGET_TONE`

_(C'est le bouton que l'humain sélectionne dans le menu déroulant avant de générer la fiche)._

| id (uuid)     | name                    | description_interne                                          |
| ------------- | ----------------------- | ------------------------------------------------------------ |
| `tone_lux_1`  | Premium & Architectural | Pour le mobilier de gamme supérieure, faire rêver.           |
| `tone_tool_1` | Expert & Pédagogue      | Pour l'outillage et le soin des plantes. Focus biomécanique. |

<br>

### Table : `STYLE_RULES`

_(C'est le "Constraint Engine" qui va s'abattre sur le LLM)._

| id (uuid) | tone_id (FK)  | rule_type         | value                                  | Interprétation Humaine                                                         |
| --------- | ------------- | ----------------- | -------------------------------------- | ------------------------------------------------------------------------------ |
| `rule_01` | **NULL**      | syntax_rule       | "Utiliser le vouvoiement (Vous)"       | **VOICE** : On vouvoie toujours le client, outil ou canapé.                    |
| `rule_02` | **NULL**      | forbidden_lexicon | "Pas cher, Promotion, Low-cost"        | **VOICE** : La marque Axolotl ne fait jamais dans le bas de gamme.             |
| `rule_03` | `tone_lux_1`  | allowed_lexicon   | "Intemporel, Asymétrie, Galerie d'art" | **TONE** : Ce lexique poétique n'est allumé que pour les meubles Luxe.         |
| `rule_04` | `tone_lux_1`  | phrasing_rule     | "Phrases longues et rythmées"          | **TONE** : On prend le temps d'installer une atmosphère.                       |
| `rule_05` | `tone_tool_1` | allowed_lexicon   | "Biomécanique, Sécurité, Poigne"       | **TONE** : On allume le lexique robuste uniquement pour les sécateurs/outils.  |
| `rule_06` | `tone_tool_1` | phrasing_rule     | "Phrases courtes et verbes d'action"   | **TONE** : Pour l'outillage, on veut de l'efficacité, pas de la poésie lourde. |

### Que se passe-t-il pendant la Vraie Génération AI ?

Si Lucas décide de générer une fiche produit pour un **"Sécateur Pro"** en sélectionnant le ton `Expert & Pédagogue` (`tone_tool_1`) :
Notre Backend (via FastAPI) va dire à la Base de Données :

> _"Donne-moi toutes les règles où `tone_id` est NULL **PLUS** les règles où `tone_id` = 'tone_tool_1'."_

**Le LLM recevra en contexte le pare-feu suivant :**
_"Tu écris au vouvoiement (Rule 1), tu ne parles jamais de produit pas cher (Rule 2), mais tu dois faire des phrases courtes avec un vocabulaire biomécanique (Rule 5 & 6)."_

Ainsi, l'intelligence artificielle respecte l'ADN profond (La Voice), tout en ajustant parfaitement sa posture commerciale (Le Tone) !

---

_Combien de règles une vraie marque haut de gamme possède-t-elle ?_
Pour une entreprise comme The Outdoor Axolotl, le PDF de style d'origine fait généralement 30 à 40 pages. Une fois digéré par notre algorithme, cela donne en moyenne :

- **1 Règle de Voix Globale (NULL)** regroupant environ **20 à 30 contraintes**.
- **3 à 5 Target Tones** (ex: Mobilier Luxe, Outillage, SAV, Collections Capsules).
- Soit un total d'environ **80 à 120 lignes** dans la table `STYLE_RULES`. C'est une taille parfaite : assez riche pour que le LLM écrive de manière sublime, mais assez léger pour une requête SQL instantanée.

Voici un extrait hyper-réaliste de ce que donne l'ingestion de la Voix globale, du Ton "Mobilier" (Aspirationnel) et du Ton "Outils" (Empathique/Expert) pour The Outdoor Axolotl :

### Table 1 : `TARGET_TONE` (Les 5 Contextes de la Marque)

| id               | name                                | description_interne                                                                                                                                    |
| :--------------- | :---------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tone_mobilier`  | Outdoor Furniture (Aspirationnel)   | [Inspiration Dedon/Fermob] Ton dédié aux collections de salons, canapés et tables. Évoque le statut, le confort absolu et l'art de vivre en extérieur. |
| `tone_outils`    | Ergonomic Tools (Expert Empathique) | [Inspiration Fiskars/Felco] Ton dédié aux outils de taille. Rassure sur la protection articulaire, la coupe nette et la fonctionnalité implacable.     |
| `tone_eclairage` | Lighting & Ambiance (Féérique)      | Ton dédié aux lampes d'extérieur. Focus sur la prolongation des soirées, les jeux d'ombres et la magie nocturne.                                       |
| `tone_textile`   | Textiles & Cushions (Sensoriel)     | Ton dédié aux coussins et tapis d'extérieur. Insiste sur le toucher, la résistance aux UV, la déperlance et le confort intérieur amené à l'extérieur.  |
| `tone_sav`       | Garantie & Care (Rassurant & Clair) | Mode instructionnel pour les notices d'entretien. Ton expert, direct, pérenne.                                                                         |

### Table 2 : `STYLE_RULES` (La Matrice de l'ADN et des Gammes)

#### A. Les 20 Règles de la Voix Globale (ADN Axolotl - S'applique PARTOUT)

| id       | target_tone_id | rule_type           | value                                                                                                                                                                           |
| :------- | :------------- | :------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `sr_101` | **NULL**       | `syntax_constraint` | **VOICE** : Vouvoiement strict de courtoisie ("Vous", "Votre"). Tutoiement formellement interdit.                                                                               |
| `sr_102` | **NULL**       | `forbidden_words`   | **VOICE** : Bannir tout lexique promotionnel : "Pas cher", "Bonne affaire", "Promo", "Liquidation".                                                                             |
| `sr_103` | **NULL**       | `forbidden_words`   | **VOICE** : Bannir l'urgence commerciale agressive : "Dépêchez-vous", "Achetez vite", "Stock limité".                                                                           |
| `sr_104` | **NULL**       | `forbidden_words`   | **VOICE** : Ne jamais utiliser le mot "Plastique". Utiliser "Polymère technique", "Résine tressée" ou le nom du matériau exact.                                                 |
| `sr_105` | **NULL**       | `forbidden_words`   | **VOICE** : Bannir le mot "Client" dans les accroches. Parler "d'Hôte", "d'Expert du jardin" ou "d'Épicurien".                                                                  |
| `sr_106` | **NULL**       | `forbidden_words`   | **VOICE** : Ne jamais écrire The Outdoor Axolotl en minuscules. Toujours avec les majuscules initiales.                                                                         |
| `sr_107` | **NULL**       | `tone_directive`    | **VOICE** : Personnalité de type "Guide Respectueux". Le ton doit être assuré, expert, mais jamais prétentieux.                                                                 |
| `sr_108` | **NULL**       | `tone_directive`    | **VOICE** : Ne jamais s'excuser dans le positionnement prix. Le prix est justifié par l'ingénierie et l'artisanat.                                                              |
| `sr_109` | **NULL**       | `mandatory_lexicon` | **VOICE** : Utiliser des mots valorisant le temps long : "Héritage", "Pérenne", "Traverser les saisons", "Investissement".                                                      |
| `sr_110` | **NULL**       | `mandatory_lexicon` | **VOICE** : Utiliser des mots d'ancrage naturel : "Symbiose", "Ciel ouvert", "Éléments", "Racines".                                                                             |
| `sr_111` | **NULL**       | `positioning`       | **VOICE** : Mettre en avant le design conçu en interne (in-house) face à l'assemblage industriel aveugle.                                                                       |
| `sr_112` | **NULL**       | `positioning`       | **VOICE** : Si l'éco-conception est mentionnée, privilégier le mot "Responsabilité" ou "Sourcing éthique" plutôt que "Green".                                                   |
| `sr_113` | **NULL**       | `syntax_constraint` | **VOICE** : Interdiction absolue d'utiliser plus d'un point d'exclamation par paragraphe.                                                                                       |
| `sr_114` | **NULL**       | `formatting`        | **VOICE** : Les listes à puces doivent toujours commencer par un verbe d'action à l'infinitif (Ex: "Assurer...", "Profiter...").                                                |
| `sr_115` | **NULL**       | `forbidden_words`   | **VOICE** : Interdiction d'utiliser des adjectifs hyperboliques génériques comme "Incroyable", "Super", "Génial".                                                               |
| `sr_116` | **NULL**       | `mandatory_lexicon` | **VOICE** : Remplacer "Super" par "Exquis", "Génial" par "Subtil", "Solide" par "Inébranlable".                                                                                 |
| `sr_117` | **NULL**       | `tone_directive`    | **VOICE** : En cas de mention de l'hiver, ne jamais l'aborder comme une contrainte. L'hiver est un "repos" ou une "épreuve que le matériau défie".                              |
| `sr_118` | **NULL**       | `syntax_constraint` | **VOICE** : Éviter le jargon scientifique sans explication. Toute spécification technique (ex: Aluminium 6061) doit inclure son bénéfice client direct (ex: Résistance marine). |
| `sr_119` | **NULL**       | `positioning`       | **VOICE** : Le produit n'est pas un but en soi, c'est un catalyseur d'art de vivre.                                                                                             |
| `sr_120` | **NULL**       | `formatting`        | **VOICE** : Ne jamais utiliser d'emojis dans les descriptions de fiches produits.                                                                                               |

#### B. Les Règles Spécifiques des 5 Target Tones (S'activent uniquement à la demande)

| id       | target_tone_id   | rule_type           | value                                                                                                                                       |
| :------- | :--------------- | :------------------ | :------------------------------------------------------------------------------------------------------------------------------------------ |
| `sr_201` | `tone_mobilier`  | `tone_directive`    | **TONE MOBILIER** : Éviter le jargon industriel pur. Le ton est poétique, axé sur l'expérience sensorielle du repos et de la réception.     |
| `sr_202` | `tone_mobilier`  | `mandatory_lexicon` | **TONE MOBILIER** : Utiliser un vocabulaire de sanctuaire (ex: "intemporel", "façonné à la main", "sérénité", "retraite", "réception").     |
| `sr_203` | `tone_outils`    | `tone_directive`    | **TONE OUTILS** : Le ton est axé sur la santé, la réduction de fatigue et la coupe franche. Grande empathie pour l'effort physique.         |
| `sr_204` | `tone_outils`    | `mandatory_lexicon` | **TONE OUTILS** : Forcer le vocabulaire biomécanique (ex: "effet de levier", "amorti", "lame trempée", "prévention des TMS").               |
| `sr_205` | `tone_outils`    | `forbidden_words`   | **TONE OUTILS** : Bannir tout vocabulaire culpabilisant sur le manque de force ou l'âge du jardinier.                                       |
| `sr_206` | `tone_outils`    | `syntax_constraint` | **TONE OUTILS** : Les titres descriptifs doivent rimer avec l'action de taille : phrases saccadées, courtes, impactantes.                   |
| `sr_207` | `tone_eclairage` | `mandatory_lexicon` | **TONE ECLAIRAGE** : Utiliser un lexique crépusculaire (ex: "clairobscur", "prolonger l'instant", "lueur tamisée", "balisage délicat").     |
| `sr_208` | `tone_textile`   | `tone_directive`    | **TONE TEXTILE** : Insister sur la disparition de la frontière entre le salon intérieur (le toucher) et la terrasse (la résilience météo).  |
| `sr_209` | `tone_textile`   | `mandatory_lexicon` | **TONE TEXTILE** : Utiliser un vocabulaire de contact (ex: "déperlant", "moelleux", "maillage respirant", "fibre acrylique teintée masse"). |
| `sr_210` | `tone_sav`       | `tone_directive`    | **TONE SAV/CARE** : Aucune poésie. Ton strictement direct, précis, numéroté pour rassurer sur la longévité de l'investissement.             |
