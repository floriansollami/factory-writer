# Roadmap POC : ingestion du guide de style

Ce document donne la **roadmap simple et ordonnée** pour faire fonctionner l'ingestion du guide de style dans le POC Factory Writer.

Il reste aligné avec :

- [ARCHITECTURE_SOTA_2026.md](/Users/floriansollami/Documents/GitHub/factory-writer/docs/ARCHITECTURE_SOTA_2026.md)
- [FINAL_ARCHITECTURE.md](/Users/floriansollami/Documents/GitHub/factory-writer/docs/FINAL_ARCHITECTURE.md)

Le but du POC est simple :

1. un PDF de guide de style arrive dans GCS
2. Eventarc appelle l'API
3. l'API démarre `StyleGuideIngestionWorkflow`
4. le workflow parse le document
5. on extrait un draft pack structuré
6. un humain approuve
7. le pack devient actif
8. le runtime produit peut charger ce pack actif

## Déjà en place

- les modèles DB existent déjà dans [backend/src/infrastructure/database/models/style_guide.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/infrastructure/database/models/style_guide.py)
- la route Eventarc et le use case existent déjà dans [backend/src/api/routes/eventarc_router.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/api/routes/eventarc_router.py) et [backend/src/application/use_cases/ingest_style_guide.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/application/use_cases/ingest_style_guide.py)
- le workflow Temporal et les activities squelette existent déjà dans [backend/src/temporal/workflows/style_guide_ingestion.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/temporal/workflows/style_guide_ingestion.py) et [backend/src/temporal/activities/style_guide_activities.py](/Users/floriansollami/Documents/GitHub/factory-writer/backend/src/temporal/activities/style_guide_activities.py)

## Roadmap unique

| Ordre | Tâche POC | Ce qu'on fait concrètement | Résultat attendu |
| --- | --- | --- | --- |
| 1 | Finaliser le contrat du draft pack | définir le JSON que LiteLLM doit retourner pour le style guide, sans surcomplexifier | un schéma clair et stable pour l'extraction |
| 2 | Compléter légèrement le modèle DB | ajouter seulement les champs vraiment utiles au POC: provenance minimale, review minimale, promotion minimale | la base peut stocker source, fragments, draft pack, décision humaine et pack actif |
| 3 | Brancher réellement Eventarc vers l'API | configurer le trigger GCS finalisé vers `/style-guide` sur Cloud Run | un upload PDF déclenche bien l'ingestion |
| 4 | Implémenter l'activity Document AI | remplacer le placeholder `trigger_style_layout_parse_activity` par un vrai appel Layout Parser | le PDF est lu et transformé en sortie exploitable |
| 5 | Implémenter la persistance des fragments | transformer la sortie Document AI en `fragment_style` persistés en base | les fragments du guide sont stockés avec une provenance minimale |
| 6 | Implémenter l'activity LiteLLM d'extraction | envoyer les fragments au modèle avec structured output et produire un draft pack | on obtient un pack brouillon structuré |
| 7 | Ajouter la validation déterministe minimale | vérifier structure JSON, enums, criticité, provenance fragment, règles vides | seules les sorties exploitables passent |
| 8 | Persister le draft pack en base | créer `pack_style` brouillon et ses `regle_style` associées | le draft pack est visible et gouvernable |
| 9 | Brancher la review humaine minimale | créer une API ou un mini back-office pour voir le draft et envoyer approve/reject au workflow | un humain peut valider ou refuser le pack |
| 10 | Implémenter la promotion du pack actif | remplacer `promote_style_pack_activity` par une vraie transaction qui active le nouveau pack et désactive l'ancien | un seul style pack actif existe pour le runtime |
| 11 | Brancher le chargement runtime du style pack actif | remplacer `load_style_pack_active_activity` par une vraie lecture PostgreSQL | le runtime produit récupère le style pack actif sans relire le PDF |
| 12 | Ajouter l'observabilité minimale | logs corrélés `source_id`, `workflow_id`, `pack_id`, statuts d'erreur clairs | on peut débugger le flux sans difficulté |
| 13 | Ajouter les tests minimums | tests sur use case d'entrée, workflow style guide, activities critiques | le POC est exécutable sans régression immédiate |

## Ordre de livraison recommandé

Si on veut aller vite pour le POC, il faut livrer dans cet ordre :

1. étapes `1` à `3`
2. étapes `4` à `8`
3. étapes `9` à `11`
4. étapes `12` à `13`

## Definition of done du POC

Le POC est considéré comme fonctionnel quand on peut faire ce scénario complet :

1. déposer un PDF de style guide dans le bucket GCS
2. voir l'API démarrer le workflow Temporal
3. voir les fragments extraits et stockés
4. voir un draft pack créé en base
5. approuver ce draft pack
6. voir un `style_pack` actif promu
7. charger ce pack actif depuis le runtime
