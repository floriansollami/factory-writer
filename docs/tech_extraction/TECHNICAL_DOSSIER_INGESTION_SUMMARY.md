# Résumé de l'ingestion des dossiers techniques usine

Ce document résume les briques utilisées pour ingérer les dossiers techniques usine et produire des facts techniques validés avant génération produit.

## Stack cible

- **Upload contrôlé depuis l'admin** : l'utilisateur dépose les documents techniques du produit, idéalement par type : fiche technique, plan, certification, notice d'assemblage.

- **Custom Classifier Document AI** : utilisé si plusieurs fichiers arrivent séparément mais sans type fiable. Il classe chaque PDF : `TECHNICAL_SHEET`, `BLUEPRINT`, `ECO_CERTIFICATE`, `ASSEMBLY_NOTICE`, etc.

- **Custom Splitter Document AI** : utilisé seulement si un seul gros PDF mélange plusieurs documents. Il découpe le PDF en sous-documents logiques avant extraction.

- **Enterprise OCR v2.1** : couche de preuve documentaire. Elle donne le texte brut, les pages, les bounding boxes, les confidence scores, les quality scores et permet le visual grounding.

- **Custom Extractor Document AI Foundation Model** : extraction des facts métier typés : dimensions, poids, matériaux, certifications, contraintes d'assemblage. Pour Axolotl, c'est le meilleur choix de départ car les fournisseurs auront probablement des formats différents.

- **Validation Python déterministe** : vérification sans IA : exact match dans la source OCR, unités, bornes physiques par famille produit, champs obligatoires, contradictions, valeurs impossibles.

- **Review humaine par exception** : uniquement si confidence basse, OCR douteux, contradiction, champ critique absent, valeur hors bornes ou auto-évaluation LLM incertaine.

- **Facts validés en base** : seuls les facts validés deviennent la source autorisée pour la génération produit via LiteLLM. Le LLM ne lit pas directement les PDF pour inventer des données techniques.

- **Fine-tuning Document AI plus tard** : les corrections humaines alimentent un dataset Document AI. Quand on a assez d'exemples, on crée une nouvelle `processor_version` fine-tuned spécialisée Axolotl.

## Flow résumé

```text
Upload admin
-> Classifier ou Splitter si nécessaire
-> Enterprise OCR pour la preuve
-> Custom Extractor pour les facts
-> Validation Python
-> Review par exception
-> Facts validés
-> LiteLLM génère uniquement depuis ces facts
```

## Ce que veut dire "Context-First"

Dans la demande client, le passage important est :

```text
"Context-First" Approach: The architecture must prioritize dynamic context management
by offering a flexible solution that doesn't lock them into a single AI provider
or require expensive training cycles.
```

Concrètement, cela veut dire :

- **Ne pas mettre l'intelligence métier dans un modèle entraîné une fois pour toutes.**

- **Construire dynamiquement le contexte utile à chaque génération.**

- **Garder les données métier dans notre système**, pas dans la mémoire implicite d'un modèle.

- **Pouvoir changer de modèle LLM** sans refaire toute l'architecture.

- **Éviter que chaque évolution métier nécessite un fine-tuning coûteux.**

Pour Axolotl, la fiche produit doit donc être générée à partir d'un contexte assemblé à la volée :

```text
facts techniques validés
+ règles de style actives
+ signaux marketing
+ feedback client
+ prompt versionné
+ modèle LLM configurable
= génération produit
```

Le LLM ne doit pas "savoir" Axolotl dans ses poids. Il doit recevoir le bon contexte au bon moment.

## Est-ce que Document AI crée du lock-in ?

Réponse courte : **oui, partiellement**, mais ce n'est pas forcément un problème si on l'isole bien.

Il faut distinguer deux types de lock-in.

### Lock-in dangereux

```text
Tout le métier est dans Google Document AI.
Les corrections humaines ne vivent que dans Google.
Le schéma des facts n'existe que dans le Custom Extractor.
L'application dépend directement du JSON Google partout.
Impossible de remplacer Google sans réécrire tout le système.
```

Ça, ce serait contraire au "Context-First".

### Lock-in maîtrisé

```text
Document AI est un adapter documentaire.
Factory Writer possède son modèle canonique.
Les facts validés sont stockés dans notre DB.
Les evidence spans sont stockés dans notre DB.
Les corrections humaines sont stockées dans notre DB.
Le code métier dépend d'un port, pas directement de Google.
```

Dans ce cas, Google Document AI est remplaçable demain par Azure AI Document Intelligence, AWS Textract, Amazon Bedrock Data Automation, Mistral OCR, LandingAI ADE, LlamaParse, Unstructured, ABBYY, UiPath, Nanonets, OpenAI Vision, Claude PDF ou un pipeline maison.

## Custom Extractor Foundation Model et Context-First

Le **Custom Extractor Foundation Model** ne contredit pas forcément la demande client parce qu'au départ :

```text
pas besoin de fine-tuning
pas besoin d'un dataset massif
pas besoin d'entraînement coûteux
on définit un schéma de champs
Google extrait des facts candidats
notre backend valide derrière
```

Donc c'est compatible avec :

```text
flexible solution
doesn't require expensive training cycles
```

Mais attention : si on passe ensuite au **fine-tuned foundation model**, là on entre dans une forme de spécialisation Google. Ce n'est pas interdit, mais ça doit rester une **optimisation optionnelle**, pas une dépendance obligatoire de l'architecture.

La formulation architecturale correcte est donc :

```text
Factory Writer est context-first au niveau de la génération.
Les modèles LLM ne sont pas fine-tunés pour apprendre Axolotl.
Ils reçoivent un contexte dynamique, validé et versionné.

Document AI est utilisé comme couche d'extraction documentaire.
Ses sorties sont normalisées dans un modèle canonique interne.
Le système ne dépend pas du format Google pour générer.
```

## Garde-fous anti lock-in

Pour éviter que Document AI devienne le coeur métier, l'architecture doit garder :

- **Un port `TechnicalDocumentExtractorPort`** : le use case ne connaît pas Google Document AI.

- **Un modèle canonique `TechnicalFactCandidate`** : dimensions, matériaux, certifications, contraintes, confidence, source page, bounding box.

- **Une table de facts validés indépendante de Google** : le runtime lit notre DB, pas Document AI.

- **Une table `extraction_run`** : `provider`, `processor_id`, `processor_version`, `request_config_snapshot`, `raw_output_uri`.

- **Une conservation du raw output** : utile pour audit, mais pas comme modèle métier principal.

- **Des corrections humaines stockées chez nous** : même si elles servent plus tard à fine-tuner Document AI.

- **LiteLLM côté génération** : pour changer de Gemini à Claude, OpenAI, Mistral ou un autre modèle sans changer les use cases.

## Classement des solutions d'extraction documentaire

Ce classement n'est pas un classement universel des OCR. Il est pondéré pour le cas Axolotl :

```text
1. exactitude des facts critiques : dimensions, matériaux, certifications
2. preuve documentaire : confidence, quality score, pages, bounding boxes
3. visual grounding pour review humaine rapide
4. extraction structurée par schéma métier
5. classification / split des dossiers composites
6. scalabilité batch
7. facilité POC dans notre stack GCP
8. risque de lock-in maîtrisable par ports et modèle canonique
```

Les benchmarks publics comme DocVQA, OCRBench, OmniDocBench, ParseBench ou IDP Leaderboard sont utiles, mais ils ne suffisent pas seuls. Ils mesurent souvent la lecture, le QA documentaire ou la structure, pas le contrat métier complet :

```text
fact critique exact
+ preuve visuelle
+ validation déterministe
+ review par exception
+ intégration workflow
```

| Rang | Solution | Verdict pour Axolotl | Pourquoi ce rang | Limite principale |
| --- | --- | --- | --- | --- |
| **1** | **Google Document AI : Enterprise OCR + Custom Classifier/Splitter + Custom Extractor Foundation Model** | **Meilleur choix cible dans notre contexte actuel** | Couvre tout le pipeline : OCR de preuve, confidence, quality score, bounding boxes, classification, splitting, extraction de facts métier, processor versions, fine-tuning optionnel. Très aligné avec GCP, Cloud Storage, Cloud SQL, Temporal et notre POC. | Lock-in Google réel. Il faut absolument normaliser dans notre modèle canonique et ne jamais exposer le JSON Google comme modèle métier. |
| **2** | **Azure AI Document Intelligence + Azure AI Content Understanding** | **Meilleure alternative cloud complète** | Très solide sur OCR/layout/tables/custom models/classifier. Content Understanding ajoute grounding, confidence et extraction orientée downstream apps. Bon candidat si Axolotl était déjà Microsoft/Azure. | Lock-in Azure équivalent. Migration depuis notre stack GCP moins naturelle. Le mix Document Intelligence + Content Understanding peut ajouter de la complexité. |
| **3** | **LandingAI Agentic Document Extraction** | **Très fort pour extraction agentic moderne** | Bon positionnement 2026 : extraction par schéma, semantic field matching, documents variables, cross-page tables, grounding et confidence en évolution. Les benchmarks DocVQA publics sont très bons. | Moins standard entreprise que Google/Azure/AWS pour une architecture cloud complète. À benchmarker sur nos dossiers usine avant engagement. |
| **4** | **Amazon Textract + Custom Queries Adapters + Bedrock Data Automation** | **Très bon si l'entreprise est AWS-first** | Textract fournit blocks, lines, words, geometry, confidence, tables/forms/queries. Custom Queries permet d'adapter des extractions. Bedrock Data Automation apporte une couche plus agentic avec confidence/grounding. | Moins naturel dans notre stack GCP. Textract Custom Queries est plus limité qu'un vrai Custom Extractor métier large. |
| **5** | **Mistral Document AI OCR** | **Excellent adapter OCR alternatif / coût-performance** | OCR moderne, structure markdown, tables HTML/Markdown, headers/footers, confidence page/word, JSON schema pour annotations. Très compatible avec une architecture context-first et fournisseur remplaçable. | Pas encore l'équivalent complet d'une chaîne Google Document AI avec classifier/splitter/custom extractor/fine-tuning de processor. À utiliser plutôt comme OCR structuré ou challenger benchmark. |
| **6** | **ABBYY Vantage / FineReader Engine** | **Très robuste pour IDP entreprise classique** | Acteur historique OCR/IDP, workflows, classification, extraction, validation humaine, options enterprise/private. Pertinent pour organisations très sensibles à la qualité OCR. | Plus lourd à intégrer dans notre POC cloud-native. Moins aligné avec Temporal/GCP/LiteLLM. Peut devenir une plateforme parallèle à maintenir. |
| **7** | **LlamaParse / LlamaCloud** | **Très bon pour parsing RAG/agent, moins pour facts critiques seuls** | Parse, extract, classify, split, index, markdown propre, tables, charts, images. Très bon pour alimenter des agents ou du RAG. | Pour le "100% dimensions/matériaux", il faut ajouter une couche de preuve OCR, confidence et validation déterministe. |
| **8** | **Unstructured** | **Meilleur choix anti lock-in / self-host possible** | Pipeline flexible de partitioning, chunking, enrichments, connecteurs, stratégie open source possible. Très bon pour garder le contrôle. | Plus d'ingénierie à construire nous-mêmes : confidence, extraction métier, visual grounding, validation, SLA batch. |
| **9** | **OpenAI Vision / PDF + Structured Outputs** | **Très bon complément LLM, pas source canonique unique** | Vision, PDF/file inputs, structured outputs, très bon raisonnement documentaire. Utile pour QA, review, extraction complémentaire ou arbitrage. | Pas une couche OCR industrielle de preuve avec confidence native par token et quality score. Risque de génération/interprétation si utilisé seul pour facts critiques. |
| **10** | **Anthropic Claude PDF + Citations** | **Très bon pour revue et citations, pas extractor canonique** | PDF support, analyse visuelle, citations et source attribution. Excellent pour assistant de review ou justification textuelle. | Pas un Custom Extractor métier avec confidence OCR/quality score. Coût/token et limites PDF à gérer. |
| **11** | **UiPath Document Understanding** | **Bon si Axolotl est déjà RPA/UiPath** | Digitization, classification, extraction, validation station, human-in-the-loop, retraining. Solide pour processus back-office. | Moins naturel pour notre architecture produit GCP + Temporal. Risque d'ajouter une stack RPA complète pour un besoin qui peut rester API-first. |
| **12** | **Nanonets Document Extraction / OCR** | **API simple pour POC ou extraction spécialisée** | Extraction Markdown/HTML/JSON/CSV, classification, batch, streaming, custom instructions, orientation developer API. | Moins prouvé pour notre exigence "zero technical hallucination" sur dossiers usine sans benchmark Axolotl. |
| **13** | **IBM Docling / Granite Docling** | **Bon parser open/local, pas plateforme IDP complète** | Conversion PDF vers Markdown/HTML, préservation tables/layout, visualisation, exécution locale possible. Bon anti lock-in. | Demande plus d'assemblage : OCR, confidence, extraction métier, review, scalabilité, monitoring. |
| **14** | **Rossum** | **Pertinent documents business, moins aligné dossiers techniques usine** | Plateforme IDP avec queues, import, extraction, verification UI. Bon sur workflows documentaires business. | Moins ciblé pour plans, dimensions, matériaux, certifications et stack GCP/Temporal. |
| **15** | **Pipeline maison pur PyMuPDF / Tesseract / PaddleOCR / Docling** | **Très bon contrôle, mais trop coûteux pour le POC** | Lock-in minimal, contrôle total, possibilité on-prem/local, optimisable par type documentaire. | Il faut reconstruire nous-mêmes classifier, splitter, extraction, confidence, UI review, monitoring, retraining et SLA. Ce n'est pas le meilleur choix pour livrer vite. |

## Lecture du classement

Pour Axolotl, le point central n'est pas de choisir "le meilleur OCR du monde" de manière abstraite. Le point central est de préserver l'architecture :

```text
provider documentaire interchangeable
-> modèle canonique Factory Writer
-> validation déterministe
-> review par exception
-> facts validés
-> génération context-first via LiteLLM
```

Donc Document AI est acceptable si :

- il ne devient pas la source métier finale ;

- ses résultats sont normalisés dans nos tables ;

- ses erreurs sont capturées par validation et review ;

- ses corrections sont stockées dans Factory Writer ;

- une autre implémentation du port peut produire les mêmes `TechnicalFactCandidate`.

La meilleure posture POC/prod est :

```text
POC :
Google Document AI Enterprise OCR + Custom Extractor Foundation Model
avec modèle canonique interne et validation Python.

Prod cible :
même architecture, mais adapter documentaire interchangeable.
On peut comparer Google, Azure, AWS, LandingAI, Mistral, ABBYY ou Docling
sur un dataset Axolotl figé avant de changer de fournisseur.
```

## Sources consultées pour le classement

Les sources ci-dessous combinent documentation officielle, benchmarks académiques/ouverts et comparatifs secondaires. Les comparatifs secondaires ne sont pas pris comme vérité absolue : ils servent surtout à repérer les tendances et les points à benchmarker sur un dataset Axolotl.

### Documentation officielle produit

- [Client Request](../CLIENT_REQUEST.md)
- [Google Document AI overview](https://docs.cloud.google.com/document-ai/docs/overview)
- [Google Enterprise Document OCR](https://docs.cloud.google.com/document-ai/docs/enterprise-document-ocr)
- [Google Custom Extractor overview](https://docs.cloud.google.com/document-ai/docs/custom-extractor-overview)
- [Google Custom Extractor with generative AI](https://docs.cloud.google.com/document-ai/docs/ce-with-genai)
- [Google Custom Extractor mechanisms](https://docs.cloud.google.com/document-ai/docs/ce-mechanisms)
- [Google Custom Classifier](https://docs.cloud.google.com/document-ai/docs/custom-classifier)
- [Google Custom Splitter](https://docs.cloud.google.com/document-ai/docs/custom-splitter)
- [Google Layout Parser / chunking for RAG](https://cloud.google.com/document-ai/docs/layout-parse-chunk)
- [Google Vertex AI Search parse and chunk documents](https://docs.cloud.google.com/generative-ai-app-builder/docs/parse-chunk-documents)
- [Google Manage processor versions](https://docs.cloud.google.com/document-ai/docs/manage-processor-versions)
- [Google Train and evaluate processors](https://docs.cloud.google.com/document-ai/docs/training-overview)
- [Azure AI Document Intelligence overview](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/overview?view=doc-intel-4.0.0)
- [Azure custom document models](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/train/custom-model?view=doc-intel-4.0.0)
- [Azure custom classifier](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept-custom-classifier?view=doc-intel-4.0.0)
- [Azure Document Processing Models](https://learn.microsoft.com/en-us/azure/applied-ai-services/form-recognizer/concept-model-overview)
- [Azure AI Content Understanding](https://azure.microsoft.com/en-us/products/ai-services/ai-content-understanding)
- [Azure Content Understanding grounding and confidence](https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/document/enrichments)
- [Amazon Textract overview](https://docs.aws.amazon.com/textract/latest/dg/what-is.html)
- [Amazon Textract AnalyzeDocument](https://docs.aws.amazon.com/textract/latest/dg/API_AnalyzeDocument.html)
- [Amazon Textract response objects](https://docs.aws.amazon.com/textract/latest/dg/how-it-works-document-layout.html)
- [Amazon Textract Custom Queries / adapters](https://docs.aws.amazon.com/textract/latest/dg/textract-adapters-tutorial.html)
- [Amazon Textract customizing queries responses](https://docs.aws.amazon.com/en_us/textract/latest/dg/textract-using-adapters.html)
- [Amazon Textract adapter best practices](https://docs.aws.amazon.com/textract/latest/dg/best-practices-adapters.html)
- [Amazon Bedrock Data Automation](https://docs.aws.amazon.com/bedrock/latest/userguide/bda.html)
- [Mistral Document AI OCR](https://docs.mistral.ai/capabilities/document_ai/basic_ocr/)
- [Mistral OCR API endpoint](https://docs.mistral.ai/api/endpoint/ocr)
- [Mistral structured extraction via annotations](https://docs.mistral.ai/cookbook/mistral-ocr-data_extraction)
- [LandingAI ADE Extract Data](https://docs.landing.ai/ade/ade-extract)
- [LandingAI ADE changelog confidence scores](https://docs.landing.ai/ade/ade-changelog)
- [LlamaParse / LlamaCloud documentation](https://developers.llamaindex.ai/llamaparse/)
- [Unstructured partitioning](https://docs.unstructured.io/open-source/core-functionality/partitioning)
- [Unstructured enriching](https://docs.unstructured.io/ui/enriching/overview)
- [IBM Granite Docling](https://www.ibm.com/granite/docs/models/docling)
- [ABBYY documentation](https://docs.abbyy.com/home)
- [ABBYY Vantage classification](https://support.abbyy.com/hc/en-us/articles/25740652323731-How-does-Vantage-classify-documents)
- [UiPath Document Understanding](https://docs.uipath.com/document-understanding/automation-suite/2023.10/classic-user-guide/introduction)
- [Nanonets Document Extraction API](https://enterprise.nanonets.com/docs)
- [OpenAI file inputs](https://developers.openai.com/api/docs/guides/file-inputs)
- [OpenAI vision](https://developers.openai.com/api/docs/guides/images-vision)
- [OpenAI Structured Outputs](https://openai.com/index/introducing-structured-outputs-in-the-api/)
- [OpenAI Vision fine-tuning](https://platform.openai.com/docs/guides/vision-fine-tuning)
- [Anthropic PDF support](https://docs.anthropic.com/en/docs/build-with-claude/pdf-support)
- [Anthropic citations](https://www.anthropic.com/news/introducing-citations-api)
- [Anthropic API citations release notes](https://docs.anthropic.com/en/release-notes/api)
- [Rossum document import specification](https://developers.rossum.ai/docs/document-import-specification)

### Benchmarks et travaux techniques

- [DocVQA Benchmark](https://www.docvqa.org/)
- [OCRBench](https://github.com/Yuliang-Liu/MultimodalOCR)
- [OmniDocBench](https://arxiv.org/abs/2412.07626)
- [ParseBench](https://arxiv.org/abs/2604.08538)
- [IDP Leaderboard OCR benchmark](https://idp-leaderboard.org/ocr-benchmark)
- [IDP Leaderboard table extraction benchmark](https://idp-leaderboard.org/table-extraction-benchmark/)
- [LandingAI DocVQA benchmark](https://landing.ai/blog/answer-99-15-of-docvqa-without-images-in-qa-agentic-document-extraction)
- [LandingAI ADE DocVQA benchmark gallery](https://landing-ai.github.io/ade-docvqa-benchmark/gallery.html)
- [ExtractBench: structured PDF-to-JSON extraction](https://arxiv.org/abs/2602.12247)
- [DTBench: Document-to-Table Extraction](https://arxiv.org/abs/2602.13812)
- [OCR-Reasoning Benchmark](https://arxiv.org/abs/2505.17163)
- [MMDocRAG benchmark](https://arxiv.org/abs/2505.16470)
- [MMLongBench-Doc](https://proceedings.neurips.cc/paper_files/paper/2024/file/ae0e43289bffea0c1fa34633fc608e92-Paper-Datasets_and_Benchmarks_Track.pdf)
- [DesignQA engineering documentation benchmark](https://arxiv.org/abs/2404.07917)
- [Image2Struct benchmark](https://papers.neurips.cc/paper_files/paper/2024/file/d0718553fd6b227a353c6432cf893285-Paper-Datasets_and_Benchmarks_Track.pdf)
- [DUE: End-to-End Document Understanding](https://datasets-benchmarks-proceedings.neurips.cc/paper_files/paper/2021/file/069059b7ef840f0c74a814ec9237b6ec-Paper-round2.pdf)
- [Docling technical report / model documentation](https://www.ibm.com/granite/docs/models/docling)
- [PP-DocLayout](https://arxiv.org/abs/2503.17213)
- [PreP-OCR](https://arxiv.org/abs/2505.20429)
- [OCR-Quality dataset](https://arxiv.org/abs/2510.21774)

### Comparatifs secondaires et retours marché

- [Awesome Agents document understanding comparison](https://awesomeagents.ai/capabilities/document-understanding/)
- [Awesome Agents AI PDF tools 2026](https://awesomeagents.ai/tools/best-ai-pdf-tools-2026/)
- [Snowflake engineering: enterprise-scale Document AI](https://www.snowflake.com/en/engineering-blog/enterprise-scale-document-ai/)
- [AI Multiple OCR benchmark](https://aimultiple.com/lazarus-ai)
- [DigiParser OCR accuracy by document type](https://www.digiparser.com/statistics/ocr-accuracy-by-document-type)
- [OCR accuracy benchmark PDF comparison](https://www.pdf-to-excel.com/articles/pdfs/financial-ocr-solutions-comparison.pdf)
- [Planet AI OCR benchmark whitepaper](https://planet-ai.com/wp-content/uploads/2025/03/Update-Whitepaper_OCR-Benchmark_PLANET-AI_EN_final.pdf)
- [Chandra OCR benchmark](https://skywork.ai/blog/sheets/chandra-ocr-benchmark/)
- [DocAI Fabric benchmark arena](https://www.docaifabric.com/benchmarks/)
- [Microsoft Research Document AI](https://www.microsoft.com/en-us/research/project/document-ai/)
