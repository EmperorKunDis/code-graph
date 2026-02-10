#!/bin/bash
# Uninstall Code Graph from a project

set -e

PROJECT_ROOT="${1:-.}"
PROJECT_ROOT="$(cd "$PROJECT_ROOT" && pwd)"

echo "🗑️  Removing Code Graph from: $PROJECT_ROOT"

rm -rf "$PROJECT_ROOT/.claude/skills/code-graph"
rm -f "$PROJECT_ROOT/.claude/commands/init-graph.md"
rm -f "$PROJECT_ROOT/.claude/commands/graph.md"
rm -f "$PROJECT_ROOT/.code_graph.json"
rm -f "$PROJECT_ROOT/code_graph_viewer.html"

echo ""
echo "✅ Removed. You may also want to:"
echo "   - Remove the 'Code Graph' section from CLAUDE.md"
echo "   - Remove hooks from .claude/settings.json"
echo "   - Remove .git/hooks/post-commit if you added the auto-update hook"
