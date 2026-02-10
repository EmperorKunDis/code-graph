#!/usr/bin/env python3
"""
Code Graph Analyzer - Analyzes a codebase and generates a dependency graph JSON.

Scans source code files, detects relationships (imports, DB operations, API calls,
event handling, caching, etc.) and outputs a structured JSON graph.

Usage:
    python3 analyze_codebase.py /path/to/project -o code_graph.json
    python3 analyze_codebase.py /path/to/project --languages python,typescript
    python3 analyze_codebase.py /path/to/project --exclude migrations,fixtures
"""

import argparse
import ast
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ─── Configuration ───────────────────────────────────────────────────────────

DEFAULT_EXCLUDE_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "env",
    ".env", "dist", "build", ".next", ".nuxt", ".svelte-kit",
    "vendor", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "htmlcov", "coverage", ".coverage", "eggs", "*.egg-info",
    ".idea", ".vscode", ".DS_Store", "staticfiles", "media",
}

LANGUAGE_EXTENSIONS = {
    "python": {".py"},
    "javascript": {".js", ".jsx", ".mjs", ".cjs"},
    "typescript": {".ts", ".tsx", ".mts", ".cts"},
    "php": {".php"},
    "ruby": {".rb"},
    "java": {".java"},
    "go": {".go"},
    "rust": {".rs"},
    "csharp": {".cs"},
    "vue": {".vue"},
    "svelte": {".svelte"},
}

NODE_COLORS = {
    "endpoint": "#00d4ff",
    "collection": "#ff4466",
    "file": "#44ff88",
    "router": "#4488ff",
    "script": "#aa66ff",
    "task": "#ffaa00",
    "cache_key": "#ff44ff",
    "service": "#00cc99",
    "utility": "#aabbcc",
    "webhook": "#ff6644",
    "event": "#ff88cc",
    "external_api": "#ffdd44",
    "middleware": "#6666ff",
    "serializer": "#ffbb44",
    "test": "#888899",
    "config": "#aa8866",
    "component": "#44ddaa",
    "template": "#cc88ff",
}

EDGE_COLORS = {
    "imports": "#556677",
    "db_read": "#00aaff",
    "db_write": "#ff8800",
    "endpoint_handler": "#44ff88",
    "api_call": "#ffdd44",
    "cache_read": "#6688aa",
    "cache_write": "#8866aa",
    "webhook_receive": "#ff6644",
    "webhook_send": "#ff4422",
    "event_publish": "#ff88cc",
    "event_subscribe": "#cc88ff",
    "inherits": "#aaaaff",
    "calls": "#778899",
    "middleware_chain": "#6666ff",
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def make_id(text: str) -> str:
    """Create a short deterministic ID from text."""
    return hashlib.md5(text.encode()).hexdigest()[:12]


def relative_path(filepath: str, project_root: str) -> str:
    """Get path relative to project root."""
    return os.path.relpath(filepath, project_root)


# ─── Node & Edge Collectors ─────────────────────────────────────────────────

class GraphBuilder:
    """Collects nodes and edges during analysis."""

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.project_name = os.path.basename(os.path.abspath(project_root))
        self.nodes: dict[str, dict] = {}
        self.edges: list[dict] = []
        self.file_id_map: dict[str, str] = {}  # filepath -> node_id
        self._edge_set: set[tuple] = set()  # dedup edges
        self._pending_inheritance: list[tuple] = []  # (class_id, base_name)

    def add_node(self, node_id: str, label: str, node_type: str,
                 filepath: str = "", line: int = 0, **metadata) -> str:
        """Add or update a node."""
        if node_id not in self.nodes:
            self.nodes[node_id] = {
                "id": node_id,
                "label": label,
                "type": node_type,
                "file": filepath,
                "line": line,
                "metadata": metadata,
            }
        return node_id

    def add_file_node(self, filepath: str) -> str:
        """Add a file node and return its ID."""
        rel = relative_path(filepath, self.project_root)
        node_id = make_id(rel)
        self.file_id_map[rel] = node_id

        # Determine file type
        node_type = self._classify_file(rel, filepath)
        label = os.path.basename(rel)

        self.add_node(node_id, label, node_type, filepath=rel)
        return node_id

    def add_edge(self, source: str, target: str, edge_type: str, **metadata):
        """Add an edge (deduplicated)."""
        key = (source, target, edge_type)
        if key not in self._edge_set and source != target:
            self._edge_set.add(key)
            self.edges.append({
                "source": source,
                "target": target,
                "type": edge_type,
                "metadata": metadata,
            })

    def _classify_file(self, rel_path: str, abs_path: str) -> str:
        """Classify a file into a node type based on path and name patterns."""
        lower = rel_path.lower()
        name = os.path.basename(lower)

        # Test files
        if any(p in lower for p in ["test_", "_test.", "tests/", "spec.", "__tests__",
                                     ".test.", ".spec."]):
            return "test"

        # Config files
        if name in {"settings.py", "config.py", "conf.py", ".env", "config.js",
                     "config.ts", "webpack.config.js", "tsconfig.json", "package.json",
                     "pyproject.toml", "setup.py", "setup.cfg", "manage.py",
                     "docker-compose.yml", "dockerfile", "makefile", ".eslintrc.js",
                     "babel.config.js", "jest.config.js", "vite.config.ts",
                     "tailwind.config.js", "next.config.js", "nuxt.config.ts"}:
            return "config"

        # Routers / URL configs
        if any(p in lower for p in ["urls.py", "routes.", "router.", "routing."]):
            return "router"

        # Middleware
        if "middleware" in lower:
            return "middleware"

        # Serializers
        if any(p in lower for p in ["serializer", "schema", "dto"]):
            return "serializer"

        # Models / Collections
        if any(p in lower for p in ["models/", "models.py", "model.", "entities/",
                                     "entity."]):
            return "collection"

        # Views / Endpoints / Controllers
        if any(p in lower for p in ["views/", "views.py", "viewset", "controller",
                                     "endpoints/", "handlers/", "api/"]):
            return "endpoint"

        # Services
        if any(p in lower for p in ["services/", "service.", "use_cases/", "usecases/"]):
            return "service"

        # Tasks
        if any(p in lower for p in ["tasks/", "tasks.py", "celery", "jobs/",
                                     "cron", "workers/"]):
            return "task"

        # Webhooks
        if "webhook" in lower:
            return "webhook"

        # Events / Signals
        if any(p in lower for p in ["signals", "events/", "event.", "listeners/"]):
            return "event"

        # Utilities
        if any(p in lower for p in ["utils/", "utils.py", "helpers/", "helpers.",
                                     "lib/", "common/"]):
            return "utility"

        # Scripts / Management commands
        if any(p in lower for p in ["management/commands/", "scripts/", "bin/"]):
            return "script"

        # Templates
        if any(p in lower for p in ["templates/", "template.", ".html", ".jinja"]):
            return "template"

        # Components (frontend)
        if any(p in lower for p in ["components/", "component.", ".vue", ".svelte",
                                     ".jsx", ".tsx"]):
            return "component"

        return "file"

    def to_json(self) -> dict:
        """Export the graph as a JSON-serializable dict."""
        node_type_counts = defaultdict(int)
        for n in self.nodes.values():
            node_type_counts[n["type"]] += 1

        edge_type_counts = defaultdict(int)
        for e in self.edges:
            edge_type_counts[e["type"]] += 1

        return {
            "project": self.project_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "stats": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "node_types": dict(sorted(node_type_counts.items(),
                                          key=lambda x: -x[1])),
                "edge_types": dict(sorted(edge_type_counts.items(),
                                          key=lambda x: -x[1])),
            },
            "node_colors": NODE_COLORS,
            "edge_colors": EDGE_COLORS,
            "nodes": list(self.nodes.values()),
            "edges": self.edges,
        }


# ─── Python Analyzer ────────────────────────────────────────────────────────

class PythonAnalyzer:
    """Analyze Python files for imports, classes, functions, and relationships."""

    # Patterns for detecting various operations
    DB_READ_PATTERNS = [
        r'\.objects\.(all|filter|get|exclude|values|values_list|annotate|aggregate|count|exists|first|last|order_by|select_related|prefetch_related)',
        r'\.objects\.(raw|extra)',
        r'SELECT\s+.*\s+FROM',
        r'session\.(query|execute).*SELECT',
        r'cursor\.execute.*SELECT',
    ]

    DB_WRITE_PATTERNS = [
        r'\.objects\.(create|get_or_create|update_or_create|bulk_create|bulk_update)',
        r'\.(save|delete)\(\)',
        r'\.objects\.filter.*\.(update|delete)',
        r'INSERT\s+INTO',
        r'UPDATE\s+.*\s+SET',
        r'DELETE\s+FROM',
        r'session\.(add|merge|delete|commit)',
    ]

    CACHE_READ_PATTERNS = [
        r'cache\.(get|get_many|get_or_set)',
        r'redis.*\.(get|hget|hgetall|lrange|smembers|mget)',
    ]

    CACHE_WRITE_PATTERNS = [
        r'cache\.(set|set_many|delete|clear)',
        r'redis.*\.(set|hset|lpush|rpush|sadd|setex|mset)',
    ]

    API_CALL_PATTERNS = [
        r'requests\.(get|post|put|patch|delete|head|options)',
        r'httpx\.(get|post|put|patch|delete|head|options)',
        r'aiohttp\.ClientSession',
        r'urllib\.request\.urlopen',
        r'fetch\(',
        r'axios\.(get|post|put|patch|delete)',
    ]

    WEBHOOK_SEND_PATTERNS = [
        r'webhook.*send|send.*webhook',
        r'webhook.*post|post.*webhook',
        r'webhook.*trigger|trigger.*webhook',
    ]

    EVENT_PUBLISH_PATTERNS = [
        r'\.send\(|\.send_robust\(',
        r'signal.*send|emit\(',
        r'publish\(|dispatch\(',
        r'event.*fire|fire.*event',
    ]

    def __init__(self, graph: GraphBuilder):
        self.graph = graph

    def analyze_file(self, filepath: str):
        """Analyze a single Python file."""
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return

        rel_path = relative_path(filepath, self.graph.project_root)
        file_id = self.graph.file_id_map.get(rel_path)
        if not file_id:
            return

        # Parse AST for structured analysis
        try:
            tree = ast.parse(content, filename=filepath)
            self._analyze_ast(tree, filepath, file_id, rel_path)
        except SyntaxError:
            pass

        # Pattern-based analysis for things AST misses
        self._analyze_patterns(content, file_id, rel_path)

    def _analyze_ast(self, tree: ast.AST, filepath: str, file_id: str,
                     rel_path: str):
        """Analyze Python AST for imports, classes, and functions."""
        for node in ast.walk(tree):
            # Imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._resolve_import(alias.name, file_id, rel_path)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self._resolve_import(node.module, file_id, rel_path,
                                         names=[a.name for a in node.names])

            # Class definitions - detect models, views, serializers etc.
            elif isinstance(node, ast.ClassDef):
                self._analyze_class(node, filepath, file_id, rel_path)

            # Function definitions - detect endpoints, tasks etc.
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                self._analyze_function(node, filepath, file_id, rel_path)

    def _resolve_import(self, module_name: str, file_id: str, rel_path: str,
                        names: list[str] | None = None):
        """Resolve an import to a file in the project and create an edge."""
        # Convert module path to file path
        parts = module_name.split(".")
        project_root = self.graph.project_root

        # Try various resolutions
        candidates = []
        for i in range(len(parts), 0, -1):
            partial = os.path.join(*parts[:i])
            candidates.extend([
                partial + ".py",
                os.path.join(partial, "__init__.py"),
            ])

        # Also try relative to the current file's directory
        file_dir = os.path.dirname(rel_path)
        for i in range(len(parts), 0, -1):
            partial = os.path.join(file_dir, *parts[:i])
            candidates.extend([
                partial + ".py",
                os.path.join(partial, "__init__.py"),
            ])

        for candidate in candidates:
            normalized = os.path.normpath(candidate)
            if normalized in self.graph.file_id_map:
                target_id = self.graph.file_id_map[normalized]
                imported_names = ", ".join(names) if names else module_name
                self.graph.add_edge(file_id, target_id, "imports",
                                    module=module_name,
                                    names=imported_names)
                break

    def _analyze_class(self, node: ast.ClassDef, filepath: str,
                       file_id: str, rel_path: str):
        """Analyze a class definition for type classification and inheritance."""
        class_name = node.name
        bases = [self._get_name(b) for b in node.bases]

        # Detect model classes
        model_bases = {"Model", "models.Model", "Document", "Base",
                       "DeclarativeBase", "AbstractBaseUser", "AbstractUser"}
        if any(b in model_bases for b in bases):
            node_id = make_id(f"{rel_path}:{class_name}")
            self.graph.add_node(node_id, class_name, "collection",
                                filepath=rel_path, line=node.lineno,
                                bases=", ".join(bases))
            self.graph.add_edge(file_id, node_id, "endpoint_handler",
                                relation="defines")

        # Detect viewsets / views
        view_bases = {"ViewSet", "ModelViewSet", "APIView", "GenericAPIView",
                      "ListAPIView", "CreateAPIView", "RetrieveAPIView",
                      "UpdateAPIView", "DestroyAPIView", "View",
                      "TemplateView", "ListView", "DetailView", "FormView"}
        if any(b in view_bases for b in bases):
            node_id = make_id(f"{rel_path}:{class_name}")
            self.graph.add_node(node_id, class_name, "endpoint",
                                filepath=rel_path, line=node.lineno,
                                bases=", ".join(bases))
            self.graph.add_edge(file_id, node_id, "endpoint_handler",
                                relation="defines")

        # Detect serializers
        serializer_bases = {"Serializer", "ModelSerializer",
                            "HyperlinkedModelSerializer"}
        if any(b in serializer_bases for b in bases):
            node_id = make_id(f"{rel_path}:{class_name}")
            self.graph.add_node(node_id, class_name, "serializer",
                                filepath=rel_path, line=node.lineno)
            self.graph.add_edge(file_id, node_id, "endpoint_handler",
                                relation="defines")

        # Detect middleware
        if "Middleware" in class_name or any("Middleware" in b for b in bases):
            node_id = make_id(f"{rel_path}:{class_name}")
            self.graph.add_node(node_id, class_name, "middleware",
                                filepath=rel_path, line=node.lineno)
            self.graph.add_edge(file_id, node_id, "middleware_chain",
                                relation="defines")

        # Track inheritance — edges resolved in post-processing
        for base_name in bases:
            if base_name and base_name not in {"object", "type", "Exception",
                                                "Model", "models.Model", "Document",
                                                "Base", "DeclarativeBase",
                                                "AbstractBaseUser", "AbstractUser",
                                                "ViewSet", "ModelViewSet", "APIView",
                                                "GenericAPIView", "ListAPIView",
                                                "CreateAPIView", "RetrieveAPIView",
                                                "UpdateAPIView", "DestroyAPIView",
                                                "View", "TemplateView", "ListView",
                                                "DetailView", "FormView",
                                                "Serializer", "ModelSerializer",
                                                "HyperlinkedModelSerializer"}:
                class_id = make_id(f"{rel_path}:{class_name}")
                if class_id in self.graph.nodes:
                    # Store for deferred resolution
                    self.graph._pending_inheritance.append(
                        (class_id, base_name)
                    )

    def _analyze_function(self, node, filepath: str,
                          file_id: str, rel_path: str):
        """Analyze function definitions for decorators and type."""
        func_name = node.name

        for decorator in node.decorator_list:
            dec_name = self._get_decorator_name(decorator)

            # Celery tasks
            if dec_name in {"task", "shared_task", "app.task", "celery.task"}:
                node_id = make_id(f"{rel_path}:{func_name}")
                self.graph.add_node(node_id, func_name, "task",
                                    filepath=rel_path, line=node.lineno,
                                    decorator=dec_name)
                self.graph.add_edge(file_id, node_id, "endpoint_handler",
                                    relation="defines_task")

            # API endpoints (DRF decorators)
            if dec_name in {"api_view", "action", "route", "app.route",
                            "router.get", "router.post", "router.put",
                            "router.delete", "router.patch"}:
                node_id = make_id(f"{rel_path}:{func_name}")
                self.graph.add_node(node_id, func_name, "endpoint",
                                    filepath=rel_path, line=node.lineno,
                                    decorator=dec_name)
                self.graph.add_edge(file_id, node_id, "endpoint_handler",
                                    relation="defines_endpoint")

            # Signal receivers
            if dec_name in {"receiver"}:
                node_id = make_id(f"{rel_path}:{func_name}")
                self.graph.add_node(node_id, func_name, "event",
                                    filepath=rel_path, line=node.lineno)
                self.graph.add_edge(file_id, node_id, "event_subscribe",
                                    relation="signal_receiver")

    def _analyze_patterns(self, content: str, file_id: str, rel_path: str):
        """Pattern-based analysis for DB operations, API calls, caching, etc."""
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            # DB reads
            for pattern in self.DB_READ_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    # Try to extract model name
                    model_match = re.search(r'(\w+)\.objects', line)
                    if model_match:
                        model_name = model_match.group(1)
                        model_id = make_id(f"model:{model_name}")
                        self.graph.add_node(model_id, model_name, "collection",
                                            filepath=rel_path, line=i,
                                            detected_via="pattern")
                        self.graph.add_edge(file_id, model_id, "db_read",
                                            operation=line.strip()[:100])
                    break

            # DB writes
            for pattern in self.DB_WRITE_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    model_match = re.search(r'(\w+)\.objects', line)
                    if model_match:
                        model_name = model_match.group(1)
                        model_id = make_id(f"model:{model_name}")
                        self.graph.add_node(model_id, model_name, "collection",
                                            filepath=rel_path, line=i,
                                            detected_via="pattern")
                        self.graph.add_edge(file_id, model_id, "db_write",
                                            operation=line.strip()[:100])
                    break

            # Cache reads
            for pattern in self.CACHE_READ_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    cache_match = re.search(r'["\']([a-zA-Z_:]+)["\']', line)
                    cache_label = cache_match.group(1) if cache_match else "cache"
                    cache_id = make_id(f"cache:{cache_label}")
                    self.graph.add_node(cache_id, cache_label, "cache_key",
                                        filepath=rel_path, line=i)
                    self.graph.add_edge(file_id, cache_id, "cache_read")
                    break

            # Cache writes
            for pattern in self.CACHE_WRITE_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    cache_match = re.search(r'["\']([a-zA-Z_:]+)["\']', line)
                    cache_label = cache_match.group(1) if cache_match else "cache"
                    cache_id = make_id(f"cache:{cache_label}")
                    self.graph.add_node(cache_id, cache_label, "cache_key",
                                        filepath=rel_path, line=i)
                    self.graph.add_edge(file_id, cache_id, "cache_write")
                    break

            # API calls
            for pattern in self.API_CALL_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    url_match = re.search(r'["\']https?://([^"\']+)["\']', line)
                    api_label = url_match.group(1)[:40] if url_match else "external_api"
                    api_id = make_id(f"api:{api_label}")
                    self.graph.add_node(api_id, api_label, "external_api",
                                        filepath=rel_path, line=i)
                    self.graph.add_edge(file_id, api_id, "api_call")
                    break

            # Webhook sends
            for pattern in self.WEBHOOK_SEND_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    wh_id = make_id(f"webhook:send:{rel_path}")
                    self.graph.add_node(wh_id, "webhook_out", "webhook",
                                        filepath=rel_path, line=i)
                    self.graph.add_edge(file_id, wh_id, "webhook_send")
                    break

            # Event publishing
            for pattern in self.EVENT_PUBLISH_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    signal_match = re.search(r'(\w+)\.(send|send_robust|emit|publish|dispatch)', line)
                    if signal_match:
                        signal_name = signal_match.group(1)
                        evt_id = make_id(f"event:{signal_name}")
                        self.graph.add_node(evt_id, signal_name, "event",
                                            filepath=rel_path, line=i)
                        self.graph.add_edge(file_id, evt_id, "event_publish")
                    break

    def _get_name(self, node) -> str:
        """Get a string name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            return self._get_name(node.value)
        return ""

    def _get_decorator_name(self, node) -> str:
        """Get the name of a decorator."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_decorator_name(node.func)
        return ""


# ─── JavaScript/TypeScript Analyzer ─────────────────────────────────────────

class JSAnalyzer:
    """Analyze JavaScript/TypeScript files for imports and relationships."""

    IMPORT_PATTERNS = [
        # ES6 imports
        r'import\s+(?:(?:\{[^}]*\}|\w+|\*\s+as\s+\w+)\s*,?\s*)*\s*from\s*["\']([^"\']+)["\']',
        # require()
        r'require\s*\(\s*["\']([^"\']+)["\']\s*\)',
        # Dynamic import
        r'import\s*\(\s*["\']([^"\']+)["\']\s*\)',
    ]

    ROUTE_PATTERNS = [
        r'(app|router)\.(get|post|put|patch|delete|all|use)\s*\(\s*["\']([^"\']+)["\']',
        r'@(Get|Post|Put|Patch|Delete|All)\s*\(\s*["\']?([^"\')\s]*)',
        r'path\s*:\s*["\']([^"\']+)["\']',
    ]

    DB_PATTERNS = [
        r'\.(find|findOne|findMany|findById|findAll|aggregate|count|countDocuments)\s*\(',
        r'\.(create|insertOne|insertMany|save|updateOne|updateMany|deleteOne|deleteMany|remove|bulkWrite)\s*\(',
        r'\.(select|from|where|join|groupBy|orderBy|having)\s*\(',
        r'prisma\.\w+\.(findUnique|findFirst|findMany|create|update|delete|upsert|aggregate)',
        r'(SELECT|INSERT|UPDATE|DELETE)\s+',
    ]

    FETCH_PATTERNS = [
        r'fetch\s*\(\s*["`\']([^"`\']+)["`\']',
        r'axios\.(get|post|put|patch|delete)\s*\(\s*["`\']([^"`\']+)["`\']',
        r'http\.(get|post|put|patch|delete)\s*\(\s*["`\']([^"`\']+)["`\']',
    ]

    def __init__(self, graph: GraphBuilder):
        self.graph = graph

    def analyze_file(self, filepath: str):
        """Analyze a JS/TS file."""
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return

        rel_path = relative_path(filepath, self.graph.project_root)
        file_id = self.graph.file_id_map.get(rel_path)
        if not file_id:
            return

        self._analyze_imports(content, file_id, rel_path)
        self._analyze_routes(content, file_id, rel_path)
        self._analyze_db(content, file_id, rel_path)
        self._analyze_api_calls(content, file_id, rel_path)
        self._analyze_exports(content, file_id, rel_path)

    def _analyze_imports(self, content: str, file_id: str, rel_path: str):
        """Extract and resolve imports."""
        for pattern in self.IMPORT_PATTERNS:
            for match in re.finditer(pattern, content):
                module_path = match.group(1)

                # Skip node_modules imports
                if not module_path.startswith(".") and not module_path.startswith("@/"):
                    continue

                # Resolve relative path
                resolved = self._resolve_js_import(module_path, rel_path)
                if resolved and resolved in self.graph.file_id_map:
                    target_id = self.graph.file_id_map[resolved]
                    self.graph.add_edge(file_id, target_id, "imports",
                                        module=module_path)

    def _resolve_js_import(self, module_path: str, from_file: str) -> str | None:
        """Resolve a JS/TS import path to a project file."""
        if module_path.startswith("@/") or module_path.startswith("~/"):
            # Alias - try from project root
            clean = module_path[2:]
            base_dir = ""
        else:
            # Relative import
            clean = module_path
            base_dir = os.path.dirname(from_file)

        # Try various extensions
        extensions = [".ts", ".tsx", ".js", ".jsx", ".mjs", ".vue", ".svelte", ""]
        index_files = ["index.ts", "index.tsx", "index.js", "index.jsx"]

        target = os.path.normpath(os.path.join(base_dir, clean))

        for ext in extensions:
            candidate = target + ext
            if candidate in self.graph.file_id_map:
                return candidate

        # Try as directory with index file
        for idx in index_files:
            candidate = os.path.normpath(os.path.join(target, idx))
            if candidate in self.graph.file_id_map:
                return candidate

        return None

    def _analyze_routes(self, content: str, file_id: str, rel_path: str):
        """Detect route definitions."""
        for pattern in self.ROUTE_PATTERNS:
            for match in re.finditer(pattern, content):
                groups = match.groups()
                route_path = groups[-1] if groups else ""
                if route_path:
                    method = groups[1].upper() if len(groups) > 1 else "GET"
                    node_id = make_id(f"route:{method}:{route_path}")
                    self.graph.add_node(node_id, f"{method} {route_path}",
                                        "endpoint", filepath=rel_path,
                                        method=method, path=route_path)
                    self.graph.add_edge(file_id, node_id, "endpoint_handler")

    def _analyze_db(self, content: str, file_id: str, rel_path: str):
        """Detect database operations."""
        for pattern in self.DB_PATTERNS:
            for match in re.finditer(pattern, content):
                line = match.group(0)
                # Determine if read or write
                reads = {"find", "findOne", "findMany", "findById", "findAll",
                         "aggregate", "count", "countDocuments", "select",
                         "findUnique", "findFirst", "SELECT"}
                edge_type = "db_read" if any(r in line for r in reads) else "db_write"

                # Try to get model/collection name
                model_match = re.search(r'(?:prisma\.)?(\w+)\.(?:find|create|update|delete|save|insert|remove)', line)
                if model_match:
                    model_name = model_match.group(1)
                    model_id = make_id(f"model:{model_name}")
                    self.graph.add_node(model_id, model_name, "collection",
                                        filepath=rel_path)
                    self.graph.add_edge(file_id, model_id, edge_type)

    def _analyze_api_calls(self, content: str, file_id: str, rel_path: str):
        """Detect external API calls."""
        for pattern in self.FETCH_PATTERNS:
            for match in re.finditer(pattern, content):
                groups = match.groups()
                url = groups[-1] if groups else ""
                if url and ("http" in url or url.startswith("/")):
                    api_label = url[:50]
                    api_id = make_id(f"api:{api_label}")
                    self.graph.add_node(api_id, api_label, "external_api",
                                        filepath=rel_path)
                    self.graph.add_edge(file_id, api_id, "api_call", url=url)

    def _analyze_exports(self, content: str, file_id: str, rel_path: str):
        """Detect component/function exports for better labeling."""
        # React components
        component_match = re.search(
            r'export\s+(?:default\s+)?(?:function|class|const)\s+(\w+)', content)
        if component_match:
            name = component_match.group(1)
            if name[0].isupper() and any(ext in rel_path for ext in
                                          [".jsx", ".tsx", ".vue", ".svelte"]):
                self.graph.nodes.get(self.graph.file_id_map.get(rel_path, ""), {}) \
                    .update({"label": name})


# ─── Generic Analyzer (PHP, Ruby, Go, Java, etc.) ───────────────────────────

class GenericAnalyzer:
    """Pattern-based analysis for languages without dedicated AST parsing."""

    IMPORT_PATTERNS_BY_LANG = {
        "php": [
            r'use\s+([A-Z][\w\\]+)',
            r'require(?:_once)?\s*(?:\()?\s*["\']([^"\']+)["\']',
            r'include(?:_once)?\s*(?:\()?\s*["\']([^"\']+)["\']',
        ],
        "ruby": [
            r'require\s+["\']([^"\']+)["\']',
            r'require_relative\s+["\']([^"\']+)["\']',
            r'include\s+(\w+)',
        ],
        "java": [
            r'import\s+([\w.]+)',
        ],
        "go": [
            r'import\s+["\']([^"\']+)["\']',
            r'"([^"]+)"',  # inside import block
        ],
        "rust": [
            r'use\s+([\w:]+)',
            r'mod\s+(\w+)',
        ],
        "csharp": [
            r'using\s+([\w.]+)',
        ],
    }

    def __init__(self, graph: GraphBuilder, language: str):
        self.graph = graph
        self.language = language

    def analyze_file(self, filepath: str):
        """Analyze a file using patterns."""
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return

        rel_path = relative_path(filepath, self.graph.project_root)
        file_id = self.graph.file_id_map.get(rel_path)
        if not file_id:
            return

        # Import analysis
        patterns = self.IMPORT_PATTERNS_BY_LANG.get(self.language, [])
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                module = match.group(1)
                # Try to find matching file
                for candidate_path, candidate_id in self.graph.file_id_map.items():
                    candidate_name = os.path.splitext(os.path.basename(candidate_path))[0]
                    if module.endswith(candidate_name) or candidate_name in module:
                        self.graph.add_edge(file_id, candidate_id, "imports",
                                            module=module)
                        break

        # Generic pattern detection (DB, API, etc.) - same as Python
        self._detect_generic_patterns(content, file_id, rel_path)

    def _detect_generic_patterns(self, content: str, file_id: str, rel_path: str):
        """Detect common patterns regardless of language."""
        # HTTP/API calls
        api_patterns = [
            r'https?://[\w\-_.~:/?#\[\]@!$&\'()*+,;=%]+',
        ]
        for pattern in api_patterns:
            for match in re.finditer(pattern, content):
                url = match.group(0)
                if any(skip in url for skip in ["example.com", "localhost",
                                                  "127.0.0.1", "schema.org"]):
                    continue
                api_label = url[:50]
                api_id = make_id(f"api:{api_label}")
                self.graph.add_node(api_id, api_label, "external_api",
                                    filepath=rel_path)
                self.graph.add_edge(file_id, api_id, "api_call", url=url)


# ─── URL/Route Analyzer (Django specific) ───────────────────────────────────

class DjangoURLAnalyzer:
    """Analyze Django URL configurations to map routes to views."""

    URL_PATTERNS = [
        # path() and re_path()
        r'(?:path|re_path)\s*\(\s*["\']([^"\']*)["\'].*?(\w+(?:\.\w+)*)',
        # include()
        r'include\s*\(\s*["\']([^"\']+)["\']',
    ]

    def __init__(self, graph: GraphBuilder):
        self.graph = graph

    def analyze_file(self, filepath: str):
        """Analyze a Django URL config file."""
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return

        rel_path = relative_path(filepath, self.graph.project_root)
        file_id = self.graph.file_id_map.get(rel_path)
        if not file_id:
            return

        # Mark as router
        if file_id in self.graph.nodes:
            self.graph.nodes[file_id]["type"] = "router"

        for pattern in self.URL_PATTERNS:
            for match in re.finditer(pattern, content):
                url_path = match.group(1)
                view_ref = match.group(2) if match.lastindex > 1 else None

                route_id = make_id(f"route:{url_path}")
                self.graph.add_node(route_id, url_path or "/", "endpoint",
                                    filepath=rel_path, path=url_path)
                self.graph.add_edge(file_id, route_id, "endpoint_handler",
                                    view=view_ref or "")


# ─── Main Scanner ────────────────────────────────────────────────────────────

def scan_project(project_root: str, exclude_dirs: set[str],
                 max_depth: int, languages: set[str] | None) -> GraphBuilder:
    """Scan the entire project and build the graph."""

    # Collect valid extensions
    valid_extensions = set()
    if languages:
        for lang in languages:
            if lang in LANGUAGE_EXTENSIONS:
                valid_extensions.update(LANGUAGE_EXTENSIONS[lang])
    else:
        for exts in LANGUAGE_EXTENSIONS.values():
            valid_extensions.update(exts)

    graph = GraphBuilder(project_root)

    # Phase 1: Discover all files and create file nodes
    print(f"📂 Scanning project: {project_root}")
    file_count = 0

    for root, dirs, files in os.walk(project_root):
        # Calculate depth
        depth = root.replace(project_root, "").count(os.sep)
        if depth > max_depth:
            dirs.clear()
            continue

        # Exclude directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs
                   and not d.startswith(".")]

        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in valid_extensions:
                continue

            filepath = os.path.join(root, filename)
            graph.add_file_node(filepath)
            file_count += 1

    print(f"   Found {file_count} source files")

    # Phase 2: Analyze each file for relationships
    print("🔍 Analyzing relationships...")

    python_analyzer = PythonAnalyzer(graph)
    js_analyzer = JSAnalyzer(graph)
    django_url_analyzer = DjangoURLAnalyzer(graph)

    analyzed = 0
    for rel_path, node_id in list(graph.file_id_map.items()):
        filepath = os.path.join(project_root, rel_path)
        ext = os.path.splitext(filepath)[1].lower()

        if ext == ".py":
            python_analyzer.analyze_file(filepath)
            # Check if it's a URL config
            if "urls" in rel_path.lower():
                django_url_analyzer.analyze_file(filepath)
        elif ext in {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts",
                     ".cts", ".vue", ".svelte"}:
            js_analyzer.analyze_file(filepath)
        else:
            # Determine language from extension
            for lang, exts in LANGUAGE_EXTENSIONS.items():
                if ext in exts:
                    GenericAnalyzer(graph, lang).analyze_file(filepath)
                    break

        analyzed += 1
        if analyzed % 100 == 0:
            print(f"   Analyzed {analyzed}/{file_count} files...")

    print(f"✅ Analysis complete: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
    return graph


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Analyze a codebase and generate a dependency graph JSON."
    )
    parser.add_argument("project_root", help="Path to the project root directory")
    parser.add_argument("-o", "--output", default="code_graph.json",
                        help="Output JSON file path (default: code_graph.json)")
    parser.add_argument("--exclude", default="",
                        help="Additional directories to exclude (comma-separated)")
    parser.add_argument("--max-depth", type=int, default=10,
                        help="Maximum directory depth to scan (default: 10)")
    parser.add_argument("--languages", default="",
                        help="Limit to specific languages (comma-separated)")

    args = parser.parse_args()

    # Validate project root
    project_root = os.path.abspath(args.project_root)
    if not os.path.isdir(project_root):
        print(f"❌ Error: {project_root} is not a directory")
        sys.exit(1)

    # Build exclusion set
    exclude = DEFAULT_EXCLUDE_DIRS.copy()
    if args.exclude:
        exclude.update(d.strip() for d in args.exclude.split(","))

    # Parse languages
    languages = None
    if args.languages:
        languages = {l.strip().lower() for l in args.languages.split(",")}
        unknown = languages - set(LANGUAGE_EXTENSIONS.keys())
        if unknown:
            print(f"⚠️  Unknown languages: {', '.join(unknown)}")
            print(f"   Supported: {', '.join(LANGUAGE_EXTENSIONS.keys())}")

    # Run analysis
    graph = scan_project(project_root, exclude, args.max_depth, languages)

    # Save JSON
    output_path = os.path.abspath(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph.to_json(), f, indent=2, ensure_ascii=False)

    print(f"💾 Graph saved to: {output_path}")

    # Print summary
    data = graph.to_json()
    print(f"\n📊 Summary for '{data['project']}':")
    print(f"   Nodes: {data['stats']['total_nodes']}")
    print(f"   Edges: {data['stats']['total_edges']}")
    print(f"\n   Node types:")
    for ntype, count in data["stats"]["node_types"].items():
        print(f"     {ntype}: {count}")
    print(f"\n   Edge types:")
    for etype, count in data["stats"]["edge_types"].items():
        print(f"     {etype}: {count}")


if __name__ == "__main__":
    main()
