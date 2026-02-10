# Initialize Code Graph

Analyze the entire codebase and generate a dependency graph for intelligent code navigation.

## Steps

1. Run the codebase analyzer:
```bash
python3 .claude/skills/code-graph/scripts/analyze_codebase.py . -o .code_graph.json --languages python,typescript --exclude migrations,node_modules,static,media,dist,.angular,__pycache__,htmlcov,fixtures,collected_static,logs,.git,venv,.venv,env
```

2. Show the project overview:
```bash
python3 .claude/skills/code-graph/scripts/query_graph.py overview
```

3. Show the top 10 riskiest files:
```bash
python3 .claude/skills/code-graph/scripts/query_graph.py risky-files --top 10
```

4. Check for dead code:
```bash
python3 .claude/skills/code-graph/scripts/query_graph.py dead-code
```

5. Summarize findings to the user: how many nodes/edges were found, the architecture layers, the riskiest files, and any dead code detected.

6. Remind the user they can now use `/graph` commands for targeted queries.
