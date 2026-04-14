# Structure des dossiers — Plugin Claude Code

## Arborescence complète

```
~/.claude/plugins/
├── cache/                          ← sources brutes téléchargées
│   └── everything-claude-code/
│       └── everything-claude-code/
│           └── 1.9.0/              ← version exacte (git clone)
│               ├── commands/
│               ├── skills/
│               ├── agents/
│               └── ...
│
├── marketplaces/                   ← version "installée" (active)
│   └── everything-claude-code/
│       ├── CLAUDE.md
│       ├── commands/
│       ├── skills/
│       ├── agents/
│       ├── .mcp.json               ← MCP servers actifs
│       └── ...
│
├── data/                           ← état runtime du plugin
│   └── everything-claude-code-everything-claude-code/
│
├── installed_plugins.json          ← registre des plugins installés
├── known_marketplaces.json         ← liste des marketplaces connus
└── install-counts-cache.json
```

## Le rôle de chaque dossier

### `cache/`

C'est le **téléchargement brut** — le git clone complet du repo ECC avec tout son contenu (docs, tests, scripts, exemples…). Il contient des fichiers qui ne sont pas utilisés directement par Claude Code (ex: `tests/`, `research/`, `docs/`).

### `marketplaces/`

C'est la **version active** — seuls les fichiers que Claude Code charge réellement : commands, skills, agents, hooks, rules, et le `.mcp.json` des serveurs MCP actifs.

### `data/`

État runtime du plugin — mémoire persistante, instincts appris, données de session.

### Fichiers à la racine

| Fichier | Rôle |
|---------|------|
| `installed_plugins.json` | Registre des plugins installés (version, date, git SHA) |
| `known_marketplaces.json` | Liste des marketplaces connus |
| `install-counts-cache.json` | Cache des compteurs d'installation |

## Différence cache vs marketplaces

| `cache/` | `marketplaces/` |
|----------|-----------------|
| Copie complète du repo | Seuls les fichiers actifs |
| Référence pour les mises à jour | Ce que Claude Code charge réellement |
| Contient la version (`1.9.0/`) | Sans versioning |

Claude Code **lit les skills/agents/commands depuis `marketplaces/`**, pas depuis `cache/`. Le cache sert à vérifier les mises à jour et à reconstruire `marketplaces/` lors d'un `/reload-plugins`.
