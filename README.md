<div align="center">

# 🕸️ Code Graph for Claude Code

**Give your AI developer a map of your codebase before it touches anything.**

Code Graph analyzes your project, builds a dependency graph, and lets Claude Code query it before every edit — so it always knows what depends on what.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Compatible-blueviolet)](https://claude.ai)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-green.svg)](https://python.org)

[Installation](#-installation) · [How It Works](#-how-it-works) · [Commands](#-commands) · [Screenshots](#-screenshots) · [Languages](#-supported-languages)

</div>

---

## The Problem

AI coding agents are blind. They edit files without understanding the full architecture. Change a model? 15 views break. Refactor a service? The cache layer falls apart.

**Code Graph fixes this.** It builds a complete dependency map of your codebase and gives Claude Code targeted queries — so before it edits `user_service.py`, it already knows that 5 files depend on it and the change will cascade through 3 levels.

```
You: "Refactor the user service to use async"

Claude Code (without Code Graph):
  → Edits user_service.py ✅
  → Forgets to update user_views.py ❌
  → Breaks sync_tasks.py ❌
  → Cache layer still calls sync methods ❌

Claude Code (with Code Graph):
  → Queries: impact user_service.py
  → Sees: 5 files affected across 3 levels
  → Updates ALL dependent files ✅
  → Verifies cache layer compatibility ✅
```

## ⚡ Installation

Pick one. Copy → paste into terminal → done.

### 🔹 Option A: This project only

```bash
git clone https://github.com/EmperorKunDis/code-graph.git /tmp/code-graph && bash /tmp/code-graph/install.sh . && rm -rf /tmp/code-graph && echo "✅ Done — open Claude Code and run: /init-graph"
```

### 🔹 Option B: All projects, forever

```bash
git clone https://github.com/EmperorKunDis/code-graph.git /tmp/code-graph && bash /tmp/code-graph/global-setup.sh && rm -rf /tmp/code-graph && exec $SHELL
```

Then for any new project:
```bash
cd ~/my-project && code-graph-install .
```

> **Both options:** after install, open Claude Code and type **`/init-graph`** to generate the graph.

### What gets installed

```
your-project/
├── CLAUDE.md                        ← adds Code Graph instructions
└── .claude/
    ├── settings.json                ← auto-query hook before edits
    ├── commands/
    │   ├── init-graph.md            ← /init-graph command
    │   └── graph.md                 ← /graph <query> command
    └── skills/code-graph/
        ├── SKILL.md                 ← skill instructions
        └── scripts/
            ├── analyze_codebase.py  ← graph generator
            ├── query_graph.py       ← targeted queries (the key piece)
            └── generate_viewer.py   ← HTML visualization
```

### Manual installation

If you prefer to install manually:

```bash
# Clone
git clone https://github.com/EmperorKunDis/code-graph.git

# Copy skill + commands into your project
mkdir -p /path/to/project/.claude/{commands,skills}
cp -r code-graph/claude-config/skills/code-graph /path/to/project/.claude/skills/
cp code-graph/claude-config/commands/*.md /path/to/project/.claude/commands/

# Add the CLAUDE.md section
cat code-graph/CLAUDE_MD_SECTION.md >> /path/to/project/CLAUDE.md
```

## 🔍 How It Works

### 1. Analyze → Build the graph

```
/init-graph
```

Scans every source file, parses AST (Python) or patterns (JS/TS/others), and detects:
- **Imports** between files
- **Database reads/writes** (ORM queries, raw SQL)
- **Cache operations** (Redis, Django cache)
- **API calls** (requests, fetch, axios)
- **Class inheritance** chains
- **Route → handler** mappings
- **Webhooks, events, signals**
- **Task/job definitions** (Celery, etc.)

Output: `.code_graph.json` — a complete graph of your codebase.

### 2. Query → Ask specific questions

Instead of reading the entire (huge) JSON, Claude Code runs targeted queries:

```bash
# Before editing a file — what's the risk?
python3 .claude/skills/code-graph/scripts/query_graph.py file views/users.py

# What breaks if I change this?
python3 .claude/skills/code-graph/scripts/query_graph.py impact models/user.py

# Who reads/writes this model?
python3 .claude/skills/code-graph/scripts/query_graph.py model User
```

Returns only the relevant nodes and edges — **a few lines** instead of thousands.

### 3. Protect → Auto-check before edits

The installed hook in `settings.json` makes Claude Code automatically query the graph before every file edit. No extra prompting needed.

## 📋 Commands

### Slash Commands

| Command | What it does |
|---------|-------------|
| `/init-graph` | Generate/regenerate the dependency graph |
| `/graph overview` | Compact architecture overview |
| `/graph file <path>` | Check a file's risk level and connections |
| `/graph impact <path>` | Full cascade analysis — what breaks if changed |
| `/graph deps <path>` | What a file depends on |
| `/graph dependents <path>` | What depends on a file |
| `/graph model <Name>` | All readers/writers of a database model |
| `/graph hubs` | Most connected (riskiest) nodes |
| `/graph search <query>` | Find nodes by name or path |
| `/graph path <from> <to>` | Shortest connection between two files |
| `/graph risky-files` | Files ranked by change risk |
| `/graph dead-code` | Find potentially unused code |
| `/graph endpoint <path>` | Full request chain for an endpoint |
| `/graph cluster <path>` | Show connected component |
| `/graph stats` | Project statistics |
| `/graph report` | **Full report** — overview + risks + dead code + gaps in one call |
| `/graph changes <f1> <f2>` | Pre-change check for multiple files at once |

### Example: Impact Analysis

```
> /graph impact core/services/user_service.py

💥 Impact Analysis: user_service.py
   Risk: 🟡 MEDIUM — 8 connections, 3 dependents

  → Direct dependents (3 files):
    [test] test_users.py — tests/test_users.py
    [task] sync_tasks.py — core/tasks/sync_tasks.py
    [endpoint] user_views.py — api/views/user_views.py

  →→ 2nd-level impact (1 files):
    [endpoint] __init__.py — api/views/__init__.py

  →→→ 3rd-level impact (1 files):
    [router] urls.py — api/urls.py

  📊 Total affected: 5 files across 3 levels
```

### Example: Model Usage

```
> /graph model User

🗄️  Model: User (core/models/user.py)
   Risk: 🔴 HIGH — 14 connections, 8 dependents

  📖 Read by (5):
    user_service.py [service]
    product_service.py [service]
    user_views.py [endpoint]
    ...

  ✏️  Written by (3):
    user_service.py [service]
    registration_view.py [endpoint]
    ...
```

## Risk Levels

| Level | Connections | Meaning |
|-------|------------|---------|
| 🟢 LOW | ≤3 | Safe to change freely |
| 🟡 MEDIUM | 4-10 | Check dependents first |
| 🔴 HIGH | 10+ | Run full impact analysis |
| ⛔ CRITICAL | 20+ | Warn user, suggest incremental approach |

## 📸 Screenshots

### Interactive Graph Viewer

Generate a visual graph you can explore in your browser:

```bash
python3 .claude/skills/code-graph/scripts/generate_viewer.py .code_graph.json -o graph.html
open graph.html
```

Features:
- Force-directed layout with physics simulation
- Filter by node type (endpoints, models, services...)
- Filter by edge type (imports, db_read, api_call...)
- Search nodes by name
- Double-click for detail panel with all connections
- Minimap for navigation
- Hover highlighting of connected nodes

## 🌐 Supported Languages

| Language | Analysis Method | Detected Patterns |
|----------|----------------|-------------------|
| **Python** | AST parsing + patterns | Imports, classes, decorators, ORM, signals, Celery tasks |
| **TypeScript** | Pattern matching | ES6 imports, routes, Prisma/Mongoose, fetch/axios |
| **JavaScript** | Pattern matching | require/import, Express routes, DB operations |
| **PHP** | Pattern matching | use/require, namespaces |
| **Ruby** | Pattern matching | require, include |
| **Go** | Pattern matching | import statements |
| **Java** | Pattern matching | import statements |
| **Rust** | Pattern matching | use/mod statements |
| **C#** | Pattern matching | using statements |
| **Vue/Svelte** | Pattern matching | Component imports, script analysis |

## Node Types

| Type | Color | Examples |
|------|-------|---------|
| `endpoint` | 🔵 Cyan | API views, route handlers, controllers |
| `collection` | 🔴 Red | Database models, schemas |
| `file` | 🟢 Green | Source files, modules |
| `component` | 🟢 Teal | Frontend components (React, Angular, Vue) |
| `service` | 🟢 Dark Teal | Business logic, service layer |
| `task` | 🟠 Orange | Background tasks, Celery, cron |
| `router` | 🔵 Blue | URL configs, route definitions |
| `serializer` | 🟠 Amber | Serializers, DTOs, data transformers |
| `middleware` | 🔵 Indigo | Middleware components |
| `webhook` | 🔴 Coral | Webhook handlers |
| `event` | 🟣 Pink | Signals, event handlers |
| `external_api` | 🟡 Yellow | External API integrations |
| `cache_key` | 🟣 Magenta | Cache operations |
| `utility` | ⚪ Gray | Helpers, utils |
| `test` | ⚪ Dark Gray | Test files |
| `config` | 🟤 Brown | Configuration files |

## ⚙️ Configuration

### Customize analyzer options

```bash
# Limit to specific languages
python3 .claude/skills/code-graph/scripts/analyze_codebase.py . -o .code_graph.json \
  --languages python,typescript

# Exclude directories
python3 .claude/skills/code-graph/scripts/analyze_codebase.py . -o .code_graph.json \
  --exclude migrations,fixtures,static,seeds

# Limit scan depth
python3 .claude/skills/code-graph/scripts/analyze_codebase.py . -o .code_graph.json \
  --max-depth 6
```

### Auto-update with git hook

The installer doesn't set this up automatically, but you can add it:

```bash
cat > .git/hooks/post-commit << 'EOF'
#!/bin/bash
python3 .claude/skills/code-graph/scripts/analyze_codebase.py . -o .code_graph.json \
  --languages python,typescript \
  --exclude migrations,node_modules,static,media,dist,.angular,__pycache__
EOF
chmod +x .git/hooks/post-commit
```

### Gitignore recommendation

```gitignore
# Generated viewer (large HTML file)
code_graph_viewer.html

# Keep .code_graph.json tracked — Claude Code needs it
# Do NOT gitignore .code_graph.json
```

## 🤝 Contributing

Contributions welcome! Some ideas:

- **More language analyzers** — add full AST parsing for TypeScript, Go, etc.
- **Framework-specific detection** — Next.js pages, FastAPI routes, Rails conventions
- **Graph diff** — show what changed between two graph versions
- **VS Code extension** — visualize the graph inline in your editor
- **MCP server** — expose graph queries as an MCP tool

## 📄 License

MIT — do whatever you want with it.

---

<div align="center">

**Built by [Praut s.r.o.](https://praut.cz)** — AI integration & business automation

*If Code Graph saves you from a cascading bug, star the repo ⭐*

</div>
