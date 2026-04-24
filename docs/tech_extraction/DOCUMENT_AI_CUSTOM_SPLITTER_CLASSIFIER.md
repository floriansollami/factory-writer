# Document AI Custom Splitter / Custom Classifier

Ce document explique le rôle du **Custom Splitter** et du **Custom Classifier** dans l’ingestion des dossiers techniques usine Axolotl.

Objectif :

```text
Recevoir un dossier technique fournisseur
-> comprendre quels types de documents il contient
-> découper les PDF composites si nécessaire
-> router chaque document vers le bon extracteur
```

Le point clé :

```text
Custom Classifier = identifier le type d’un document
Custom Splitter = découper un PDF composite en sous-documents typés
Custom Extractor = extraire les facts métier après classification/split
```

## 1. Pourquoi on a besoin de Splitter / Classifier

Un dossier technique usine réel n’est pas forcément un PDF propre avec une seule fiche.

Il peut contenir :

```text
pages 1-2 : fiche technique produit
page 3 : certificat FSC
pages 4-6 : notice d’assemblage
page 7 : plan / blueprint
pages 8-9 : fiche matière
```

Si on envoie tout ce paquet directement dans un seul Custom Extractor, on mélange plusieurs contrats d’extraction :

```text
dimensions
certifications
contraintes d’assemblage
matières
plans techniques
```

Ce mélange augmente le risque :

```text
wrong extractor
wrong schema
wrong fact
wrong evidence
review plus difficile
```

Donc on ajoute une couche de routage documentaire avant l’extraction métier.

## 2. Custom Classifier : ce que ça fait

Le **Custom Classifier** répond à cette question :

```text
Quel est le type de ce document ?
```

Exemple :

```text
input : AX-TABLE-190_certificat_FSC.pdf
output : ECO_CERTIFICATE, confidence 0.94
```

Google le définit comme un processor qui classe un document dans une classe définie par l’utilisateur. Google précise aussi que le résultat peut ensuite être utilisé pour envoyer le document vers le bon processor d’extraction.

Pour Axolotl, les classes utiles seraient :

| Classe | Description | Extracteur cible |
| --- | --- | --- |
| `TECHNICAL_SHEET` | Fiche technique produit avec dimensions, poids, matériaux. | Technical Sheet Custom Extractor |
| `MATERIAL_SPEC` | Fiche matière, nuance bois, acier, finition, traitement. | Material Spec Custom Extractor |
| `ECO_CERTIFICATE` | Certificat FSC, PEFC, REACH, RoHS, ISO, etc. | Eco Certification Custom Extractor |
| `ASSEMBLY_NOTICE` | Notice d’assemblage, outils, contraintes, temps, nombre de personnes. | Assembly Notice Custom Extractor |
| `BLUEPRINT` | Plan, cartouche, cotes, vues techniques. | Blueprint / Technical Drawing flow |
| `PACKAGING_SPEC` | Dimensions colis, poids brut/net, nombre de colis. | Packaging Spec Custom Extractor |
| `UNKNOWN` | Document non reconnu ou hors périmètre. | Review humaine |

## 3. Custom Splitter : ce que ça fait

Le **Custom Splitter** répond à deux questions :

```text
Où commence et où finit chaque sous-document dans un PDF composite ?
Quel est le type de chaque sous-document ?
```

Exemple :

```text
input : AX-TABLE-190_supplier_pack.pdf

output :
pages 1-2 -> TECHNICAL_SHEET, confidence 0.97
page 3 -> ECO_CERTIFICATE, confidence 0.91
pages 4-6 -> ASSEMBLY_NOTICE, confidence 0.88
page 7 -> BLUEPRINT, confidence 0.84
```

Google précise deux points importants :

```text
Le splitter prédit les pages qui composent chaque document logique.
Le splitter ne découpe pas physiquement le PDF à ta place.
```

Pour découper physiquement le PDF, Google recommande d’utiliser **Document AI Toolbox**, qui sait utiliser les limites de pages retournées par le splitter.

## 4. Différence entre Classifier et Splitter

| Question | Custom Classifier | Custom Splitter |
| --- | --- | --- |
| Le document est-il déjà isolé ? | Oui | Non, il peut être composite |
| Ce qu’il prédit | Une classe documentaire | Des segments de pages + une classe par segment |
| Exemple | `certificat.pdf -> ECO_CERTIFICATE` | `pack.pdf -> pages 1-2 TECHNICAL_SHEET, page 3 ECO_CERTIFICATE` |
| Utilité principale | Router un document déjà séparé | Découper et router un dossier composite |
| Risque principal | Mauvaise classe | Mauvaise frontière de pages + mauvaise classe |
| Review recommandée | Si confidence basse ou classe critique | Plus importante, car un mauvais split casse la suite |

Phrase simple :

```text
Classifier = étiquette le document.
Splitter = découpe le paquet puis étiquette chaque morceau.
```

## 5. Comment Google renvoie le résultat

Pour un splitter/classifier, Google renvoie un `Document` dont les sous-documents sont représentés dans `document.entities`.

Chaque entity contient notamment :

| Champ | Sens |
| --- | --- |
| `entity.type_` | Classe prédite, par exemple `TECHNICAL_SHEET`. |
| `entity.confidence` | Confiance de la prédiction. |
| `entity.page_anchor.page_refs` | Pages couvertes par le sous-document. |

Exemple conceptuel :

```json
{
  "entities": [
    {
      "type": "TECHNICAL_SHEET",
      "confidence": 0.97,
      "pageAnchor": {
        "pageRefs": [
          { "page": "0" },
          { "page": "1" }
        ]
      }
    },
    {
      "type": "ECO_CERTIFICATE",
      "confidence": 0.91,
      "pageAnchor": {
        "pageRefs": [
          { "page": "2" }
        ]
      }
    }
  ]
}
```

Attention : les pages Document AI sont généralement indexées à partir de `0`. Pour l’UI, il faut afficher `page + 1`.

## 6. Utilisation avec le SDK Python

L’appel ressemble aux autres processors Document AI.

```python
from typing import Sequence

from google.api_core.client_options import ClientOptions
from google.cloud import documentai


def process_splitter_or_classifier(
    *,
    project_id: str,
    location: str,
    processor_id: str,
    processor_version: str,
    file_path: str,
    mime_type: str = "application/pdf",
) -> documentai.Document:
    client = documentai.DocumentProcessorServiceClient(
        client_options=ClientOptions(
            api_endpoint=f"{location}-documentai.googleapis.com"
        )
    )

    name = client.processor_version_path(
        project_id,
        location,
        processor_id,
        processor_version,
    )

    with open(file_path, "rb") as f:
        content = f.read()

    request = documentai.ProcessRequest(
        name=name,
        raw_document=documentai.RawDocument(
            content=content,
            mime_type=mime_type,
        ),
    )

    result = client.process_document(request=request)
    return result.document


def page_refs_to_pages(
    page_refs: Sequence[documentai.Document.PageAnchor.PageRef],
) -> list[int]:
    return [int(page_ref.page) + 1 for page_ref in page_refs]


def read_splitter_output(document: documentai.Document) -> list[dict]:
    return [
        {
            "document_type": entity.type_,
            "confidence": entity.confidence,
            "pages": page_refs_to_pages(entity.page_anchor.page_refs),
        }
        for entity in document.entities
    ]
```

Exemple de sortie normalisée côté Factory Writer :

```json
[
  {
    "document_type": "TECHNICAL_SHEET",
    "confidence": 0.97,
    "pages": [1, 2]
  },
  {
    "document_type": "ECO_CERTIFICATE",
    "confidence": 0.91,
    "pages": [3]
  }
]
```

## 7. Utilisation avec Document AI Toolbox

Google précise que le splitter ne découpe pas physiquement le PDF.

Document AI Toolbox peut prendre :

```text
le PDF source
+ le JSON Document AI du splitter
```

et produire :

```text
un PDF par sous-document logique
```

Exemple conceptuel :

```python
from google.cloud.documentai_toolbox import document


def split_pdf_with_toolbox(
    *,
    document_json_path: str,
    pdf_path: str,
    output_path: str,
) -> list[str]:
    wrapped_document = document.Document.from_document_path(
        document_path=document_json_path
    )
    output_files = wrapped_document.split_pdf(
        pdf_path=pdf_path,
        output_path=output_path,
    )
    return [str(path) for path in output_files]
```

Dans Factory Writer, on peut choisir deux stratégies :

| Stratégie | Description | Avantage | Limite |
| --- | --- | --- | --- |
| Découpe physique | Créer un PDF par segment puis appeler le bon extractor. | Simple à raisonner, debug facile. | Plus d’I/O GCS, gestion de fichiers en plus. |
| Découpe logique | Garder le PDF source et passer les pages au bon extractor si possible. | Moins de fichiers. | Plus complexe selon les APIs et processors. |

Pour un POC, la découpe physique via Toolbox est plus simple à expliquer.

## 8. Comment l’entraîner

Le flow d’entraînement ressemble à celui des Custom Extractors.

```text
1. Créer le Custom Splitter ou Custom Classifier.
2. Créer le dataset.
3. Définir les classes.
4. Importer des documents.
5. Labeler les documents ou segments.
6. Assigner train/test.
7. Train new version.
8. Évaluer.
9. Déployer.
10. Appeler explicitement la processor version.
```

Exemples de classes Axolotl :

```text
TECHNICAL_SHEET
MATERIAL_SPEC
ECO_CERTIFICATE
ASSEMBLY_NOTICE
BLUEPRINT
PACKAGING_SPEC
UNKNOWN
```

Pour le Classifier, tu labels le document entier :

```text
ce PDF = ECO_CERTIFICATE
```

Pour le Splitter, tu labels les segments :

```text
pages 1-2 = TECHNICAL_SHEET
page 3 = ECO_CERTIFICATE
pages 4-6 = ASSEMBLY_NOTICE
```

## 9. Données nécessaires

Les limites et minimums exacts dépendent du type de processor et de la version, mais Google donne des règles importantes :

| Point | Lecture pratique |
| --- | --- |
| Il faut des documents en training et test. | Sans test set, tu ne peux pas mesurer proprement. |
| Les labels doivent être représentés. | Une classe absente du test set ne peut pas être évaluée correctement. |
| Plus la variation est forte, plus il faut de données. | Fournisseurs hétérogènes = dataset plus large. |
| Les descriptions de labels aident. | Ajouter une description pour `BLUEPRINT`, `ECO_CERTIFICATE`, etc. |
| Les datasets Google-managed sont plus simples. | Évite de casser le dataset en manipulant le bucket. |

Pour Axolotl, je viserais en POC+ :

| Classe | Minimum raisonnable POC+ |
| --- | --- |
| `TECHNICAL_SHEET` | 10 à 20 exemples |
| `MATERIAL_SPEC` | 10 à 20 exemples |
| `ECO_CERTIFICATE` | 10 à 20 exemples |
| `ASSEMBLY_NOTICE` | 10 à 20 exemples |
| `BLUEPRINT` | 10 à 20 exemples |

En production, le test set doit être beaucoup plus représentatif :

```text
plusieurs fournisseurs
plusieurs familles produits
plusieurs langues
plusieurs années/templates
scans et PDF natifs si les deux existent
```

## 10. Review humaine : point critique

Google indique clairement qu’un mauvais split est très problématique :

```text
un mauvais split peut casser deux documents
et provoquer des erreurs d’extraction en cascade
```

Donc pour Axolotl :

```text
split confidence basse -> review
classe inconnue -> review
BLUEPRINT détecté -> review ciblée si cote critique
document composite avec split douteux -> review
```

Pattern recommandé :

```text
si confidence >= seuil et classe non critique
-> routage automatique

si confidence < seuil ou document critique
-> review du split/classification
```

Exemple :

```json
{
  "document_type": "ECO_CERTIFICATE",
  "pages": [3],
  "confidence": 0.62,
  "routing_status": "NEEDS_REVIEW",
  "review_reason": "LOW_CLASSIFICATION_CONFIDENCE"
}
```

## 11. Flow cible Axolotl

```text
PDF dossier usine
-> Enterprise OCR evidence layer
-> Custom Splitter si PDF composite
-> Review du split si confidence basse
-> Découpe logique ou physique
-> Custom Classifier si document isolé mais type inconnu
-> Routage vers le bon Custom Extractor
-> Extraction des facts métier
-> Validation Python
-> Review par exception
-> Facts validés
-> LiteLLM génération produit
```

Version avec classes :

```text
TECHNICAL_SHEET
-> Technical Sheet Extractor

MATERIAL_SPEC
-> Material Spec Extractor

ECO_CERTIFICATE
-> Eco Certification Extractor

ASSEMBLY_NOTICE
-> Assembly Notice Extractor

BLUEPRINT
-> Blueprint flow avec OCR, extraction prudente, review visuelle ciblée

UNKNOWN
-> Review humaine
```

## 12. Où placer Splitter / Classifier dans notre pipeline

Il y a deux cas.

### Cas 1 : PDF composite

Exemple :

```text
un seul PDF contient fiche technique + certificat + notice
```

Flow :

```text
PDF
-> Custom Splitter
-> segments typés
-> review si split douteux
-> extraction par segment
```

### Cas 2 : Documents déjà séparés

Exemple :

```text
technical_sheet.pdf
certificate_fsc.pdf
assembly_notice.pdf
```

Flow :

```text
chaque PDF
-> Custom Classifier
-> classe documentaire
-> extractor adapté
```

### Cas 3 : Convention de dépôt fiable

Exemple :

```text
le fournisseur ou Axolotl dépose déjà les fichiers dans :
technical_sheets/
certificates/
assembly_notices/
```

Flow :

```text
pas besoin de classifier au runtime
la classe vient du chemin de dépôt
classifier utilisé seulement en audit ou fallback
```

Pour le POC, si l’UI impose le type de document à l’upload, on peut différer le Classifier/Splitter.

Pour la production multi-fournisseurs, il faut les prévoir.

## 13. Ce qu’il faut stocker

Pour chaque décision de split/classification :

```text
document_routing_run_id
source_document_id
processor_id
processor_version
routing_strategy
document_type
confidence
page_start
page_end
review_status
review_reason
created_at
```

Pour un PDF composite :

```text
technical_document_segment
source_document_id
segment_index
document_type
page_start
page_end
confidence
derived_pdf_uri
splitter_processor_version
review_status
```

Pour audit :

```text
original_pdf_uri
splitter_output_uri
classifier_output_uri
human_corrected_document_type
human_corrected_page_range
exported_to_docai_dataset_at
```

## 14. Recommandation Axolotl

Pour Axolotl, je ne mettrais pas Splitter/Classifier au centre du POC style guide.

Mais pour les dossiers techniques usine :

```text
si chaque produit reçoit un dossier composite
-> Custom Splitter indispensable

si les fichiers sont déjà séparés mais non typés
-> Custom Classifier utile

si l’admin impose le type au moment de l’upload
-> Classifier optionnel au début
```

Recommandation progressive :

```text
POC
-> type documentaire sélectionné dans l’UI
-> pas encore de Custom Splitter si les fichiers sont séparés

POC+
-> Custom Classifier pour contrôler le type déclaré
-> Splitter uniquement sur PDF composites

Production
-> Custom Splitter pour dossiers composites
-> Custom Classifier pour documents isolés ou fallback
-> thresholds de confidence
-> review humaine des splits/classes douteux
-> routage vers Custom Extractors par famille documentaire
```

Phrase à retenir :

```text
Le Classifier décide “ce que c’est”.
Le Splitter décide “où ça commence, où ça finit, et ce que c’est”.
Ils ne remplacent pas les extracteurs : ils routent vers eux.
```

## Sources Google utilisées

1. [Custom Classifier](https://docs.cloud.google.com/document-ai/docs/custom-classifier)
2. [Custom Splitter](https://docs.cloud.google.com/document-ai/docs/custom-splitter)
3. [Document splitters behavior](https://docs.cloud.google.com/document-ai/docs/splitters-behavior)
4. [Handle processing response](https://docs.cloud.google.com/document-ai/docs/handle-response)
5. [Train and evaluate](https://docs.cloud.google.com/document-ai/docs/training-overview)
6. [Label documents](https://docs.cloud.google.com/document-ai/docs/label-documents)
7. [Processor list](https://docs.cloud.google.com/document-ai/docs/processors-list)
8. [Document AI overview](https://docs.cloud.google.com/document-ai/docs/overview)
9. [Quotas and limits](https://docs.cloud.google.com/document-ai/limits)
10. [Document splitters](https://docs.cloud.google.com/document-ai/docs/splitters)
