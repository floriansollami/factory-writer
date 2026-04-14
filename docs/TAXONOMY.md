# Recommandations de taxonomie produit pour le POC Axolotl

Dans le POC Factory Writer, la taxonomie produit minimale recommandée repose sur trois notions :

- **`famille`** : grand type de produit, par exemple `mobilier_jardin` ou `outils_jardin`
- **`sous_famille`** : type précis utile au pipeline, par exemple `table_repas`, `banc_exterieur`, `secateur` ou `transplantoir`
- **`sku`** : référence vendable exacte, par exemple `AXO-TABLE-210-TECK` ou `AXO-SECATEUR-ERG-PRO`

---

## Tableau d'exemples

| Produit                            | Famille           | Sous-famille            |
| ---------------------------------- | ----------------- | ----------------------- |
| Table repas teck 210 cm            | `mobilier_jardin` | `table_repas`           |
| Table bistrot aluminium compact    | `mobilier_jardin` | `table_bistrot`         |
| Banc extérieur teck 180 cm         | `mobilier_jardin` | `banc_exterieur`        |
| Fauteuil lounge corde et aluminium | `mobilier_jardin` | `fauteuil_lounge`       |
| Chaise repas outdoor empilable     | `mobilier_jardin` | `chaise_repas`          |
| Méridienne de jardin premium       | `mobilier_jardin` | `meridienne_exterieure` |
| Sécateur ergonomique coupe franche | `outils_jardin`   | `secateur`              |
| Coupe-branches à effet de levier   | `outils_jardin`   | `coupe_branches`        |
| Transplantoir ergonomique renforcé | `outils_jardin`   | `transplantoir`         |
| Désherbeur manuel longue portée    | `outils_jardin`   | `desherbeur`            |
| Scie d'élagage pliante             | `outils_jardin`   | `scie_elagage`          |
| Griffe de jardin ergonomique       | `outils_jardin`   | `griffe_jardin`         |

---

## Table `PRODUCT` pour le POC

Comme ici on ne modélise pas une table de base de données complète mais **les informations minimales utiles sur un produit pour faire tourner le POC**, on ne garde que les champs réellement nécessaires au pipeline.

| Champ               | Type indicatif | Obligatoire | Description                                                                                              | Exemple                |
| ------------------- | -------------- | ----------- | -------------------------------------------------------------------------------------------------------- | ---------------------- |
| `sku`               | `string`       | oui         | Identifiant métier principal du produit. C'est la clé de référence commune avec le PLM / ERP / commerce. | `AXO-TABLE-210-TECK`   |
| `nom_interne`       | `string`       | oui         | Nom de travail du produit, tel qu'il existe côté métier avant rédaction marketing finale.                | `Table repas teck 210` |
| `famille_code`      | `string`       | oui         | Référence vers la famille produit.                                                                       | `mobilier_jardin`      |
| `sous_famille_code` | `string`       | oui         | Référence vers la sous-famille produit.                                                                  | `table_repas`          |
| `season_code`       | `string`       | oui         | Saison commerciale, par exemple `SS26`.                                                                  | `SS26`                 |
| `segment_prix_code` | `string`       | oui         | Segment prix métier, utile pour le positionnement et les comparables.                                    | `premium`              |
