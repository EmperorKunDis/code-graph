# Changelog

## [1.1.0] — 2026-02-10

### Fixed
- **Ghost node bug**: Analyzer created edges to non-existent nodes (e.g. `? []` with 92 connections). Added edge validation in `to_json()` that removes all ghost edges.
- **Barrel exports misclassified**: `index.ts`, `__init__.py` and similar barrel files in `models/` directories were classified as `collection` instead of `file`. Now detected early in classification.
- **Inheritance edges**: Previously created edges to phantom `class:Model` nodes. Now deferred and resolved only to existing nodes.
- **dead-code truncation**: Was limited to 15 results, forcing Claude Code to spawn sub-agents. Now grouped by type with `--all` flag for full output.

### Added
- **`report` command**: Full project report in one call — overview + risks + dead code + coverage gaps. Replaces 6 separate queries.
- **`changes <f1> <f2> ...` command**: Pre-change analysis for multiple files at once with aggregate impact.
- **`--all` flag**: Show all results without truncation (dead-code, etc.)
- **Angular detection**: `.component.ts`, `.store.ts`, `.guard.ts`, `.interceptor.ts`, `.pipe.ts`, `.directive.ts`, `.resolver.ts`, `.module.ts` patterns now correctly classified.
- **Edge validation**: `validate_edges()` runs before JSON export, removing any edges pointing to non-existent nodes.
- **Deferred inheritance resolution**: Inheritance edges resolved after all files analyzed, finding actual base class nodes by label.

### Improved
- **init-graph**: Now uses single `report` command instead of 4 separate queries.
- **Stats**: Shows ghost edge count when edges were filtered.
- **Dead code grouping**: Results grouped by node type for readability.

## 1.0.0 (2026-02-10)

### 🎉 Initial Release

- **Codebase Analyzer** — AST-based Python analysis + pattern-based support for 9 more languages
- **Query Engine** — 14 targeted commands for querying the graph without loading it all
- **Interactive Viewer** — Force-directed HTML visualization with filters, search, minimap
- **Claude Code Integration** — Slash commands (`/init-graph`, `/graph`), hooks, CLAUDE.md section
- **One-command installer** — `bash install.sh /path/to/project`

### Detected Patterns
- 16 node types (endpoint, collection, component, service, task, router, etc.)
- 14 edge types (imports, db_read, db_write, endpoint_handler, api_call, cache, webhooks, etc.)

### Supported Languages
- Python (full AST parsing)
- TypeScript, JavaScript, PHP, Ruby, Go, Java, Rust, C#, Vue/Svelte (pattern matching)
