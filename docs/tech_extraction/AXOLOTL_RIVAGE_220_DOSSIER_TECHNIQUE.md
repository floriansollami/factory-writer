# Dossier technique POC - Table Rivage 220

Ce dossier simule les trois PDF usine reçus pour créer la future fiche produit de la table extérieure **Rivage 220**.

L'objectif n'est pas de rendre l'extraction trop facile. Les documents utilisent des formulations fournisseur, parfois différentes des noms marketing, pour tester correctement :

- le Custom Classifier Document AI ;
- le Custom Extractor foundation model ;
- la validation déterministe côté backend ;
- la revue humaine si une preuve manque ou si une contradiction apparaît.

## Fichiers du dossier

| Fichier | Type attendu par le classifier | Rôle |
| --- | --- | --- |
| `AXOLOTL_RIVAGE_220_FICHE_ATELIER.pdf` | `technical_specification` | Source principale des dimensions, matériaux, finition, poids et contrôles qualité. |
| `AXOLOTL_RIVAGE_220_NOTICE_MONTAGE.pdf` | `assembly_instructions` | Source des contraintes de montage, outillage, nombre de personnes, ordre d'assemblage et restrictions. |
| `AXOLOTL_RIVAGE_220_ATTESTATION_MATIERE.pdf` | `eco_certification` | Source des certifications, revendications FSC/SVLK/FLEGT et limites exactes de ces preuves. |

## Produit concerné

```json
{
  "sku": "AX-TB-RIV-220-TKGR",
  "nom": "Table Rivage 220",
  "famille_code": "mobilier_jardin",
  "sous_famille_code": "table_repas_exterieur",
  "season_code": "printemps_ete",
  "segment_prix_code": "premium",
  "langue_principale": "fr-FR"
}
```

## Facts techniques à extraire

### Depuis la fiche atelier

- `product_name` : Table Rivage 220.
- `sku` : AX-TB-RIV-220-TKGR.
- `material_primary` : teck massif, Tectona grandis.
- `material_secondary` : aluminium 6063-T5, finition poudre polyester graphite mat RAL 7021.
- `dimension_width_cm` : 220 cm.
- `dimension_depth_cm` : 95 cm.
- `dimension_height_cm` : 74 cm.
- `weight_kg` : 58 kg +/- 2 kg.
- `parasol_hole_diameter_mm` : 50 mm.
- `usage_capacity` : 8 couverts.

### Depuis la notice de montage

- `assembly_people_required` : 2 adultes.
- `assembly_time_minutes` : 25 min.
- `required_tool` : clé Allen 5 mm fournie.
- `max_torque_nm` : 8 N·m.
- `assembly_constraints` :
  - assembler sur mousse ou carton ;
  - ne pas serrer à fond avant équerrage ;
  - serrage progressif en croix ;
  - ne pas utiliser de visseuse à choc ;
  - garder 3 à 5 mm de jeu bois/métal.

### Depuis l'attestation matière

- `eco_certifications` :
  - FSC Mix Credit sur composants teck du plateau ;
  - SVLK / FLEGT batch IDN-2026-AX-7721.
- `fsc_license_code` : FSC-C184206-AOX.
- `chain_of_custody_code` : COC-INT-77842.
- `covered_component` : plateau teck et bouchon ombrage.
- `excluded_component` : piètement aluminium, visserie inox, carton export.
- `certificate_valid_until` : 30/09/2026.

## Validations déterministes attendues

- Les dimensions doivent être converties de `mm` vers `cm`.
- Les matériaux doivent être non vides et sourcés.
- Les certifications doivent être acceptées uniquement si elles apparaissent explicitement dans l'attestation.
- La mention `FSC Mix Credit` ne doit pas devenir `100 % FSC`.
- Le piètement aluminium ne doit pas hériter de la certification FSC.
- Les contraintes d'assemblage doivent provenir de la notice, pas d'une inférence marketing.
- Les formulations fournisseur comme `outdoor all season` ne doivent pas devenir une promesse absolue.

## Points volontairement piégeux

- Les documents ne portent pas tous le même titre marketing.
- La fiche atelier parle de `Table Rivage 220`, mais aussi de `RIVAGE 220` et de `AX-TB-RIV-220-TKGR`.
- Les dimensions sont données en millimètres, alors que le modèle canonique attend des centimètres.
- L'attestation limite explicitement le périmètre de la preuve FSC.
- La notice contient des restrictions qui doivent être conservées comme contraintes, pas transformées en bénéfices commerciaux.

## Résultat attendu du pipeline

```text
3 PDFs uploadés
-> classifier : technical_specification / assembly_instructions / eco_certification
-> extractor : facts candidats + evidence source
-> validation déterministe
-> facts validés ou review humaine
-> contexte produit prêt pour génération
```

La génération de fiche produit ne doit utiliser que les facts validés, le style pack actif et le snapshot commercial sélectionné.
