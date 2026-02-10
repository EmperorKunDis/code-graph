## Code Graph — Codebase Intelligence

This project uses a dependency graph (`.code_graph.json`) for understanding code architecture before making changes.

### Before Any Code Change

**MANDATORY**: Before editing any file, query its impact:
```bash
python3 .claude/skills/code-graph/scripts/query_graph.py file <path-being-edited>
```

If risk is 🟡 MEDIUM or higher, also run:
```bash
python3 .claude/skills/code-graph/scripts/query_graph.py impact <path-being-edited>
```

**NEVER read `.code_graph.json` directly — it's too large. Always use `query_graph.py`.**

### Quick Commands

| Need | Command |
|------|---------|
| Check a file before editing | `python3 .claude/skills/code-graph/scripts/query_graph.py file <path>` |
| Full impact analysis | `python3 .claude/skills/code-graph/scripts/query_graph.py impact <path>` |
| Find what depends on a file | `python3 .claude/skills/code-graph/scripts/query_graph.py dependents <path>` |
| Check model usage before schema change | `python3 .claude/skills/code-graph/scripts/query_graph.py model <ModelName>` |
| Find related code | `python3 .claude/skills/code-graph/scripts/query_graph.py search <keyword>` |
| Architecture overview | `python3 .claude/skills/code-graph/scripts/query_graph.py overview` |
| Riskiest files | `python3 .claude/skills/code-graph/scripts/query_graph.py risky-files` |
| Find dead code | `python3 .claude/skills/code-graph/scripts/query_graph.py dead-code` |
| Connection path between files | `python3 .claude/skills/code-graph/scripts/query_graph.py path <from> <to>` |
| Full project report (one call) | `python3 .claude/skills/code-graph/scripts/query_graph.py report` |
| Pre-check multiple files | `python3 .claude/skills/code-graph/scripts/query_graph.py changes <f1> <f2>` |
| Regenerate graph | `/init-graph` |

### Risk Levels

- 🟢 LOW (≤3 connections) — safe to change
- 🟡 MEDIUM (4-10) — check dependents first
- 🔴 HIGH (10+) — run full impact analysis
- ⛔ CRITICAL (20+) — warn user, suggest incremental approach

### When to Regenerate

Run `/init-graph` after: adding new files, significant refactoring, changing imports, or modifying models.
