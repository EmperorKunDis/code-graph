# Initialize Code Graph

Analyze the entire codebase and generate a dependency graph for intelligent code navigation.

## Steps

1. Run the codebase analyzer:
```bash
python3 .claude/skills/code-graph/scripts/analyze_codebase.py . -o .code_graph.json --languages python,typescript --exclude migrations,node_modules,static,media,dist,.angular,__pycache__,htmlcov,fixtures,collected_static,logs,.git,venv,.venv,env
```

2. Run the full report (overview + risks + dead code + coverage gaps in one call):
```bash
python3 .claude/skills/code-graph/scripts/query_graph.py report
```

3. Summarize findings to the user and remind them about `/graph` commands.
