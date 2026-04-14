# Guide complet — Everything Claude Code (ECC) v1.9.0

## Table des matières

**Référence**
- [Tableau complet — Commandes & Skills](#tableau-complet--commandes--skills)
- [Agents spécialisés (38)](#agents-spécialisés-38)
- [Skills (156)](#skills-156)
- [Hooks automatiques (22)](#hooks-automatiques-22)
- [Règles (89)](#règles-89)
- [Commandes slash (72 documentés sur 156)](#commandes-slash-72-documentés-sur-156)
- [Serveurs MCP](#serveurs-mcp)

**Architecture & concepts fondamentaux**
- [C'est quoi le harness ?](#cest-quoi-le-harness-)
- [Sessions, agents et contexte — comment ça marche vraiment](#sessions-agents-et-contexte--comment-ça-marche-vraiment)
- [Gestion du contexte — /compact, /fork et budget](#gestion-du-contexte--compact-fork-et-budget)
- [CLAUDE.md — la mémoire permanente de Claude](#claudemd--la-mémoire-permanente-de-claude)
- [La mémoire persistante — auto-memory et MEMORY.md](#la-mémoire-persistante--auto-memory-et-memorymd)
- [Les règles — instructions permanentes](#les-règles--instructions-permanentes)
- [Les hooks — automatisations sur événements](#les-hooks--automatisations-sur-événements)
- [Les MCPs — outils externes intégrés dans Claude](#les-mcps--outils-externes-intégrés-dans-claude)
- [Permissions et settings.json — contrôle fin des autorisations](#permissions-et-settingsjson--contrôle-fin-des-autorisations)
- [Plan Mode — planifier avant d'agir](#plan-mode--planifier-avant-dagir)
- [Mode non-interactif — scripts, CI/CD et automatisations](#mode-non-interactif--scripts-cicd-et-automatisations)
- [Extended Thinking — niveaux d'effort](#extended-thinking--niveaux-deffort)
- [Créer ses propres skills, commandes et agents](#créer-ses-propres-skills-commandes-et-agents)

**Installation & maintenance**
- [Installation](#installation)
- [Mise à jour et maintenance d'ECC](#mise-à-jour-et-maintenance-decc)

**Workflows & usage avancé**
- [Boucles autonomes](#boucles-autonomes)
- [Workflows multi-modèles (CCG)](#workflows-multi-modèles-ccg)
- [Système d'instincts](#système-dinstincts)
- [Workflow quotidien](#workflow-quotidien)
- [Delegation](#delegation)
- [Gestion des sessions](#gestion-des-sessions)
- [Santa Loop — revue adversariale convergente](#santa-loop--revue-adversariale-convergente)
- [Codemaps — documentation d'architecture pour Claude](#codemaps--documentation-darchitecture-pour-claude)
- [Le workflow PRP](#le-workflow-prp)

**Référence & diagnostic**
- [Variables d'environnement clés](#variables-denvironnement-clés)
- [Debugging — quand Claude fait n'importe quoi](#debugging--quand-claude-fait-nimporte-quoi)
- [Optimisation des coûts](#optimisation-des-coûts)
- [Exemples de sessions typiques](#exemples-de-sessions-typiques)
- [Ressources](#ressources)

---

**Everything Claude Code** est un système d'optimisation pour Claude Code composé de :

- **72 commandes slash** — invocables via `/commande`. Claude peut les auto-déclencher si elles ont une `description` (52/72). 20 n'en ont pas → manuel uniquement
- **156 skills** — invocables via `/commande`. Claude peut les auto-déclencher via leur `description` — 3 ont des instructions `TRIGGER when` explicites (`blueprint`, `prompt-optimizer`, `token-budget-advisor`), les 153 autres s'appuient sur la description seule
- **38 agents spécialisés** — sous-processus autonomes délégués par Claude
- **89 règles** — best practices par langage appliquées automatiquement
- **16 hooks** — automatisations déclenchées sur des événements (edit, shell, session…)
- **6 serveurs MCP actifs** + **30+ serveurs optionnels** — outils externes intégrés directement dans Claude

---

## Tableau complet — Commandes & Skills

> Données extraites directement des fichiers sources ECC v1.9.0.
> **Claude auto-déclenche ?** : ✅ = `TRIGGER when` explicite · 🟡 = description présente, Claude infère · ❌ = pas de description · 🔒 = `disable-model-invocation: true` · 👤 = `user-invocable: false` (Claude-only, caché du `/`)

### Commandes slash (72)

| Commande | Description | Toi via `/` | Claude auto-déclenche | Legacy |
| -------- | ----------- | ----------- | --------------------- | ------ |
| `aside` | Pause conversationnelle pure (pas de sous-session) — Claude gèle mentalement la tâche, répond en lecture seule, puis reprend automatiquement. La question et la réponse consomment du contexte normalement. | Oui | 🟡 Possible | — |
| `build-fix` | Correction incrémentale des erreurs de build et de types — détecte automatiquement le build system (npm, tsc, Cargo, Maven, Go, Python…) | Oui | ❌ Non | — |
| `checkpoint` | Points de sauvegarde nommés dans le code — `create` fige l'état git actuel avec un nom, `verify` compare l'état actuel à ce point (fichiers modifiés, tests, couverture), `list` liste tous les checkpoints | Oui | ❌ Non | — |
| `claw` | Alias de compatibilité legacy → redirige vers le skill `nanoclaw-repl`. Ignorez-le si vous n'avez pas l'habitude de `/claw` — utilisez directement `nanoclaw-repl` | Oui | 🟡 Possible | ⚠️ Oui |
| `code-review` | Revue de code en 2 modes : **local** (analyse les fichiers modifiés non commités — sécurité, qualité, bonnes pratiques) ou **PR GitHub** (`/code-review 42` ou URL) — lit le diff complet, exécute les validations (lint, tests, build), poste la revue sur GitHub avec décision APPROVE / REQUEST CHANGES / BLOCK | Oui | 🟡 Possible | — |
| `context-budget` | Alias legacy → skill `context-budget`. Audite la consommation de tokens de la session (agents, skills, règles, MCP) et produit un rapport priorisé des économies possibles — utile quand la session ralentit ou qu'on veut savoir combien de contexte il reste | Oui | 🟡 Possible | ⚠️ Oui |
| `cpp-build` | Correction incrémentale des erreurs de build C++, CMake et linker | Oui | 🟡 Possible | — |
| `cpp-review` | Revue C++ complète — memory safety, idiomes modernes, concurrence | Oui | 🟡 Possible | — |
| `cpp-test` | Workflow TDD C++ — écrire les tests GoogleTest d'abord, implémenter ensuite | Oui | 🟡 Possible | — |
| `devfleet` | Shim vers le skill `claude-devfleet` | Oui | 🟡 Possible | ⚠️ Oui |
| `docs` | Shim vers le skill `documentation-lookup` | Oui | 🟡 Possible | ⚠️ Oui |
| `e2e` | Shim vers le skill `e2e-testing` | Oui | 🟡 Possible | ⚠️ Oui |
| `eval` | Shim vers le skill `eval-harness` | Oui | 🟡 Possible | ⚠️ Oui |
| `evolve` | Regroupe les instincts accumulés par thème et propose de les consolider en commandes, skills ou agents ECC — `/evolve` suggère uniquement, `/evolve --generate` écrit les fichiers | Oui | 🟡 Possible | — |
| `flutter-build` | Correction incrémentale des erreurs Dart analyzer et Flutter | Oui | 🟡 Possible | — |
| `flutter-review` | Revue Flutter/Dart — patterns idiomatiques, widgets, state management, performance, accessibilité et sécurité | Oui | 🟡 Possible | — |
| `flutter-test` | Exécute les tests Flutter/Dart, remonte les échecs et corrige incrementalement | Oui | 🟡 Possible | — |
| `gan-build` | **GAN** (Generative Adversarial Network) appliqué au code : concept ML où un Générateur et un Évaluateur s'affrontent en boucle jusqu'à atteindre un seuil de qualité. Ici : 3 phases — **1)** Planificateur génère `spec.md` + `eval-rubric.md` depuis ton brief **2)** Boucle Générateur/Évaluateur : le Générateur construit l'app, l'Évaluateur la teste (Playwright/screenshot/code), note sur rubrique et écrit son feedback → le Générateur lit ce feedback et améliore — s'arrête si score ≥ `--pass-threshold` (défaut 7.0), plateau détecté, ou `--max-iterations` atteint (défaut 15) **3)** Rapport final avec progression des scores itération par itération | Oui | ❌ Non | — |
| `gan-design` | Même boucle GAN mais sans planificateur (le brief est la spec) — uniquement Générateur + Évaluateur, rubrique orientée qualité UI/UX avec poids fort sur l'originalité visuelle (`--pass-threshold` défaut 7.5) | Oui | ❌ Non | — |
| `go-build` | Correction incrémentale des erreurs `go build`, `go vet` et linter | Oui | 🟡 Possible | — |
| `go-review` | Revue Go complète — patterns idiomatiques, sécurité de la concurrence, gestion d'erreurs et sécurité | Oui | 🟡 Possible | — |
| `go-test` | Workflow TDD Go — table-driven tests d'abord, implémentation ensuite | Oui | 🟡 Possible | — |
| `gradle-build` | Correction des erreurs Gradle pour projets Android et KMP | Oui | 🟡 Possible | — |
| `harness-audit` | Diagnostic déterministe de ta configuration ECC — exécute un script fixe et note 7 catégories sur 10 (Tool Coverage, Context Efficiency, Quality Gates, Memory Persistence, Eval Coverage, Security Guardrails, Cost Efficiency) pour un score total /70, avec les 3 actions prioritaires à corriger. Score reproductible au même commit. | Oui | ❌ Non | — |
| `instinct-export` | Exporte les instincts (portée projet ou globale) vers un fichier | Oui | 🟡 Possible | — |
| `instinct-import` | Importe des instincts depuis un fichier ou une URL | Oui | 🟡 Possible | — |
| `instinct-status` | Affiche les instincts appris (projet + globaux) avec leur score de confiance | Oui | 🟡 Possible | — |
| `jira` | Récupère un ticket Jira, analyse les exigences, met à jour le statut ou ajoute des commentaires | Oui | 🟡 Possible | — |
| `kotlin-build` | Correction incrémentale des erreurs Kotlin/Gradle, warnings compilateur et dépendances | Oui | 🟡 Possible | — |
| `kotlin-review` | Revue Kotlin complète — patterns idiomatiques, null safety, sécurité des coroutines et sécurité | Oui | 🟡 Possible | — |
| `kotlin-test` | Workflow TDD Kotlin — tests Kotest d'abord, implémentation ensuite | Oui | 🟡 Possible | — |
| `learn` | Analyse la session et extrait les patterns non-triviaux (résolutions d'erreurs, techniques de debug, workarounds, patterns projet) pour les sauvegarder comme skills dans `~/.claude/skills/learned/` — demande confirmation avant de sauvegarder | Oui | ❌ Non | — |
| `learn-eval` | Version renforcée de `/learn` : extrait les patterns puis applique une checklist (vérifie les doublons, décide portée globale/projet) et un verdict holistic — **Save** / **Improve then Save** / **Absorb into [X]** (fusionne avec un skill existant) / **Drop** (abandonne si trivial ou redondant). Préférer `/learn-eval` à `/learn` pour éviter de polluer les skills. | **Non** | 👤 Claude-only | — |
| `loop-start` | Lance Claude en mode autonome sur un pattern de boucle : **sequential** (tâches en séquence), **continuous-pr** (implémente + PR en boucle), **rfc-dag** (graphe de dépendances RFC), **infinite** (surveille et améliore sans fin) — mode `safe` (défaut) avec quality gates stricts, mode `fast` pour aller plus vite | Oui | ❌ Non | — |
| `loop-status` | Inspecte l'état d'une boucle active — phase courante, checkpoints, échecs, dérive coût/temps et intervention recommandée | Oui | ❌ Non | — |
| `model-route` | Recommande le meilleur modèle (haiku/sonnet/opus) pour la tâche selon sa complexité et le budget | Oui | ❌ Non | — |
| `multi-backend` | ⚠️ Requiert `codeagent-wrapper` externe (Codex + Gemini). Claude orchestre 6 phases backend : Research (analyse codebase) → Ideation (Codex propose 2+ solutions) → Plan (Codex architecture, sauvegardé dans `.claude/plan/`) → Execute (Claude implémente) → Optimize (Codex revue du diff) → Review (vérification finale + tests). Seul Claude écrit les fichiers. | Oui | ❌ Non | — |
| `multi-execute` | Exécution collaborative multi-modèles — prototype Codex/Gemini refactoré en code production par Claude | Oui | ❌ Non | — |
| `multi-frontend` | Workflow frontend multi-modèles Gemini-led — 6 phases : Research → Ideation → Plan → Execute → Optimize → Review | Oui | ❌ Non | — |
| `multi-plan` | Planification collaborative multi-modèles — analyse contextuelle + double modèle → plan step-by-step (lecture seule, jamais de code prod) | Oui | ❌ Non | — |
| `multi-workflow` | Workflow de développement complet avec routing intelligent : frontend→Gemini, backend→Codex, orchestration→Claude | Oui | ❌ Non | — |
| `orchestrate` | Shim vers `dmux-workflows` et `autonomous-agent-harness` | Oui | 🟡 Possible | ⚠️ Oui |
| `plan` | Reformule les exigences, évalue les risques et crée un plan d'implémentation step-by-step — ATTEND la confirmation utilisateur avant de toucher au code | Oui | 🟡 Possible | — |
| `pm2` | Analyse le projet et génère automatiquement les configs et commandes PM2 pour tous les services détectés | Oui | ❌ Non | — |
| `projects` | Tableau de bord du système d'instincts — liste tous les projets observés avec pour chacun : instincts personnels, instincts hérités (globaux), nombre d'observations capturées et date de dernière activité | Oui | 🟡 Possible | — |
| `promote` | Promeut des instincts de portée projet vers la portée globale | Oui | 🟡 Possible | — |
| `prompt-optimize` | Shim vers le skill `prompt-optimizer` | Oui | 🟡 Possible | ⚠️ Oui |
| `prp-commit` | Workflow **PRP** (4/5) — commit intelligent avec ciblage en langage naturel : décris ce que tu veux commiter (`the auth changes`, `except tests`, `only new files`, `*.ts`…), Claude identifie les bons fichiers depuis le diff, les stage et génère un message conventionnel (`feat:` / `fix:` / `refactor:`…) automatiquement | Oui | 🟡 Possible | — |
| `prp-implement` | Workflow **PRP** (3/5) — exécute un plan `.md` en 6 phases : détection du gestionnaire de paquets → chargement du plan → branche git → implémentation tâche par tâche (typecheck après **chaque fichier modifié**, jamais d'état cassé) → validation en 5 niveaux (lint → tests → build → intégration → edge cases) → rapport dans `.claude/PRPs/reports/` | Oui | 🟡 Possible | — |
| `prp-plan` | Workflow **PRP** (2/5) — analyse le codebase pour en extraire patterns et conventions, puis génère un plan auto-suffisant dans `.claude/PRPs/plans/` : tout le contexte pour implémenter sans poser de questions supplémentaires | Oui | 🟡 Possible | — |
| `prp-pr` | Workflow **PRP** (5/5) — crée une PR GitHub depuis la branche courante avec les commits non poussés | Oui | 🟡 Possible | — |
| `prp-prd` | Workflow **PRP** (1/5, optionnel) — générateur interactif de PRD (Product Requirements Document) : centré sur le problème, spec pilotée par hypothèses, avec questions de clarification avant de rédiger | Oui | 🟡 Possible | — |
| `prune` | Nettoyage des instincts `pending` générés automatiquement par l'Observer mais jamais validés via `/promote`. Supprime ceux de plus de 30 jours (seuil personnalisable avec `--max-age 60`). `--dry-run` pour prévisualiser sans supprimer. Ne touche jamais aux instincts déjà promus (actifs) | Oui | 🟡 Possible | — |
| `python-review` | Revue Python complète via l'agent `python-reviewer` : lance `ruff`, `mypy`, `black`, `bandit`, `pip-audit`, `pytest --cov` automatiquement, puis revue par sévérité — 🔴 CRITICAL (SQL injection, eval, pickle unsafe, credentials hardcodés → merge bloqué), 🟠 HIGH (type hints manquants, args mutables par défaut, exceptions avalées), 🟡 MEDIUM (PEP 8, print au lieu de logging, f-strings). Vérifications bonus si Django / FastAPI / Flask détecté. ⚠️ S'exécute en **foreground** : Claude est bloqué pendant toute la durée, pas d'interaction possible | Oui | 🟡 Possible | — |
| `quality-gate` | Version manuelle des hooks ECC : détecte le langage (Python → `ruff`/`black`, TypeScript → `eslint`/`prettier`, Go → `gofmt`…), puis lance formatage → lint → type check et produit une liste de corrections. `--fix` applique les corrections automatiques (modifie les fichiers), `--strict` traite les warnings comme des erreurs. Plus rapide et généraliste que `/python-review` — pas de sécurité ni d'analyse intelligente, juste "est-ce que le code passe les checks ?" | Oui | ❌ Non | — |
| `refactor-clean` | Suppression sécurisée du code mort en 6 étapes : détecte avec l'outil adapté (`knip`/`depcheck`/`ts-prune` pour JS/TS, `vulture` Python, `deadcode` Go, `cargo-udeps` Rust) → classe par risque (SAFE / CAUTION / DANGER) → boucle atomique : tests verts → supprime un item → re-run tests → si rouge : `git checkout` immédiat et skip → consolide les doublons (fonctions >80% similaires, re-exports inutiles). Règle absolue : une suppression à la fois, jamais sans tests verts avant | Oui | ❌ Non | — |
| `resume-session` | Charge un fichier de session sauvegardé (`.tmp` dans `~/.claude/session-data/`) et produit un briefing structuré avant de reprendre : état actuel (✅ done / en cours / pas commencé), approches qui ont échoué (ne pas retenter), blockers, prochaine étape exacte. Claude **attend** après le briefing sans toucher au code. Gère les fichiers > 7 jours (avertissement), fichiers référençant des fichiers supprimés, et plusieurs sessions le même jour (charge la plus récente) | Oui | 🟡 Possible | — |
| `rules-distill` | Shim vers le skill `rules-distill` | Oui | 🟡 Possible | ⚠️ Oui |
| `rust-build` | Correction incrémentale des erreurs Rust, borrow checker et dépendances | Oui | 🟡 Possible | — |
| `rust-review` | Revue Rust complète — ownership, lifetimes, gestion d'erreurs, usage d'unsafe | Oui | 🟡 Possible | — |
| `rust-test` | Workflow TDD Rust — tests d'abord, implémentation ensuite | Oui | 🟡 Possible | — |
| `santa-loop` | Revue adversariale convergente : deux reviewers **indépendants** (Reviewer A = Claude Opus, Reviewer B = GPT via Codex CLI / Gemini 2.5 Pro / Claude Opus fallback) tournent **en parallèle** sur la même rubric PASS/FAIL — les deux doivent approuver (NICE) pour pusher. Si l'un échoue (NAUGHTY) : correction des issues flaggées → commit → nouveaux reviewers repartant de zéro (pas d'anchoring bias). Max 3 rounds, sinon escalade manuelle. Ne push jamais en cours de loop | Oui | 🟡 Possible | — |
| `save-session` | Sauvegarde l'état complet de la session dans un fichier horodaté pour reprise future | Oui | 🟡 Possible | — |
| `sessions` | Gère l'historique des sessions Claude Code — liste, charge, crée des aliases et métadonnées | Oui | 🟡 Possible | — |
| `setup-pm` | Configure quel package manager Claude doit utiliser (npm/pnpm/yarn/bun). Détection automatique par priorité : variable `CLAUDE_PACKAGE_MANAGER` → `.claude/package-manager.json` → champ `packageManager` dans `package.json` → lock file présent → config globale `~/.claude/` → fallback pnpm>bun>yarn>npm. `--global` pour tous les projets, `--project` pour ce projet uniquement (versionnable git). ⚠️ `disable-model-invocation: true` — jamais déclenché automatiquement | Oui | 🔒 Non | — |
| `skill-create` | Lit les 200 derniers commits git et en extrait automatiquement les conventions de l'équipe : messages de commit (`feat:`/`fix:`…), fichiers qui changent toujours ensemble, séquences de workflow répétitives, architecture des dossiers, patterns de tests. Produit un `SKILL.md` que Claude utilisera dans les sessions suivantes. `--instincts` génère aussi des instincts pour continuous-learning-v2. Version locale de la Skill Creator GitHub App | Oui | 🟡 Possible | — |
| `skill-health` | Dashboard analytique sur tous les skills : taux de succès quotidien sur 30j (sparklines), patterns d'échecs regroupés (barchart), amendments en attente, historique des versions. `--panel failures` pour n'afficher que les échecs, `--json` pour sortie machine. Si skills en déclin → suggère `/evolve` | Oui | 🟡 Possible | — |
| `tdd` | Shim vers le skill `tdd-workflow` | Oui | 🟡 Possible | ⚠️ Oui |
| `test-coverage` | Analyse la couverture de tests, identifie les fichiers sous 80% et génère les tests manquants pour atteindre le seuil | Oui | ❌ Non | — |
| `update-codemaps` | Génère 5 fichiers token-lean dans `docs/CODEMAPS/` optimisés pour être lus par Claude : `architecture.md` (diagramme système), `backend.md` (routes → service → repo), `frontend.md` (pages, composants, state), `data.md` (tables, relations, migrations), `dependencies.md` (services externes). Format minimaliste < 1000 tokens par fichier. Si diff > 30% par rapport à l'existant → demande confirmation avant d'écraser. Rapport de diff dans `.reports/codemap-diff.txt`. À lancer après chaque feature importante ou refactoring | Oui | ❌ Non | — |
| `update-docs` | Régénère les sections de doc dérivables du code depuis leurs sources de vérité : `package.json` → tableau de scripts, `.env.example` → variables d'env (required/optional/format), `openapi.yaml`/routes → référence API, `Dockerfile` → infra. Met à jour `docs/CONTRIBUTING.md` et `docs/RUNBOOK.md`. Ne touche que les sections `<!-- AUTO-GENERATED -->`, préserve la prose manuelle. Signale les docs > 90 jours non mises à jour | Oui | ❌ Non | — |
| `verify` | Shim vers le skill `verification-loop` | Oui | 🟡 Possible | ⚠️ Oui |

### Skills (156)

| Skill | Description | Toi via `/` | Claude auto-déclenche |
| ----- | ----------- | ----------- | --------------------- |
| `agent-eval` | Comparaison head-to-head d'agents de code (Claude Code, Aider, Codex…) sur des tâches custom — métriques de pass rate, coût, temps et consistance | Oui | 🟡 Possible |
| `agent-harness-construction` | Conception et optimisation des espaces d'action, définitions d'outils et formatage des observations pour maximiser le taux de complétion des agents IA | Oui | 🟡 Possible |
| `agent-payment-x402` | Ajoute la capacité de paiement x402 aux agents IA — budgets par tâche, contrôles de dépenses et wallets non-custodial via MCP. Pour les agents qui doivent payer des APIs, services ou d'autres agents | Oui | 🟡 Possible |
| `agentic-engineering` | Opérer en ingénieur agentique — exécution eval-first, décomposition des tâches et routing cost-aware des modèles selon la complexité | Oui | 🟡 Possible |
| `ai-first-engineering` | Modèle opérationnel pour les équipes où les agents IA génèrent une large part du code de production — pratiques, revues et boucles de feedback adaptées | Oui | 🟡 Possible |
| `ai-regression-testing` | Tests de régression pour le développement IA — tests API en sandbox sans BDD, workflows de bug-check automatisés, et patterns pour détecter les angles morts quand le même modèle écrit et relit le code | Oui | 🟡 Possible |
| `android-clean-architecture` | Clean Architecture pour Android et KMP — structure des modules, règles de dépendances, UseCases, Repositories et patterns de couche data | Oui | 🟡 Possible |
| `api-design` | Patterns de design d'API REST — nommage des ressources, codes de statut, pagination, filtrage, versioning et rate limiting pour APIs de production | Oui | 🟡 Possible |
| `architecture-decision-records` | Capture les décisions architecturales des sessions Claude Code sous forme d'ADRs structurés — auto-détecte les moments de décision, enregistre le contexte, les alternatives considérées et le raisonnement | Oui | 🟡 Possible |
| `article-writing` | Rédige des articles, guides, posts de blog, tutoriels et newsletters en maintenant une voix cohérente dérivée d'exemples fournis ou d'un guide de marque | Oui | 🟡 Possible |
| `autonomous-agent-harness` | Transforme Claude Code en système d'agents entièrement autonome — mémoire persistante, opérations planifiées (crons), task queuing et computer use. Remplace Hermes/AutoGPT en s'appuyant sur les capacités natives de Claude Code | Oui | 🟡 Possible |
| `autonomous-loops` | ⚠️ Déprécié depuis v1.8 — patterns de boucles autonomes de simples pipelines séquentiels aux systèmes DAG multi-agents pilotés par RFC (remplacé par `continuous-agent-loop`) | Oui | 🟡 Possible |
| `backend-patterns` | Patterns d'architecture backend, design d'API, optimisation BDD et bonnes pratiques serveur pour Node.js, Express et les API routes Next.js | Oui | 🟡 Possible |
| `benchmark` | Mesure les baselines de performance, détecte les régressions avant/après PR et compare des alternatives de stack | Oui | 🟡 Possible |
| `blueprint` | Transforme un objectif en une phrase en plan de construction étape par étape pour projets multi-sessions et multi-agents — revue adversariale, graphe de dépendances et détection des étapes parallélisables | Oui | ✅ TRIGGER when |
| `brand-voice` | Construit un profil de voix et de style à partir de vrais posts, essais ou docs, puis réutilise ce profil dans les workflows de contenu, outreach et réseaux sociaux | Oui | 🟡 Possible |
| `browser-qa` | Automatise les tests visuels et la vérification des interactions UI via automation browser après le déploiement de features | Oui | 🟡 Possible |
| `bun-runtime` | Bun en tant que runtime, package manager, bundler et test runner — quand choisir Bun vs Node, notes de migration et support Vercel | Oui | 🟡 Possible |
| `canary-watch` | Surveille une URL déployée pour détecter des régressions après déploiements, merges ou mises à jour de dépendances | Oui | 🟡 Possible |
| `carrier-relationship-management` | Expertise codifiée pour la gestion des relations transporteurs (supply chain) — évaluations de performance, escalades et négociations contractuelles | Oui | 🟡 Possible |
| `ck` | Mémoire persistante par projet pour Claude Code — charge automatiquement le contexte au démarrage de session, traque l'activité git et écrit en mémoire native. Comportement déterministe garanti par des scripts Node.js | Oui | 🟡 Possible |
| `claude-api` | Patterns API Anthropic pour Python et TypeScript — Messages API, streaming, tool use, vision, extended thinking, batches, prompt caching et Claude Agent SDK | Oui | 🟡 Possible |
| `claude-devfleet` | Orchestration de tâches multi-agents via Claude DevFleet — planification de projets, dispatch d'agents parallèles en worktrees isolés et suivi de progression | Oui | 🟡 Possible |
| `click-path-audit` | Trace chaque bouton ou point de contact utilisateur à travers sa séquence complète de changements d'état — détecte les bugs où les fonctions fonctionnent individuellement mais s'annulent mutuellement ou laissent l'UI dans un état incohérent | Oui | 🟡 Possible |
| `clickhouse-io` | Patterns ClickHouse, optimisation de requêtes, analytics et data engineering pour charges analytiques haute performance | Oui | 🟡 Possible |
| `codebase-onboarding` | Analyse un codebase inconnu et génère un guide d'onboarding structuré — carte d'architecture, points d'entrée clés, conventions et un CLAUDE.md de démarrage | Oui | 🟡 Possible |
| `coding-standards` | Standards de code universels, bonnes pratiques et patterns pour TypeScript, JavaScript, React et Node.js | Oui | 🟡 Possible |
| `compose-multiplatform-patterns` | Patterns Compose Multiplatform et Jetpack Compose pour KMP — state management, navigation, theming, performance et UI spécifique à chaque plateforme | Oui | 🟡 Possible |
| `configure-ecc` | Installeur interactif pour Everything Claude Code — guide la sélection et l'installation des skills et règles au niveau utilisateur ou projet, vérifie les chemins et optimise les fichiers installés | Oui | 🟡 Possible |
| `connections-optimizer` | Réorganise le réseau X et LinkedIn — élagage review-first, recommandations d'abonnements et outreach warm rédigé dans la vraie voix de l'utilisateur | Oui | 🟡 Possible |
| `content-engine` | Crée des systèmes de contenu natifs pour X, LinkedIn, TikTok, YouTube et newsletters — une source adaptée proprement sur chaque plateforme | Oui | 🟡 Possible |
| `content-hash-cache-pattern` | Met en cache les résultats de traitements coûteux via hachage SHA-256 — indépendant des chemins, auto-invalidant, avec séparation de la couche service | Oui | 🟡 Possible |
| `context-budget` | Audite la consommation de la fenêtre de contexte (agents, skills, MCPs, règles), identifie les composants redondants et produit des recommandations priorisées d'économies de tokens | Oui | 🟡 Possible |
| `continuous-agent-loop` | Patterns de boucles d'agents autonomes continues avec quality gates, evals et contrôles de récupération | Oui | 🟡 Possible |
| `continuous-learning` | Extrait automatiquement les patterns réutilisables des sessions Claude Code et les sauvegarde comme skills appris pour une utilisation future | Oui | 🟡 Possible |
| `continuous-learning-v2` | Système d'apprentissage par instincts — observe les sessions via hooks, crée des instincts atomiques avec scoring de confiance et les fait évoluer en skills/commandes/agents. Les instincts project-scoped (v2.1) évitent la contamination cross-projet | Oui | 🟡 Possible |
| `cost-aware-llm-pipeline` | Patterns d'optimisation des coûts LLM — routing par complexité de tâche, suivi de budget, logique de retry et prompt caching | Oui | 🟡 Possible |
| `cpp-coding-standards` | Standards C++ basés sur les C++ Core Guidelines (isocpp.github.io) pour écrire, revoir ou refactoriser du code C++ moderne, sûr et idiomatique | Oui | 🟡 Possible |
| `cpp-testing` | Écriture, mise à jour et correction de tests C++ avec GoogleTest/CTest — configuration, diagnostic des tests flaky et ajout de coverage/sanitizers | Oui | 🟡 Possible |
| `crosspost` | Distribution de contenu multi-plateforme sur X, LinkedIn, Threads et Bluesky — adapte le contenu à chaque plateforme, jamais de copier-coller identique | Oui | 🟡 Possible |
| `csharp-testing` | Patterns de tests C# et .NET avec xUnit, FluentAssertions, mocking, tests d'intégration et bonnes pratiques d'organisation | Oui | 🟡 Possible |
| `customer-billing-ops` | Opère les workflows de facturation client — abonnements, remboursements, triage churn, récupération via billing portal et analyse de plans via Stripe | Oui | 🟡 Possible |
| `customs-trade-compliance` | Expertise codifiée pour la conformité douanière et commerciale — classification HTS, licences d'exportation, screening des partenaires commerciaux et documentation | Oui | 🟡 Possible |
| `dart-flutter-patterns` | Patterns Dart et Flutter de production — null safety, state management (BLoC, Riverpod, Provider), GoRouter, Dio, Freezed et clean architecture | Oui | 🟡 Possible |
| `data-scraper-agent` | Construit un agent de collecte de données automatisé pour toute source publique — scraping planifié, enrichissement via LLM, stockage dans Notion/Sheets/Supabase. Tourne gratuitement sur GitHub Actions | Oui | 🟡 Possible |
| `database-migrations` | Bonnes pratiques de migrations BDD — changements de schéma, rollbacks et déploiements sans interruption pour PostgreSQL, MySQL et les ORMs courants (Prisma, Drizzle, Django, TypeORM…) | Oui | 🟡 Possible |
| `deep-research` | Recherche approfondie multi-sources via les MCPs firecrawl et exa — synthèse des résultats et rapports cités avec attribution des sources | Oui | 🟡 Possible |
| `deployment-patterns` | Workflows de déploiement, pipelines CI/CD, containerisation Docker, health checks, stratégies de rollback et checklists de production readiness | Oui | 🟡 Possible |
| `design-system` | Génère ou audite des design systems, vérifie la cohérence visuelle et revue les PRs touchant au style | Oui | 🟡 Possible |
| `django-patterns` | Patterns d'architecture Django — REST API avec DRF, ORM, cache, signals, middleware et apps Django de production | Oui | 🟡 Possible |
| `django-security` | Sécurité Django — authentification, autorisation, CSRF, injection SQL, XSS et configurations de déploiement sécurisées | Oui | 🟡 Possible |
| `django-tdd` | Tests Django avec pytest-django, TDD, factory_boy, mocking, coverage et tests d'APIs DRF | Oui | 🟡 Possible |
| `django-verification` | Boucle de vérification Django — migrations, lint, tests avec coverage, scans de sécurité et checks de production readiness avant release ou PR | Oui | 🟡 Possible |
| `dmux-workflows` | Orchestration multi-agents via dmux (gestionnaire de panneaux tmux) — patterns de workflows parallèles pour Claude Code, Codex, OpenCode et autres harnesses | Oui | 🟡 Possible |
| `docker-patterns` | Patterns Docker et Docker Compose — développement local, sécurité des conteneurs, réseaux, stratégies de volumes et orchestration multi-services | Oui | 🟡 Possible |
| `documentation-lookup` | Consulte la documentation à jour des libs et frameworks via Context7 MCP plutôt que les données d'entraînement — s'active pour les questions de setup, références d'API ou dès qu'un framework est mentionné | Oui | 🟡 Possible |
| `dotnet-patterns` | Patterns C# et .NET idiomatiques — conventions, dependency injection, async/await et bonnes pratiques pour des applications .NET robustes | Oui | 🟡 Possible |
| `e2e-testing` | Patterns de tests E2E Playwright — Page Object Model, configuration, intégration CI/CD, gestion des artifacts et stratégies anti-flaky | Oui | 🟡 Possible |
| `energy-procurement` | Expertise codifiée pour le procurement énergétique — évaluation des fournisseurs, négociation des contrats, analyse des marchés spot et couverture des risques prix | Oui | 🟡 Possible |
| `enterprise-agent-ops` | Opère des charges de travail agents longue durée avec observabilité, périmètres de sécurité et gestion du cycle de vie | Oui | 🟡 Possible |
| `eval-harness` | Framework d'évaluation formel pour sessions Claude Code — implémente les principes de l'eval-driven development (EDD) | Oui | 🟡 Possible |
| `exa-search` | Recherche neurale via Exa MCP — web, code, intel d'entreprises et recherche de personnes avec le moteur de recherche IA d'Exa | Oui | 🟡 Possible |
| `fal-ai-media` | Génération de médias unifiée via fal.ai MCP — texte-vers-image (Nano Banana), texte/image-vers-vidéo (Seedance, Kling, Veo 3), TTS (CSM-1B) et vidéo-vers-audio (ThinkSound) | Oui | 🟡 Possible |
| `flutter-dart-code-review` | Checklist de revue Flutter/Dart agnostique aux libs — widgets, state management (BLoC, Riverpod, Provider, GetX, MobX, Signals), idiomes Dart, performance, accessibilité et sécurité | Oui | 🟡 Possible |
| `foundation-models-on-device` | Framework Apple FoundationModels pour LLM on-device iOS 26+ — génération de texte, génération guidée (@Generable), tool calling et snapshot streaming | Oui | 🟡 Possible |
| `frontend-patterns` | Patterns de développement frontend pour React, Next.js, state management, optimisation des performances et bonnes pratiques UI | Oui | 🟡 Possible |
| `frontend-slides` | Crée des présentations HTML riches en animations — de zéro ou depuis des fichiers PowerPoint. Pour construire des slides de talk, pitch ou convertir PPT/PPTX en web | Oui | 🟡 Possible |
| `gan-style-harness` | Harness Generator-Evaluator inspiré des GANs pour construire des applications de haute qualité en autonomie — basé sur le papier de design Anthropic (mars 2026) | Oui | 🟡 Possible |
| `git-workflow` | Patterns git — stratégies de branches, conventions de commit, merge vs rebase, résolution de conflits et bonnes pratiques de collaboration pour équipes de toutes tailles | Oui | 🟡 Possible |
| `golang-patterns` | Patterns Go idiomatiques, bonnes pratiques et conventions pour des applications robustes, efficaces et maintenables | Oui | 🟡 Possible |
| `golang-testing` | Patterns de tests Go — table-driven tests, subtests, benchmarks, fuzzing et couverture. Méthodologie TDD avec pratiques Go idiomatiques | Oui | 🟡 Possible |
| `google-workspace-ops` | Opère sur Google Drive, Docs, Sheets et Slides comme une surface de workflow unifiée — plans, trackers, decks et documents partagés sans descendre aux appels d'outils bruts | Oui | 🟡 Possible |
| `healthcare-cdss-patterns` | Patterns de développement CDSS — vérification d'interactions médicamenteuses, validation de doses, scoring clinique (NEWS2, qSOFA), classification des alertes et intégration dans les workflows EMR | Oui | 🟡 Possible |
| `healthcare-emr-patterns` | Patterns EMR/EHR — sécurité clinique, workflows d'encounter, génération de prescriptions, intégration CDSS et UI accessible pour la saisie médicale | Oui | 🟡 Possible |
| `healthcare-eval-harness` | Harness d'évaluation de sécurité patient — suites de tests automatisées pour la précision CDSS, l'exposition PHI et l'intégrité des workflows cliniques. Bloque les déploiements sur les échecs de sécurité | Oui | 🟡 Possible |
| `healthcare-phi-compliance` | Patterns de conformité PHI/PII — classification des données, contrôles d'accès, audit trails, chiffrement et vecteurs de fuite courants. Couvre HIPAA et la dé-identification | Oui | 🟡 Possible |
| `hexagonal-architecture` | Conception, implémentation et refactoring de systèmes Ports & Adapters — frontières de domaine claires, inversion des dépendances et orchestration de use-cases testables pour TypeScript, Java, Kotlin et Go | Oui | 🟡 Possible |
| `inventory-demand-planning` | Expertise codifiée pour la planification des stocks et de la demande — prévision de la demande, seuils de réapprovisionnement, gestion des ruptures et optimisation des niveaux de stock | Oui | 🟡 Possible |
| `investor-materials` | Crée et met à jour pitch decks, one-pagers, mémos investisseurs, candidatures accélérateurs et modèles financiers — maintient la cohérence interne entre tous les assets de fundraising | Oui | 🟡 Possible |
| `investor-outreach` | Rédige emails cold, warm intro blurbs, relances et update emails pour le fundraising auprès d'angels, VCs, investisseurs stratégiques et accélérateurs | Oui | 🟡 Possible |
| `iterative-retrieval` | Pattern de raffinement progressif du contexte pour résoudre le problème de contexte des sous-agents — récupère exactement ce dont l'agent a besoin sans surcharger la fenêtre | Oui | 🟡 Possible |
| `java-coding-standards` | Standards Java pour services Spring Boot — nommage, immutabilité, usage d'Optional, streams, exceptions, generics et structure de projet | Oui | 🟡 Possible |
| `jira-integration` | Récupération de tickets Jira, analyse des exigences, mise à jour de statut, ajout de commentaires et transition d'issues — via MCP ou appels REST directs | Oui | 🟡 Possible |
| `jpa-patterns` | Patterns JPA/Hibernate pour Spring Boot — design d'entités, relations, optimisation de requêtes, transactions, auditing, indexation, pagination et connection pooling | Oui | 🟡 Possible |
| `kotlin-coroutines-flows` | Patterns Kotlin Coroutines et Flow pour Android et KMP — concurrence structurée, opérateurs Flow, StateFlow, gestion d'erreurs et tests | Oui | 🟡 Possible |
| `kotlin-exposed-patterns` | Patterns ORM JetBrains Exposed — requêtes DSL, DAO pattern, transactions, HikariCP, migrations Flyway et repository pattern | Oui | 🟡 Possible |
| `kotlin-ktor-patterns` | Patterns serveur Ktor — routing DSL, plugins, authentification, Koin DI, kotlinx.serialization, WebSockets et testing avec testApplication | Oui | 🟡 Possible |
| `kotlin-patterns` | Patterns Kotlin idiomatiques — coroutines, null safety, DSL builders et bonnes pratiques pour des applications robustes et maintenables | Oui | 🟡 Possible |
| `kotlin-testing` | Patterns de tests Kotlin avec Kotest, MockK, tests de coroutines, property-based testing et coverage Kover — méthodologie TDD | Oui | 🟡 Possible |
| `laravel-patterns` | Patterns d'architecture Laravel — routing/controllers, Eloquent ORM, service layers, queues, events, cache et API resources pour apps de production | Oui | 🟡 Possible |
| `laravel-plugin-discovery` | Découverte et évaluation de packages Laravel via LaraPlugins.io MCP — trouver des plugins, vérifier la santé du package et l'adéquation Laravel/PHP | Oui | 🟡 Possible |
| `laravel-security` | Sécurité Laravel — authn/authz, validation, CSRF, mass assignment, uploads de fichiers, secrets, rate limiting et déploiement sécurisé | Oui | 🟡 Possible |
| `laravel-tdd` | TDD Laravel avec PHPUnit et Pest — factories, tests de base de données, fakes et objectifs de coverage | Oui | 🟡 Possible |
| `laravel-verification` | Boucle de vérification Laravel — vérifications env, lint, analyse statique, tests avec coverage, scans de sécurité et production readiness | Oui | 🟡 Possible |
| `lead-intelligence` | Pipeline de lead intelligence natif IA — remplace Apollo, Clay et ZoomInfo par du scoring de signaux, ranking mutuel, découverte de chemins warm et outreach multi-canal (email, LinkedIn, X) | Oui | 🟡 Possible |
| `liquid-glass-design` | Design system Liquid Glass iOS 26 — matériau verre dynamique avec flou, réflexion et morphing interactif pour SwiftUI, UIKit et WidgetKit | Oui | 🟡 Possible |
| `logistics-exception-management` | Expertise codifiée pour la gestion des exceptions logistiques — détection proactive des retards, escalades fournisseurs, reprogrammation des livraisons et communication client | Oui | 🟡 Possible |
| `manim-video` | Crée des explainers Manim réutilisables pour concepts techniques, graphes et diagrammes système — s'intègre avec la stack vidéo ECC pour une post-production complète | Oui | 🟡 Possible |
| `market-research` | Conduit des études de marché, analyses concurrentielles, due diligence investisseurs et intelligence sectorielle — résumés orientés décision avec attribution des sources | Oui | 🟡 Possible |
| `mcp-server-patterns` | Construit des serveurs MCP avec le SDK Node/TypeScript — outils, ressources, prompts, validation Zod, choix entre stdio et Streamable HTTP | Oui | 🟡 Possible |
| `nanoclaw-repl` | Opère et étend NanoClaw v2, le REPL zero-dépendance session-aware d'ECC construit sur `claude -p` | Oui | 🟡 Possible |
| `nestjs-patterns` | Patterns d'architecture NestJS — modules, controllers, providers, validation DTO, guards, interceptors, config et backends TypeScript de production | Oui | 🟡 Possible |
| `nextjs-turbopack` | Next.js 16+ et Turbopack — bundling incrémental, cache FS, vitesse de développement et quand choisir Turbopack vs webpack | Oui | 🟡 Possible |
| `nutrient-document-processing` | Traitement de documents via Nutrient DWS API — conversion, OCR, extraction, rédaction, signature et remplissage. Supporte PDF, DOCX, XLSX, PPTX, HTML et images | Oui | 🟡 Possible |
| `nuxt4-patterns` | Patterns Nuxt 4 — sécurité d'hydratation, performance, route rules, lazy loading et fetch SSR-safe avec useFetch et useAsyncData | Oui | 🟡 Possible |
| `openclaw-persona-forge` | Forge des personas complets pour agents IA OpenClaw — identité, voix, contraintes comportementales et profils de compétences | Oui | 🟡 Possible |
| `opensource-pipeline` | Pipeline de publication open-source — fork, sanitize et package des projets privés via 3 agents chaînés (forker, sanitizer, packager) pour une release publique sécurisée | Oui | 🟡 Possible |
| `perl-patterns` | Idiomes Perl 5.36+ modernes, bonnes pratiques et conventions pour des applications robustes et maintenables | Oui | 🟡 Possible |
| `perl-security` | Sécurité Perl complète — taint mode, validation des entrées, requêtes DBI paramétrées, sécurité web (XSS/SQLi/CSRF) et politiques perlcritic | Oui | 🟡 Possible |
| `perl-testing` | Patterns de tests Perl avec Test2::V0, Test::More, prove runner, mocking, coverage via Devel::Cover et méthodologie TDD | Oui | 🟡 Possible |
| `plankton-code-quality` | Enforcement qualité à l'écriture via Plankton — auto-formatage, lint et corrections Claude à chaque édition de fichier via hooks | Oui | 🟡 Possible |
| `postgres-patterns` | Patterns PostgreSQL — optimisation de requêtes, design de schéma, indexation et sécurité. Basé sur les bonnes pratiques Supabase | Oui | 🟡 Possible |
| `product-lens` | Valide le "pourquoi" avant de construire — diagnostique produit et convertit les idées vagues en specs actionnables | Oui | 🟡 Possible |
| `production-scheduling` | Expertise codifiée pour l'ordonnancement de production — planification des lignes, gestion des goulots d'étranglement, optimisation des séquences et coordination des ressources | Oui | 🟡 Possible |
| `project-flow-ops` | Opère les flux d'exécution sur GitHub et Linear — triage des issues et PRs, liaison du travail actif, GitHub pour le public et Linear pour l'exécution interne | Oui | 🟡 Possible |
| `project-guidelines-example` | Template de skill project-specific basé sur une vraie application de production — à copier et adapter pour documenter les conventions et patterns de ton propre projet | Oui | 🟡 Possible |
| `prompt-optimizer` | Analyse les prompts bruts, identifie les lacunes et mappe les composants ECC adaptés (skills, agents, règles) pour maximiser leur efficacité | Oui | ✅ TRIGGER when |
| `python-patterns` | Idiomes Pythoniques, standards PEP 8, type hints et bonnes pratiques pour des applications Python robustes, efficaces et maintenables | Oui | 🟡 Possible |
| `python-testing` | Tests Python avec pytest — TDD, fixtures, mocking, parametrisation et exigences de coverage | Oui | 🟡 Possible |
| `pytorch-patterns` | Patterns PyTorch — pipelines d'entraînement robustes et reproductibles, architectures de modèles et chargement de données efficace | Oui | 🟡 Possible |
| `quality-nonconformance` | Expertise codifiée pour la gestion des non-conformités qualité — enregistrement des NC, analyse des causes racines (5 Pourquoi, Ishikawa), plans d'action corrective et suivi d'efficacité | Oui | 🟡 Possible |
| `ralphinho-rfc-pipeline` | Pattern d'exécution DAG multi-agents piloté par RFC — quality gates, merge queues et orchestration d'unités de travail | Oui | 🟡 Possible |
| `regex-vs-llm-structured-text` | Framework de décision pour choisir entre regex et LLM pour parser du texte structuré — commencer par regex, ajouter le LLM uniquement pour les cas limites à faible confiance | Oui | 🟡 Possible |
| `remotion-video-creation` | Bonnes pratiques Remotion (vidéos en React) — 29 règles couvrant la 3D, animations, audio, captions, graphiques, transitions et plus | Oui | 🟡 Possible |
| `repo-scan` | Audit cross-stack du code source — classifie chaque fichier, détecte les librairies tierces embarquées et produit des verdicts à 4 niveaux par module avec rapports HTML interactifs | Oui | 🟡 Possible |
| `returns-reverse-logistics` | Expertise codifiée pour les retours et la logistique inversée — autorisation de retour (RMA), inspection, remise en stock, recycling et analyse des causes de retour | Oui | 🟡 Possible |
| `rules-distill` | Scanne les skills pour extraire les principes transversaux et les distiller en règles — ajoute, révise ou crée de nouveaux fichiers de règles | Oui | 🟡 Possible |
| `rust-patterns` | Patterns Rust idiomatiques — ownership, gestion d'erreurs, traits, concurrence et bonnes pratiques pour des applications sûres et performantes | Oui | 🟡 Possible |
| `rust-testing` | Patterns de tests Rust — unit, intégration, async, property-based testing, mocking et coverage. Méthodologie TDD | Oui | 🟡 Possible |
| `safety-guard` | Prévient les opérations destructives lors du travail sur des systèmes de production ou dans des boucles d'agents autonomes | Oui | 🟡 Possible |
| `santa-method` | Vérification adversariale multi-agents avec boucle de convergence — deux reviewers indépendants doivent tous deux approuver avant que le code soit livré | Oui | 🟡 Possible |
| `search-first` | Workflow recherche-avant-code — cherche les outils, libs et patterns existants avant d'écrire du code custom. Invoque l'agent researcher | Oui | 🟡 Possible |
| `security-review` | Checklist de sécurité complète pour l'authentification, la gestion des entrées utilisateur, les secrets, les endpoints API et les fonctionnalités de paiement | Oui | 🟡 Possible |
| `security-scan` | Scanne la configuration Claude Code (`.claude/`) via AgentShield — CLAUDE.md, settings.json, MCPs, hooks et agents pour détecter vulnérabilités, mauvaises configs et risques d'injection | Oui | 🟡 Possible |
| `skill-comply` | Visualise si les skills, règles et agents sont réellement suivis — génère des scénarios à 3 niveaux de strictness, exécute des agents, classifie les séquences comportementales et rapporte les taux de conformité | Oui | 🟡 Possible |
| `skill-stocktake` | Audit qualité des skills et commandes Claude — Quick Scan (skills modifiés uniquement) ou Full Stocktake avec évaluation par lots de sous-agents | Oui | 🟡 Possible |
| `social-graph-ranker` | Ranking pondéré du graphe social pour la découverte de warm intros, le scoring des bridges et l'analyse des lacunes réseau sur X et LinkedIn | Oui | 🟡 Possible |
| `springboot-patterns` | Patterns Spring Boot — design REST, services en couches, accès aux données, cache, traitement async et logging | Oui | 🟡 Possible |
| `springboot-security` | Sécurité Spring Security — authn/authz, validation, CSRF, secrets, headers, rate limiting et sécurité des dépendances | Oui | 🟡 Possible |
| `springboot-tdd` | TDD Spring Boot avec JUnit 5, Mockito, MockMvc, Testcontainers et JaCoCo — features, bugs et refactoring en test-first | Oui | 🟡 Possible |
| `springboot-verification` | Boucle de vérification Spring Boot — build, analyse statique, tests avec coverage, scans de sécurité et diff review avant release ou PR | Oui | 🟡 Possible |
| `strategic-compact` | Suggère des moments stratégiques pour `/compact` aux intervalles logiques de la tâche — préserve le contexte utile plutôt que de laisser la compaction auto couper arbitrairement | Oui | 🟡 Possible |
| `swift-actor-persistence` | Persistance thread-safe en Swift via actors — cache mémoire avec stockage fichier, élimine les data races par conception | Oui | 🟡 Possible |
| `swift-concurrency-6-2` | Swift 6.2 Approachable Concurrency — single-threaded par défaut, `@concurrent` pour le background explicite et conformances isolées pour les types main actor | Oui | 🟡 Possible |
| `swift-protocol-di-testing` | Injection de dépendances basée sur les protocoles pour du code Swift testable — mock du file system, réseau et APIs externes via des protocoles ciblés et Swift Testing | Oui | 🟡 Possible |
| `swiftui-patterns` | Patterns d'architecture SwiftUI — state management (@Observable), composition de vues, navigation, optimisation des performances et bonnes pratiques iOS/macOS modernes | Oui | 🟡 Possible |
| `tdd-workflow` | Enforce le TDD (tests d'abord, puis implémentation) — 80%+ coverage incluant tests unit, intégration et E2E | Oui | 🟡 Possible |
| `team-builder` | Sélecteur interactif d'agents pour composer et dispatcher des équipes parallèles selon la tâche | Oui | 🟡 Possible |
| `token-budget-advisor` | Propose à l'utilisateur un choix éclairé sur la profondeur de réponse avant de consommer le budget de contexte — réponse courte vs approfondie | Oui | ✅ TRIGGER when |
| `ui-demo` | Enregistre des vidéos de démo UI soignées via Playwright — cursor visible, timing naturel, rendu professionnel en WebM. Pour démos, walkthroughs et tutoriels d'applications web | Oui | 🟡 Possible |
| `verification-loop` | Système de vérification complet pour sessions Claude Code — build, type check, lint, tests en séquence avec arrêt sur premier échec | Oui | 🟡 Possible |
| `video-editing` | Workflows d'édition vidéo assistés par IA — pipeline complet de la capture brute au polish final via FFmpeg, Remotion, ElevenLabs, fal.ai, Descript et CapCut | Oui | 🟡 Possible |
| `videodb` | Ingestion, compréhension et action sur vidéos et audio — indexation visuelle/sémantique/temporelle, recherche de moments, édition de timeline, overlays, doublage, traduction et alertes en temps réel depuis fichiers, URLs ou flux live | Oui | 🟡 Possible |
| `visa-doc-translate` | Traduit des documents de demande de visa (images) en anglais et crée un PDF bilingue avec l'original et la traduction côte à côte | Oui | 🟡 Possible |
| `workspace-surface-audit` | Audite le repo actif, MCPs, plugins, connecteurs, variables d'env et le harness — recommande les skills, hooks, agents et workflows ECC les plus pertinents pour ton environnement | Oui | 🟡 Possible |
| `x-api` | Intégration API X/Twitter — posts, threads, lecture de timeline, recherche et analytics. Couvre l'auth OAuth, les rate limits et la publication de contenu natif | Oui | 🟡 Possible |

---

## Sessions, agents et contexte — comment ça marche vraiment

### La session

Une session Claude Code = **une conversation liée à un répertoire**. Chaque session a sa propre fenêtre de contexte, indépendante de toutes les autres.

Ce que contient le contexte au démarrage (dans l'ordre de chargement) :

| Élément | Tokens estimés |
|---------|---------------|
| System prompt interne (toujours en premier, invisible) | ~4 200 |
| MEMORY.md / auto-mémoire (200 premières lignes max) | ~680 |
| Info d'environnement (répertoire, shell, OS, git status…) | ~280 |
| Schémas MCP (chargés à la demande, pas d'un coup) | ~120 noms seulement |

Tout le reste s'accumule pendant la session : messages, lectures de fichiers, sorties de commandes, skills invoqués, schémas MCP utilisés.

**Sessions et terminaux :** si tu ouvres le même répertoire dans deux terminaux sans `--fork-session`, les deux écrivent dans le **même fichier de session** — les messages s'entremêlent. Utilise `--fork-session` pour bifurquer à partir d'un point donné sans altérer la session originale.

**Reprise :** `claude --continue` ou `claude --resume` restaure l'historique complet de la conversation — mais pas les permissions accordées pendant la session, qui doivent être ré-approuvées.

**Compaction automatique :** quand la fenêtre de contexte approche sa limite, Claude Code vide d'abord les outputs d'outils anciens, puis résume la conversation. Les instructions données tôt dans la session peuvent être perdues. Solution : les mettre dans `CLAUDE.md` (chargé à chaque session) et utiliser `/compact` pour contrôler manuellement ce qui est préservé.

---

### Les sous-agents

Un sous-agent est un Claude secondaire lancé par Claude principal pour une tâche spécifique. C'est le mécanisme derrière l'outil `Agent` dans Claude Code.

**Ce qui est clé :**

- Chaque sous-agent a sa propre **fenêtre de contexte isolée** — son travail ne pollue pas le contexte du parent
- Le sous-agent reçoit uniquement son propre system prompt + les infos d'environnement de base. Il ne reçoit **pas** l'historique de la conversation parent
- Quand il a fini, seul un **résumé** de son travail remonte dans le contexte parent — pas tout ce qu'il a lu/fait
- **Les sous-agents ne peuvent pas spawner d'autres sous-agents** (pas d'imbrication)

**Modèles disponibles pour les sous-agents :**

| Agent | Modèle par défaut | Outils | Usage |
|-------|-------------------|--------|-------|
| `Explore` | Haiku (rapide) | Lecture seule | Exploration de codebase |
| `Plan` | Hérite du parent | Lecture seule | Recherche pour la planification |
| `general-purpose` | Hérite du parent | Tous | Tâches complexes multi-étapes |

**Configuration custom** (fichier YAML dans `.claude/agents/` ou `~/.claude/agents/`) :
- `tools` / `disallowedTools` — liste d'outils autorisés/interdits
- `model` — `sonnet`, `opus`, `haiku`, ou `inherit`
- `permissionMode` — `default`, `acceptEdits`, `auto`, `bypassPermissions`…
- `maxTurns` — nombre maximum de tours agentiques
- `isolation: worktree` — isole dans un worktree git temporaire
- `background: true` — toujours en arrière-plan

**Ordre de résolution du modèle :** variable d'env `CLAUDE_CODE_SUBAGENT_MODEL` → paramètre par invocation → frontmatter de l'agent → modèle de la conversation parent.

---

### Agents en parallèle

#### Option 1 — Deux sous-agents dans la même session

Le pattern le plus simple : Claude principal lance deux sous-agents dans le même message (via deux appels `Agent` dans la même réponse). Les deux s'exécutent en parallèle, Claude parent attend les deux résultats, puis synthétise.

```
Claude parent
  ├── Agent A (contexte isolé) → résumé
  └── Agent B (contexte isolé) → résumé
           ↓
    Claude synthétise les deux
```

- Tu n'interagis pas pendant leur exécution
- Chaque agent a son propre contexte isolé
- Seuls les résumés remontent → coût modéré

#### Option 2 — Agent Teams (expérimental)

Les **Agent Teams** sont une fonctionnalité expérimentale (désactivée par défaut, nécessite `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` et Claude Code v2.1.32+).

Architecture :

| Rôle | Description |
|------|-------------|
| **Team lead** | La session principale — crée l'équipe, dispatch les tâches, coordonne |
| **Teammates** | Instances Claude Code **entièrement indépendantes**, chacune avec son propre contexte |
| **Task list** | Liste partagée dans `~/.claude/tasks/{team-name}/` — les teammates la consultent et se l'approprient |
| **Mailbox** | Messagerie directe entre agents |

Différences avec les sous-agents classiques :

| | Sous-agents | Agent Teams |
|---|---|---|
| Communication | Résultat → parent uniquement | Les teammates se parlent directement |
| Coordination | Parent gère tout | Liste de tâches partagée, auto-coordination |
| Coût | Modéré — résumés seulement | Élevé — chaque teammate est une instance complète |
| Idéal pour | Tâche isolée dont seul le résultat compte | Travail complexe nécessitant collaboration |

**Taille recommandée :** 3–5 teammates, 5–6 tâches par teammate.

**Limitations actuelles :** pas de `/resume` ou `/rewind` avec des teammates actifs, pas d'équipes imbriquées, un seul team lead par session.

#### Option 3 — Deux terminaux

Deux instances Claude Code complètement indépendantes. Chacune a son propre contexte, ses propres permissions. Tu interagis avec les deux manuellement. Aucune coordination automatique.

Utile pour : travailler sur deux **projets différents** en même temps, ou superviser deux longues tâches indépendantes.

---

### Worktrees — isolation du système de fichiers

Un worktree git = un **répertoire de travail séparé** avec sa propre branche, qui partage le même historique et le même remote que le repo principal.

Pourquoi c'est important avec des agents parallèles : sans worktree, plusieurs agents qui modifient les mêmes fichiers créent des conflits. Avec worktree, chaque agent travaille dans son propre espace.

```bash
# Créer un worktree nommé
claude --worktree feature-auth
# → crée .claude/worktrees/feature-auth/ sur la branche worktree-feature-auth

# Nom auto-généré
claude --worktree
# → ex: .claude/worktrees/bright-running-fox/
```

**Pour les sous-agents :** ajouter `isolation: worktree` dans le frontmatter de l'agent — Claude Code crée automatiquement un worktree temporaire, nettoyé à la fin si aucune modification n'a été faite.

**Copier les fichiers ignorés par git dans les worktrees** (`.env`, secrets…) : créer un fichier `.worktreeinclude` à la racine du projet avec la même syntaxe que `.gitignore`.

```
.env
.env.local
config/secrets.json
```

**Nettoyage automatique :** si un worktree de sous-agent est orphelin (crash), il est supprimé au prochain démarrage si : plus ancien que `cleanupPeriodDays` ET aucun fichier tracké modifié ET aucun commit non pushé. Les worktrees créés avec `--worktree` ne sont jamais nettoyés automatiquement.

---

### Résumé — ce qui est partagé et ce qui est isolé

| | Session 1 terminal | Session 2 terminaux (même dir) | Sous-agent | Agent Team teammate | Worktree |
|---|---|---|---|---|---|
| Contexte | — | Partagé ⚠️ | Isolé ✅ | Isolé ✅ | — |
| Fichiers | — | Partagé ⚠️ | Partagé ⚠️ | Partagé ⚠️ | Isolé ✅ |
| Historique conversation | — | Partagé ⚠️ | Non transmis ✅ | Non transmis ✅ | — |
| Permissions | — | Partagées ⚠️ | Héritées/config | Héritées du lead | — |

**Règle d'or :** pour des agents qui modifient des fichiers en parallèle → toujours utiliser `isolation: worktree` pour éviter les conflits.

---

### Coût des agents parallèles

- **Sous-agents** : coût modéré — le travail verbose reste dans leur contexte, seul le résumé remonte
- **Agent Teams** : coût élevé — chaque teammate est une instance complète, la consommation de tokens est **linéaire** avec le nombre de teammates. Les teammates en plan mode consomment ~7× plus de tokens qu'une session standard
- **Broadcast** (envoyer à tous les teammates simultanément) : coûteux — éviter
- **Conseil** : utiliser Sonnet (pas Opus) pour les teammates, garder les spawn prompts courts et ciblés

---

## Gestion du contexte — /compact, /fork et budget

La fenêtre de contexte est la ressource la plus critique d'une session Claude. Bien la gérer évite les compactions intempestives, les pertes d'instructions, et les coûts inutiles.

### Ce qui consomme du contexte au démarrage

Au lancement, Claude charge automatiquement (dans l'ordre) :

| Composant | Tokens estimés |
|-----------|----------------|
| System prompt (instructions internes) | ~4 200 |
| `MEMORY.md` (200 premières lignes) | ~680 |
| Infos environnement (dossier, OS, git…) | ~280 |
| Noms des outils MCP (schémas différés) | ~120 |
| Descriptions des skills (1 ligne chacune) | ~450 |
| `~/.claude/CLAUDE.md` (user global) | ~320 |
| `CLAUDE.md` du projet | ~1 800 |
| **Total overhead de démarrage** | **~8 000** |

Sur une fenêtre de 200k tokens, ~4 % sont déjà consommés avant ton premier message. Le reste est disponible pour la conversation, les fichiers lus, les outputs d'outils, etc.

### Les commandes de gestion du contexte

| Commande | Effet |
|----------|-------|
| `/compact [instructions]` | Résume la conversation, libère du contexte, réinjecte CLAUDE.md depuis le disque |
| `/compact focus sur les changements API` | Compact avec instruction de focus |
| `/clear` (alias `/reset`, `/new`) | Réinitialisation complète — conversation effacée, nouveau départ |
| `/context` | Visualise l'usage du contexte par catégorie (grille colorée) |
| `/context-budget` (ECC) | Audit complet des tokens par composant + recommandations |
| `/fork` (alias `/branch`) | Crée une branche de la session au point courant |

### `/compact` — tout ce qu'il faut savoir

**Ce qui survit à `/compact` :**
- ✅ CLAUDE.md — relu depuis le disque et ré-injecté en entier
- ✅ La liste des tâches (`/task`)
- ✅ Le contexte essentiel (résumé structuré)

**Ce qui est perdu :**
- ❌ Les descriptions de skills qui n'ont pas été invoqués
- ❌ Les instructions données uniquement en chat (pas dans CLAUDE.md)
- ❌ Les détails des fichiers lus (résumés, pas reproduits)

**Compact automatique :** se déclenche à ~95 % d'utilisation du contexte. Claude vide d'abord les anciens outputs d'outils, puis résume si nécessaire.

**Désactiver :**
```bash
DISABLE_AUTO_COMPACT=1    # désactive l'auto seulement (/compact manuel reste possible)
DISABLE_COMPACT=1          # désactive tout
```

**Déclencher plus tôt :**
```bash
CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=70  # compact à 70% au lieu de 95%
```

**Ajouter des instructions permanentes de compact** dans CLAUDE.md :
```markdown
## Compact Instructions
Quand tu compactes, préserve : les décisions d'architecture, les commandes testées, les patterns de bug découverts. Oublie : les explorations abandonnées, les fichiers listés mais non modifiés.
```

### Quand compacter vs quand repartir

| Situation | Action recommandée |
|-----------|--------------------|
| En plein milieu d'une tâche, contexte qui monte | `/compact` — préserve l'état de travail |
| Tâche terminée, nouvelle tâche sans rapport | `/clear` — ardoise propre |
| Veux explorer une piste alternative en parallèle | `/fork` — branche la session au point courant |
| Instructions du début de session perdues | Vérifie CLAUDE.md, puis `/clear` et recommence |
| Claude ignore des règles | `/memory` pour vérifier les fichiers chargés |

### `/fork` — brancher une session

`/fork [nom]` crée un point de bifurcation : deux chemins explorent indépendamment à partir du même état. La session originale reste intacte. Utile pour comparer deux approches sans perdre l'une ou l'autre.

Via CLI :
```bash
claude --continue --fork-session   # nouvelle session ID, hérite de l'historique
```

> ⚠️ Les permissions approuvées en cours de session **ne sont pas héritées** par les sessions forkées.

### Le `/context-budget` d'ECC

Le skill ECC `/context-budget` fait un audit complet :
- Tokens par composant (agents, skills, règles, MCPs, fichiers config)
- Warnings : descriptions d'agents > 30 mots, fichiers surdimensionnés, contenu dupliqué dans les règles, MCPs remplaçables par des commandes CLI
- Top 3 des économies possibles avec projections de tokens

```
/context-budget          # audit standard
/context-budget --verbose  # détail fichier par fichier
```

### Optimiser son usage du contexte

1. **CLAUDE.md < 200 lignes** — au-delà, les instructions sont moins bien suivies ET coûtent plus
2. **`disable-model-invocation: true`** sur les skills rarement utiles — leur description disparaît du contexte
3. **Déléguer aux sous-agents** les explorations longues — ils ont leur propre contexte, seul le résumé revient
4. **`/btw <question>`** pour les questions ponctuelles — n'entre jamais dans l'historique de conversation
5. **`paths:`** dans les règles — les règles path-scoped ne se chargent que quand les fichiers concernés sont ouverts

---

## C'est quoi le harness ?

Dans le contexte ECC, **harness** = l'ensemble de l'infrastructure qui entoure Claude Code pour le rendre plus efficace, fiable et contrôlable.

C'est une métaphore empruntée aux tests logiciels (*test harness* = le système qui exécute les tests, capture les résultats, applique les règles) mais étendu à toute la configuration de Claude.

**Concrètement, le harness ECC c'est :**

```
~/.claude/
├── commands/       ← ce que tu peux invoquer
├── skills/         ← ce que Claude sait faire automatiquement
├── agents/         ← sous-processus délégués
├── rules/          ← contraintes appliquées en permanence
├── hooks/          ← automatisations sur événements
└── settings.json   ← configuration globale
```

Tout ce qui **encadre** Claude — avant qu'il réponde, pendant qu'il travaille, après qu'il termine — c'est le harness.

**Analogie :** un harnais pour un cheval. Claude est le cheval (la puissance brute). Le harness ECC est le harnais — il ne le remplace pas, il le guide, le contraint et l'outille pour qu'il aille dans la bonne direction.

C'est pour ça que `/harness-audit` note ton setup sur 7 dimensions : il vérifie que ton harnais est bien configuré. Un harness mal ficelé = Claude qui part dans tous les sens.

---

## CLAUDE.md — la mémoire permanente de Claude

### Ce que c'est

`CLAUDE.md` est un fichier Markdown que Claude Code charge automatiquement au démarrage de chaque session. C'est là qu'il lit les instructions persistantes : standards de code, conventions du projet, workflows, commandes de build… Tout ce que tu ne veux pas ré-expliquer à chaque session.

**Important :** le contenu est injecté comme un message utilisateur après le system prompt — pas comme du code de configuration. Claude le lit et essaie de le suivre, mais ce n'est pas de l'enforcement stricte. Des instructions vagues ou contradictoires peuvent être ignorées.

**Survit à la compaction** : quand le contexte est compacté (`/compact`), CLAUDE.md est relu depuis le disque et ré-injecté en entier. Les instructions données uniquement dans la conversation sont perdues — celles dans CLAUDE.md, jamais.

### La hiérarchie des fichiers

Plusieurs fichiers coexistent. Tous sont concaténés dans le contexte (pas de remplacement, d'accumulation) :

| Fichier | Portée | Versionnable |
|---------|--------|-------------|
| `/Library/Application Support/ClaudeCode/CLAUDE.md` (macOS) | Organisation entière (MDM) | Non |
| `~/.claude/CLAUDE.md` | Tous tes projets (user) | Non |
| `.claude/CLAUDE.md` ou `./CLAUDE.md` | Projet (équipe) | **Oui** |
| `./CLAUDE.local.md` | Projet (personnel) | Non — à ajouter au `.gitignore` |

**Résolution en remontant l'arborescence :** si tu travailles dans `foo/bar/`, Claude charge `foo/bar/CLAUDE.md`, `foo/bar/CLAUDE.local.md`, `foo/CLAUDE.md`, `foo/CLAUDE.local.md`… jusqu'à la racine. Les fichiers des sous-répertoires **en dessous** de ton répertoire courant ne sont chargés qu'à la demande, quand Claude ouvre un fichier dans ce sous-dossier.

### Ce qu'on y met

```markdown
# Mon Projet

## Commandes
- Build : `npm run build`
- Tests : `npm test`
- Dev server : `npm run dev`

## Conventions
- 2 espaces d'indentation, pas de tabs
- Nommage : camelCase pour les variables, PascalCase pour les composants
- Les handlers API valident toujours les inputs avec Zod

## Architecture
- API REST dans `src/api/handlers/`
- Logique métier dans `src/domain/`
- Pas de logique dans les controllers — uniquement du routing
```

**Règle d'or :** une instruction concrète et spécifique vaut 5 phrases vagues.

| Moins efficace | Plus efficace |
|----------------|---------------|
| "Formate le code proprement" | "2 espaces, Prettier, `npm run format` pour appliquer" |
| "Écris des tests" | "Lance `npm test` avant chaque commit, coverage > 80%" |
| "Organise bien les fichiers" | "Les handlers vivent dans `src/api/handlers/`" |

### La syntaxe `@import`

Pour éviter de dupliquer du contenu, tu peux importer d'autres fichiers :

```markdown
# Instructions projet

Voir @README.md pour la vue d'ensemble.
Commandes disponibles : @package.json

## Workflow git
@docs/git-workflow.md
```

- Chemins relatifs au fichier qui importe (pas au répertoire courant)
- Profondeur max d'import : 5 niveaux
- La première fois qu'ECC détecte des imports externes, Claude Code affiche une boîte de dialogue d'approbation

### CLAUDE.md vs MEMORY.md — la différence

| | `CLAUDE.md` | `MEMORY.md` (auto-mémoire) |
|---|---|---|
| Qui écrit ? | **Toi** | **Claude** |
| Contenu | Instructions et règles | Apprentissages et patterns découverts |
| Portée | Projet, user, ou org | Par répertoire de travail |
| Chargé au démarrage | Tout le contenu | 200 premières lignes seulement |
| Exemples | Standards de code, architecture | Commandes de build, patterns de debug |

L'auto-mémoire se trouve dans `~/.claude/projects/<projet>/memory/MEMORY.md`. Claude y écrit ce qu'il découvre pendant les sessions (commandes qui marchent, conventions qu'il a observées…). **Pas de limite de taille sur CLAUDE.md** — mais au-delà de 200 lignes la qualité de suivi des instructions commence à baisser.

### Garder CLAUDE.md lean

1. **Viser < 200 lignes par fichier** — plus long = moins bien suivi ET plus de tokens consommés
2. **Déporter dans `.claude/rules/`** — les standards détaillés vont dans des fichiers de règles thématiques (voir chapitre suivant)
3. **Utiliser les commentaires HTML** — `<!-- note pour les humains -->` est supprimé avant injection, coûte zéro token
4. **Externaliser avec `@import`** — `README.md`, `package.json`, docs déjà existants
5. **Laisser Claude écrire MEMORY.md** — ne pas dupliquer dans CLAUDE.md ce que Claude peut découvrir et mémoriser seul

### Déboguer ce que Claude voit réellement

```
/memory
```

Liste tous les fichiers d'instructions chargés dans la session courante : CLAUDE.md, CLAUDE.local.md, et toutes les règles actives. Si une instruction n'est pas suivie, c'est le premier endroit où chercher — vérifier que le fichier est bien dans la liste.

### Générer un CLAUDE.md automatiquement

```
/init
```

Claude analyse le codebase et génère un `CLAUDE.md` de départ. Avec `CLAUDE_CODE_NEW_INIT=1`, le mode interactif s'active : exploration avec un sous-agent, questions de clarification, proposition avant écriture.

---

## La mémoire persistante — auto-memory et MEMORY.md

L'auto-mémoire est le système par lequel Claude **écrit lui-même** ce qu'il découvre pendant les sessions, pour que ses futures instances s'en souviennent. C'est le pendant de CLAUDE.md (que tu écris) : Claude écrit MEMORY.md, tu écris CLAUDE.md.

> Requiert Claude Code v2.1.59 ou plus récent (`claude --version`).

### Structure du dossier mémoire

```
~/.claude/projects/<projet>/memory/
├── MEMORY.md              # Index concis — 200 premières lignes chargées à chaque session
├── debugging.md           # Notes de debug détaillées (chargées à la demande)
├── api-conventions.md     # Décisions d'API (chargées à la demande)
└── ...                    # Tout autre fichier thématique que Claude crée
```

`<projet>` est dérivé de la racine du dépôt git. Tous les worktrees et sous-répertoires du même repo partagent le même dossier mémoire. La mémoire est **locale à la machine** — elle ne se synchronise pas entre machines.

### Ce que Claude sauvegarde (et ce qu'il ne sauvegarde pas)

Claude ne sauvegarde pas quelque chose à chaque session — il évalue si l'information serait utile dans une future conversation. Il sauvegarde notamment :

- Commandes de build / lancement / test
- Patterns de debug découverts
- Conventions de code qu'il a observées
- Préférences de workflow qu'il a inférées
- Ce que tu lui demandes explicitement de mémoriser

> "Always use pnpm, not npm" → Claude l'écrit dans MEMORY.md (ou mets-le dans CLAUDE.md pour qu'il soit garanti chargé)

### La limite 200 lignes / 25 Ko

Seules les **200 premières lignes** (ou les 25 premiers Ko) de `MEMORY.md` sont chargées au démarrage de chaque session. Au-delà, le contenu n'est pas injecté.

**Design pattern :** Claude maintient `MEMORY.md` comme un **index concis** avec des pointeurs vers des fichiers thématiques (`debugging.md`, `api-conventions.md`…). Les fichiers thématiques sont lus à la demande, pas au démarrage — leur taille n'est pas limitée.

| | `MEMORY.md` | Fichiers thématiques |
|--|-------------|----------------------|
| Chargé au démarrage | Oui (200 lignes max) | Non |
| Chargé à la demande | Non | Oui (quand Claude en a besoin) |
| Qui l'écrit | Claude | Claude |
| Taille | Concis (index) | Illimitée |

### Gérer la mémoire

**Via la commande `/memory` :**
```
/memory
```
- Liste tous les fichiers chargés dans la session (CLAUDE.md, rules, MEMORY.md…)
- Bouton pour activer / désactiver l'auto-mémoire
- Lien pour ouvrir le dossier mémoire dans l'éditeur

**Désactiver l'auto-mémoire :**
```json
{ "autoMemoryEnabled": false }
```
Ou via la variable d'environnement : `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`

**Dossier personnalisé :**
```json
{ "autoMemoryDirectory": "~/ma-memoire-perso" }
```
Uniquement dans `~/.claude/settings.json` (pas dans `.claude/settings.json` du projet, pour des raisons de sécurité).

### Demander à Claude de mémoriser quelque chose

En cours de session :
```
mémorise que pour ce projet on utilise toujours pnpm et jamais npm
mémorise que les tests d'intégration nécessitent une instance Redis locale sur le port 6379
```

Claude écrit dans `MEMORY.md` et/ou crée un fichier thématique.

**Important :** si tu veux une garantie que l'information est toujours là, mets-la dans **CLAUDE.md** (chargé en entier, toujours). MEMORY.md est soumis à la limite des 200 lignes.

### Inspecter et éditer la mémoire manuellement

Tous les fichiers mémoire sont du Markdown simple — tu peux les lire, modifier ou supprimer directement :

```bash
ls ~/.claude/projects/*/memory/
cat ~/.claude/projects/<projet>/memory/MEMORY.md
```

Si une entrée mémorisée est fausse ou obsolète, édite le fichier directement — Claude utilisera la version mise à jour à la prochaine session.

### Récapitulatif : les 3 systèmes de mémoire

| Système | Qui écrit | Chargé | Partagé |
|---------|-----------|--------|---------|
| `CLAUDE.md` | Toi | Tout le contenu, chaque session | Oui (git) |
| `MEMORY.md` + thématiques | Claude | 200 lignes index + demande | Non (machine locale) |
| `.claude/rules/` | Toi | Toujours (ou par path glob) | Oui (git) |

---

## Les règles — instructions permanentes

### Ce que c'est

Une règle = un fichier `.md` placé dans `.claude/rules/`. Elle est **chargée automatiquement dans le contexte à chaque session**, au même titre que `CLAUDE.md`. Claude la lit sans que tu aies à faire quoi que ce soit.

Différence fondamentale avec un skill : un skill se déclenche quand on l'invoque ou quand Claude juge la situation pertinente. Une règle est **toujours là**, dans tous les contextes.

| | Règle (`rules/`) | Skill (`skills/`) | CLAUDE.md |
|---|---|---|---|
| Chargée quand ? | Toujours (ou sur fichier correspondant) | À la demande / auto-inférence | Toujours |
| Invocable via `/` ? | Non | Oui | Non |
| Frontmatter riche ? | Non (juste `paths:`) | Oui | Non |
| Cas d'usage | Standards permanents | Workflows répétables | Contexte projet fondamental |

### Les deux niveaux

```
~/.claude/rules/        ← portée user — s'applique à tous tes projets
.claude/rules/          ← portée projet — versionnable, partagé avec l'équipe
```

Les deux peuvent coexister. Le projet a la priorité en cas de conflit.

### Règle sans `paths:` — toujours active

```markdown
# Conventions API

- Valider les inputs → exécuter → répondre, toujours dans cet ordre
- Utiliser Zod pour la validation, colocalisé avec chaque handler
- Codes de statut autorisés : 200, 201, 400, 401, 404, 500 uniquement
```

Cette règle est chargée à chaque session, peu importe le fichier sur lequel tu travailles.

### Règle avec `paths:` — chargée uniquement sur les fichiers correspondants

```markdown
---
paths:
  - "**/*.ts"
  - "**/*.tsx"
---

# TypeScript

- Préférer `const` sur `let`, jamais `var`
- Strict null checks — éviter `!` non-null assertions
- Toutes les fonctions async doivent avoir un type de retour explicite
```

Cette règle ne consomme du contexte que quand Claude ouvre un fichier `.ts` ou `.tsx`. C'est le mécanisme principal d'économie de tokens.

> ⚠️ Uniquement la forme YAML array fonctionne pour `paths:` — `paths: src/**/*.ts` (string) est silencieusement ignoré. Toujours utiliser la forme liste :
> ```yaml
> paths:
>   - "src/**/*.ts"
> ```

### Structure recommandée

```
.claude/rules/
├── code-style.md          ← style universel, toujours actif
├── testing.md             ← standards de tests, toujours actif
├── security.md            ← checklist sécurité, toujours actif
├── git-workflow.md        ← conventions git, toujours actif
├── typescript.md          ← paths: ["**/*.ts", "**/*.tsx"]
├── python.md              ← paths: ["**/*.py"]
└── api/
    └── conventions.md     ← paths: ["src/api/**"]
```

### Déboguer les règles actives

```
/memory
```

Cette commande built-in liste tous les fichiers d'instructions chargés dans la session courante : `CLAUDE.md`, `CLAUDE.local.md`, et **toutes les règles actives** avec leur chemin.

### Ce que couvrent les 89 règles ECC

ECC livre deux couches :

**Couche commune (toujours active, langage-agnostique) :**
- `coding-style.md` — immutabilité, organisation des fichiers, gestion d'erreurs, validation des inputs
- `testing.md` — TDD obligatoire, 80%+ coverage, organisation des tests
- `security.md` — checklist P0 (secrets, injection, vulnérabilités critiques)
- `git-workflow.md` — format de commit conventionnel, workflow PR, nommage des branches
- `performance.md` — optimisation tokens, gestion de la fenêtre de contexte, sélection de modèle
- `agents.md` — quand et comment déléguer à un sous-agent, critères de sélection
- `hooks.md` — types de hooks, bonnes pratiques TodoWrite, validation automatisée
- `patterns.md` — repository pattern, format de réponse API, sélection de design patterns

**Couche langage (chargée selon les fichiers ouverts) :**
12 langages couverts (TypeScript, Python, Go, Swift, Java, Kotlin, Rust, C++, C#, Dart, PHP, Perl) — chacun avec ses propres versions de `coding-style.md`, `testing.md`, `patterns.md`, `hooks.md` et `security.md` adaptées aux idiomes du langage.

---

## Les hooks — automatisations sur événements

### Ce que c'est

Un hook = un script (bash, Node, HTTP…) que Claude Code exécute automatiquement à des moments précis du cycle de vie de la session. Tu n'as pas à invoquer quoi que ce soit — le hook se déclenche sur l'événement.

C'est ce qui permet à ECC de faire des choses comme : bloquer un `git push --no-verify`, formater les fichiers automatiquement après chaque édition, envoyer une notification macOS quand Claude a fini, ou auditer chaque commande bash dans un log.

### Les événements principaux

Claude Code expose plus de 20 événements. Les plus utiles :

| Événement | Moment | Peut bloquer ? |
|-----------|--------|---------------|
| `SessionStart` | Début ou reprise de session | Non |
| `UserPromptSubmit` | Tu envoies un message | **Oui** |
| `PreToolUse` | Avant qu'un outil s'exécute (Bash, Edit, Write…) | **Oui** |
| `PermissionRequest` | Claude demande une permission | **Oui** |
| `PostToolUse` | Après qu'un outil a réussi | Non |
| `PostToolUseFailure` | Après qu'un outil a échoué | Non |
| `Stop` | Claude finit sa réponse | **Oui** |
| `SubagentStop` | Un sous-agent termine | **Oui** |
| `PreCompact` / `PostCompact` | Avant/après une compaction | Non |
| `SessionEnd` | Session qui se termine | Non |

**Bloquer** signifie : si le hook retourne un code d'erreur 2, Claude Code annule l'action. Exemple : un hook `PreToolUse` sur `Bash` peut empêcher une commande dangereuse de s'exécuter.

### Données reçues par le hook

Le hook reçoit un JSON sur stdin avec toujours ces champs de base :

```json
{
  "session_id": "abc123",
  "hook_event_name": "PreToolUse",
  "cwd": "/path/to/project",
  "permission_mode": "default"
}
```

Pour `PreToolUse` / `PostToolUse`, s'ajoutent :

```json
{
  "tool_name": "Bash",
  "tool_input": { "command": "git push --no-verify" },
  "tool_use_id": "toolu_01ABC..."
}
```

### Comment configurer un hook

Dans `~/.claude/settings.json` (ou `.claude/settings.json` pour un projet) :

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/check-bash.sh",
            "timeout": 10
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "node ~/.claude/hooks/notify.js",
            "async": true
          }
        ]
      }
    ]
  }
}
```

- **`matcher`** : filtre sur le nom de l'outil (`"Bash"`, `"Edit|Write"`, `"mcp__.*"`) — omis = s'applique à tout
- **`async: true`** : s'exécute en arrière-plan, ne peut jamais bloquer
- **`timeout`** : secondes avant annulation (600s par défaut)

### Écrire un hook script

**Bash — pattern de blocage :**

```bash
#!/bin/bash
COMMAND=$(jq -r '.tool_input.command' < /dev/stdin)

if [[ "$COMMAND" == *"--no-verify"* ]]; then
  echo "Bloqué : --no-verify interdit" >&2
  exit 2   # bloque l'action
fi

exit 0     # laisse passer
```

**Codes de sortie :**

| Code | Effet |
|------|-------|
| `0` | Succès — Claude Code lit le JSON stdout si présent |
| `2` | Erreur bloquante — annule l'action, stderr affiché à Claude |
| Autre non-zéro | Erreur non-bloquante — stderr visible en mode verbose |

### Ce que font les hooks ECC

ECC installe ses hooks via le système de plugins. Ils sont filtrés par `ECC_HOOK_PROFILE`.

**PreToolUse (bloquants) :**
| Hook | Ce qu'il fait |
|------|--------------|
| `block-no-verify` | Bloque tout `git push/commit --no-verify` — protège les pre-commit hooks |
| `config-protection` | Bloque les modifications aux fichiers de config lint/format (eslint, prettier…) |
| `mcp-health-check` | Bloque un appel MCP si le serveur est détecté comme non-sain |
| `commit-quality` | Valide le format du message de commit et cherche des `console.log`/secrets avant commit |

**PreToolUse (non-bloquants) :**
| Hook | Ce qu'il fait |
|------|--------------|
| `auto-tmux-dev` | Lance automatiquement les serveurs de dev dans tmux |
| `suggest-compact` | Suggère `/compact` tous les ~50 appels d'outils |
| `continuous-learning` (pre) | Capture chaque appel d'outil pour le système d'instincts (async) |

**PostToolUse :**
| Hook | Ce qu'il fait |
|------|--------------|
| `quality-gate` | Lance les checks qualité après chaque édition de fichier (async) |
| `console-warn` | Avertit si un `console.log` est détecté après une édition |
| `post-edit:accumulator` | Accumule les fichiers JS/TS édités pour un format+typecheck en batch au Stop |
| `command-log` | Log chaque commande Bash dans `~/.claude/bash-commands.log` |

**Stop (à chaque fin de réponse) :**
| Hook | Ce qu'il fait |
|------|--------------|
| `format-typecheck` | Formate et type-checke en batch tous les fichiers JS/TS édités dans cette réponse |
| `cost-tracker` | Enregistre les métriques de tokens et coût (async) |
| `evaluate-session` | Analyse la session pour en extraire des patterns (continuous learning, async) |
| `desktop-notify` | Envoie une notification macOS/WSL quand Claude termine (async) |
| `session-end-marker` | Marker de fin de session et nettoyage (async) |

### Variables d'environnement utiles dans les hooks

```bash
$CLAUDE_PROJECT_DIR    # racine du projet
$CLAUDE_PLUGIN_ROOT    # répertoire d'installation du plugin
$CLAUDE_ENV_FILE       # fichier pour persister des variables d'env (SessionStart seulement)
```

`CLAUDE_ENV_FILE` est particulier : si tu y écris des exports dans un hook `SessionStart`, ces variables seront disponibles dans la session Claude Code pour toute sa durée.

```bash
# Dans un hook SessionStart :
echo 'export NODE_ENV=production' >> "$CLAUDE_ENV_FILE"
```

---

## Les MCPs — outils externes intégrés dans Claude

### Ce que c'est

**MCP = Model Context Protocol** — un standard open-source qui permet à Claude Code de se connecter à des outils et services externes. Sans MCP, Claude ne sait que lire/écrire des fichiers et exécuter des commandes. Avec MCP, il peut interroger GitHub, rechercher sur le web, lire une BDD, automatiser un navigateur, etc.

Le principe : chaque service qui implémente le protocole MCP devient automatiquement utilisable par Claude — sans code custom côté client. Claude découvre les outils disponibles au démarrage de la session et les appelle nativement.

**Comment les outils MCP apparaissent à Claude :** ils sont nommés selon le pattern `mcp__<serveur>__<outil>`. Par exemple :
- `mcp__github__create_pull_request`
- `mcp__context7__query-docs`
- `mcp__playwright__browser_click`

### Les deux types de serveurs MCP

| Type | Comment ça fonctionne | Idéal pour |
|------|-----------------------|------------|
| **stdio** | Claude Code spawne un process local — communication via stdin/stdout | Outils locaux, packages npm/pip, accès filesystem |
| **HTTP** | Claude Code fait des requêtes HTTP vers une URL distante | Services cloud, APIs hébergées — à préférer |
| ~~SSE~~ | HTTP avec Server-Sent Events | Déprécié — utiliser HTTP à la place |

### Configuration dans `~/.claude.json`

Les MCPs se configurent dans `~/.claude.json` (pas `settings.json`) :

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "ghp_xxx" }
    },
    "vercel": {
      "type": "http",
      "url": "https://mcp.vercel.com"
    }
  }
}
```

**3 portées disponibles :**
- `local` (défaut) — toi uniquement, ce projet
- `project` — dans `.mcp.json` à la racine du repo, partagé avec l'équipe
- `user` — toi uniquement, tous les projets

```bash
# Ajouter un MCP HTTP
claude mcp add --transport http vercel https://mcp.vercel.com

# Ajouter un MCP stdio
claude mcp add --transport stdio github \
  -- npx -y @modelcontextprotocol/server-github

# Lister / supprimer
claude mcp list
claude mcp remove github

# Vérifier le statut dans une session
/mcp
```

### Désactiver un MCP par projet

Dans `.claude/settings.json` du projet :

```json
{
  "disabledMcpServers": ["playwright", "exa"]
}
```

### Les 6 MCPs actifs avec ECC

ECC pre-configure 6 serveurs MCP prêts à l'emploi :

| MCP | Ce qu'il fait |
|-----|--------------|
| **github** | Opérations GitHub — PRs, issues, repos, recherche de code, gestion des branches |
| **context7** | Documentation à jour des libs — résout les IDs de packages et requête les docs en temps réel (utilisé par le skill `documentation-lookup`) |
| **memory** | Graphe de connaissances persistant — entités, relations, observations entre sessions |
| **playwright** | Automation navigateur — naviguer, cliquer, remplir des formulaires, prendre des screenshots, exécuter du JS |
| **sequential-thinking** | Raisonnement structuré multi-étapes — décompose les problèmes complexes en chaînes de pensée |
| **exa** | Recherche web neurale — web, code, entreprises et personnes via l'API Exa |

### Les 30+ MCPs optionnels d'ECC

ECC fournit un catalogue dans `mcp-configs/mcp-servers.json`. Les plus utiles :

| MCP | Cas d'usage |
|-----|------------|
| `jira` | Récupérer/créer/mettre à jour des tickets Jira |
| `supabase` | Opérations BDD Supabase |
| `firecrawl` | Web scraping et crawling |
| `vercel` / `railway` | Déploiements cloud |
| `clickhouse` | Requêtes analytiques ClickHouse |
| `omega-memory` | Mémoire persistante avec recherche sémantique — plus riche que `memory` |
| `fal-ai` | Génération d'images/vidéos/audio via fal.ai |
| `playwright` | Automation navigateur |
| `insaits` | Monitoring de sécurité IA — 23 types d'anomalies, OWASP Top 10 MCP, 100% local |
| `devfleet` | Orchestration multi-agents via Claude DevFleet |
| `confluence` | Recherche et lecture de pages Confluence |
| `laraplugins` | Découverte de packages Laravel |

Pour les activer : copier la config depuis `mcp-configs/mcp-servers.json` dans ton `~/.claude.json`, remplacer les placeholders `YOUR_*_HERE`.

> ⚠️ **Limite pratique :** chaque outil MCP consomme des tokens de description au démarrage. Avec plus de ~10 MCPs actifs (80+ outils), la fenêtre de contexte utilisable peut tomber à ~70k au lieu de 200k. Activer uniquement ce dont tu as besoin.

---

## Permissions et settings.json — contrôle fin des autorisations

Claude Code dispose d'un système de permissions en couches qui détermine quels outils peuvent s'exécuter sans confirmation, lesquels nécessitent une approbation, et lesquels sont bloqués. Ce système repose sur des fichiers `settings.json` et s'applique à chaque outil (Bash, Read, Edit, WebFetch, MCP…).

### Hiérarchie des fichiers de configuration

| Niveau | Fichier | Portée | Versionné ? |
|--------|---------|--------|-------------|
| **Managed** | `/Library/Application Support/ClaudeCode/managed-settings.json` (macOS) | Toute la machine | Déployé par IT/MDM |
| **User** | `~/.claude/settings.json` | Tous tes projets | Non |
| **Project** | `.claude/settings.json` | Tous les collaborateurs du repo | Oui (commit git) |
| **Local** | `.claude/settings.local.json` | Toi seul dans ce repo | Non (gitignored) |

**Priorité (du plus fort au plus faible) :** Managed → CLI args → Local → Project → User

Les managed settings ne peuvent pas être outrepassées par quoi que ce soit, y compris les arguments CLI. Un `deny` défini au niveau managed est définitif.

### Modes de permission (`defaultMode`)

Configurable dans `settings.json` via `permissions.defaultMode` ou en ligne avec `--permission-mode` :

| Mode | Comportement |
|------|--------------|
| `default` | Demande confirmation au premier usage de chaque outil |
| `acceptEdits` | Accepte automatiquement les modifications de fichiers pour la session |
| `plan` | Plan Mode : Claude analyse sans modifier ni exécuter |
| `auto` | Approuve automatiquement avec vérification de cohérence en arrière-plan (research preview) |
| `dontAsk` | Refuse automatiquement sauf règles `allow` explicites |
| `bypassPermissions` | Skip toutes les confirmations (sauf dossiers protégés) |

> ⚠️ **Dossiers toujours protégés même en `bypassPermissions` :** `.git`, `.claude`, `.vscode`, `.idea`, `.husky`. Exceptions : `.claude/commands`, `.claude/agents`, `.claude/skills` (Claude y écrit légitimement).
>
> N'utiliser `bypassPermissions` que dans des environnements isolés (containers, VMs).

### Structure de `settings.json`

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "defaultMode": "acceptEdits",
    "allow": [
      "Bash(npm run lint)",
      "Bash(npm run test:*)",
      "Bash(git status)",
      "Bash(git log *)"
    ],
    "ask": [
      "Bash(git push *)"
    ],
    "deny": [
      "Read(./.env)",
      "Read(./secrets/**)",
      "Bash(curl *)",
      "WebFetch"
    ]
  }
}
```

L'ordre d'évaluation est **deny → ask → allow** : la première règle qui correspond l'emporte. Un `deny` ne peut jamais être outrepassé par un `allow` dans un niveau inférieur.

### Syntaxe des règles de permission

| Motif | Effet |
|-------|-------|
| `Bash` | Tous les appels Bash |
| `Bash(npm run build)` | Commande exacte |
| `Bash(npm run *)` | Tout ce qui commence par `npm run` |
| `Bash(git * main)` | `git checkout main`, `git merge main`… |
| `Read(./.env)` | Fichier `.env` à la racine |
| `Read(./secrets/**)` | Tout sous `secrets/` |
| `Read(//Users/alice/*.pdf)` | Chemin absolu (`//` préfixe) |
| `Edit(/src/**/*.ts)` | Relatif à la racine du projet |
| `WebFetch(domain:example.com)` | Fetch vers example.com uniquement |
| `mcp__github` | Tous les outils du MCP `github` |
| `mcp__github__create_pull_request` | Outil MCP spécifique |
| `Agent(Explore)` | Contrôle quels sous-agents peuvent être lancés |

> ⚠️ **Les règles Read/Edit ne bloquent pas Bash.** Un `deny: ["Read(./.env)"]` empêche le tool `Read` mais pas `cat .env` dans Bash. Pour une protection au niveau OS, activer le sandboxing.

### Approuver "une fois pour toutes" (`Don't ask again`)

- Pour les **commandes Bash** : répondre "Yes, don't ask again" sauvegarde une règle permanente pour ce projet + cette commande.
- Pour les **modifications de fichiers** : l'approbation "don't ask again" dure uniquement jusqu'à la fin de la session.
- Pour les **commandes composées** (`git status && npm test`) : Claude Code crée une règle séparée pour chaque sous-commande (jusqu'à 5 règles).

### Gérer les permissions

```bash
/permissions          # voir et modifier les règles actives
```

La commande `/permissions` affiche toutes les règles en vigueur, leur source (`~/.claude/settings.json`, `.claude/settings.json`…), et permet de les éditer directement.

### Paramètres clés de `settings.json`

Au-delà des permissions, `settings.json` contrôle de nombreux comportements :

| Clé | Description |
|-----|-------------|
| `model` | Modèle par défaut (`claude-opus-4-6`, `claude-sonnet-4-6`…) |
| `hooks` | Configuration des hooks (identique à `.claude/settings.json`) |
| `env` | Variables d'environnement appliquées à chaque session |
| `language` | Langue de réponse de Claude (`"french"`, `"japanese"`…) |
| `permissions.additionalDirectories` | Dossiers supplémentaires accessibles en lecture/écriture |
| `permissions.disableBypassPermissionsMode` | Bloquer le mode bypass (`"disable"`) |
| `cleanupPeriodDays` | Durée de rétention des sessions (défaut : 30 jours) |
| `includeGitInstructions` | Inclure les instructions git dans le prompt système (défaut : `true`) |

> 💡 **Astuce VS Code :** Le `$schema` dans `settings.json` active l'autocomplétion et la validation inline dans VS Code, Cursor et tout éditeur compatible JSON Schema.

---

## Plan Mode — planifier avant d'agir

Plan Mode est un **mode de permission** où Claude explore librement le code et rédige une proposition de changements, mais **ne peut physiquement rien écrire ni exécuter de commandes destructives**. C'est une restriction technique au niveau du système de permissions, pas une simple instruction comportementale.

### Ce que Claude peut / ne peut pas faire en Plan Mode

| Action | Plan Mode | Mode normal |
|--------|-----------|-------------|
| Lire des fichiers | ✅ | ✅ |
| Exécuter des commandes shell (lecture) | ✅ (`grep`, `find`…) | ✅ |
| Poser des questions de clarification | ✅ | ✅ |
| Modifier des fichiers source | ❌ | ✅ |
| Créer / supprimer des fichiers | ❌ | ✅ |
| Écrire dans le dépôt | ❌ | ✅ |

### Comment activer Plan Mode

**a) Raccourci clavier (en cours de session)**
```
Shift+Tab   →  cycle : default → acceptEdits → plan
```

**b) Au démarrage**
```bash
claude --permission-mode plan
```

**c) Par défaut dans `settings.json`**
```json
{
  "permissions": {
    "defaultMode": "plan"
  }
}
```

**d) Pour un seul prompt**
```
/plan <ton prompt>
```

### La boîte de dialogue d'approbation

Quand Claude a terminé son plan, il le présente et propose plusieurs options :

1. **Approuver et démarrer en mode auto** — exécution autonome
2. **Approuver et accepter les éditions** — mode `acceptEdits`
3. **Approuver et revoir chaque édition** — retour au mode `default`
4. **Continuer à planifier** — rester en Plan Mode, donner du feedback
5. **Affiner avec Ultraplan** — envoyer dans une session cloud avec commentaires inline

Chaque option propose aussi de **vider le contexte de planification** avant l'exécution (économie de tokens).

### Plan Mode vs "planifie d'abord" en chat

| | Plan Mode | Instruction textuelle |
|--|-----------|----------------------|
| **Enforcement** | Restriction technique — impossible d'écrire | Comportemental — Claude *pourrait* dévier |
| **Contexte** | Peut être vidé avant exécution | Reste dans la conversation (coûte des tokens) |
| **Persistence** | Reste actif jusqu'au prochain Shift+Tab | Un seul tour, aucune garantie |
| **Agent Teams** | Workflow d'approbation formel par le lead | Pas d'équivalent pour les sous-agents |

### Plan Mode et Agent Teams (le facteur ×7)

Dans les Agent Teams, chaque coéquipier est une instance Claude Code indépendante avec son propre contexte. Si plusieurs coéquipiers fonctionnent en Plan Mode simultanément :

- Chacun lit des fichiers, exécute des commandes exploratoires, génère un plan complet
- Tout ça dans des fenêtres de contexte séparées
- **Résultat : ~7× plus de tokens** qu'une session standard

Workflow de plan en Agent Teams :
1. Le coéquipier explore et rédige un plan
2. Il envoie une **demande d'approbation au lead**
3. Le lead approuve ou renvoie avec des retours
4. Si approuvé → le coéquipier sort du Plan Mode et implémente

**Conseils de coût pour Agent Teams :**
- Utiliser Sonnet pour les coéquipiers (moins cher qu'Opus)
- Garder les équipes petites (3–5 membres max)
- Libérer les coéquipiers inactifs (ils consomment des tokens même au repos)

### Ultraplan (research preview)

Une extension de Plan Mode qui exécute la planification dans une session cloud, libérant ton terminal local. Déclenché par `/ultraplan <prompt>` ou depuis la boîte d'approbation. La session cloud fonctionne en Plan Mode ; tu révises dans le navigateur avec commentaires inline et réactions emoji.

> 💡 **Conseil pratique :** Plan Mode est particulièrement utile pour les tâches complexes — Claude explore d'abord, propose une direction, et tu valides avant qu'un seul fichier ne soit modifié. Cela évite les implémentations longues dans la mauvaise direction.

---

## Créer ses propres skills, commandes et agents

Claude Code permet de créer trois types de primitives personnalisables : les **skills** (instructions injectées dans le contexte courant), les **commandes** (format legacy, équivalent aux skills), et les **agents** (sous-agents avec leur propre fenêtre de contexte isolée).

### Les trois primitives

| Primitive | Fichier | Contexte | Invoqué par | Usage |
|-----------|---------|----------|-------------|-------|
| **Skill** | `.claude/skills/<nom>/SKILL.md` | Inline (courant) | Toi (`/nom`) ou Claude (auto) | Injecter instructions / prompts de tâche |
| **Command** (legacy) | `.claude/commands/<nom>.md` | Inline (courant) | Toi (`/nom`) ou Claude (auto) | Idem — format plus simple, toujours supporté |
| **Agent** | `.claude/agents/<nom>.md` | Isolé (propre fenêtre) | Claude (délégation) | Exécution autonome spécialisée |

> 💡 Les commands ont été fusionnées dans les skills. Un fichier `.claude/commands/deploy.md` et un skill `.claude/skills/deploy/SKILL.md` créent tous deux `/deploy` et fonctionnent identiquement. Les `.claude/commands/` restent supportés mais les skills sont recommandés (ils supportent des fichiers supplémentaires).

### Structure d'un skill

Un skill est un **dossier** contenant un fichier `SKILL.md` obligatoire, plus des fichiers optionnels :

```
mon-skill/
├── SKILL.md           # Instructions principales (obligatoire)
├── template.md        # Template à compléter (optionnel)
├── examples/
│   └── sample.md      # Exemple de sortie (optionnel)
└── scripts/
    └── validate.sh    # Script exécutable (optionnel)
```

### Frontmatter de `SKILL.md`

Tous les champs sont optionnels sauf `description` (fortement recommandé).

| Champ | Description |
|-------|-------------|
| `name` | Nom affiché, devient la commande `/nom`. Lowercase, tirets, max 64 chars. |
| `description` | Déclencheur sémantique — Claude lit ceci pour décider d'activer le skill automatiquement. Max ~250 chars utiles. |
| `argument-hint` | Affiché en autocomplétion. Ex : `[numéro-issue]` |
| `disable-model-invocation` | `true` = seul l'utilisateur peut déclencher (Claude ne voit pas la description) |
| `user-invocable` | `false` = caché du menu `/` ; seul Claude peut l'activer |
| `allowed-tools` | Outils approuvés sans confirmation pour ce skill |
| `model` | Modèle à utiliser quand ce skill est actif |
| `effort` | `low` / `medium` / `high` / `max` |
| `context` | `fork` = exécuter dans un sous-agent isolé |
| `agent` | Type de sous-agent si `context: fork` (ex : `Explore`, `Plan`) |
| `paths` | Glob patterns — le skill n'est auto-activé que sur ces fichiers |
| `hooks` | Hooks scoped à ce skill |

### Variables d'interpolation dans le contenu

| Variable | Valeur |
|----------|--------|
| `$ARGUMENTS` | Tous les arguments passés à l'invocation |
| `$ARGUMENTS[N]` | Argument N (index 0) |
| `$N` | Raccourci pour `$ARGUMENTS[N]` |
| `${CLAUDE_SESSION_ID}` | ID de session courant |
| `${CLAUDE_SKILL_DIR}` | Chemin absolu du dossier du skill |

**Injection dynamique via shell :** utilise `` !`commande` `` dans le contenu pour exécuter une commande et injecter son résultat avant que Claude lise le skill :

```markdown
## Contexte PR
- Diff : !`gh pr diff`
- Commentaires : !`gh pr view --comments`
```

### Exemple minimal

```markdown
---
name: expliquer-code
description: Explique du code avec des diagrammes et analogies. Utiliser quand l'utilisateur demande "comment fonctionne X ?" ou veut comprendre une partie du code.
argument-hint: [fichier ou fonction]
---

Quand tu expliques du code :
1. **Commence par une analogie** — comparaison avec quelque chose du quotidien
2. **Dessine un diagramme ASCII** — montre le flux
3. **Parcours le code pas à pas** — explique chaque étape
4. **Signale un piège courant** — erreur fréquente à éviter
```

### Où placer les skills

| Portée | Chemin | S'applique à |
|--------|--------|--------------|
| **Utilisateur** | `~/.claude/skills/<nom>/SKILL.md` | Tous tes projets |
| **Projet** | `.claude/skills/<nom>/SKILL.md` | Ce projet uniquement (commitable) |
| **Plugin** | Via ECC, nommé `plugin-name:skill-name` | Là où le plugin est activé |

**Monorepo :** Claude découvre automatiquement les skills dans les sous-dossiers. Si tu édites `packages/frontend/src/foo.ts`, Claude cherche aussi dans `packages/frontend/.claude/skills/`.

**Priorité en cas de conflit :** Managed > Utilisateur > Projet.

### Déclenchement automatique vs manuel

| Configuration | Toi | Claude | Description dans contexte |
|---------------|-----|--------|--------------------------|
| (défaut) | ✅ | ✅ | Toujours présente |
| `disable-model-invocation: true` | ✅ | ❌ | Absente (Claude ignore le skill) |
| `user-invocable: false` | ❌ | ✅ | Toujours présente |

**Écrire une bonne description :** mets le cas d'usage principal en premier (les descriptions sont tronquées à ~250 chars), inclus des formulations naturelles que l'utilisateur utiliserait, sois assez spécifique pour éviter les déclenchements intempestifs.

### Créer un agent personnalisé

Un agent est défini par un fichier `.md` dans `.claude/agents/` (projet) ou `~/.claude/agents/` (utilisateur) :

```markdown
---
name: mon-agent
description: Spécialiste en optimisation de requêtes SQL. Déléguer quand l'utilisateur demande d'optimiser des performances de base de données.
model: claude-sonnet-4-6
tools: Bash(psql *), Read, Grep
permissionMode: acceptEdits
maxTurns: 20
---

Tu es un expert en optimisation SQL. Analyse les requêtes, propose des index, réécris si nécessaire.
```

Champs clés d'un agent :

| Champ | Description |
|-------|-------------|
| `name` | Identifiant de l'agent |
| `description` | Déclencheur sémantique pour la délégation automatique |
| `model` | Modèle dédié (ex : `claude-haiku-4-5` pour speed/coût) |
| `tools` | Liste des outils autorisés (règles de permission identiques aux skills) |
| `permissionMode` | Mode de permission de cet agent |
| `maxTurns` | Limite de tours d'inférence |
| `skills` | Skills pré-injectés dans le prompt système de l'agent |

Gérer les agents via la commande interactive `/agents`.

---

## Mode non-interactif — scripts, CI/CD et automatisations

Le flag `-p` (print mode) permet d'utiliser Claude comme une commande shell : il reçoit un prompt, exécute la tâche, et sort. Aucune session interactive n'est ouverte. C'est la porte d'entrée pour les scripts, les pipelines CI/CD, et toute automatisation.

### Utilisation de base

```bash
claude -p "qu'est-ce que le module auth fait ?"
cat logs.txt | claude -p "résume les erreurs"
git diff main | claude -p "identifie les problèmes de sécurité potentiels"
gh pr diff "$PR" | claude -p "revue de code — que penses-tu de ces changements ?"
```

Le contenu passé via stdin est fusionné avec le prompt argument.

### Formats de sortie (`--output-format`)

| Format | Comportement |
|--------|--------------|
| `text` (défaut) | Réponse texte brute sur stdout |
| `json` | Un seul objet JSON après completion |
| `stream-json` | NDJSON — un événement JSON par ligne, en temps réel |

**Format JSON** — champs clés :
```json
{
  "result": "...",
  "session_id": "uuid-pour-reprendre",
  "is_error": false,
  "num_turns": 3,
  "total_cost_usd": 0.0042,
  "usage": { "input_tokens": 1200, "output_tokens": 350 }
}
```

Extraire le résultat : `claude -p "query" --output-format json | jq -r '.result'`

**Format stream-json** — streaming en temps réel avec filtre jq :
```bash
claude -p "écris un poème" --output-format stream-json --verbose --include-partial-messages | \
  jq -rj 'select(.type == "stream_event" and .event.delta.type? == "text_delta") | .event.delta.text'
```

### Flags importants

| Flag | Description |
|------|-------------|
| `--max-turns N` | Limite le nombre de tours d'inférence ; sort en erreur si dépassé |
| `--max-budget-usd N` | Stoppe si le coût API dépasse N dollars |
| `--allowedTools "Bash,Read,Edit"` | Outils approuvés sans confirmation |
| `--disallowedTools "WebFetch"` | Outils retirés entièrement |
| `--permission-mode acceptEdits` | Auto-approuve les éditions de fichiers |
| `--permission-mode bypassPermissions` | Skip toutes les confirmations |
| `--bare` | Mode minimal — recommandé pour CI |
| `--fallback-model sonnet` | Bascule sur ce modèle si le défaut est surchargé |
| `--output-format json` | Résultat JSON structuré |
| `--json-schema '{...}'` | Force une sortie JSON conforme à ce schéma |
| `--no-session-persistence` | N'enregistre pas la session sur disque |
| `--include-partial-messages` | Active le streaming token par token (avec `stream-json`) |

### Le mode `--bare` pour CI

```bash
claude --bare -p "lance les tests et corrige les échecs" --allowedTools "Bash,Read,Edit"
```

`--bare` (ou `CLAUDE_CODE_SIMPLE=1`) désactive au démarrage :
- CLAUDE.md, hooks, skills, plugins, MCPs
- Auto-mémoire
- OAuth / keychain → l'authentification doit venir de `ANTHROPIC_API_KEY`

**Résultat : comportement reproductible** quel que soit l'environnement. `--bare` deviendra le comportement par défaut de `-p` dans une future version.

### Usage CI/CD

```yaml
# GitHub Actions
- name: Claude Code Review
  run: |
    git diff origin/main | claude --bare -p \
      --allowedTools "Read,Bash(git *)" \
      --max-turns 10 \
      --output-format json \
      "revue de sécurité sur ce diff" | jq -r '.result'
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

**Codes de sortie :**
- `0` — succès
- `1` — erreur (ou `--max-turns` dépassé)

**Sortie structurée (`--json-schema`)** — force Claude à répondre dans un format JSON défini :
```bash
claude -p "extraits les noms de fonctions de auth.py" \
  --output-format json \
  --json-schema '{"type":"object","properties":{"functions":{"type":"array","items":{"type":"string"}}}}'
```

> 💡 **Tip :** sans `--allowedTools`, tout outil non pré-approuvé avorte la session en mode `-p`. Pré-approuve toujours les outils nécessaires avec `--allowedTools` ou configure `--permission-mode`.

---

## Extended Thinking — niveaux d'effort

Claude Code peut moduler la profondeur de raisonnement avant de répondre. Ce système s'appelle l'**effort adaptatif** : pas de budget fixe en tokens, mais une allocation dynamique selon le niveau choisi.

### Les quatre niveaux

| Niveau | Usage recommandé | Persiste ? | Modèles supportés |
|--------|-----------------|------------|-------------------|
| `low` | Tâches simples, routinières | Oui | Opus 4.6, Sonnet 4.6 |
| `medium` | **Défaut** — la plupart des tâches de code | Oui | Opus 4.6, Sonnet 4.6 |
| `high` | Debug difficile, décisions d'architecture | Oui | Opus 4.6, Sonnet 4.6 |
| `max` | Raisonnement maximal, sans contrainte de tokens | **Non** (session uniquement) | **Opus 4.6 uniquement** |

> ⚠️ `max` ne peut pas être persisté dans `settings.json`. Pour le rendre permanent, utiliser `CLAUDE_CODE_EFFORT_LEVEL=max`.
>
> Le niveau par défaut est `medium` sur Opus 4.6 et Sonnet 4.6. Un niveau plus élevé ne signifie pas toujours un meilleur résultat — Claude peut "overthink" des tâches simples.

### Comment changer le niveau d'effort

**En cours de session (slash command) :**
```
/effort low
/effort medium
/effort high
/effort max
/effort auto    # revenir au défaut du modèle
```

**Au démarrage (CLI) :**
```bash
claude --effort high
```

**Persistant dans `settings.json` :**
```json
{ "effortLevel": "high" }
```

**Via variable d'environnement (seule façon de persister `max`) :**
```bash
export CLAUDE_CODE_EFFORT_LEVEL=max
```

**Modifier le modèle dans `/model` :** les flèches gauche/droite ajustent le niveau d'effort quand Opus 4.6 ou Sonnet 4.6 est sélectionné.

**Raccourci clavier :**
```
Option+T  (macOS)  /  Alt+T  (Windows/Linux)   → activer/désactiver l'extended thinking
```

**Pour un seul prompt sans changer le niveau :**
- Inclure le mot `ultrathink` dans le prompt → active le niveau `high` pour ce tour uniquement

**Indicateur visuel :** le niveau actuel est affiché à côté du logo et du spinner (`with low effort`, `with high effort`…).

### Quand l'utiliser

- **`low`** : reformatage, renommage, refactoring mécanique, questions simples
- **`medium`** (défaut) : implémentation de features, correction de bugs courants, revue de code
- **`high`** : bugs intermittents difficiles à reproduire, conception d'architecture, analyse de performance
- **`max`** : problèmes complexes one-shot où le coût est secondaire (Opus 4.6 seulement)

### Impact sur le coût

Les tokens de réflexion sont facturés comme des tokens de sortie au tarif standard du modèle. Le bilan avec les niveaux plus élevés :
- Réponses plus lentes
- Plus de tokens générés (facturation output)
- Potentiellement moins de tours nécessaires (fewer back-and-forth)

> 💡 **Dans les skills et agents :** le champ `effort:` dans le frontmatter permet de surcharger le niveau par skill/agent, sans affecter le reste de la session.

---

## Installation

### Via le plugin Claude Code (recommandé)

```
/plugin marketplace add affaan-m/everything-claude-code
/plugin install everything-claude-code@everything-claude-code
/reload-plugins
```

### Via Git

```bash
git clone https://github.com/affaan-m/everything-claude-code.git
cd everything-claude-code && npm install
./install.sh --profile full
```

---

## Mise à jour et maintenance d'ECC

ECC suit un versioning sémantique (`v1.9.0`, `v1.10.0`…). Les mises à jour peuvent apporter de nouveaux skills, corriger des bugs, mais aussi modifier des hooks et des scripts MCP qui s'exécutent avec tes privilèges. **Toujours relire ce qui change avant d'appliquer.**

### Vérifier si une mise à jour est disponible

```bash
# SHA actuellement installé
jq '.plugins["everything-claude-code@everything-claude-code"]' \
  ~/.claude/plugins/installed_plugins_v2.json

# SHA distant (HEAD du repo)
git ls-remote https://github.com/affaan-m/everything-claude-code HEAD
```

Comparer les deux SHAs. Si différents, une mise à jour est disponible.

### Mettre à jour (installation via plugin)

```bash
claude plugin update everything-claude-code@everything-claude-code
# puis dans Claude Code :
/reload-plugins
```

### Mettre à jour (installation manuelle — git clone)

```bash
cd ~/path/to/everything-claude-code
git fetch origin main
git log --oneline HEAD..origin/main    # voir les commits avant de pull
git checkout <sha-vérifié>             # pincer à un commit précis
./install.sh --profile full            # réinstaller
```

### Ce qu'il faut relire avant chaque mise à jour

| Fichier | Pourquoi c'est critique |
|---------|-------------------------|
| `hooks/hooks.json` | Les hooks exécutent des commandes shell à chaque événement (SessionStart, PostToolUse…) |
| `.mcp.json` | Les MCPs tournent comme des sous-processus avec tes privilèges utilisateur |
| `scripts/` | Scripts invoqués par les hooks — une modification peut changer leur comportement |

**Workflow recommandé :**
1. Comparer les commits sur GitHub : `github.com/affaan-m/everything-claude-code/compare/<ancien-sha>...<nouveau-sha>`
2. Lire le `CHANGELOG.md`
3. Inspecter spécifiquement les diffs de `hooks/`, `.mcp.json`, `scripts/`
4. Appliquer seulement si satisfait

### Auto-update

Par défaut, l'auto-update est **désactivé** pour les plugins de marketplaces tierces (comme ECC). Ne pas l'activer à moins d'avoir confiance totale dans les releases du mainteneur.

```bash
DISABLE_AUTOUPDATER=1          # désactive l'auto-update de Claude Code lui-même
FORCE_AUTOUPDATE_PLUGINS=1     # force l'auto-update des plugins (déconseillé pour ECC)
```

### Règles ECC — cas particulier

> ⚠️ Les règles ECC **ne sont pas distribuées automatiquement** via le système de plugins. Après une mise à jour, tu dois manuellement re-copier les règles mises à jour depuis le dossier `rules/` du repo vers ton projet.

### Pincer à une version spécifique

```bash
# Lors de l'ajout du marketplace, pincer à un tag
/plugin marketplace add https://github.com/affaan-m/everything-claude-code#v1.9.0
```

---

## Boucles autonomes

Les boucles autonomes permettent à Claude de travailler **sans intervention de ta part** sur une série de tâches. Tu définis le pattern, Claude exécute, teste, corrige et itère seul.

### Les 4 patterns

**`sequential`** — Liste de tâches exécutées l'une après l'autre. Claude finit chaque tâche, vérifie que ça passe les quality gates, puis passe à la suivante.

```
/loop-start sequential
→ tâche 1 → tests ✅ → tâche 2 → tests ✅ → tâche 3 → ...
```

**`continuous-pr`** — Claude implémente une feature, crée une PR, passe à la suivante, en boucle. Utile pour traiter une backlog d'issues GitHub en automatique.

```
/loop-start continuous-pr
→ implémente issue #1 → PR créée → implémente issue #2 → PR créée → ...
```

**`rfc-dag`** — Exécute un plan structuré sous forme de graphe de dépendances (DAG = Directed Acyclic Graph). Les tâches qui ne dépendent pas les unes des autres s'exécutent en parallèle, les autres en séquence selon l'ordre défini dans le RFC.

```
/loop-start rfc-dag
→ tâches indépendantes en parallèle → tâches dépendantes en séquence
```

**`infinite`** — Boucle sans condition d'arrêt. Claude surveille, détecte des problèmes et les corrige en continu. À utiliser uniquement pour des tâches de monitoring ou maintenance continue.

```
/loop-start infinite
→ surveille → détecte problème → corrige → surveille → ...
```

### Modes

| Mode | Comportement |
|------|-------------|
| `safe` (défaut) | Quality gates stricts à chaque itération — s'arrête si les tests échouent |
| `fast` | Gates réduits — va plus vite mais moins de vérifications |

### Sécurité

Avant de démarrer, ECC vérifie :
- Les tests passent dans l'état courant
- La boucle a une condition d'arrêt explicite (sauf `infinite`)
- `ECC_HOOK_PROFILE` n'est pas désactivé

Un runbook est écrit dans `.claude/plans/` à chaque démarrage.

### Monitorer une boucle active

```
/loop-status           ← snapshot : phase courante, checkpoints, échecs, dérive coût
/loop-status --watch   ← rafraîchissement continu
```

`/loop-status` recommande aussi une intervention si nécessaire : continue / pause / stop.

---

## Workflows multi-modèles (CCG)

> ⚠️ **Prérequis** : ces commandes nécessitent `~/.claude/bin/codeagent-wrapper` installé séparément, avec accès à **Codex** (OpenAI) et **Gemini** (Google). Sans cette infrastructure, elles ne fonctionnent pas. Pour du développement sans setup externe, utilise `/plan` + `/prp-implement` à la place.

Le système CCG (Claude Code Gateway) permet à Claude d'orchestrer **3 modèles en parallèle** sur une même tâche :

| Modèle | Rôle | Autorité |
|--------|------|----------|
| **Claude** | Orchestrateur — lit, planifie, écrit tous les fichiers | Seul à avoir accès filesystem |
| **Codex** | Spécialiste backend — logique, algos, sécurité, performance | Autorité backend |
| **Gemini** | Spécialiste frontend — UI/UX, accessibilité, design | Autorité frontend |

**Règle fondamentale :** Codex et Gemini ne peuvent jamais modifier de fichiers — ils produisent uniquement des analyses et des diffs. Claude est le seul à écrire.

### Qui fait quoi concrètement ?

**Claude est toujours le seul à écrire du code.** Codex et Gemini produisent uniquement des diffs (patches) ou des analyses — jamais d'appels d'outils filesystem. Ce sont des **consultants** qui tournent en parallèle. Claude est le **seul exécutant**.

Les appels à Codex et Gemini se font en parallèle (`run_in_background: true`) via des sessions séparées. Chaque modèle garde sa propre `SESSION_ID` réutilisée entre les phases pour conserver le contexte.

| Phase | Parallèle ? |
|-------|------------|
| Ideation — Codex analyse + Gemini analyse | ✅ Oui |
| Planning — Codex architecture + Gemini architecture | ✅ Oui |
| Prototype — Codex backend + Gemini frontend (fullstack) | ✅ Oui |
| Audit final — Codex review + Gemini review | ✅ Oui |
| Implémentation (écriture fichiers) | ❌ Non — Claude seul, séquentiel |

```
Codex ──┐
         ├── résultats → Claude synthétise → Claude écrit les fichiers
Gemini ──┘
```

---

### Les 5 commandes CCG

**`/multi-plan`** — Phase de planification uniquement. Claude interroge Codex et Gemini **en parallèle**, croise leurs analyses, puis synthétise un plan sauvegardé dans `.claude/plan/<feature>.md`. Ne touche jamais au code de production. À la fin, te donne la commande `/multi-execute` à lancer dans une nouvelle session.

**`/multi-execute`** — Exécution du plan. Lit le plan généré par `/multi-plan`, récupère les SESSION_IDs pour reprendre les contextes Codex/Gemini, puis :
1. Route la tâche (frontend → Gemini, backend → Codex, fullstack → les deux en parallèle)
2. Récupère un prototype sous forme de diff
3. Claude **refactorise** le prototype en code production-grade
4. Audit final en parallèle par Codex + Gemini avant livraison

**`/multi-backend`** — Workflow complet backend en une commande (Research → Ideation → Plan → Execute → Optimize → Review), Codex-led. Gemini consulté pour référence uniquement.

**`/multi-frontend`** — Même workflow complet mais frontend, Gemini-led. Codex consulté pour référence uniquement.

**`/multi-workflow`** — Workflow complet fullstack avec routing automatique : frontend → Gemini, backend → Codex, les deux en parallèle pour les tâches mixtes.

---

### Flux typique

```
/multi-plan "ajouter authentification JWT"
  → Codex analyse backend  ┐ en parallèle
  → Gemini analyse frontend ┘
  → Claude synthétise → .claude/plan/jwt-auth.md
  → "Lancez /multi-execute .claude/plan/jwt-auth.md"

[nouvelle session]

/multi-execute .claude/plan/jwt-auth.md
  → Codex prototype backend  ┐ en parallèle
  → Gemini prototype frontend ┘
  → Claude refactorise et implémente
  → Codex review  ┐ audit en parallèle
  → Gemini review ┘
  → Livraison
```

---

## Système d'instincts

### Ce que c'est

Les instincts sont le mécanisme d'apprentissage continu d'ECC. Ce sont de petites règles comportementales **atomiques** — une seule idée par instinct — extraites automatiquement ou manuellement de tes sessions.

Exemples :
- *"quand j'ajoute une table en BDD, toujours créer la migration en premier"*
- *"préférer le style fonctionnel pour les fonctions utilitaires"*
- *"quand je debug, commencer par isoler le composant défaillant"*

**Différence instinct vs skill :** un instinct est une micro-règle atomique avec un score de confiance qui évolue. Un skill est un guide structuré, statique, écrit une fois. Les instincts peuvent évoluer en skills via `/evolve`.

---

### Comment les observations se collectent

ECC capture automatiquement tout ce que tu fais via des hooks PreToolUse/PostToolUse — chaque appel d'outil (Read, Edit, Bash…) est loggé dans :

```
~/.claude/homunculus/projects/<project-id>/observations.jsonl
```

Chaque ligne = un événement : timestamp, outil utilisé, input, output. Les secrets sont scrubés avant persistance.

**Tu peux voir tes observations :**
```bash
tail -20 ~/.claude/homunculus/projects/<id>/observations.jsonl
```

---

### Comment les instincts se créent

**Mode automatique — l'Observer (désactivé par défaut)**

Un agent Haiku tourne en arrière-plan, lit les observations toutes les 5 minutes, et crée un instinct dès qu'il détecte un pattern répété 3+ fois. Il cherche 4 types de patterns :
- Corrections utilisateur (tu corriges Claude sur quelque chose)
- Résolutions d'erreurs (erreur → fix)
- Workflows répétés (même séquence d'outils)
- Préférences d'outils (tu utilises toujours X plutôt que Y)

Pour l'activer :

```json
// ~/.claude/homunculus/config.json
{
  "observer": {
    "enabled": true,
    "run_interval_minutes": 5,
    "min_observations_to_analyze": 20
  }
}
```

**Mode manuel**

- `/learn` — analyse la session et extrait les patterns, demande confirmation avant de sauvegarder
- `/learn-eval` — pareil, mais ajoute une checklist anti-redondance et un verdict holistic (Save / Improve / Absorb / Drop) avant de sauvegarder

---

### Score de confiance et portée

Chaque instinct naît avec un score faible qui monte à mesure qu'il se confirme :

| Observations | Confiance |
|:---:|:---:|
| 1–2 | 0.3 |
| 3–5 | 0.5 |
| 6–10 | 0.7 |
| 11+ | 0.85 |

**Portée projet** (`~/.claude/homunculus/projects/<id>/instincts/`) — s'applique uniquement au projet courant. C'est là que tous les instincts naissent.

**Portée globale** (`~/.claude/homunculus/instincts/`) — s'applique à tous les projets. On y accède via `/promote`.

En cas de conflit d'ID entre un instinct projet et un instinct global, le projet a la priorité.

---

### Cycle de vie complet

```
Sessions Claude
      │
      ▼
Observations (hooks) ──────────────────────────────────────────┐
      │                                                         │
      ▼                                                         │
Observer (auto) ou /learn / /learn-eval (manuel)               │
      │                                                         │
      ▼                                                         │
Instinct créé [portée projet, confiance 0.3]                   │
      │                                                         │
      ▼                                                         │
Se renforce à chaque confirmation [0.3 → 0.5 → 0.7 → 0.85]    │
      │                                                         │
      ├── /promote ──→ portée globale (tous projets)           │
      │                                                         │
      ├── /evolve  ──→ regroupement en commande / skill / agent │
      │                                                         │
      └── /prune   ──→ suppression si > 30 jours sans promotion │
```

---

### Commandes et skills associés

| Commande / Skill | Type | Ce qu'il fait |
|-----------------|------|--------------|
| `/learn` | Commande | Extrait manuellement les patterns de la session et les sauvegarde comme skills dans `~/.claude/skills/learned/` |
| `/learn-eval` | Commande (Claude-only) | Idem + checklist anti-redondance + verdict holistic avant sauvegarde |
| `/instinct-status` | Commande | Affiche tous les instincts (projet + globaux) groupés par domaine avec leur score de confiance |
| `/projects` | Commande | Liste tous les projets connus avec leurs compteurs d'instincts et d'observations |
| `/promote` | Commande | Promeut des instincts de portée projet → portée globale |
| `/prune` | Commande | Supprime les instincts en attente depuis plus de 30 jours jamais promus |
| `/evolve` | Commande | Regroupe des clusters d'instincts en commandes, skills ou agents ECC — `/evolve --generate` écrit les fichiers |
| `continuous-learning-v2` | Skill | Infrastructure complète du système — hooks d'observation, Observer, CLI (`instinct-cli.py`) |
| `continuous-learning` | Skill | Version précédente (v1) — extrait des patterns en fin de session sans le système de confiance |

---

## Workflow quotidien

### Modèles recommandés

```
/model sonnet    → 80 % des tâches (implémentation, debug, tests)
/model opus      → Architecture complexe uniquement
```

### Gestion du contexte

> Commandes **natives Claude Code** (pas ECC).

| Commande   | Quand                        | Effet                                           |
| ---------- | ---------------------------- | ----------------------------------------------- |
| `/clear`   | Entre deux tâches sans lien  | Reset complet, gratuit                          |
| `/compact` | À 50-60% du contexte utilisé | Résumé intelligent, conserve les décisions clés |
| `/cost`    | À tout moment                | Affiche les dépenses de la session              |

### Variables d'environnement

#### `ECC_HOOK_PROFILE`

**Comment ça marche :** Claude Code enregistre tous les hooks du plugin et les exécute tous à chaque événement. Mais chaque hook ECC commence par appeler `run-with-flags.js` qui lit `ECC_HOOK_PROFILE` et **sort immédiatement** si le profil actuel ne correspond pas. C'est donc ECC qui filtre en interne — pas Claude Code. Changer `ECC_HOOK_PROFILE` ne retire pas de hooks de la liste, ça change lesquels passent le filtre.

**Répartition réelle par profil :**

| Hook                                                                                                                                                                                              | minimal | standard | strict |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :-----: | :------: | :----: |
| Toujours actifs (pas de filtre profil) : `block-no-verify`, `auto-tmux-dev`, `session-start`, `command-log`                                                                                       |    ✓    |    ✓     |   ✓    |
| Lifecycle : `session-end`, `evaluate-session`, `cost-tracker`, `session-end-marker`                                                                                                               |    ✓    |    ✓     |   ✓    |
| Qualité & sécurité : `config-protection`, `quality-gate`, `mcp-health-check`, `format-typecheck`, `console-warn`, `doc-file-warning`, `suggest-compact`, `continuous-learning`, `desktop-notify`… |    —    |    ✓     |   ✓    |
| Friction maximale : `tmux-reminder`, `git-push-reminder`, `commit-quality`                                                                                                                        |    —    |    —     |   ✓    |

| Valeur     | Défaut | Quand l'utiliser                                                           |
| ---------- | :----: | -------------------------------------------------------------------------- |
| `minimal`  |        | Quand les hooks ralentissent trop le workflow — seul le lifecycle tourne   |
| `standard` |   ✓    | Usage quotidien : qualité et sécurité sans friction excessive              |
| `strict`   |        | Avant une release ou sur du code critique : tous les rappels et guardrails |

**Option A — variable d'environnement (session courante)**

```bash
export ECC_HOOK_PROFILE=standard

# Désactiver des hooks spécifiques sans changer de profil
export ECC_DISABLED_HOOKS="pre:bash:tmux-reminder,post:edit:typecheck"
```

**Option B — `settings.json` (persistant, recommandé)**

Claude Code lit le champ `env` de `~/.claude/settings.json` et l'injecte automatiquement à chaque session — plus besoin d'exporter dans le shell.

```json
{
  "env": {
    "ECC_HOOK_PROFILE": "minimal"
  }
}
```

Pour un projet spécifique, utilise `.claude/settings.json` à la racine du repo (surcharge le global).

---

#### `MAX_THINKING_TOKENS`

**Qu'est-ce que le thinking ?**

Avant de répondre, Claude raisonne en interne — il explore des approches, évalue des options, décompose le problème. Ce processus se passe dans un espace caché que tu ne vois jamais dans la conversation :

```
Tu : "refactorise cette fonction"
         ↓
[thinking — invisible pour toi]
  "Qu'est-ce que cette fonction fait ?
   Quelles dépendances ? Quel pattern ?
   Est-ce que ça casse les tests ?"
         ↓
Claude : "Voici le refactoring…"
```

Ce raisonnement est facturé comme des **output tokens** — la catégorie la plus chère. Si Claude pense 20 000 tokens avant de répondre, tu paies 20 000 output tokens que tu ne vois jamais.

Claude Sonnet 4.6 utilise l'**adaptive thinking** : il décide lui-même combien penser selon la complexité de la tâche. `MAX_THINKING_TOKENS` est le plafond qu'il ne peut pas dépasser.

**Quand le thinking vaut son coût :**

| Tâche | Thinking utile ? |
|-------|-----------------|
| Architecture, décisions structurantes, debug complexe | ✓ améliore vraiment la qualité |
| Ajouter un `console.log`, modifier un import, tâche simple | ✗ gaspillage — Claude sait déjà |

**Les valeurs :**

| Valeur               | Effet                                                     |
| -------------------- | --------------------------------------------------------- |
| `31999` (défaut)     | Budget maximal — Claude pense autant qu'il veut           |
| `10000` (recommandé) | Suffisant pour 95% des tâches, réduit ~70% du coût caché |
| `8000`               | Valeur mentionnée dans la doc officielle pour économiser  |
| `0`                  | Thinking désactivé — uniquement pour les tâches triviales |

```bash
export MAX_THINKING_TOKENS=10000
```

> Pour voir le thinking dans le terminal : `Ctrl+O`. Pour le désactiver complètement via l'UI : `Option+T` (macOS) / `Alt+T`. Pour changer l'effort par session : `/effort low|medium|high`.

---

#### `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`

**Qu'est-ce que la fenêtre de contexte ?**

Claude ne se souvient de rien entre les sessions — il travaille avec une fenêtre de contexte qui contient tout ce qu'il voit en ce moment : l'historique de la conversation, les fichiers lus, les outputs de commandes, les instructions CLAUDE.md, les skills chargés. Cette fenêtre a une taille maximale (en tokens). Quand elle se remplit, Claude ne peut plus traiter de nouvelles informations sans en sacrifier d'autres.

```
[Début de session]
  CLAUDE.md + skills + règles ECC         → toujours présent
  Ton prompt + réponses de Claude         → s'accumule
  Outputs de commandes / fichiers lus     → s'accumule vite
                                            ↓
              [Fenêtre pleine à X%]
                                            ↓
              Compaction automatique
```

**Ce que fait la compaction :**

Claude Code gère automatiquement le contexte quand tu approches la limite. Il procède en deux temps :
1. **Supprime les anciens outputs d'outils** — les résultats de commandes passées qui ne sont plus utiles
2. **Résume la conversation** si ce n'est pas suffisant — il compresse l'historique en un résumé

Ce qui est **préservé** : tes requêtes, les snippets de code importants, les décisions clés.
Ce qui peut être **perdu** : les instructions détaillées données tôt dans la conversation, le contexte fin des échanges anciens.

**Pourquoi 95% c'est trop tard :**

À 95% de remplissage, Claude opère déjà avec un contexte dégradé depuis un moment. Le résumé produit à cet instant est de moindre qualité car Claude manque lui-même de place pour bien synthétiser.

**Les valeurs :**

| Valeur            | Comportement                                                        |
| ----------------- | ------------------------------------------------------------------- |
| `95` (défaut)     | Compaction très tardive — contexte dégradé avant même la compaction |
| `50` (recommandé) | Compaction à mi-chemin — meilleure qualité, plus de marge           |

```bash
export CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50
```

**Alternatives à la compaction automatique :**

- `/compact` — force une compaction maintenant, avec focus optionnel : `/compact focus on the API changes`
- `/clear` — repart à zéro (plus radical, gratuit)
- Ajoute une section `# Compact instructions` dans ton `CLAUDE.md` pour dire à Claude quoi préserver lors de chaque compaction

---

#### `CLAUDE_CODE_SUBAGENT_MODEL`

**Contexte : qu'est-ce qu'un sous-agent ?**

Quand Claude exécute l'outil `Agent` (visible dans les logs comme `Launching agent...`), il spawn un sous-processus Claude indépendant pour traiter une sous-tâche en parallèle ou en isolation. ECC en fait un usage intensif : chaque `code-reviewer`, `typescript-reviewer`, `build-error-resolver`, etc. tourne en tant que sous-agent distinct.

**Le problème par défaut :** sans cette variable, chaque sous-agent hérite du modèle parent — si tu utilises Sonnet, chaque revue de code, chaque recherche exploratoire et chaque correction de build lance un Sonnet complet. Sur une session ECC typique, Claude peut spawner **5 à 15 sous-agents** par tâche complexe.

**Ce que fait la variable :** elle fixe le modèle utilisé *uniquement* par les sous-agents, sans toucher au modèle principal. Tu gardes toute la puissance de Sonnet pour le raisonnement principal, et les sous-tâches mécaniques tournent sur le modèle le moins cher.

| Valeur                          | Coût relatif | Quand l'utiliser                                                                     |
| ------------------------------- | ------------ | ------------------------------------------------------------------------------------ |
| _(hérité, défaut)_              | 100%         | Jamais — c'est du gaspillage pur                                                     |
| `claude-haiku-4-5-20251001` ✓   | ~10%         | Exploration, recherche de fichiers, exécution de tests, reviews mécaniques           |
| `claude-sonnet-4-6`             | ~40%         | Sous-tâches nécessitant du raisonnement approfondi (refactos complexes, architecture)|

> **Règle pratique :** Haiku suffit pour 90% des sous-agents ECC. Si un reviewer rate quelque chose d'évident, passe à Sonnet.

```bash
export CLAUDE_CODE_SUBAGENT_MODEL=claude-haiku-4-5-20251001
```

---

#### Configuration recommandée complète

Dans `~/.claude/settings.json` (persistant, sans avoir à exporter à chaque session) :

```json
{
  "env": {
    "MAX_THINKING_TOKENS": "10000",
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "50",
    "CLAUDE_CODE_SUBAGENT_MODEL": "haiku",
    "ECC_HOOK_PROFILE": "standard"
  }
}
```

---

## Commandes slash (72 documentés sur 156)

### C'est quoi ?

**Une commande slash** = ce que tu tapes avec `/`. C'est une syntaxe d'invocation.
**Un skill** = un fichier Markdown avec un prompt structuré. C'est du contenu.

Ce sont deux concepts séparés, mais liés : quand un skill existe, il devient automatiquement accessible via `/nom-du-skill`. Un skill *expose* une commande slash — ce n'est pas un synonyme.

La différence se voit dans ce qu'il y a derrière :

| Ce que tu tapes | Ce qu'il y a derrière |
| --------------- | --------------------- |
| `/compact`      | Logique codée dans Claude Code — pas de fichier, pas de prompt |
| `/plan`         | Un fichier `SKILL.md` qu'ECC a installé, lu et interprété par Claude |

Il existe donc trois catégories de commandes slash :

**1. Commandes built-in** — intégrées à Claude Code, logique fixe, pas de fichier derrière :
`/help`, `/config`, `/cost`, `/model`, `/compact`, `/clear`, `/status`, `/mcp`, `/permissions`…

**2. Commandes custom via `.claude/commands/`** — format historique de Claude Code, encore officiellement supporté. Un fichier `.md` par commande, placé dans `.claude/commands/`. ECC utilise ce format pour ses 72 commandes documentées ci-dessous.

**3. Commandes custom via `.claude/skills/`** — nouveau format recommandé par Anthropic. Un dossier par skill contenant un `SKILL.md` + éventuellement des fichiers annexes (templates, exemples, scripts). ECC utilise ce format pour ses 156 skills.

Les deux formats sont **fonctionnellement identiques** pour l'auto-invocation — Claude utilise le champ `description` du frontmatter dans les deux cas pour décider de les déclencher. La seule vraie différence est organisationnelle : les skills permettent de bundler des fichiers annexes.

| Format | Structure | Quand l'utiliser |
| ------ | --------- | ---------------- |
| `.claude/commands/nom.md` | Un seul fichier | Commandes simples, sans fichiers annexes |
| `.claude/skills/nom/SKILL.md` | Dossier + fichiers | Commandes complexes avec templates, exemples… |

---

### Qui les déclenche — toi ou Claude ?

Le mécanisme est le même pour les commandes et les skills : **Claude lit la `description` du frontmatter** et décide si c'est pertinent pour le contexte actuel.

**Ce qui détermine si Claude peut auto-invoquer :**

- **`description` présente** → Claude peut inférer la pertinence et déclencher automatiquement
- **Pas de `description`** → Claude n'a aucune guidance, invocation manuelle uniquement
- **`TRIGGER when` / `DO NOT TRIGGER when` dans la description** → guidance explicite, auto-invocation la plus fiable (seulement 3 skills ECC : `blueprint`, `prompt-optimizer`, `token-budget-advisor`)
- **`disable-model-invocation: true`** → bloqué explicitement, Claude ne peut jamais l'invoquer (et la description n'est même pas chargée dans le contexte)

**Dans ECC concrètement :**

| Type | Toi (via `/`) | Claude (auto) |
| ---- | ------------- | ------------- |
| Built-in (`/compact`, `/clear`…) | Oui | **Jamais** |
| 20 commandes sans `description` | Oui | **Non** — pas de guidance |
| 52 commandes avec `description` | Oui (sauf `learn-eval`) | **Possible** — Claude infère depuis la description |
| `setup-pm` | Oui | **Non** — `disable-model-invocation: true` |
| 3 skills avec `TRIGGER when` | Oui | **Oui** — guidance explicite et fiable |
| 153 skills sans `TRIGGER when` | Oui | **Possible** — Claude infère depuis la description |

---

### Ce qui contrôle le déclenchement (pour tes propres fichiers)

Deux flags frontmatter permettent de forcer un comportement :

**`user-invocable: false`** — cache du menu `/` (Claude seul peut l'invoquer)
**`disable-model-invocation: true`** — empêche Claude de le déclencher automatiquement

Ces flags s'appliquent aux deux formats (`commands/` et `skills/`).

---

### Comment les voir et les utiliser ?

- Tape `/` dans le prompt pour voir toutes les commandes disponibles avec filtrage au fil de frappe
- Passe des arguments : `/plan "ma feature"` → reçu comme `$ARGUMENTS` dans le skill
- Les commandes marquées **[shim]** ci-dessous sont de simples redirections vers le skill du même nom

---

### Les shims — commandes legacy

Un **shim** (prononcé "chime") est une fine couche de compatibilité qui ne fait rien par elle-même : elle redirige vers autre chose.

Dans ECC, un shim est une commande dans `.claude/commands/` dont l'unique rôle est de déléguer au skill du même nom dans `.claude/skills/`. C'est une commande qui dit juste "va voir le skill".

**Pourquoi ça existe ?**

ECC a commencé avec des commandes dans `commands/`. Au fil des versions, certaines ont migré vers le format `skills/` (plus puissant : dossier, fichiers annexes, meilleure organisation). Pour ne pas casser les habitudes des utilisateurs qui tapaient `/python-review` ou `/context-budget`, les anciens fichiers `commands/` ont été transformés en shims — ils restent là, mais ne font que passer le relais au skill.

**Exemple concret — `/context-budget` :**

```markdown
# Context Budget Optimizer (Legacy Shim)

Use this only if you still invoke /context-budget.
The maintained workflow lives in skills/context-budget/SKILL.md.

## Delegation
Apply the context-budget skill.
- Pass through --verbose if the user supplied it.
```

Le fichier `commands/context-budget.md` ne contient aucune logique — il dit juste "applique le skill `context-budget`". Tout le vrai travail est dans `skills/context-budget/SKILL.md`.

**Les 11 shims ECC (marqués ⚠️ Oui dans la colonne Legacy du tableau) :**

| Commande | Redirige vers |
|----------|--------------|
| `context-budget` | skill `context-budget` |
| `devfleet` | skill `devfleet` |
| `docs` | skill `doc-updater` |
| `e2e` | skill `e2e-testing` |
| `eval` | skill `eval-harness` |
| `orchestrate` | skill `enterprise-agent-ops` |
| `prompt-optimize` | skill `prompt-optimizer` |
| `rules-distill` | skill `rules-distill` |
| `tdd` | skill `tdd-workflow` |
| `verify` | skill `verification-loop` |
| `claw` | skill `nanoclaw-repl` |

**En pratique :** tu peux continuer à taper `/context-budget` ou `/tdd` — ça fonctionne. Mais si tu veux lire le code source de ce que la commande fait vraiment, il faut aller dans le skill, pas dans le fichier `commands/`.

---

### Portée : personnelle vs projet

Les skills peuvent être définis à deux niveaux :

| Niveau | Emplacement | Portée |
| ------ | ----------- | ------ |
| Personnel | `~/.claude/skills/<nom>/SKILL.md` | Tous tes projets |
| Projet | `.claude/skills/<nom>/SKILL.md` | Ce projet uniquement (versionnable via git) |

ECC installe ses skills au niveau personnel (`~/.claude/`). Tes skills projet ont priorité sur ECC si le nom entre en conflit.

---

## Gestion des sessions

### Le problème

Claude n'a pas de mémoire entre les sessions. Quand tu fermes et rouvres Claude Code, il repart de zéro — il ne sait pas sur quoi vous travailliez, ce qui a échoué, où vous en étiez. Sur une feature qui s'étale sur plusieurs jours ou qui atteint les limites de contexte, c'est un problème.

ECC résout ça avec un système de fichiers de session : à la fin de chaque session, un fichier de résumé est écrit sur disque. Au début de la session suivante, Claude le lit et reprend exactement où il s'était arrêté.

---

### `/save-session` — sauvegarder l'état courant

Écrit un fichier `.tmp` horodaté dans `~/.claude/session-data/` avec tout ce qui s'est passé dans la session.

**Déclenché automatiquement** par un hook ECC à la fin de chaque session — c'est pourquoi tu as déjà des fichiers dans ton `session-data/` sans jamais avoir lancé la commande manuellement :

```
~/.claude/session-data/
├── 2026-04-03-GitHub-session.tmp
├── 2026-04-04-GitHub-session.tmp
└── 2026-04-05-GitHub-session.tmp
```

Tu peux aussi le lancer manuellement à tout moment, par exemple avant d'atteindre la limite de contexte :

```bash
/save-session
```

**Ce que le fichier contient :**

| Section | Contenu |
|---------|---------|
| **What We Are Building** | Description du projet/feature avec assez de contexte pour repartir de zéro |
| **What WORKED** | Ce qui fonctionne, avec les preuves (test passé, Postman 200, vu en browser…) |
| **What Did NOT Work** | ⚠️ Section la plus critique — chaque approche ratée avec la raison exacte, pour ne pas la retenter |
| **What Has NOT Been Tried Yet** | Idées prometteuses pas encore essayées |
| **Current State of Files** | Chaque fichier touché avec son statut (✅ Complete / In Progress / ❌ Broken / Not Started) |
| **Decisions Made** | Choix d'architecture et pourquoi, pour ne pas les remettre en question |
| **Blockers & Open Questions** | Ce qui bloque ou reste sans réponse |
| **Exact Next Step** | La prochaine action précise pour reprendre sans réfléchir où recommencer |

Après écriture, Claude affiche le fichier et demande confirmation avant de clore.

> La section "What Did NOT Work" est la plus importante : sans elle, la session suivante va retenter les mêmes approches ratées.

---

### `/resume-session` — reprendre une session

Charge un fichier de session et produit un briefing structuré avant de reprendre le travail.

```bash
/resume-session                          # charge le fichier le plus récent
/resume-session 2026-04-03               # charge la session de ce jour-là
/resume-session ~/.claude/session-data/2026-04-03-GitHub-session.tmp  # fichier précis
```

Claude lit le fichier, puis produit ce briefing dans un format fixe :

```
SESSION LOADED: ~/.claude/session-data/2026-04-05-GitHub-session.tmp
════════════════════════════════════════════════

PROJECT: factory-writer — plugin.md ECC v1.9.0

WHAT WE'RE BUILDING:
[résumé en 2-3 phrases]

CURRENT STATE:
✅ Working: 3 items confirmés
   In Progress: plugin.md (descriptions en cours)
   Not Started: commandes save-session → zap

WHAT NOT TO RETRY:
None

OPEN QUESTIONS / BLOCKERS:
—

NEXT STEP:
Continuer les descriptions dans l'ordre du tableau — prochaine : save-session

════════════════════════════════════════════════
Ready to continue. What would you like to do?
```

**Après le briefing : Claude attend.** Il ne touche à aucun fichier, ne commence rien. C'est toi qui dis quoi faire.

**Cas gérés automatiquement :**
- Fichier de plus de 7 jours → `WARNING: This session is from N days ago`
- Fichier référence un fichier supprimé → `WARNING: path/to/file.ts not found on disk`
- Plusieurs sessions le même jour → charge la plus récente
- Fichier vide ou corrompu → message d'erreur clair

---

### Workflow typique

```
Fin de session J     →   hook déclenche /save-session automatiquement
                         → ~/.claude/session-data/YYYY-MM-DD-session.tmp créé

Début de session J+1 →   /resume-session
                         → briefing complet
                         → tu dis "continue" ou donnes une nouvelle direction
                         → travail reprend exactement où il s'était arrêté
```

Tu peux aussi lancer `/save-session` manuellement en cours de session si tu sens que le contexte devient trop chargé, puis ouvrir une nouvelle session et faire `/resume-session` pour repartir proprement.

---

## Santa Loop — revue adversariale convergente

### Le nom

Le nom vient du **Père Noël (Santa)** et de sa liste naughty/nice. Avant Noël, Santa classe les enfants en deux catégories — les sages qui méritent des cadeaux, les vilains qui n'en auront pas. Ici c'est ton code qui passe l'évaluation :

- **NICE** → les deux reviewers approuvent → le code est pushé
- **NAUGHTY** → au moins un reviewer trouve des problèmes → correction obligatoire avant de recommencer

La **"loop"** c'est la boucle de correction : Santa ne valide pas jusqu'à ce que la liste soit propre.

---

### Le problème que ça résout

Un seul reviewer a des angles morts. Claude Opus peut rater des problèmes de sécurité qu'un modèle entraîné différemment aurait attrapés, et inversement. La solution : deux modèles **différents**, avec **aucun contexte partagé**, qui évaluent le même code indépendamment. Si les deux approuvent, les chances qu'un problème soit passé à travers les deux filets sont très faibles.

---

### Déroulement

```
Code à revoir
     ↓
Scope (arguments ou git diff HEAD)
     ↓
Rubric PASS/FAIL construite (correction, sécurité, erreurs, complétude…)
     ↓
┌─────────────────────┐   ┌─────────────────────┐
│   Reviewer A        │   │   Reviewer B        │
│   Claude Opus       │   │   GPT (Codex CLI)   │
│   agent isolé       │   │   ou Gemini 2.5 Pro │
│                     │   │   ou Claude Opus*   │
└─────────────────────┘   └─────────────────────┘
         ↓ en parallèle ↓
         Verdict gate
         ↙           ↘
      NICE           NAUGHTY
   (les deux PASS)  (au moins un FAIL)
       ↓                  ↓
     PUSH           Fix des issues flaggées
                         ↓
                    Commit "fix: round N"
                         ↓
                  Nouveaux reviewers (round N+1)
                  max 3 rounds
                         ↓
                  Si encore NAUGHTY → escalade manuelle
```

*\* fallback si aucun CLI externe installé — avec avertissement : la diversité de modèles est perdue, seul l'isolement de contexte subsiste*

---

### Les reviewers

| Reviewer | Modèle | Condition |
|----------|--------|-----------|
| A | Claude Opus | Toujours — garantit au moins un reviewer solide |
| B | GPT-5.4 via Codex CLI | Si `codex` est installé (préféré) |
| B | Gemini 2.5 Pro via Gemini CLI | Si `gemini` installé, pas `codex` |
| B | Claude Opus (second agent isolé) | Fallback uniquement |

La diversité de modèles est l'objectif clé pour le Reviewer B. GPT et Gemini ont des données d'entraînement différentes, des biais différents, des angles morts différents — c'est ça qui donne une vraie indépendance.

---

### La rubric

Chaque critère a une condition PASS/FAIL objective — pas de "c'est bien écrit" subjectif. La rubric de base :

| Critère | Condition PASS |
|---------|---------------|
| Correction | Logique saine, pas de bugs, edge cases gérés |
| Sécurité | Pas de secrets, injection, XSS, OWASP Top 10 |
| Gestion d'erreurs | Erreurs traitées explicitement, aucune avalée silencieusement |
| Complétude | Toutes les exigences couvertes |
| Cohérence interne | Pas de contradictions entre fichiers |
| Pas de régression | Les changements ne cassent pas l'existant |

Des critères spécifiques au langage s'ajoutent automatiquement (type safety TypeScript, memory safety Rust, migration safety SQL…).

---

### Les règles clés

- **Reviewers frais à chaque round** — pas de mémoire du round précédent. Évite l'anchoring bias : un reviewer qui a déjà vu les corrections a tendance à les valider même si elles sont insuffisantes.
- **Fix uniquement ce qui est flaggé** — pas de refactor opportuniste pendant la correction.
- **Commit à chaque round NAUGHTY** — les fixes sont préservés même si la loop est interrompue.
- **Push uniquement après NICE** — jamais en cours de loop.
- **Maximum 3 rounds** — au-delà, escalade manuelle. Le problème est probablement architectural et ne se résoudra pas en bouclant.

---

### Quand l'utiliser

`/santa-loop` est adapté pour du code **critique avant merge** : authentification, paiements, migrations de base de données, APIs publiques. Pour du code ordinaire, `/code-review` ou `/python-review` suffisent.

---

## Codemaps — documentation d'architecture pour Claude

### Le problème

Sur un projet avec des dizaines de fichiers, Claude perd du temps à explorer le codebase avant chaque tâche — il doit retrouver où sont les routes, comment les services s'enchaînent, quelles tables existent. Ce temps d'exploration consomme du contexte et ralentit le travail.

Les codemaps résolvent ça : une documentation d'architecture compacte, mise à jour manuellement après chaque changement majeur, que Claude lit en début de session pour avoir une vue globale immédiate.

---

### Ce que c'est

5 fichiers Markdown dans `docs/CODEMAPS/`, **volontairement minimalistes**. Pas de prose, pas d'explications longues — que des chemins, des signatures et des relations. Chaque fichier cible moins de 1000 tokens pour être chargé efficacement dans le contexte de Claude.

| Fichier | Contenu |
|---------|---------|
| `architecture.md` | Diagramme système haut niveau, frontières de services, flux de données |
| `backend.md` | Routes API, chaîne de middleware, mapping service → repository |
| `frontend.md` | Arbre de pages, hiérarchie de composants, flux de state management |
| `data.md` | Tables de BDD, relations, historique des migrations |
| `dependencies.md` | Services externes, intégrations tierces, librairies partagées |

**Exemple de contenu `backend.md` :**

```markdown
<!-- Generated: 2026-04-05 | Files scanned: 142 | Token estimate: ~800 -->

## Routes
POST /api/users     → UserController.create   → UserService.create   → UserRepo.insert
GET  /api/users/:id → UserController.get      → UserService.findById → UserRepo.findById
DELETE /api/users/:id → UserController.delete → UserService.delete   → UserRepo.softDelete

## Key Files
src/controllers/user.ts  (HTTP layer, 95 lines)
src/services/user.ts     (business logic, 120 lines)
src/repos/user.ts        (database access, 80 lines)

## Dependencies
- PostgreSQL (primary data store)
- Redis (session cache, rate limiting)
- Stripe (payment processing)
```

Pas de blocs de code, pas de documentation de fonctions — juste assez pour que Claude sache où chercher sans avoir à explorer.

---

### `/update-codemaps` — générer ou mettre à jour

Lance l'analyse du codebase et produit ou régénère les 5 fichiers.

**Protection contre les écrasements accidentels :**
- Diff ≤ 30% par rapport à l'existant → mise à jour en place silencieuse
- Diff > 30% → affiche ce qui change et demande confirmation avant d'écraser

**Rapport de diff** écrit dans `.reports/codemap-diff.txt` après chaque exécution :
- Fichiers ajoutés / supprimés / modifiés depuis le dernier scan
- Nouvelles dépendances détectées
- Changements d'architecture (nouvelles routes, nouveaux services)
- Avertissements si un codemap n'a pas été mis à jour depuis 90+ jours

---

### `/update-docs` — mettre à jour la documentation générale

Commande complémentaire qui met à jour les READMEs, commentaires, et guides en cohérence avec le code. Là où `/update-codemaps` génère une vue structurelle pour Claude, `/update-docs` maintient la documentation lisible par les humains.

---

### Quand les lancer

```
Feature importante mergée     →   /update-codemaps
Refactoring structurel terminé →   /update-codemaps
Changement d'API publique     →   /update-docs
Nouvelle dépendance externe   →   /update-codemaps (dependencies.md)
Avertissement "90 jours"      →   /update-codemaps
```

> Les codemaps sont particulièrement utiles combinés avec `/resume-session` : Claude charge les codemaps en début de session et dispose immédiatement d'une carte du projet sans avoir à l'explorer.

---

## Le workflow PRP

### C'est quoi PRP ?

**PRP** est un workflow de développement structuré, adapté du projet open-source **[PRPs-agentic-eng](https://github.com/Wirasm/PRPs-agentic-eng)** par **Wirasm**. Le sigle n'a pas de définition officielle dans les sources — il désigne simplement la suite de commandes `prp-*`.

L'idée centrale : avant d'écrire une seule ligne de code, produire un **plan auto-suffisant** qui capture tout le contexte dont Claude a besoin pour implémenter sans jamais poser de questions supplémentaires. Patterns du codebase, conventions de nommage, gestion d'erreurs, imports, pièges connus — tout est capturé une fois dans le plan, référencé tout au long de l'implémentation.

> **Philosophie fondamentale** : si tu aurais besoin de fouiller le codebase pendant l'implémentation, capture cette connaissance maintenant dans le plan.

Un PRP répond au problème classique où Claude commence à coder, bloque sur un pattern qu'il n'a pas vu, pose des questions, perd le fil. Avec un bon plan, il implémente en **une seule passe**, du début à la fin.

---

### Les 5 commandes PRP

```
(optionnel)
/prp-prd   →   /prp-plan   →   /prp-implement   →   /prp-commit   →   /prp-pr
   1/5             2/5               3/5                  4/5              5/5
```

#### 1. `/prp-prd` — Générer le Product Requirements Document *(optionnel)*

Point de départ si tu ne sais pas encore exactement quoi construire. Claude joue le rôle d'un product manager qui **part du problème**, pas de la solution.

Il te pose 3 séries de questions avec des étapes de validation intermédiaires :
1. **Foundation** : Qui a ce problème ? Quelle douleur concrète ? Pourquoi maintenant ?
2. **Grounding** : Recherche marché + exploration du codebase existant
3. **Decisions** : MVP, must-haves, hypothèse testable, hors-scope explicite

Résultat : un fichier `.claude/PRPs/prds/{nom}.prd.md` avec le problème, les utilisateurs cibles, les métriques de succès, et les phases d'implémentation découpées.

> **Anti-pattern évité** : Claude ne remplit pas les sections avec du flan. Si une information manque, il écrit "TBD - needs research" plutôt qu'inventer.

#### 2. `/prp-plan` — Créer le plan d'implémentation

Prend en entrée soit une description libre, soit un fichier `.prd.md`. Analyse le codebase en profondeur dans **8 catégories** :

| Catégorie | Ce que Claude cherche |
|-----------|----------------------|
| Implémentations similaires | Features analogues déjà en place |
| Conventions de nommage | Comment fichiers, fonctions, classes sont nommés |
| Gestion d'erreurs | Comment les erreurs sont attrapées, propagées, loggées |
| Patterns de logs | Ce qui est loggé, à quel niveau, dans quel format |
| Types & interfaces | Où sont définis les types, comment organisés |
| Patterns de tests | Structure des tests, setup/teardown, assertions |
| Configuration | Fichiers de config, variables d'env, feature flags |
| Dépendances | Packages et modules internes utilisés |

Résultat : un fichier `.claude/PRPs/plans/{nom}.plan.md` avec chaque tâche découpée, chaque tâche ayant son ACTION, son pattern à reproduire (avec extrait de code réel du codebase), ses imports, ses pièges, et sa commande de validation.

**Test du "développeur inconnu"** : avant de finaliser, Claude vérifie qu'un développeur qui ne connaît pas le codebase pourrait implémenter la feature en lisant uniquement ce plan, sans chercher quoi que ce soit ailleurs.

#### 3. `/prp-implement` — Exécuter le plan

La commande la plus rigoureuse. Elle exécute le plan en 6 phases avec une règle absolue : **jamais d'état cassé accumulé**.

```
Phase 0 : DETECT    → détecte npm/yarn/pnpm/bun et les scripts de validation disponibles
Phase 1 : LOAD      → lit le plan, extrait tâches + patterns + commandes de validation
Phase 2 : PREPARE   → branche git (crée ou synchronise)
Phase 3 : EXECUTE   → implémente tâche par tâche — typecheck après CHAQUE fichier modifié
Phase 4 : VALIDATE  → 5 niveaux : lint → tests unitaires → build → intégration → edge cases
Phase 5 : REPORT    → rapport dans .claude/PRPs/reports/, plan archivé dans completed/
```

La différence avec un simple `/plan` suivi d'implémentation : Claude **ne peut pas avancer** si le code est cassé. Chaque modification est validée immédiatement. Si le typecheck échoue après un fichier → correction obligatoire avant de passer au suivant.

#### 4. `/prp-commit` — Commit intelligent

Commit en langage naturel. Tu décris ce que tu veux commiter, Claude lit le `git status` + `git diff` pour identifier les bons fichiers, les stage, et génère un message conventionnel.

| Tu dis | Ce qui se passe |
|--------|----------------|
| `/prp-commit` | Stage tout, génère le message |
| `/prp-commit staged` | Commit ce qui est déjà stagé |
| `/prp-commit the auth changes` | Trouve les fichiers d'auth dans le diff, les stage |
| `/prp-commit except tests` | Stage tout sauf les fichiers de test |
| `/prp-commit *.ts` | Stage uniquement les fichiers TypeScript |
| `/prp-commit only new files` | Stage uniquement les fichiers non trackés |

Message généré : `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `perf:`, `ci:` — impératif, sous 72 caractères.

#### 5. `/prp-pr` — Créer la Pull Request

Crée la PR GitHub depuis la branche courante. Vérifie d'abord que tu n'es pas sur `main`, que le working directory est propre, et qu'il y a bien des commits à pousser. Ensuite :

1. Cherche un template PR dans `.github/` (si existant, l'utilise)
2. Analyse les commits pour générer le titre (`feat:`, `fix:`…)
3. Pousse la branche (`git push -u origin HEAD`)
4. Crée la PR via `gh pr create`
5. Vérifie l'état des CI checks
6. Relie les artifacts PRP existants (plan, rapport) dans le corps de la PR

Si la branche a divergé : rebase automatique avant le push. Jamais de `--force`, uniquement `--force-with-lease`.

---

### Quand utiliser le workflow PRP ?

| Situation | Recommandation |
|-----------|---------------|
| Feature simple, bien connue | `/plan` suffit — plus rapide |
| Feature complexe, codebase peu connu | `/prp-plan` + `/prp-implement` |
| Nouveau projet, besoin de clarifier quoi construire | Commencer par `/prp-prd` |
| Besoin de 0 régression sur une feature critique | `/prp-implement` pour la validation systématique |

---

### Fichiers produits

```
.claude/
└── PRPs/
    ├── prds/
    │   └── {feature}.prd.md          # Product Requirements Document
    ├── plans/
    │   ├── {feature}.plan.md         # Plan d'implémentation
    │   └── completed/
    │       └── {feature}.plan.md     # Archivé après exécution
    └── reports/
        └── {feature}-report.md       # Rapport post-implémentation
```

---

### Planification & Architecture

| Commande              | Usage                          | Ce que ça fait                                                                                      |
| --------------------- | ------------------------------ | --------------------------------------------------------------------------------------------------- |
| `/plan "description"` | Avant de commencer une feature | Lit le codebase, découpe en étapes ordonnées, identifie les fichiers et risques                     |
| `/blueprint`          | Projet multi-sessions complexe | Décompose l'objectif en étapes ordonnées, chacune avec son brief de contexte et revue adversariale  |
| `/prp-prd "objectif"`   | En début de projet                   | Générateur interactif de PRD (Product Requirements Document) — part du problème, pas de la solution |
| `/prp-plan "feature"`   | Après le PRD                         | Plan d'implémentation détaillé avec analyse du codebase existant                                    |
| `/prp-implement`        | Après `/prp-plan`                    | Exécute le plan avec boucles de validation à chaque étape                                           |
| `/prp-pr`               | Feature terminée                     | Crée la PR GitHub depuis la branche courante                                                        |
| `/prp-commit "message"` | Avant un commit                      | Commit en langage naturel avec ciblage intelligent des fichiers                                     |

### Développement

| Commande           | Usage                               | Ce que ça fait                                                                                                                                                                          |
| ------------------ | ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/tdd` **[shim]**  | Nouvelle fonctionnalité             | Cycle red/green/refactor : tests d'abord, implémentation ensuite                                                                                                                        |
| `/build-fix`       | Build cassé                         | Analyse les erreurs, identifie la cause racine, corrections minimales                                                                                                                   |
| `/refactor-clean`  | Après une feature, ou régulièrement | Détecte le langage (via `package.json`, `go.mod`, `Cargo.toml`…), lance l'outil adapté (`knip`, `vulture`, `deadcode`…), supprime le code mort atomiquement avec vérification des tests |
| `/update-docs`     | Après changement d'API              | Met à jour READMEs, codemaps, commentaires en cohérence avec le code                                                                                                                    |
| `/update-codemaps` | Après refacto structurel            | Regénère les cartes du codebase                                                                                                                                                         |
| `/setup-pm`        | Nouveau projet                      | Configure le package manager (npm/pnpm/yarn/bun)                                                                                                                                        |

### Revue & Qualité

| Commande             | Usage                      | Ce que ça fait                                                         |
| -------------------- | -------------------------- | ---------------------------------------------------------------------- |
| `/code-review`       | Avant un commit / PR       | Revue des fichiers modifiés : qualité, maintenabilité, patterns        |
| `/security-scan`     | Audit de la config Claude Code | Scanne `.claude/` (CLAUDE.md, settings.json, MCP, hooks) pour détecter des mauvaises configurations et risques d'injection via AgentShield |
| `/verify` **[shim]** | Avant un merge             | Build + tests + lint en séquence, remonte les blockers                 |
| `/quality-gate`      | Sur un fichier ou le projet entier | Format, lint et vérification de types via le pipeline qualité ECC      |
| `/test-coverage`     | Après implémentation       | Vérifie les métriques de couverture, identifie les zones non testées   |
| `/e2e` **[shim]**    | Feature UI terminée        | Génère des tests Playwright couvrant le parcours utilisateur           |

### Langages spécifiques

| Commande          | Langage      | Usage                                               |
| ----------------- | ------------ | --------------------------------------------------- |
| `/python-review`  | Python       | PEP 8, type hints, idiomes, sécurité, performance   |
| `/go-review`      | Go           | Idiomes Go, concurrence, gestion d'erreurs          |
| `/go-build`       | Go           | Résolution d'erreurs `go build` / `go vet`          |
| `/go-test`        | Go           | Workflow TDD Go avec table-driven tests             |
| `/rust-review`    | Rust         | Ownership, lifetimes, unsafe, patterns idiomatiques |
| `/rust-build`     | Rust         | Erreurs cargo, borrow checker, Cargo.toml           |
| `/rust-test`      | Rust         | TDD Rust avec coverage                              |
| `/kotlin-review`  | Kotlin       | Patterns Kotlin, coroutines, Compose, architecture  |
| `/kotlin-build`   | Kotlin       | Erreurs Gradle/Kotlin                               |
| `/kotlin-test`    | Kotlin       | TDD Kotlin avec Kotest                              |
| `/flutter-review` | Flutter/Dart | Widgets, state management, performance              |
| `/flutter-build`  | Flutter/Dart | Erreurs Dart analyzer                               |
| `/flutter-test`   | Flutter/Dart | Tests Flutter                                       |
| `/cpp-review`     | C++          | Memory safety, concurrence, modern C++              |
| `/cpp-build`      | C++          | Erreurs CMake, linker, templates                    |
| `/cpp-test`       | C++          | TDD C++ avec GoogleTest                             |
| `/gradle-build`   | Android/KMP  | Erreurs Gradle                                      |

### Multi-agents

> Décomposent automatiquement le travail et délèguent à plusieurs instances en parallèle.

| Commande                        | Usage                                | Ce que ça fait                                                          |
| ------------------------------- | ------------------------------------ | ----------------------------------------------------------------------- |
| `/multi-plan "tâche"`           | Tâche trop grande pour un seul agent | Planification collaborative multi-modèles (Codex + Gemini + Claude) avec récupération de contexte parallèle |
| `/multi-execute`                | Après `/multi-plan`                  | Implémente via Codex/Gemini, refactorise en code de production, puis audit multi-modèles             |
| `/multi-backend "pipeline"`     | Backend : API, algorithmes, BDD      | Workflow 6 phases orchestré par Claude, Codex comme autorité backend, Gemini en auxiliaire           |
| `/multi-frontend "feature"`     | Frontend : composants, layout, UI    | Workflow 6 phases orchestré par Claude, Gemini comme autorité frontend, Codex en auxiliaire          |
| `/multi-workflow "description"` | Workflow cross-services              | Coordination avec gestion des dépendances entre étapes                  |
| `/orchestrate` **[shim]**       | Coordination multi-agents            | Redirige vers `dmux-workflows` (tmux multi-agents) ou `autonomous-agent-harness` (boucles longues) |

### Apprentissage continu

| Commande           | Usage                                      | Ce que ça fait                                                    |
| ------------------ | ------------------------------------------ | ----------------------------------------------------------------- |
| `/learn`           | Fin de session productive                  | Extrait les patterns et décisions, les sauvegarde comme skills réutilisables dans `~/.claude/skills/learned/` |
| `/learn-eval`      | Quand tu veux valider avant de sauvegarder | Extrait les patterns, évalue leur qualité et détermine où les sauvegarder (Global vs Projet) avant persistance |
| `/evolve`          | Un pattern revient souvent                 | Analyse les instincts et génère des structures évoluées : commandes, skills ou agents selon leur nature |
| `/instinct-status` | Pour voir ce qu'ECC a appris               | Liste les instincts appris (projet + globaux) groupés par domaine, avec leur score de confiance       |
| `/instinct-export` | Partager des instincts                     | Exporte les instincts appris vers un fichier                      |
| `/instinct-import` | Importer des instincts                     | Importe des instincts depuis un fichier                           |
| `/prune`           | Nettoyage mensuel                          | Supprime les instincts expirés (TTL 30j)                          |

### Gestion de sessions

| Commande          | Usage                              | Ce que ça fait                                                     |
| ----------------- | ---------------------------------- | ------------------------------------------------------------------ |
| `/save-session`   | Fin d'une session longue           | Sauvegarde l'état complet : contexte, décisions, fichiers modifiés |
| `/resume-session` | Début de session                   | Recharge automatiquement la dernière session avec son contexte     |
| `/checkpoint`     | Point intermédiaire dans une tâche | Crée un point de sauvegarde sans terminer la session               |
| `/sessions`       | Retrouver une session passée       | Gère l'historique : liste, charge, crée des aliases et affiche les métadonnées des sessions sauvegardées |

### Infra & Monitoring

| Commande         | Usage                          | Ce que ça fait                                                         |
| ---------------- | ------------------------------ | ---------------------------------------------------------------------- |
| `/model-route`   | Optimiser les coûts            | Recommande le tier de modèle adapté (haiku/sonnet/opus) pour la tâche courante selon sa complexité |
| `/harness-audit` | Audit du harness complet       | Scorecard sur 7 catégories (hooks, skills, agents, context efficiency, quality gates…) avec recommandations prioritisées |
| `/loop-start`    | Tâche autonome longue durée    | Démarre une boucle avec pattern choisi (sequential/continuous-pr/rfc-dag/infinite) et garde-fous de sécurité |
| `/loop-status`   | Boucle en cours                | Inspecte l'état, les checkpoints, le drift coût/temps et recommande une intervention (continuer/pauser/stopper) |
| `/pm2`           | Gestion de processus           | Analyse le projet, génère la config PM2 (`ecosystem.config.cjs`) et les commandes Claude pour gérer chaque service |

### Outils spéciaux

| Commande                      | Usage                         | Ce que ça fait                                                    |
| ----------------------------- | ----------------------------- | ----------------------------------------------------------------- |
| `/aside "question"`           | Question rapide hors-contexte | Répond sans polluer le contexte de la tâche en cours              |
| `/skill-create`               | Créer un skill custom         | Analyse l'historique git du repo, extrait les patterns de l'équipe et génère des fichiers `SKILL.md` réutilisables |
| `/skill-health`               | Vérifier l'état des skills    | Liste les skills actifs et détecte les problèmes                  |
| `/projects`                   | Gestion de projets            | Liste les projets connus et leur état                             |
| `/jira "ticket"`              | Intégration Jira              | Récupère, commente, fait avancer un ticket ou recherche via JQL   |
| `/promote`                    | Instincts                     | Promeut des instincts de portée projet vers la portée globale (continuous-learning-v2) |
| `/santa-loop`                 | Revue adversariale            | Deux reviewers indépendants (modèles différents, contexte isolé) doivent tous deux approuver, jusqu'à 3 rounds |
| `/context-budget` **[shim]**  | Audit du contexte             | Analyse la consommation du contexte et fait des recommandations   |
| `/eval` **[shim]**            | Évaluation formelle           | Lance le framework d'évaluation sur une tâche                     |
| `/docs` **[shim]**            | Doc d'une lib                 | Recherche la documentation via Context7                           |
| `/prompt-optimize` **[shim]** | Optimiser un prompt           | Analyse et améliore un prompt existant                            |
| `/rules-distill` **[shim]**   | Extraire des règles           | Scan des skills pour extraire des règles réutilisables            |
| `/devfleet` **[shim]**        | Multi-agents DevFleet         | Orchestration multi-agents via DevFleet                           |
| `/claw` **[shim]**            | REPL Nanoclaw                 | Lance le REPL zero-dépendance session-aware                       |

---

## Agents spécialisés (38)

Un agent est un **sous-processus autonome** : il reçoit une tâche, travaille dans sa propre fenêtre de contexte isolée, et renvoie uniquement un résumé à Claude principal. Il a ses propres outils, son propre modèle, et ses propres permissions.

### Qui peut invoquer un agent ?

| Mode | Mécanisme | Exemple |
|------|-----------|---------|
| **Claude décide seul** | Claude lit la `description` de chaque agent et délègue automatiquement si la situation correspond | Après avoir modifié un fichier `.ts`, Claude invoque `typescript-reviewer` sans qu'on le lui demande |
| **Tu l'invites explicitement** | Mentionner l'agent dans ton prompt | `"utilise l'agent security-reviewer sur src/auth.ts"` |
| **Via un slash command** | Certains skills déclenchent des agents en interne | `/review-pr` délègue à `code-reviewer` |
| **Jamais** (user-invocable: false) | Quelques agents sont marqués pour usage interne uniquement — Claude peut les appeler, pas toi via `/` | Agents utilitaires internes à ECC |

### Ce qui se passe quand un agent est invoqué

```
Ta session (contexte principal)
  │
  ├─ Claude décide de déléguer
  │
  └─► Agent (contexte isolé, vierge)
        │  lit les fichiers pertinents
        │  exécute ses outils propres
        │  produit son travail
        └─► résumé seulement revient dans ton contexte
```

**Trois conséquences importantes :**
1. **L'agent ne voit pas ta conversation** — il démarre avec un contexte vide, juste la tâche qu'on lui donne
2. **Tu ne vois pas le détail de son travail** — seulement ce qu'il renvoie (résumé, fichiers modifiés, rapport)
3. **Pas d'imbrication** — un agent ne peut pas en invoquer un autre (pas de nesting)

### Quelle est la différence avec un skill ?

| | Skill | Agent |
|--|-------|-------|
| Contexte | Partagé avec ta session | Isolé — fenêtre propre |
| Invoqué par Claude | Oui (via description) | Oui (via description) |
| Invoqué par toi | Oui (`/nom`) | Oui (dans le prompt) |
| Voit ta conversation | Oui | Non |
| Modèle configurable | Oui (`model:`) | Oui (`model:`) |
| Coût | Tokens dans ta session | Tokens séparés |
| Cas d'usage | Instructions, contexte métier | Travail autonome long et isolé |

### Comment forcer ou empêcher l'invocation automatique

Claude décide de déléguer à un agent en lisant sa `description`. Si tu ne veux pas qu'un agent soit déclenché automatiquement sur un projet :

```json
// .claude/settings.json
{
  "permissions": {
    "deny": ["Agent(code-reviewer)", "Agent(security-reviewer)"]
  }
}
```

Pour invoquer explicitement un agent spécifique quand Claude ne le fait pas :
```
"je veux que tu délègues cette tâche à l'agent database-reviewer"
"utilise le sous-agent planner pour planifier cette feature"
```

---

### Revue de code

| Agent                 | Quand ECC le délègue             | Ce qu'il fait                                                                  |
| --------------------- | -------------------------------- | ------------------------------------------------------------------------------ |
| `code-reviewer`       | Après toute modification de code | Revue qualité, sécurité, maintenabilité — génère des commentaires actionnables |
| `typescript-reviewer` | Fichiers `.ts` / `.tsx` modifiés | Type safety, async correctness, patterns idiomatiques TS/JS                    |
| `python-reviewer`     | Fichiers `.py` modifiés          | PEP 8, type hints, idiomes, gestion d'erreurs                                  |
| `go-reviewer`         | Fichiers `.go` modifiés          | Idiomes Go, concurrence, error handling                                        |
| `rust-reviewer`       | Fichiers `.rs` modifiés          | Ownership, lifetimes, unsafe, patterns idiomatiques                            |
| `kotlin-reviewer`     | Fichiers `.kt` modifiés          | Coroutines, Compose, architecture clean                                        |
| `flutter-reviewer`    | Fichiers `.dart` modifiés        | Widgets, state management, performance                                         |
| `java-reviewer`       | Fichiers `.java` modifiés        | Spring Boot, JPA, sécurité, architecture                                       |
| `cpp-reviewer`        | Fichiers `.cpp` / `.h` modifiés  | Memory safety, concurrence, modern C++                                         |
| `csharp-reviewer`     | Fichiers `.cs` modifiés          | Conventions .NET, async/await, DI                                              |

### Résolution de build

| Agent                    | Quand ECC le délègue               | Ce qu'il fait                                                  |
| ------------------------ | ---------------------------------- | -------------------------------------------------------------- |
| `build-error-resolver`   | Erreurs TypeScript/JS en cascade   | Analyse les erreurs de type, propose des corrections minimales |
| `go-build-resolver`      | `go build` / `go vet` qui échouent | Résolution ciblée, zero changement architectural               |
| `rust-build-resolver`    | `cargo build` qui échoue           | Borrow checker, linker, Cargo.toml                             |
| `kotlin-build-resolver`  | Build Gradle/Kotlin en échec       | Gradle, Kotlin compiler, dépendances                           |
| `java-build-resolver`    | Build Maven/Gradle Java en échec   | Compiler, classpath, dépendances                               |
| `cpp-build-resolver`     | CMake / compilation C++ en échec   | Linker, templates, erreurs de compilation                      |
| `dart-build-resolver`    | Dart analyzer / Flutter en échec   | Dépendances pubspec, erreurs Dart                              |
| `pytorch-build-resolver` | Erreurs PyTorch runtime / CUDA     | Tensor shapes, device errors, DataLoader                       |

### Planification & Architecture

| Agent       | Quand l'utiliser                                         | Ce qu'il fait                                                  |
| ----------- | -------------------------------------------------------- | -------------------------------------------------------------- |
| `planner`   | Feature complexe avec beaucoup d'inconnues               | Lit le codebase, produit un plan step-by-step avec estimations |
| `architect` | Choix structurant (DB, framework, pattern d'intégration) | Compare options, documente la décision (ADR)                   |
| `tdd-guide` | Feature critique, apprentissage TDD                      | Accompagne pas à pas : spec → test → implémentation → refacto  |

### Qualité & Sécurité

| Agent                   | Quand ECC le délègue            | Ce qu'il fait                                              |
| ----------------------- | ------------------------------- | ---------------------------------------------------------- |
| `security-reviewer`     | Code touchant auth, inputs, API | OWASP Top 10, secrets, injection, SSRF                     |
| `database-reviewer`     | SQL, migrations, schéma         | Optimisation requêtes, index, patterns PostgreSQL/Supabase |
| `refactor-cleaner`      | Code mort détecté               | Suppression sûre et atomique avec vérification des tests   |
| `performance-optimizer` | Goulots d'étranglement détectés | Analyse et optimisation de performance                     |

### Tests & Documentation

| Agent         | Quand ECC le délègue              | Ce qu'il fait                                                           |
| ------------- | --------------------------------- | ----------------------------------------------------------------------- |
| `e2e-runner`  | Feature UI terminée               | Génère, maintient et exécute les tests Playwright                       |
| `doc-updater` | Après refacto ou changement d'API | Met à jour tous les fichiers de doc en cohérence avec le code           |
| `docs-lookup` | Question sur une lib externe      | Récupère la doc à jour via Context7, retourne des exemples fonctionnels |

### Infrastructure & Agents

| Agent               | Quand l'utiliser                      | Ce qu'il fait                                                          |
| ------------------- | ------------------------------------- | ---------------------------------------------------------------------- |
| `harness-optimizer` | Hooks lents ou configuration douteuse | Analyse et améliore la config du harness                               |
| `loop-operator`     | Boucle autonome en cours              | Surveille et intervient si la boucle stalle                            |
| `chief-of-staff`    | Triage de communications              | Classe emails/Slack en tiers (skip/info/action), génère des brouillons |

### Open-Source Pipeline

| Agent                  | Quand l'utiliser         | Ce qu'il fait                          |
| ---------------------- | ------------------------ | -------------------------------------- |
| `opensource-forker`    | Forker un projet privé   | Fork avec suppression des credentials  |
| `opensource-packager`  | Préparer une publication | Génère packaging, setup, README public |
| `opensource-sanitizer` | Avant publication        | Vérifie l'absence de données sensibles |

### Agents GAN (Generator-Evaluator)

| Agent           | Rôle           | Ce qu'il fait                                             |
| --------------- | -------------- | --------------------------------------------------------- |
| `gan-planner`   | Planification  | Transforme un prompt en spécification complète            |
| `gan-generator` | Implémentation | Implémente et itère sur le feedback de l'évaluateur       |
| `gan-evaluator` | Test live      | Teste l'application via Playwright et remonte le feedback |

### Healthcare

| Agent                 | Quand l'utiliser          | Ce qu'il fait                               |
| --------------------- | ------------------------- | ------------------------------------------- |
| `healthcare-reviewer` | Code médical / CDSS / EMR | Revue conformité PHI/HIPAA, safety clinique |

---

## Skills (156)

> Un skill est un domaine de connaissance. Il s'active :
>
> - **Automatiquement** : ECC détecte le contexte et injecte le skill pertinent
> - **Dans un prompt** : `"en utilisant le skill tdd-workflow, implémente..."`
> - **Via slash** : `/tdd` (qui charge le skill `tdd-workflow`)

### Développement backend

| Skill                     | Quand l'activer                  | Ce qu'il apporte                                                   |
| ------------------------- | -------------------------------- | ------------------------------------------------------------------ |
| `backend-patterns`        | Design d'une couche service/repo | Repository, CQRS, factory, patterns adaptés au contexte            |
| `api-design`              | Création ou évolution d'API REST | Versioning, validation, gestion des erreurs, conventions           |
| `database-migrations`     | Modification de schéma           | Migrations sûres, réversibles, avec gestion des données existantes |
| `nestjs-patterns`         | Projets NestJS                   | Modules, DI, guards, interceptors, pipes                           |
| `django-patterns`         | Projets Django                   | Architecture, DRF, ORM, patterns best practices                    |
| `django-security`         | Code Django sensible             | Sécurité Django : CSRF, XSS, injection, permissions                |
| `django-tdd`              | TDD sur Django                   | Test-driven avec pytest-django, fixtures, factories                |
| `django-verification`     | Avant merge Django               | Boucle de vérification : tests, lint, types                        |
| `laravel-patterns`        | Projets Laravel                  | Routing, Eloquent, service layers, architecture                    |
| `laravel-security`        | Code Laravel sensible            | Sécurité Laravel : CSRF, auth, validation                          |
| `laravel-tdd`             | TDD sur Laravel                  | PHPUnit / Pest, factories, feature tests                           |
| `laravel-verification`    | Avant merge Laravel              | Vérification complète : tests, phpstan, lint                       |
| `springboot-patterns`     | Projets Spring Boot              | Architecture Spring, beans, configuration                          |
| `springboot-security`     | Code Spring sensible             | Spring Security, OAuth2, RBAC                                      |
| `springboot-tdd`          | TDD sur Spring Boot              | JUnit 5, Mockito, @SpringBootTest                                  |
| `springboot-verification` | Avant merge Spring               | Vérification : tests, checkstyle, spotbugs                         |

### Bases de données

| Skill                        | Quand l'activer             | Ce qu'il apporte                                |
| ---------------------------- | --------------------------- | ----------------------------------------------- |
| `postgres-patterns`          | SQL / PostgreSQL            | Optimisation requêtes, index, JSONB, sécurité   |
| `jpa-patterns`               | Spring Boot + JPA           | Hibernate, lazy loading, N+1, migrations Flyway |
| `clickhouse-io`              | ClickHouse / analytics      | Requêtes analytiques, MergeTree, optimisation   |
| `content-hash-cache-pattern` | Caching de fichiers coûteux | Pattern SHA-256 pour éviter le retraitement     |

### Python

| Skill              | Quand l'activer       | Ce qu'il apporte                                          |
| ------------------ | --------------------- | --------------------------------------------------------- |
| `python-patterns`  | Code Python           | Idiomes Pythoniques, PEP 8, type hints, gestion d'erreurs |
| `python-testing`   | Tests Python          | pytest, fixtures, mocks, paramétrise, coverage            |
| `pytorch-patterns` | Deep learning PyTorch | DataLoaders, training loops, CUDA, checkpointing          |

### Go

| Skill             | Quand l'activer | Ce qu'il apporte                                    |
| ----------------- | --------------- | --------------------------------------------------- |
| `golang-patterns` | Code Go         | Idiomes Go, interfaces, concurrence, error handling |
| `golang-testing`  | Tests Go        | Table-driven tests, benchmarks, fuzzing             |

### Rust

| Skill           | Quand l'activer | Ce qu'il apporte                                      |
| --------------- | --------------- | ----------------------------------------------------- |
| `rust-patterns` | Code Rust       | Ownership, error handling avec `?`, traits, lifetimes |
| `rust-testing`  | Tests Rust      | Unit/integration tests, proptest, coverage            |

### Java / Kotlin / JVM

| Skill                            | Quand l'activer      | Ce qu'il apporte                                  |
| -------------------------------- | -------------------- | ------------------------------------------------- |
| `java-coding-standards`          | Java / Spring Boot   | Conventions, architecture en couches, Javadoc     |
| `kotlin-patterns`                | Code Kotlin          | Idiomes Kotlin, extension functions, data classes |
| `kotlin-coroutines-flows`        | Async Kotlin         | Coroutines, Flow, StateFlow, channels             |
| `kotlin-exposed-patterns`        | Kotlin + Exposed ORM | DSL Exposed, transactions, migrations             |
| `kotlin-ktor-patterns`           | Ktor server          | Routing, DI, authentification, serialisation      |
| `kotlin-testing`                 | Tests Kotlin         | Kotest, MockK, BDD patterns                       |
| `android-clean-architecture`     | Android / KMP        | Clean Architecture, ViewModel, Repository         |
| `compose-multiplatform-patterns` | Compose KMP          | Shared UI, state management cross-platform        |

### C++ / C# / .NET

| Skill                  | Quand l'activer | Ce qu'il apporte                          |
| ---------------------- | --------------- | ----------------------------------------- |
| `cpp-coding-standards` | Code C++        | C++ Core Guidelines, RAII, smart pointers |
| `cpp-testing`          | Tests C++       | GoogleTest, CTest, mocking avec gMock     |
| `csharp-testing`       | Tests C#        | xUnit, FluentAssertions, Moq, BDD         |
| `dotnet-patterns`      | Code .NET       | Conventions C#, async/await, DI, SOLID    |

### Swift / iOS

| Skill                         | Quand l'activer         | Ce qu'il apporte                                |
| ----------------------------- | ----------------------- | ----------------------------------------------- |
| `swiftui-patterns`            | Interfaces SwiftUI      | Architecture MVVM, state management, navigation |
| `swift-concurrency-6-2`       | Swift 6.2 async         | Approachable Concurrency, actors, async/await   |
| `swift-actor-persistence`     | Persistence thread-safe | Actors pour la persistance, CoreData/SwiftData  |
| `swift-protocol-di-testing`   | DI en Swift             | Protocol-based DI, testabilité, mocking         |
| `foundation-models-on-device` | LLM on-device Apple     | Apple FoundationModels, inférence locale        |

### Flutter / Dart

| Skill                      | Quand l'activer    | Ce qu'il apporte                                   |
| -------------------------- | ------------------ | -------------------------------------------------- |
| `dart-flutter-patterns`    | Code Flutter/Dart  | Patterns de production, architecture, performance  |
| `flutter-dart-code-review` | Revue code Flutter | Checklist exhaustive : widgets, state, Dart idioms |

### PHP / Perl

| Skill                      | Quand l'activer             | Ce qu'il apporte                       |
| -------------------------- | --------------------------- | -------------------------------------- |
| `laravel-plugin-discovery` | Chercher un package Laravel | Découverte via LaraPlugins, évaluation |
| `perl-patterns`            | Code Perl                   | Perl 5.36+ idioms, modern Perl         |
| `perl-security`            | Code Perl sensible          | Taint mode, sécurité Perl              |
| `perl-testing`             | Tests Perl                  | Test::More, Prove, patterns de test    |

### Frontend

| Skill                 | Quand l'activer   | Ce qu'il apporte                               |
| --------------------- | ----------------- | ---------------------------------------------- |
| `frontend-patterns`   | React / Next.js   | State management, performance, hooks patterns  |
| `nextjs-turbopack`    | Next.js 16+       | Turbopack, incremental bundling, optimisations |
| `nuxt4-patterns`      | Nuxt 4            | Hydration, SSR, composables patterns           |
| `design-system`       | Système de design | Générer et auditer un design system cohérent   |
| `liquid-glass-design` | iOS 26            | Liquid Glass design system Apple               |
| `bun-runtime`         | Bun               | Bun comme runtime, package manager, bundler    |

### Tests & Qualité

| Skill                    | Quand l'activer        | Ce qu'il apporte                                       |
| ------------------------ | ---------------------- | ------------------------------------------------------ |
| `tdd-workflow`           | Toute nouvelle feature | Cycle red/green/refactor strict, vérification coverage |
| `verification-loop`      | Avant un merge ou PR   | Vérification séquentielle : build, types, lint, tests — stoppe et corrige à chaque échec avant de continuer |
| `e2e-testing`            | Feature UI terminée    | Playwright : génération, maintenance, tests flaky      |
| `benchmark`              | Performance à mesurer  | Baseline de performance, comparaison avant/après       |
| `ai-regression-testing`  | CI avec LLM            | Régression testing pour comportements IA               |
| `quality-nonconformance` | Suivi qualité          | Tracking et reporting des non-conformités              |
| `eval-harness`           | Évaluation formelle    | Framework d'évaluation eval-driven                     |
| `coding-standards`       | Revue ou refacto       | Conventions universelles, cohérence codebase           |
| `plankton-code-quality`  | À l'écriture           | Enforcement qualité en temps réel                      |

### Sécurité

| Skill             | Quand l'activer            | Ce qu'il apporte                                      |
| ----------------- | -------------------------- | ----------------------------------------------------- |
| `security-review` | Avant tout commit sensible | Checklist OWASP, patterns dangereux, mitigations      |
| `safety-guard`    | Opérations destructives    | Prévient les `rm -rf`, `git reset --hard` accidentels |

### Architecture & Design

| Skill                           | Quand l'activer               | Ce qu'il apporte                                           |
| ------------------------------- | ----------------------------- | ---------------------------------------------------------- |
| `hexagonal-architecture`        | Design d'une nouvelle app     | Ports & Adapters, séparation domaine/infrastructure        |
| `architecture-decision-records` | Décision technique importante | Capture formelle ADR : contexte, décision, conséquences    |
| `blueprint`                     | Projet multi-sessions complexe | Génère un plan de construction step-by-step avec dépendances, briefs de contexte et revue adversariale |
| `codebase-onboarding`           | Nouveau projet / codebase     | Analyse complète pour comprendre rapidement l'architecture |
| `android-clean-architecture`    | Android / KMP                 | Clean Architecture multi-couches                           |
| `project-guidelines-example`    | Créer des guidelines projet   | Template de skill project-specific                         |
| `ralphinho-rfc-pipeline`        | RFC complexe                  | Pipeline RFC multi-agent avec DAG                          |

### Infrastructure & DevOps

| Skill                 | Quand l'activer             | Ce qu'il apporte                               |
| --------------------- | --------------------------- | ---------------------------------------------- |
| `docker-patterns`     | Dockerfile / docker-compose | Multi-stage builds, layers optimisés, sécurité |
| `deployment-patterns` | CI/CD, déploiement          | Blue/green, canary, rollback, health checks    |
| `mcp-server-patterns` | Créer un serveur MCP        | Architecture, transport, outils, ressources    |
| `git-workflow`        | Workflow git                | Branching, rebasing, PR patterns, conventions  |

### Agents & Automatisation

| Skill                        | Quand l'activer          | Ce qu'il apporte                                        |
| ---------------------------- | ------------------------ | ------------------------------------------------------- |
| `autonomous-loops`           | ⚠️ Déprécié (v1.8+)      | Remplacé par `continuous-agent-loop` — conservé pour compatibilité une release |
| `continuous-agent-loop`      | Architecture de boucle   | Patterns pour boucles autonomes avec quality gates et contrôles de récupération (sequential, continuous-pr, rfc-dag, infinite) |
| `enterprise-agent-ops`       | Agents en production     | Long-lived agents avec observabilité                    |
| `agent-harness-construction` | Améliorer un agent       | Optimiser l'espace d'action, les définitions d'outils et le formatage des observations pour de meilleurs taux de complétion |
| `autonomous-agent-harness`   | Système autonome complet | Harness avec mémoire, scheduling, boucles               |
| `agent-eval`                 | Comparer des agents      | Métriques de comparaison head-to-head                   |
| `santa-method`               | Revue adversariale       | Dual-review avec convergence multi-agents               |
| `eval-harness`               | Évaluation formelle      | Framework eval-driven                                   |
| `strategic-compact`          | Session longue approchant la limite | Suggère des moments stratégiques pour `/compact` plutôt que la compaction automatique arbitraire |
| `token-budget-advisor`       | Audit du contexte        | Analyse la consommation et recommande                   |
| `context-budget`             | Budget de contexte       | Audit et optimisation du contexte                       |
| `agent-payment-x402`         | Paiements per-task       | Intégration x402 pour budget par tâche                  |

### Claude & API Anthropic

| Skill                     | Quand l'activer              | Ce qu'il apporte                                |
| ------------------------- | ---------------------------- | ----------------------------------------------- |
| `claude-api`              | Développer avec l'API Claude | Patterns Python/TypeScript pour l'API Anthropic |
| `claude-devfleet`         | Orchestration multi-agents   | DevFleet pour coordination d'agents             |
| `cost-aware-llm-pipeline` | Optimiser les coûts LLM      | Patterns d'optimisation pour pipelines LLM      |

### Apprentissage continu

| Skill                    | Quand l'activer      | Ce qu'il apporte                                   |
| ------------------------ | -------------------- | -------------------------------------------------- |
| `continuous-learning`    | Fin de session       | Extraire et sauvegarder les patterns réutilisables |
| `continuous-learning-v2` | Apprentissage avancé | Système d'instincts avec scoring de confiance et isolation par projet (v2.1) pour éviter la contamination cross-projet |
| `agentic-engineering`    | Développement individuel avec IA | Exécution eval-first, décomposition de tâches et routing de modèles selon la complexité |
| `ai-first-engineering`   | Équipes avec forte part d'IA | Modèle opérationnel : process, revues et architecture pour équipes où les agents génèrent la majorité du code |

### Recherche & Documentation

| Skill                  | Quand l'activer         | Ce qu'il apporte                                  |
| ---------------------- | ----------------------- | ------------------------------------------------- |
| `documentation-lookup` | Question sur une lib    | Recherche doc via Context7, exemples fonctionnels |
| `deep-research`        | Recherche multi-sources | Recherche web approfondie sur plusieurs sources   |
| `exa-search`           | Recherche web et code   | Recherche neurale via Exa MCP : web, code, entreprises, personnes, research multi-sources |
| `iterative-retrieval`  | Contexte progressif     | Raffinement progressif du contexte par itérations |

### Contenu & Social

| Skill                   | Quand l'activer                     | Ce qu'il apporte                              |
| ----------------------- | ----------------------------------- | --------------------------------------------- |
| `article-writing`       | Rédiger un article                  | Blog posts, guides techniques, long-form      |
| `brand-voice`           | Écrire avec une voix de marque      | Extrait et applique le style d'une source     |
| `content-engine`        | Système de contenu multi-plateforme | Création de contenu adapté par plateforme     |
| `crosspost`             | Distribution multi-plateforme       | Adapter et publier sur plusieurs canaux       |
| `x-api`                 | Intégration X/Twitter               | API Twitter/X, posting, analytics             |
| `connections-optimizer` | Réseau X/LinkedIn                   | Optimisation du réseau social                 |
| `social-graph-ranker`   | Classement social                   | Ranking pondéré du graphe social              |
| `investor-materials`    | Fundraising                         | Pitch decks, mémos d'investissement           |
| `investor-outreach`     | Contacter des investisseurs         | Emails cold, warm intros, communications      |
| `market-research`       | Analyse de marché                   | Intelligence compétitive, analyse sectorielle |

### Vidéo & Multimédia

| Skill                     | Quand l'activer             | Ce qu'il apporte                               |
| ------------------------- | --------------------------- | ---------------------------------------------- |
| `ui-demo`                 | Démo produit                | Enregistrement de démo UI soigné               |
| `frontend-slides`         | Présentations               | Slides HTML animées                            |
| `manim-video`             | Vidéos explicatives animées | Manim pour animations mathématiques/techniques |
| `remotion-video-creation` | Vidéos React                | Remotion pour vidéos programmatiques           |
| `video-editing`           | Montage vidéo               | Workflow d'édition assisté par IA              |
| `fal-ai-media`            | Génération vidéo/image      | Text-to-video, image-to-video via fal.ai       |
| `videodb`                 | Base de données vidéo       | Ingest, recherche, édition de vidéos           |

### Data & Intégrations

| Skill                          | Quand l'activer           | Ce qu'il apporte                                          |
| ------------------------------ | ------------------------- | --------------------------------------------------------- |
| `mcp-server-patterns`          | Créer un serveur MCP      | Architecture, outils, ressources, transport               |
| `jira-integration`             | Tickets Jira              | Récupération, création, workflow Jira                     |
| `data-scraper-agent`           | Scraping automatisé       | Agent de collecte de données complet                      |
| `nutrient-document-processing` | PDF / documents           | OCR, conversion, traitement de documents                  |
| `visa-doc-translate`           | Traduction documents visa | Traduction spécialisée de documents administratifs        |
| `google-workspace-ops`         | Google Workspace          | Docs, Sheets, Drive — workflows automatisés               |
| `lead-intelligence`            | Génération de leads       | Pipeline IA de lead intelligence                          |
| `regex-vs-llm-structured-text` | Choix de parsing          | Framework de décision : regex vs LLM pour texte structuré |
| `click-path-audit`             | Debug UI                  | Trace les séquences de clics et changements d'état        |

### Business & Opérations

| Skill                             | Quand l'activer        | Ce qu'il apporte                         |
| --------------------------------- | ---------------------- | ---------------------------------------- |
| `customer-billing-ops`            | Billing, abonnements   | Gestion facturation et subscriptions     |
| `logistics-exception-management`  | Logistique             | Gestion des exceptions logistiques       |
| `inventory-demand-planning`       | Supply chain           | Planification inventaire et demande      |
| `production-scheduling`           | Ordonnancement         | Planification de production              |
| `returns-reverse-logistics`       | Retours                | Logistique inversée, gestion des retours |
| `carrier-relationship-management` | Transporteurs          | Gestion des relations transporteurs      |
| `customs-trade-compliance`        | Commerce international | Conformité douanière et commerciale      |
| `energy-procurement`              | Énergie                | Procurement et gestion énergétique       |
| `quality-nonconformance`          | Qualité                | Suivi et reporting des non-conformités   |

### Healthcare

| Skill                       | Quand l'activer                    | Ce qu'il apporte                            |
| --------------------------- | ---------------------------------- | ------------------------------------------- |
| `healthcare-cdss-patterns`  | CDSS / aide à la décision clinique | Patterns Clinical Decision Support Systems  |
| `healthcare-emr-patterns`   | EMR / EHR                          | Patterns pour systèmes de dossiers médicaux |
| `healthcare-eval-harness`   | Évaluation sécurité patient        | Framework d'évaluation patient safety       |
| `healthcare-phi-compliance` | Données de santé                   | PHI/PII compliance, HIPAA patterns          |

### Outils & Utilitaires

| Skill                     | Quand l'activer                | Ce qu'il apporte                             |
| ------------------------- | ------------------------------ | -------------------------------------------- |
| `ck`                      | Mémoire persistante par projet | Charge le contexte projet automatiquement au démarrage de session, tracké avec l'activité git, écrit dans la mémoire native |
| `configure-ecc`           | Installation ECC               | Installeur interactif ECC                    |
| `nanoclaw-repl`           | REPL léger                     | REPL zero-dépendance session-aware           |
| `workspace-surface-audit` | Audit de l'environnement       | Audit repo, MCP, plugins, harness            |
| `skill-stocktake`         | Inventaire des skills          | Liste et santé des skills disponibles        |
| `skill-comply`            | Mesure de conformité           | Auto-génère des scénarios, exécute des agents et mesure si les skills/règles sont réellement suivis (taux de compliance avec timeline d'appels d'outils) |
| `prompt-optimizer`        | Optimiser un prompt            | Analyse et amélioration de prompts           |
| `repo-scan`               | Audit cross-stack              | Classifie chaque fichier, détecte les libs tierces embarquées (hors package managers), génère des verdicts 4 niveaux avec rapport HTML interactif |
| `opensource-pipeline`     | Préparer un projet pour l'open source | Pipeline 3 agents : fork (suppression credentials) → sanitize (vérification) → package (CLAUDE.md, setup.sh, README public) |
| `openclaw-persona-forge`  | Personas IA                    | Création de personas pour agents IA          |
| `project-flow-ops`        | Coordination GitHub ↔ Linear   | Triage PR/issues, lie le travail actif entre GitHub (public) et Linear (exécution interne) |
| `browser-qa`              | Tests visuels                  | QA visuelle avec automatisation browser      |
| `dmux-workflows`          | Orchestration multi-agents     | Workflows tmux multi-agents                  |

---

## Hooks automatiques (22)

> Les hooks s'exécutent **sans action de ta part**. `ECC_HOOK_PROFILE` détermine lesquels passent le filtre à chaque exécution.

### Qu'est-ce qu'un tool ?

Claude ne peut rien faire directement — il doit passer par un **tool** (outil). Un tool est une capacité intégrée au runtime Claude Code que le LLM appelle pour agir sur le monde réel.

| Tool | Ce que Claude fait avec |
|------|------------------------|
| `Bash` | Exécuter n'importe quelle commande shell (`npm run dev`, `git push`, `rm`…) |
| `Edit` | Modifier du texte dans un fichier existant |
| `Write` | Créer ou écraser un fichier |
| `Read` | Lire le contenu d'un fichier |
| `Glob` | Trouver des fichiers par pattern (`**/*.ts`) |
| `Grep` | Chercher dans des fichiers avec regex |
| `WebFetch` | Récupérer une page web |
| `WebSearch` | Faire une recherche sur internet |
| `Agent` | Lancer un sous-agent |
| `mcp__<server>__<tool>` | N'importe quel outil MCP (`mcp__github__create_pull_request`…) |

**`npm run dev` est-il un tool ?** Non — c'est une commande shell. Claude l'exécute via le tool `Bash`. Le PreToolUse hook se déclenche sur `Bash`, et son script inspecte ensuite la commande pour détecter `npm run dev`.

### Comment ça fonctionne

Les hooks ne sont **pas** déclenchés par Claude (le LLM) — c'est le **runtime Claude Code** (le CLI) qui les exécute automatiquement à des points fixes du cycle de vie. Cela garantit un comportement **déterministe** : le hook tourne toujours, peu importe ce que Claude décide.

**Cycle de vie d'une session :**

```
SessionStart
     ↓
UserPromptSubmit  ← tu soumets un prompt
     ↓
┌─── Boucle agentique ──────────────────────────────────────────┐
│  Claude (LLM) choisit un tool et ses paramètres               │
│       ↓                                                        │
│  PreToolUse hook → inspecte/modifie les paramètres            │
│       exit 2 = bloque │ exit 0 = laisse passer                │
│       ↓                                                        │
│  Le tool s'exécute réellement                                  │
│       ↓                                                        │
│  PostToolUse hook → analyse le résultat (ne peut pas bloquer)  │
│       ↓                                                        │
│  Claude (LLM) voit le résultat → choisit le prochain tool     │
└───────────────────────────────────────────────────────────────┘
     ↓
Stop  ← Claude a fini de répondre
     ↓
SessionEnd
```

**Exemple concret — tu demandes "lance le serveur de dev" :**

```
1. Claude (LLM) décide : tool=Bash, command="npm run dev"
2. PreToolUse hook (matcher: Bash) se déclenche
   → le script détecte "npm run dev" dans la commande
   → il réécrit la commande : tmux new-session -d -s "mon-projet" 'npm run dev'
   → exit 0 : laisse passer la commande modifiée
3. Bash exécute la commande tmux (non-bloquante)
4. PostToolUse hook (matcher: Bash) se déclenche
   → log la commande dans ~/.claude/bash-commands.log
5. Claude voit le résultat et continue
```

**Le matcher** est une regex sur le nom du tool. Il détermine quels hooks se déclenchent :

| Matcher | Se déclenche sur |
|---------|-----------------|
| `Bash` | uniquement les commandes shell |
| `Edit\|Write` | éditions et créations de fichiers |
| `*` | tous les tools |
| `mcp__github__.*` | tous les tools du MCP GitHub |

**Les exit codes** contrôlent ce qui se passe après le hook :

| Code | Effet |
|------|-------|
| `0` | Le tool s'exécute normalement |
| `2` | Le tool est **bloqué** — le message stderr est renvoyé à Claude pour qu'il s'adapte |
| Autre | Erreur loggée, le tool s'exécute quand même |

> `PostToolUse` ne peut jamais bloquer (le tool a déjà tourné). Seuls `PreToolUse`, `UserPromptSubmit` et `Stop` peuvent bloquer avec exit 2.

**Tous les événements disponibles dans Claude Code :**

| Événement | Quand |
|-----------|-------|
| `SessionStart` | Début ou reprise de session |
| `UserPromptSubmit` | Quand tu soumets un prompt, avant que Claude traite |
| `PreToolUse` | Avant chaque appel outil — peut bloquer |
| `PermissionRequest` | Quand une dialog de permission apparaît |
| `PostToolUse` | Après chaque appel outil réussi |
| `PostToolUseFailure` | Après un outil qui a échoué |
| `Stop` | Quand Claude finit de répondre |
| `SubagentStart` / `SubagentStop` | Lancement / fin d'un sous-agent |
| `PreCompact` / `PostCompact` | Avant / après une compaction de contexte |
| `Notification` | Quand Claude Code envoie une notification |
| `ConfigChange` | Quand un fichier de config change pendant la session |
| `CwdChanged` | Quand le répertoire de travail change |
| `FileChanged` | Quand un fichier surveillé change sur le disque |
| `SessionEnd` | Fin de session |

### Hooks disponibles

**Avant l'outil (PreToolUse)**

| Hook                      | minimal | standard | strict | Action                                                  |
| ------------------------- | :-----: | :------: | :----: | ------------------------------------------------------- |
| Dev server auto-tmux      |    ✓    |    ✓     |   ✓    | Redirige `npm run dev/pnpm dev/yarn dev` dans une session tmux détachée pour ne pas bloquer Claude |
| Tmux reminder             |    —    |    —     |   ✓    | Suggère tmux pour les commandes longues                 |
| Git push reminder         |    —    |    —     |   ✓    | Rappel de review avant `git push`                       |
| Pre-commit quality check  |    —    |    —     |   ✓    | Lint, format du message de commit, détection de secrets |
| Doc file warning          |    —    |    ✓     |   ✓    | Avertit si création d'un `.md` non standard             |
| Strategic compact         |    —    |    ✓     |   ✓    | Suggère `/compact` tous les ~50 appels outils           |
| InsAIts security (opt-in) |    —    |    ✓     |   ✓    | Scan sécurité IA — nécessite `ECC_ENABLE_INSAITS=1`     |

**Après l'outil (PostToolUse)**

| Hook                        | minimal | standard | strict | Action                                                    |
| --------------------------- | :-----: | :------: | :----: | --------------------------------------------------------- |
| PR logger                   |    —    |    ✓     |   ✓    | Log l'URL du PR après `gh pr create`                      |
| Build analysis              |    —    |    ✓     |   ✓    | Analyse post-build en arrière-plan (async)                |
| Quality gate                |    —    |    ✓     |   ✓    | Checks qualité rapides après chaque édition               |
| Design quality check        |    —    |    ✓     |   ✓    | Avertit si l'UI édité ressemble à un template générique   |
| Prettier / TypeScript check |    —    |    ✓     |   ✓    | Format + `tsc --noEmit` sur les `.ts/.tsx` édités         |
| console.log warning         |    —    |    ✓     |   ✓    | Avertit si `console.log` détecté dans les fichiers édités |

**Lifecycle**

| Hook               | minimal | standard | strict | Action                                                             |
| ------------------ | :-----: | :------: | :----: | ------------------------------------------------------------------ |
| Session start      |    ✓    |    ✓     |   ✓    | Charge le contexte précédent, détecte le package manager           |
| Session summary    |    ✓    |    ✓     |   ✓    | Persiste l'état de session à chaque réponse                        |
| Pattern extraction |    ✓    |    ✓     |   ✓    | Évalue la session pour extraire des patterns (continuous learning) |
| Cost tracker       |    ✓    |    ✓     |   ✓    | Enregistre les métriques de coût et tokens                         |
| Session end marker |    ✓    |    ✓     |   ✓    | Marqueur de fin de session et nettoyage                            |
| Pre-compact        |    —    |    ✓     |   ✓    | Sauvegarde l'état avant compaction du contexte                     |
| Console.log audit  |    —    |    ✓     |   ✓    | Vérifie tous les fichiers modifiés pour `console.log`              |
| Desktop notify     |    —    |    ✓     |   ✓    | Notification macOS avec le résumé de la tâche                      |

### Configurer les hooks

**Via variable d'environnement (ponctuel)**

```bash
# Minimal : hooks légers, moins de friction
export ECC_HOOK_PROFILE=minimal

# Standard : équilibre fiabilité/vélocité (défaut)
export ECC_HOOK_PROFILE=standard

# Strict : tous les hooks, enforcement maximal
export ECC_HOOK_PROFILE=strict

# Désactiver des hooks spécifiques
export ECC_DISABLED_HOOKS="pre:bash:tmux-reminder,post:edit:typecheck"
```

**Via `settings.json` (persistant)**

```json
{
  "env": {
    "ECC_HOOK_PROFILE": "minimal",
    "ECC_DISABLED_HOOKS": "pre:bash:tmux-reminder,post:edit:typecheck"
  }
}
```

- `~/.claude/settings.json` → s'applique à toutes tes sessions Claude Code
- `.claude/settings.json` (racine du projet) → surcharge le global pour ce projet uniquement

---

## Règles (89)

> Les règles sont injectées **automatiquement** selon le langage des fichiers en cours d'édition.
> Elles définissent les conventions que Claude respectera sans que tu aies à les rappeler.

### Règles communes (toutes langues)

| Fichier de règle          | Ce qu'elle enforce                                 |
| ------------------------- | -------------------------------------------------- |
| `agents.md`               | Best practices pour l'utilisation des agents       |
| `code-review.md`          | Standards de revue de code                         |
| `coding-style.md`         | Style universel : nommage, structure, lisibilité   |
| `development-workflow.md` | Workflow de développement : branches, commits, PRs |
| `git-workflow.md`         | Conventions git : messages, branching strategy     |
| `hooks.md`                | Patterns d'utilisation des hooks                   |
| `patterns.md`             | Design patterns généraux                           |
| `performance.md`          | Optimisation de performance                        |
| `security.md`             | Sécurité : OWASP, secrets, validation              |
| `testing.md`              | Standards de test : coverage, TDD, assertions      |

### Règles par langage

Pour chaque langage (TypeScript, JavaScript, Python, Go, Rust, Java, Kotlin, C++, C#, Swift, PHP, Perl, Dart), ECC dispose de 5 règles :

| Règle          | Ce qu'elle enforce                          |
| -------------- | ------------------------------------------- |
| `coding-style` | Conventions de style spécifiques au langage |
| `hooks`        | Hooks et lifecycle patterns du langage      |
| `patterns`     | Design patterns idiomatiques                |
| `security`     | Vulnérabilités et protections spécifiques   |
| `testing`      | Patterns de test du langage                 |

### Règles web

| Fichier             | Ce qu'il enforce                         |
| ------------------- | ---------------------------------------- |
| `coding-style.md`   | HTML/CSS/JS style                        |
| `design-quality.md` | Qualité UI/UX                            |
| `hooks.md`          | Hooks front-end                          |
| `patterns.md`       | Patterns web (SPA, SSR, PWA)             |
| `performance.md`    | Core Web Vitals, bundle size             |
| `security.md`       | XSS, CSRF, CSP, CORS                     |
| `testing.md`        | Tests front-end : unit, integration, E2E |

---

## Exemples de sessions typiques

### Nouvelle feature (workflow complet)

```
/prp-prd "description du problème"   → Génère le PRD interactif
/prp-plan "feature"                  → Plan d'implémentation détaillé
/tdd                                 → Implémentation TDD
/code-review                         → Revue avant commit
/security-scan                       → Vérification sécurité
/prp-pr                              → Création de la PR
```

### Débugger un build cassé

```
/build-fix
→ Analyse les erreurs, propose des corrections
→ Si erreurs TypeScript complexes : délègue automatiquement à build-error-resolver
```

### Session longue (> 50% du contexte)

```
/compact     → Compresse intelligemment
/learn       → Extrait les patterns découverts
```

### Revue avant un merge important

```
/code-review    → Qualité et patterns
/security-scan  → Vulnérabilités
/verify         → Build + tests + lint
```

### Question rapide sans polluer le contexte

```
/aside "comment fonctionne le rate limiting dans Express ?"
→ Répond sans affecter le contexte de la tâche en cours
```

---

## Variables d'environnement clés

Référence des variables les plus utiles au quotidien. La liste complète officielle est sur `code.claude.com/docs/en/env-vars`.

### Authentification et API

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Clé API — requise en mode non-interactif et CI/CD |
| `ANTHROPIC_BASE_URL` | Proxie les requêtes vers une URL personnalisée |
| `ANTHROPIC_MODEL` | Surcharge le modèle par défaut |
| `CLAUDE_CONFIG_DIR` | Dossier de config (défaut : `~/.claude`) — utile pour plusieurs comptes |

### Modèle et effort

| Variable | Description |
|----------|-------------|
| `CLAUDE_CODE_EFFORT_LEVEL` | `low` / `medium` / `high` / `max` — seule façon de persister `max` |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | Limite les tokens de sortie par requête |
| `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING` | `1` = repasse en mode budget fixe (ancien comportement) |
| `CLAUDE_CODE_DISABLE_THINKING` | `1` = désactive l'extended thinking entièrement |
| `MAX_THINKING_TOKENS` | Budget de thinking en mode budget fixe |

### Fournisseurs cloud

| Variable | Description |
|----------|-------------|
| `CLAUDE_CODE_USE_BEDROCK` | `1` = utiliser Amazon Bedrock |
| `CLAUDE_CODE_USE_VERTEX` | `1` = utiliser Google Vertex AI |
| `ANTHROPIC_VERTEX_PROJECT_ID` | Projet GCP — requis pour Vertex AI |
| `CLAUDE_CODE_USE_FOUNDRY` | `1` = utiliser Microsoft Azure Foundry |

### Gestion du contexte et compaction

| Variable | Description |
|----------|-------------|
| `DISABLE_AUTO_COMPACT` | `1` = désactive la compaction automatique |
| `DISABLE_COMPACT` | `1` = désactive toute compaction |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | Seuil de déclenchement (défaut : ~95). Ex : `70` = compact plus tôt |
| `CLAUDE_CODE_DISABLE_AUTO_MEMORY` | `1` = désactive l'auto-mémoire |
| `CLAUDE_CODE_DISABLE_CLAUDE_MDS` | `1` = ne charge aucun fichier CLAUDE.md |

### Mode non-interactif et CI

| Variable | Description |
|----------|-------------|
| `CLAUDE_CODE_SIMPLE` | `1` = mode minimal (idem `--bare`) |
| `API_TIMEOUT_MS` | Timeout en ms (défaut : 600 000 = 10 min) |
| `CLAUDE_CODE_MAX_RETRIES` | Nombre de tentatives sur erreur API (défaut : 10) |
| `DISABLE_COST_WARNINGS` | `1` = supprime les avertissements de coût |
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | `1` = active les Agent Teams (experimental) |

### Hooks et shell

| Variable | Description |
|----------|-------------|
| `CLAUDE_ENV_FILE` | Script shell sourcé avant chaque commande Bash (ex : activation conda/virtualenv) |
| `CLAUDECODE` | `1` = positionné dans tout shell lancé par Claude — permet de détecter l'environnement |
| `BASH_DEFAULT_TIMEOUT_MS` | Timeout par défaut des commandes Bash |
| `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` | `1` = retire les credentials des environnements sous-processus |

### Debug et logging

| Variable | Description |
|----------|-------------|
| `CLAUDE_CODE_DEBUG_LOGS_DIR` | Dossier des logs de debug (défaut : `~/.claude/debug/<session-id>.txt`) |
| `CLAUDE_CODE_DEBUG_LOG_LEVEL` | `verbose` / `debug` / `info` / `warn` / `error` |
| `DISABLE_TELEMETRY` | `1` = opt-out de la télémétrie Statsig |
| `DISABLE_AUTOUPDATER` | `1` = désactive les mises à jour automatiques |

---

## Debugging — quand Claude fait n'importe quoi

Même avec une bonne configuration, Claude peut parfois boucler, ignorer des instructions, ou produire des résultats incorrects. Voici un guide de diagnostic par symptôme.

### Symptôme : Claude ignore des instructions permanentes

**Diagnostic :**
```
/memory
```
Vérifie que le fichier concerné (CLAUDE.md, règle, skill) apparaît dans la liste. S'il n'est pas là, Claude ne peut pas le voir.

**Causes fréquentes :**
- CLAUDE.md trop long (> 200 lignes) → les instructions en fin de fichier sont moins bien suivies
- Fichier de règle sans effet car la syntaxe `paths:` est incorrecte (chaîne au lieu de tableau YAML)
- Fichier dans le mauvais dossier (`.claude/rules/` vs `.claude/commands/`)
- Instruction contradictoire entre CLAUDE.md et le system prompt

**Fixes :**
- Raccourcir CLAUDE.md — déporter dans `.claude/rules/`
- Rendre les instructions plus concrètes et spécifiques (voir chapitre CLAUDE.md)
- Après `/compact`, CLAUDE.md est ré-injecté mais pas les instructions données en chat

### Symptôme : Claude boucle ou ne termine pas

**Diagnostic :** vérifier si Claude tourne en rond sur le même outil ou la même recherche.

**Solutions :**
1. Interrompre avec `Ctrl+C` ou `Escape`
2. Reformuler le prompt — être plus directif sur ce qu'on veut
3. Ajouter dans le prompt : "ne cherche pas plus loin, dis-moi ce que tu as trouvé"
4. Utiliser `--max-turns N` en mode `-p` pour forcer un arrêt
5. Si Claude cherche un fichier qui n'existe pas : lui dire explicitement que le fichier n'existe pas

**Si la boucle est dans un hook ECC :**
```bash
DISABLE_HOOKS=1 claude   # (si supporté) ou désactiver le hook dans settings.json
```

### Symptôme : outputs de mauvaise qualité, instructions mal suivies

**Vérifier le niveau d'effort :**
```
/effort high   # augmenter pour les tâches complexes
```

**Vérifier si le contexte est trop plein :**
- Le statut bar affiche l'usage — si > 80 %, compacter
- `/context` pour voir la répartition

**Techniques de réorientation :**
- Commencer une nouvelle question avec "Oublie ce qu'on a fait, concentre-toi uniquement sur X"
- `/clear` pour repartir avec un contexte propre
- Fournir un exemple de ce qu'on attend (few-shot)

### Symptôme : permissions refusées ou comportement inattendu

**Vérifier les règles actives :**
```
/permissions
```

**Vérifier les hooks bloquants (exit 2) :**
Les hooks PreToolUse qui retournent exit code 2 bloquent l'outil silencieusement. Si Claude ne peut soudainement plus faire quelque chose, vérifier `settings.json` → `hooks`.

**Désactiver temporairement les hooks :**
```bash
DISABLE_HOOKS=1 claude   # si la variable est supportée
```
Ou commenter le hook dans `settings.json` pour tester.

### Symptôme : bug reproductible à signaler

```
/bug
```

Ouvre un rapport de bug pré-rempli avec les informations de session. Soumettre sur `github.com/anthropics/claude-code/issues`.

### Symptôme : Claude modifie des fichiers qu'il ne devrait pas

**Prévention :** utiliser Plan Mode (`Shift+Tab`) avant de lancer des tâches complexes — Claude ne peut pas modifier de fichiers.

**Annuler les modifications :**
```
/rewind      # revenir à un checkpoint précédent (si le file checkpointing est activé)
git diff     # voir ce qui a changé
git checkout -- fichier.ts   # annuler les modifications sur un fichier
```

### Commandes de diagnostic utiles

| Commande | Usage |
|----------|-------|
| `/memory` | Liste les fichiers d'instructions chargés |
| `/permissions` | Voir les règles allow/deny actives |
| `/context` | Visualiser l'usage du contexte |
| `/doctor` | Vérifier la santé de l'installation Claude Code |
| `/bug` | Créer un rapport de bug |
| `claude --version` | Vérifier la version installée |

---

## Optimisation des coûts

| Paramètre                         | Valeur recommandée | Impact                                         |
| --------------------------------- | ------------------ | ---------------------------------------------- |
| Modèle par défaut                 | `sonnet`           | -60% vs Opus pour les tâches courantes         |
| `MAX_THINKING_TOKENS`             | `10000`            | -70% sur le thinking caché                     |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | `50`               | Meilleure qualité sur sessions longues         |
| `CLAUDE_CODE_SUBAGENT_MODEL`      | `haiku`            | Sous-agents légers sur le modèle le moins cher |

---

## Serveurs MCP

> Les MCP (Model Context Protocol) permettent à Claude d'appeler des outils externes directement.
> ECC fournit **6 serveurs actifs par défaut** (dans `.mcp.json`) et **30+ serveurs optionnels** (dans `mcp-configs/mcp-servers.json`).
>
> **Conseil** : garde moins de 10 MCP actifs simultanément pour préserver la fenêtre de contexte.

### Serveurs actifs par défaut

Ces 6 serveurs sont automatiquement disponibles dès l'installation d'ECC :

| Serveur               | Package                                            | Ce qu'il permet                                                                                                                |
| --------------------- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `github`              | `@modelcontextprotocol/server-github`              | Lire/créer des PRs, issues, fichiers, branches, repos GitHub directement depuis Claude                                         |
| `context7`            | `@upstash/context7-mcp`                            | Récupérer la documentation à jour de n'importe quelle lib (utilisé par le skill `documentation-lookup` et la commande `/docs`) |
| `exa`                 | HTTP `mcp.exa.ai`                                  | Recherche web neurale — utilisé par le skill `exa-search` et les agents de recherche                                           |
| `memory`              | `@modelcontextprotocol/server-memory`              | Mémoire persistante entre sessions — stockage de faits, décisions, contexte projet                                             |
| `playwright`          | `@playwright/mcp`                                  | Automatisation browser : naviguer, cliquer, remplir des formulaires, prendre des screenshots                                   |
| `sequential-thinking` | `@modelcontextprotocol/server-sequential-thinking` | Raisonnement en chaîne structurée (chain-of-thought) pour les tâches complexes                                                 |

### Serveurs optionnels (à activer selon le besoin)

Copier les entrées souhaitées depuis `mcp-configs/mcp-servers.json` dans ton `~/.claude.json` :

#### Développement & Infra

| Serveur      | Prérequis                                  | Ce qu'il permet                                                                              |
| ------------ | ------------------------------------------ | -------------------------------------------------------------------------------------------- |
| `jira`       | `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` | Rechercher, créer, commenter, faire avancer des tickets Jira                                 |
| `supabase`   | `--project-ref=<ref>`                      | Opérations base de données Supabase depuis Claude                                            |
| `vercel`     | HTTP — authentification Vercel             | Gérer les déploiements et projets Vercel                                                     |
| `railway`    | —                                          | Déploiements Railway                                                                         |
| `filesystem` | Chemin à configurer                        | Opérations filesystem élargies (au-delà du projet courant)                                   |
| `devfleet`   | `localhost:18801` (local)                  | Orchestration multi-agents — dispatch d'agents Claude en parallèle dans des worktrees isolés |

#### Cloudflare

| Serveur                       | Ce qu'il permet                             |
| ----------------------------- | ------------------------------------------- |
| `cloudflare-docs`             | Rechercher dans la documentation Cloudflare |
| `cloudflare-workers-builds`   | Gérer les builds Cloudflare Workers         |
| `cloudflare-workers-bindings` | Gérer les bindings Cloudflare Workers       |
| `cloudflare-observability`    | Accéder aux logs et métriques Cloudflare    |

#### Recherche & Documentation

| Serveur          | Prérequis                           | Ce qu'il permet                                                                   |
| ---------------- | ----------------------------------- | --------------------------------------------------------------------------------- |
| `exa-web-search` | `EXA_API_KEY`                       | Recherche web, ingestion de données, research approfondi via Exa                  |
| `confluence`     | `CONFLUENCE_BASE_URL`, email, token | Rechercher et lire des pages Confluence                                           |
| `laraplugins`    | HTTP — sans clé                     | Découvrir des packages Laravel par keyword, score de santé, compatibilité version |

#### Browser & Tests

| Serveur       | Prérequis               | Ce qu'il permet                                               |
| ------------- | ----------------------- | ------------------------------------------------------------- |
| `browserbase` | `BROWSERBASE_API_KEY`   | Sessions browser cloud — tests cross-browser sans setup local |
| `browser-use` | `x-browser-use-api-key` | Agent IA qui navigue le web comme un humain                   |

#### IA & Génération

| Serveur  | Prérequis | Ce qu'il permet                                           |
| -------- | --------- | --------------------------------------------------------- |
| `fal-ai` | `FAL_KEY` | Générer des images, vidéos, audio via les modèles fal.ai  |
| `magic`  | —         | Composants Magic UI — générer des composants React animés |

#### Qualité & Monitoring

| Serveur           | Installation                     | Ce qu'il permet                                                                                                                                     |
| ----------------- | -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `insaits`         | `pip install insa-its`           | Monitoring sécurité IA-to-IA — détection d'anomalies, exposition de credentials, hallucinations, 23 types d'anomalies, OWASP MCP Top 10. 100% local |
| `evalview`        | `pip install "evalview>=0.5,<1"` | Regression testing pour agents IA — snapshot comportement, détecter des régressions dans les appels d'outils                                        |
| `token-optimizer` | —                                | Réduction de contexte jusqu'à 95% par déduplication et compression                                                                                  |
| `omega-memory`    | `uvx omega-memory serve`         | Mémoire sémantique avancée avec knowledge graphs et coordination multi-agents (plus riche que `memory`)                                             |

#### Analytics

| Serveur      | Ce qu'il permet                               |
| ------------ | --------------------------------------------- |
| `clickhouse` | Requêtes analytiques ClickHouse depuis Claude |

### Activer un serveur optionnel

```bash
# 1. Ouvrir la config Claude
code ~/.claude.json   # ou ton éditeur préféré

# 2. Copier l'entrée depuis mcp-configs/mcp-servers.json
# Exemple pour Jira :
{
  "mcpServers": {
    "jira": {
      "command": "uvx",
      "args": ["mcp-atlassian==0.21.0"],
      "env": {
        "JIRA_URL": "https://ton-org.atlassian.net",
        "JIRA_EMAIL": "toi@exemple.com",
        "JIRA_API_TOKEN": "ton-token"
      }
    }
  }
}

# 3. Recharger
/reload-plugins
```

### Désactiver un MCP pour un projet spécifique

Dans le `.claude/settings.json` du projet :

```json
{
  "disabledMcpServers": ["playwright", "exa"]
}
```

---

## Ressources

- **Repository :** https://github.com/affaan-m/everything-claude-code
- **Issues / bugs :** GitHub Issues du repo
- **Licence :** MIT
