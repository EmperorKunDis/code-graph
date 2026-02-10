#!/bin/bash
# ─────────────────────────────────────────────────────────────────
#  🕸️  Code Graph for Claude Code — Installer
#  https://github.com/EmperorKunDis/code-graph
# ─────────────────────────────────────────────────────────────────

set -e

# Colors
G='\033[0;32m'   # Green
C='\033[0;36m'   # Cyan
Y='\033[1;33m'   # Yellow
R='\033[0;31m'   # Red
B='\033[1m'      # Bold
N='\033[0m'      # Reset

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="${1:-.}"

# Resolve absolute path
if [ "$PROJECT_ROOT" = "." ]; then
    PROJECT_ROOT="$(pwd)"
else
    PROJECT_ROOT="$(cd "$PROJECT_ROOT" 2>/dev/null && pwd)" || {
        echo -e "${R}❌ Directory not found: $1${N}"
        exit 1
    }
fi

# Check we're not installing into the repo itself
if [ "$PROJECT_ROOT" = "$REPO_DIR" ]; then
    echo -e "${R}❌ Don't install into the code-graph repo itself.${N}"
    echo -e "   Usage: ${C}bash install.sh /path/to/your/project${N}"
    exit 1
fi

echo ""
echo -e "${C}  ┌─────────────────────────────────────────┐${N}"
echo -e "${C}  │  🕸️  Code Graph for Claude Code          │${N}"
echo -e "${C}  │  Codebase intelligence installer         │${N}"
echo -e "${C}  └─────────────────────────────────────────┘${N}"
echo ""
echo -e "  Target: ${G}$PROJECT_ROOT${N}"
echo ""

# ── 1. Create directories ───────────────────────────────────────
echo -e "  ${C}[1/5]${N} Creating directories..."
mkdir -p "$PROJECT_ROOT/.claude/commands"
mkdir -p "$PROJECT_ROOT/.claude/skills/code-graph/scripts"

# ── 2. Copy skill scripts ───────────────────────────────────────
echo -e "  ${C}[2/5]${N} Installing skill + scripts..."
cp "$REPO_DIR/claude-config/skills/code-graph/scripts/analyze_codebase.py" \
   "$PROJECT_ROOT/.claude/skills/code-graph/scripts/"
cp "$REPO_DIR/claude-config/skills/code-graph/scripts/generate_viewer.py" \
   "$PROJECT_ROOT/.claude/skills/code-graph/scripts/"
cp "$REPO_DIR/claude-config/skills/code-graph/scripts/query_graph.py" \
   "$PROJECT_ROOT/.claude/skills/code-graph/scripts/"
cp "$REPO_DIR/claude-config/skills/code-graph/SKILL.md" \
   "$PROJECT_ROOT/.claude/skills/code-graph/"
chmod +x "$PROJECT_ROOT/.claude/skills/code-graph/scripts/"*.py

# ── 3. Install slash commands ────────────────────────────────────
echo -e "  ${C}[3/5]${N} Installing /init-graph and /graph commands..."
cp "$REPO_DIR/claude-config/commands/init-graph.md" \
   "$PROJECT_ROOT/.claude/commands/"
cp "$REPO_DIR/claude-config/commands/graph.md" \
   "$PROJECT_ROOT/.claude/commands/"

# ── 4. Configure hooks ──────────────────────────────────────────
echo -e "  ${C}[4/5]${N} Configuring hooks..."
SETTINGS_FILE="$PROJECT_ROOT/.claude/settings.json"
if [ -f "$SETTINGS_FILE" ]; then
    echo -e "        ${Y}⚠  .claude/settings.json already exists — skipping${N}"
    echo -e "        Merge hooks manually from: ${C}$REPO_DIR/claude-config/settings.json${N}"
else
    cp "$REPO_DIR/claude-config/settings.json" "$SETTINGS_FILE"
    echo -e "        ${G}✓${N} Hooks installed"
fi

# ── 5. Update CLAUDE.md ─────────────────────────────────────────
echo -e "  ${C}[5/5]${N} Updating CLAUDE.md..."
CLAUDE_MD="$PROJECT_ROOT/CLAUDE.md"
SECTION_MARKER="## Code Graph"

if [ -f "$CLAUDE_MD" ]; then
    if grep -q "$SECTION_MARKER" "$CLAUDE_MD"; then
        echo -e "        ${Y}⚠  Code Graph section already in CLAUDE.md — skipping${N}"
    else
        echo "" >> "$CLAUDE_MD"
        cat "$REPO_DIR/CLAUDE_MD_SECTION.md" >> "$CLAUDE_MD"
        echo -e "        ${G}✓${N} Section appended to existing CLAUDE.md"
    fi
else
    cat "$REPO_DIR/CLAUDE_MD_SECTION.md" > "$CLAUDE_MD"
    echo -e "        ${G}✓${N} CLAUDE.md created"
fi

# ── Done ─────────────────────────────────────────────────────────
echo ""
echo -e "  ${G}┌─────────────────────────────────────────┐${N}"
echo -e "  ${G}│  ✅ Installation complete!               │${N}"
echo -e "  ${G}└─────────────────────────────────────────┘${N}"
echo ""
echo -e "  ${B}Next steps:${N}"
echo ""
echo -e "    ${C}1.${N} Open Claude Code in your project:"
echo -e "       ${G}cd $PROJECT_ROOT && claude${N}"
echo ""
echo -e "    ${C}2.${N} Generate the dependency graph:"
echo -e "       ${G}/init-graph${N}"
echo ""
echo -e "    ${C}3.${N} Query before editing:"
echo -e "       ${G}/graph file views/users.py${N}"
echo -e "       ${G}/graph impact models/user.py${N}"
echo -e "       ${G}/graph model User${N}"
echo ""
echo -e "  ${B}All commands:${N}  /graph overview | file | impact | deps | dependents"
echo -e "               model | hubs | search | path | risky-files | dead-code"
echo ""
