# Contributing to Code Graph

Thanks for your interest! Here's how to help.

## Quick Start

```bash
git clone https://github.com/EmperorKunDis/code-graph.git
cd code-graph

# Test on a sample project
mkdir /tmp/test-project
bash install.sh /tmp/test-project
```

## Ways to Contribute

### 🐛 Bug Reports
Open an issue with: what you expected, what happened, your Python version, and project language.

### 🌐 Add Language Support
The analyzer in `claude-config/skills/code-graph/scripts/analyze_codebase.py` has two methods:
- `_analyze_python_file()` — full AST parsing (gold standard)
- `_analyze_generic_file()` — regex pattern matching (fallback)

To add better support for a language, create a new `_analyze_<lang>_file()` method with proper parsing.

### 🔍 Add Query Commands
The query engine in `claude-config/skills/code-graph/scripts/query_graph.py` is easy to extend. Add a new `cmd_<name>` method to `GraphQuery` class and register it in `main()`.

### 🎨 Improve the Viewer
The viewer generator in `claude-config/skills/code-graph/scripts/generate_viewer.py` outputs a self-contained HTML file. All JS/CSS is inline.

## Code Style

- Python 3.8+ compatible
- No external dependencies (stdlib only)
- Scripts must be self-contained (no pip install required)

## Pull Request Process

1. Fork and create a branch
2. Make your changes
3. Test with `bash install.sh /tmp/test && cd /tmp/test`
4. Open a PR with a clear description
