# Masterclass 2026 : Constraint Engines & Stylistic RAG
*L'état de l'art de l'Intelligence Artificielle Générative d'Entreprise dans la Silicon Valley.*

Face à l'adoption massive de l'IA (LLMs) dans l'écosystème B2B, l'année 2026 a marqué un tournant fondamental. L'ingénierie des prompts empirique (Prompt Engineering) a été officiellement remplacée par des **Guardrails Architecturaux**.

Les architectures de type *Logic Firewall* s'appuient sur un standard industriel strict en **7 Familles de Contraintes**. 

---

## 1. La Taxonomie des 7 Piliers (Standard Silicon Valley 2026)

**Légende** :
**✅** = couvert nativement ou très clairement dans la doc
**◐** = couvert partiellement / via intégration / surtout par customisation
**—** = pas de solution directe documentée pour ce point, ou hors périmètre principal du produit

| Famille | Explication simple | Ce que ça couvre en pratique | Où on l’applique en général | Portkey | LiteLLM | Google Document AI |
| --- | --- | --- | --- | --- | --- | --- |
| **1. Safety / misuse** | Empêcher que le modèle produise, facilite ou amplifie des contenus dangereux ou nuisibles. | Hate, harassment, sexual content, dangerous content, aide à des usages risqués, manipulation nuisible. | **Avant et pendant la génération** : filtres d’entrée, safety settings du modèle, blocage de certaines sorties, politiques d’usage. | **✅** Guardrails d’entrée/sortie, PII redaction, checks custom et guardrails partenaires. | **✅** Guardrails proxy, prompt injection detection, PII masking, fournisseurs de guardrails et policy flows. | **—** Produit centré sur l’extraction/classification documentaire ; pas de couche de modération safety généraliste documentée. |
| **2. Security / abuse resistance** | Protéger le système contre les attaques ou détournements. | Prompt injection, jailbreak, exfiltration de secrets, insecure output handling, plugins/outils dangereux, supply chain, model DoS. | **Autour du modèle et des agents** : passerelles de sécurité, validation des entrées/sorties, sandboxing, contrôle des outils, IAM, isolation, journalisation. | **✅** RBAC, audit logs, enterprise security/compliance, prompt-security et guardrails de sécurité. | **✅** Prompt injection detection, custom code guardrails, RBAC, OIDC/JWT, audit logs et contrôle d’accès. | **◐** Bonne sécurité cloud/documentaire (Access Transparency, CMEK, audit logs), mais pas une couche de sécurité LLM/agent type gateway. |
| **3. Reliability / operations** | Faire en sorte que le service fonctionne de manière stable, prévisible et exploitable en production. | SLA, latence, disponibilité, retries, timeouts, backpressure, quotas, autoscaling, capacité réservée, monitoring, incident response. | **Dans l’architecture runtime** : API, orchestration, queues, Cloud Run/Kubernetes, observabilité, capacity planning. | **✅** Load balancing, fallbacks, retries, observabilité et monitoring pour SLA. | **✅** Routing/load balancing/fallbacks, budgets/rate limits, spend tracking, logs/metrics/observability. | **✅** Quotas, service tiers provisioned/best effort, batch/long-running ops, erreurs et human review dans les workflows documentaires. |
| **4. Privacy / data governance** | Protéger les données et encadrer leur cycle de vie. | PII, secrets, credentials, minimisation de données, rétention, résidence des données, accès, chiffrement, masquage. | **Avant, pendant et après** : prétraitement des prompts, redaction/masking, choix des régions, contrôles d’accès, logs, stockage, grounding. | **✅** PII redaction native, isolation entreprise, chiffrement, rétention configurable, conformité. | **◐** PII masking, secret managers, audit logs, et les logs n’enregistrent pas le contenu par défaut ; la gouvernance dépend beaucoup de la config. | **✅** CMEK, audit logs, Access Transparency / Approval, sécurité et conformité Google Cloud. |
| **5. Behavior / alignment / style** | Encadrer la manière dont le modèle se comporte, répond et représente la marque. | Ton, rôle, vouvoiement/tutoiement, style de marque, degré d’autonomie, respect des instructions, refus appropriés. | **Dans la couche de pilotage du modèle** : system instructions, policies produit, Constitution/Model Spec, brand guides, filtres sur la sortie. | **◐** Prompt Library, Prompt Partials, versioning, Prompt API et observability (sans être un véritable moteur d’alignement). | **◐** Possible via custom guardrails / policy flows / structured outputs, mais pas de couche native forte de brand-style management. | **—** Les mécanismes documentés pilotent surtout le schéma et l’extraction documentaire ; pas de couche de style de marque conversationnel documentée. |
| **6. Assurance / evaluation / validation** | Vérifier que le système fait bien ce qu’il est censé faire, de façon testable. | Benchmarks, evals, rubrics, validation JSON/schema, règles métier, hallucination checks, tool-use quality, regression testing. | **Avant mise en prod et en continu** : CI/CD, campagnes d’évaluation, jeux de tests, validateurs déterministes, monitoring qualité. | **✅** JSON Schema Validator, output guardrails, batch evals et prompt observability. | **◐** Structured outputs + validation de schéma + intégrations d’observabilité/éval (pas de service d’évaluation natif complet). | **✅** Évaluation de ProcessorVersion, datasets d’évaluation, human review et versions de processeurs. |
| **7. Governance / transparency / accountability / compliance** | Définir qui décide, qui rend des comptes, quelles règles s’appliquent et comment. | Documentation, model cards, audits, approbations, ownership, conformité interne/réglementaire, gestion des incidents, traçabilité des décisions. | **Au niveau organisationnel** : comité IA, risk review, documentation, contrôle interne, processus de changement, conformité juridique. | **✅** RBAC, SSO, audit logs, règles d’accès, metadata enforcement, conformité entreprise. | **✅** RBAC, OIDC/JWT, audit logs, budgets/rate limits, multi-tenant controls et SSO/SAML en Enterprise. | **✅** Audit logging, conformité Google Cloud, Access Transparency / Approval, CMEK et IAM autour des processeurs. |

---

## 2. Implémentation Architecturale dans "Factory Writer"

Voici l'analyse profonde de la façon dont ces 7 familles sont techniquement couvertes par notre architecture chez **THE OUTDOOR AXOLOTL**, prouvant à l'organisation que l'application est "Enterprise-Grade".

### 1. Safety / misuse (Prévention d'usage inapproprié)
- **Objectif** : Interdire à l'IA de générer des discours publicitaires illégaux (ex: Greenwashing).
- **Application Factory Writer** : À travers les **Style Rules**, nous filtrons non seulement le lexique, mais nous imposons une stricte `eco_compliance_rule`. L'IA n'a pas l'autorisation d'employer les mots "100% Écologique" sans preuve. Si elle dévie, la génération est classée comme `REVIEW_REQUIRED` dans le workflow Temporal.

### 2. Security / abuse resistance (Résistance aux abus)
- **Objectif** : Empêcher un acteur malveillant de corrompre le texte généré (Prompt Injection).
- **Application Factory Writer** : Contrairement aux chatbots ouverts, Factory Writer est un **Pipeline fermé** déclenché par un upload de fichier. L'utilisateur final (client e-commerce) ne tape pas de prompt. Du côté de l'administration, les inputs des employés passent par **LiteLLM** configuré pour le filtrage strict des System Prompts.  

### 3. Reliability / operations (Opérations et Fiabilité Mathématique)
- **Objectif** : Zéro crash, 100% de disponibilité des fiches générées, conformes au CMS.
- **Application Factory Writer** : 
  1. L'utilisation magistrale de **Temporal Cloud**. En cas de timeout serveur ou d'échec de génération, Temporal gère le retry asynchrone sans perdre l'état du backend.
  2. L'usage exclusif de **Structured Outputs (Pydantic)**. Le LLM ne retourne jamais de texte libre, il est compressé dans un JSON Schema strict (ex: `{"intro": "...", "seo": "..."}`). L'interface Next.js ne plante jamais car le contrat d'interface est garanti mathématiquement.

### 4. Privacy / data governance (Confidentialité des Données)
- **Objectif** : Ne jamais révéler les secrets industriels contenus dans les dossiers usines.
- **Application Factory Writer** : L'ingestion initiale par Google **Document AI** et le **Pre-flight**. Les PDF des fournisseurs contiennent des noms de sous-traitants, des prix de revient (BOM) et la marge brute de The Outdoor Axolotl. Le système extrait uniquement les données "Publiques" vers le Canonical Fact Store. Le LLM de génération (le Cerveau) *ne voit jamais* le PDF d'origine. La donnée sensible s'arrête à la frontière de l'ingestion.

### 5. Behavior / alignment / style (Alignement comportemental)
- **Objectif** : Le fameux garde-fou contre le "Generic Drift".
- **Application Factory Writer** : Le **Stylistic RAG** incarné par notre séparation `TARGET_TONE` et nos `STYLE_RULES`. Sophie configure le Vouvoiement, la bienveillance et le lexique botanique dans une base de données SQL. Le LLM respecte aveuglément ces traits de personnalité imposés sans jamais déroger à l'identité visuelle de la marque.

### 6. Assurance / evals / validation (Assurance qualité et Évaluations)
- **Objectif** : Appliquer le *Zero-Hallucination* et certifier le discours.
- **Application Factory Writer** : 
  1. Le **Split-Screen Human-in-the-Loop** en front-end (Next.js) qui permet à un humain d'approuver formellement une tâche d'attente laissée par Temporal.
  2. L'architecture de **Locked Technical Renderer** : Le LLM n'écrit pas les dimensions. Le produit affiche les dimensions tirées directement du Truth Store. Interdire à l'IA de toucher à la "Tech" est la forme la plus aboutie de Validation en 2026.

### 7. Governance / transparency / accountability (Traçabilité)
- **Objectif** : Savoir précisément "Pourquoi l'IA a écrit ça, et de quel PDF elle l'a sorti ?" (Explainability).
- **Application Factory Writer** : La modélisation de la table `evidence_store`. À chaque "fact" (ex: "Acier Galvanisé") retenu par l'IA, le système garde un pointeur exact (BBOX - Bounding Box) vers la coordonnée spatiale du scan usine d'origine. En cas de contrôle juridique (Accountability), la marque clique sur la caractéristique et voit exactement la ligne surlignée du PDF du fournisseur d'origine. Les historiques d'exécution de Temporal garantissent par ailleurs l'auditabilité à 100% du pipeline.
