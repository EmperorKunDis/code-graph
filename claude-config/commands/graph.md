# Query Code Graph

Run a targeted query on the code graph. Usage: `/graph <command> <args>`

Available commands: file, impact, deps, dependents, model, hubs, cluster, path, search, stats, dead-code, risky-files, endpoint, overview

## Instructions

Parse the user's arguments from: $ARGUMENTS

If no arguments provided, run `overview`.

Run the appropriate query:
```bash
python3 .claude/skills/code-graph/scripts/query_graph.py $ARGUMENTS
```

If the `.code_graph.json` file doesn't exist, tell the user to run `/init-graph` first.

Present the results clearly. If the query shows HIGH or CRITICAL risk files, warn the user before making changes to those files.
