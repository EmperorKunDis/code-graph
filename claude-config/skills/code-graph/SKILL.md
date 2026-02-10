---
name: code-graph
description: Analyze a codebase and query its dependency graph. This skill MUST be consulted before making code changes — use the query tool to check impact, dependencies, and risk of files being modified. Never read the full JSON — always use targeted queries.
---

# Code Graph — Codebase Intelligence for AI Development

## 🔴 MANDATORY: Query Before Every Code Change

Before modifying ANY code, Claude MUST run a targeted query to understand the impact.

**NEVER read `.code_graph.json` directly — it's too large. Always use `query_graph.py`.**

### Quick Reference

```bash
# What am I about to change? Check risk and connections
python3 .claude/skills/code-graph/scripts/query_graph.py file <path>

# What breaks if I change this? Full cascade analysis
python3 .claude/skills/code-graph/scripts/query_graph.py impact <path>

# What does this file depend on?
python3 .claude/skills/code-graph/scripts/query_graph.py deps <path>

# What depends on this file?
python3 .claude/skills/code-graph/scripts/query_graph.py dependents <path>
```

## All Available Commands

| Command | Usage | Returns |
|---------|-------|---------|
| `file <path>` | Check a file | Risk level, all connections in/out |
| `impact <path>` | Impact analysis | Full cascade: what breaks if this changes (3 levels deep) |
| `deps <path>` | Dependencies | What this file depends on (outgoing) |
| `dependents <path>` | Reverse deps | What depends on this file (incoming) |
| `model <name>` | Model usage | All readers/writers of a DB model |
| `hubs [--top N]` | Hub nodes | Most connected nodes = riskiest to change |
| `cluster <path>` | File cluster | All files in the same connected component |
| `path <from> <to>` | Find path | Shortest connection path between two files |
| `search <query>` | Search | Find nodes by name or file path |
| `stats` | Statistics | Project summary, node/edge counts |
| `dead-code` | Dead code | Isolated or unreferenced files |
| `risky-files [--top N]` | Risk ranking | Files ranked by change risk score |
| `endpoint <path>` | Endpoint chain | Full request chain: endpoint → service → model → cache |
| `overview` | Architecture | Compact project structure overview |
| `report` | Full report | **One call**: overview + risks + dead code + coverage gaps |
| `changes <f1> <f2>...` | Multi-file check | Pre-change analysis for multiple files at once |

## When to Use Which Command

### "I need to edit a file"
```bash
# Step 1: Check risk
python3 .claude/skills/code-graph/scripts/query_graph.py file views/users.py

# Step 2: If risk is MEDIUM or higher, check impact
python3 .claude/skills/code-graph/scripts/query_graph.py impact views/users.py
```

### "I need to add a new feature"
```bash
# Step 1: Understand the area
python3 .claude/skills/code-graph/scripts/query_graph.py overview

# Step 2: Find related existing code
python3 .claude/skills/code-graph/scripts/query_graph.py search <feature-keyword>

# Step 3: Check cluster patterns for consistency
python3 .claude/skills/code-graph/scripts/query_graph.py cluster <related-file>
```

### "I need to change a model/schema"
```bash
# ALWAYS check model usage before schema changes — this is HIGH RISK
python3 .claude/skills/code-graph/scripts/query_graph.py model User
```

### "I need to fix a bug"
```bash
# Step 1: Find the buggy file's connections
python3 .claude/skills/code-graph/scripts/query_graph.py file <buggy-file>

# Step 2: Check if the bug might exist in connected files
python3 .claude/skills/code-graph/scripts/query_graph.py deps <buggy-file>

# Step 3: Trace the request chain to find root cause
python3 .claude/skills/code-graph/scripts/query_graph.py endpoint <endpoint>
```

### "I need to refactor"
```bash
# Step 1: Identify the riskiest files
python3 .claude/skills/code-graph/scripts/query_graph.py risky-files --top 10

# Step 2: Check impact of each target file
python3 .claude/skills/code-graph/scripts/query_graph.py impact <file>

# Step 3: Find dead code to clean up
python3 .claude/skills/code-graph/scripts/query_graph.py dead-code
```

### "How are these two things connected?"
```bash
python3 .claude/skills/code-graph/scripts/query_graph.py path views/users.py models/user.py
```

## Risk Levels

| Level | Meaning | Action |
|-------|---------|--------|
| 🟢 LOW | ≤3 connections, no dependents | Safe to change freely |
| 🟡 MEDIUM | 4-10 connections | Check dependents before changing |
| 🔴 HIGH | 10+ connections, widely imported | Run full impact analysis, change carefully |
| ⛔ CRITICAL | 20+ connections, hub node | Warn user, suggest incremental approach |

## Generating / Updating the Graph

### First-time setup
```bash
python3 .claude/skills/code-graph/scripts/analyze_codebase.py . -o .code_graph.json --languages python,typescript --exclude migrations,node_modules,static,media,dist,.angular,__pycache__,htmlcov,fixtures
```

### Regenerate after significant changes
```bash
python3 .claude/skills/code-graph/scripts/analyze_codebase.py . -o .code_graph.json --languages python,typescript --exclude migrations,node_modules,static,media,dist,.angular,__pycache__,htmlcov,fixtures
```

### Interactive visual viewer
```bash
python3 .claude/skills/code-graph/scripts/generate_viewer.py .code_graph.json -o code_graph_viewer.html
open code_graph_viewer.html
```

### Auto-update via git hook (recommended)
```bash
# .git/hooks/post-commit
#!/bin/bash
python3 .claude/skills/code-graph/scripts/analyze_codebase.py . -o .code_graph.json --languages python,typescript --exclude migrations,node_modules,static,media,dist,.angular,__pycache__,htmlcov,fixtures
```
