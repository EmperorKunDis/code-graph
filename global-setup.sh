#!/bin/bash
# ─────────────────────────────────────────────────────────────────
#  🕸️  Code Graph — Global Setup for Claude Code
#  Makes code-graph a standard part of every Claude Code session
# ─────────────────────────────────────────────────────────────────

set -e

G='\033[0;32m'
C='\033[0;36m'
Y='\033[1;33m'
B='\033[1m'
N='\033[0m'

echo ""
echo -e "${C}  ┌─────────────────────────────────────────┐${N}"
echo -e "${C}  │  🕸️  Code Graph — Global Setup           │${N}"
echo -e "${C}  │  Standard workflow for all projects      │${N}"
echo -e "${C}  └─────────────────────────────────────────┘${N}"
echo ""

# ── 1. Install to permanent location ─────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CODE_GRAPH_HOME="$HOME/.code-graph"

if [ -d "$CODE_GRAPH_HOME" ]; then
    echo -e "  ${C}[1/4]${N} Updating existing installation..."
    rm -rf "$CODE_GRAPH_HOME"
fi

echo -e "  ${C}[1/4]${N} Installing code-graph to ~/.code-graph..."
cp -r "$SCRIPT_DIR" "$CODE_GRAPH_HOME"

# ── 2. Add global CLAUDE.md ─────────────────────────────────────
echo -e "  ${C}[2/4]${N} Setting up global Claude Code memory..."

GLOBAL_CLAUDE_DIR="$HOME/.claude"
mkdir -p "$GLOBAL_CLAUDE_DIR"

GLOBAL_CLAUDE_MD="$GLOBAL_CLAUDE_DIR/CLAUDE.md"

GLOBAL_SECTION='## Code Graph — Global Standard

For every project, before making code changes:

1. Check if `.code_graph.json` exists in the project root
2. If NOT: ask the user if they want to run `/init-graph` to generate it
3. If YES: use `python3 .claude/skills/code-graph/scripts/query_graph.py` for targeted queries before editing files

**NEVER read .code_graph.json directly. Always use query_graph.py.**

Quick install for any new project:
```bash
bash ~/.code-graph/install.sh .
```

After installing, available commands:
- `/init-graph` — generate dependency graph
- `/graph file <path>` — check risk before editing
- `/graph impact <path>` — cascade analysis
- `/graph model <Name>` — model usage
- `/graph overview` — architecture overview'

if [ -f "$GLOBAL_CLAUDE_MD" ]; then
    if grep -q "Code Graph" "$GLOBAL_CLAUDE_MD"; then
        echo -e "        ${Y}⚠  Code Graph section already in global CLAUDE.md${N}"
    else
        echo "" >> "$GLOBAL_CLAUDE_MD"
        echo "$GLOBAL_SECTION" >> "$GLOBAL_CLAUDE_MD"
        echo -e "        ${G}✓${N} Added to existing global CLAUDE.md"
    fi
else
    echo "$GLOBAL_SECTION" > "$GLOBAL_CLAUDE_MD"
    echo -e "        ${G}✓${N} Created global CLAUDE.md"
fi

# ── 3. Add shell alias ──────────────────────────────────────────
echo -e "  ${C}[3/4]${N} Adding shell alias..."

ALIAS_LINE='alias code-graph-install="bash ~/.code-graph/install.sh"'

# Detect shell
if [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
    SHELL_RC="$HOME/.bashrc"
else
    SHELL_RC="$HOME/.zshrc"
fi

if grep -q "code-graph-install" "$SHELL_RC" 2>/dev/null; then
    echo -e "        ${Y}⚠  Alias already exists in $SHELL_RC${N}"
else
    echo "" >> "$SHELL_RC"
    echo "# Code Graph for Claude Code" >> "$SHELL_RC"
    echo "$ALIAS_LINE" >> "$SHELL_RC"
    echo -e "        ${G}✓${N} Added alias to $SHELL_RC"
fi

# ── 4. Create global git template hook ───────────────────────────
echo -e "  ${C}[4/4]${N} Setting up git template for new repos..."

GIT_TEMPLATE="$HOME/.git-templates/hooks"
mkdir -p "$GIT_TEMPLATE"

cat > "$GIT_TEMPLATE/post-commit" << 'HOOK'
#!/bin/bash
# Auto-regenerate code graph after commit (if installed)
if [ -f .claude/skills/code-graph/scripts/analyze_codebase.py ] && [ -f .code_graph.json ]; then
    python3 .claude/skills/code-graph/scripts/analyze_codebase.py . -o .code_graph.json \
        --exclude migrations,node_modules,static,media,dist,.angular,__pycache__,htmlcov,fixtures,venv,.venv 2>/dev/null &
fi
HOOK
chmod +x "$GIT_TEMPLATE/post-commit"

# Set global git template
git config --global init.templateDir "$HOME/.git-templates"
echo -e "        ${G}✓${N} Git template hook created"

# ── Done ─────────────────────────────────────────────────────────
echo ""
echo -e "  ${G}┌─────────────────────────────────────────┐${N}"
echo -e "  ${G}│  ✅ Global setup complete!               │${N}"
echo -e "  ${G}└─────────────────────────────────────────┘${N}"
echo ""
echo -e "  ${B}What's configured:${N}"
echo ""
echo -e "    ${G}✓${N} ~/.code-graph/              — repo with all scripts"
echo -e "    ${G}✓${N} ~/.claude/CLAUDE.md          — global instruction for Claude Code"
echo -e "    ${G}✓${N} code-graph-install alias     — quick install for any project"
echo -e "    ${G}✓${N} git template hook            — auto-update graph on commit"
echo ""
echo -e "  ${B}How to use:${N}"
echo ""
echo -e "    ${C}For any project — install code-graph:${N}"
echo -e "    ${G}cd ~/my-project && code-graph-install .${N}"
echo ""
echo -e "    ${C}Then in Claude Code:${N}"
echo -e "    ${G}/init-graph${N}                    — generate the graph"
echo -e "    ${G}/graph impact views.py${N}         — check before editing"
echo ""
echo -e "    ${C}Or just start Claude Code — it will auto-suggest${N}"
echo -e "    ${C}installing code-graph thanks to global CLAUDE.md${N}"
echo ""
echo -e "  ${Y}Run 'source $SHELL_RC' or restart terminal for alias.${N}"
echo ""
