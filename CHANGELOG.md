# Changelog

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
