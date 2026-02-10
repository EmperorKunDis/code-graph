#!/usr/bin/env python3
"""
Code Graph Query Tool — Query the code graph without loading it all into context.

Claude Code calls this script with specific queries and gets back only the
relevant nodes and edges, keeping context window usage minimal.

Usage:
    python3 query_graph.py <command> [args] [--graph .code_graph.json]

Commands:
    file <path>           Show a file's connections and risk level
    impact <path>         Show full impact analysis for changing a file
    deps <path>           Show what a file depends on (outgoing)
    dependents <path>     Show what depends on a file (incoming)
    model <name>          Show all readers/writers of a database model
    hubs [--top N]        Show the most connected nodes (default top 15)
    cluster <path>        Show the cluster a file belongs to
    path <from> <to>      Find connection path between two files
    search <query>        Search nodes by name/file pattern
    stats                 Show project statistics summary
    dead-code [--all]     Find potentially unused/isolated nodes
    risky-files [--top N] Rank files by change risk (default top 20)
    endpoint <path>       Show endpoint details and full chain
    overview              Compact project architecture overview
    report                Full project report (overview + risks + dead code + gaps)
    changes <f1> <f2> ... Pre-change analysis for multiple files at once
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path


class GraphQuery:
    """Query engine for the code graph."""

    def __init__(self, graph_path: str):
        with open(graph_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        self.nodes = {n["id"]: n for n in self.data["nodes"]}

        # Filter out ghost edges (pointing to non-existent nodes)
        self.edges = [e for e in self.data["edges"]
                      if e["source"] in self.nodes and e["target"] in self.nodes]
        self._ghost_edges = len(self.data["edges"]) - len(self.edges)

        # Build adjacency lists
        self.outgoing = defaultdict(list)  # source -> [(edge, target_id)]
        self.incoming = defaultdict(list)  # target -> [(edge, source_id)]

        for e in self.edges:
            self.outgoing[e["source"]].append((e, e["target"]))
            self.incoming[e["target"]].append((e, e["source"]))

        # Connection counts
        self.connection_counts = Counter()
        for e in self.edges:
            self.connection_counts[e["source"]] += 1
            self.connection_counts[e["target"]] += 1

    # ── Helpers ──────────────────────────────────────────────────────────

    def find_nodes_by_file(self, path_query: str) -> list[dict]:
        """Find nodes matching a file path (partial match)."""
        query = path_query.strip("/").lower()
        results = []
        for n in self.nodes.values():
            file_path = (n.get("file") or "").lower()
            if query in file_path or query in n["label"].lower():
                results.append(n)
        return results

    def find_node_by_id(self, node_id: str) -> dict | None:
        return self.nodes.get(node_id)

    def get_risk_level(self, node_id: str) -> tuple[str, str]:
        """Return risk level and emoji for a node."""
        count = self.connection_counts.get(node_id, 0)
        incoming = len(self.incoming.get(node_id, []))
        node = self.nodes.get(node_id, {})
        node_type = node.get("type", "")

        if count >= 20 or node_type in ("router", "config"):
            return "⛔ CRITICAL", f"{count} connections — hub node, changes affect many files"
        elif count >= 10 or (incoming >= 5 and node_type in ("collection", "service")):
            return "🔴 HIGH", f"{count} connections, {incoming} dependents"
        elif count >= 4 or incoming >= 2:
            return "🟡 MEDIUM", f"{count} connections, {incoming} dependents"
        else:
            return "🟢 LOW", f"{count} connections, {incoming} dependents"

    def format_node(self, n: dict, compact: bool = False) -> str:
        """Format a node for output."""
        if compact:
            return f"  [{n['type']}] {n['label']} — {n.get('file', 'N/A')}"
        risk, risk_detail = self.get_risk_level(n["id"])
        conn = self.connection_counts.get(n["id"], 0)
        lines = [
            f"  {n['label']}",
            f"    Type: {n['type']}",
            f"    File: {n.get('file', 'N/A')}",
            f"    Line: {n.get('line', 'N/A')}",
            f"    Risk: {risk} ({risk_detail})",
        ]
        meta = n.get("metadata", {})
        if meta:
            for k, v in meta.items():
                if v:
                    lines.append(f"    {k}: {v}")
        return "\n".join(lines)

    def format_edge(self, e: dict, direction: str = "→") -> str:
        """Format an edge for output."""
        source = self.nodes.get(e["source"], {})
        target = self.nodes.get(e["target"], {})
        return f"  {source.get('label', '?')} {direction}[{e['type']}]{direction} {target.get('label', '?')}"

    # ── Commands ─────────────────────────────────────────────────────────

    def cmd_file(self, path: str) -> str:
        """Show a file's connections and risk level."""
        nodes = self.find_nodes_by_file(path)
        if not nodes:
            return f"❌ No nodes found matching '{path}'"

        output = []
        for n in nodes[:5]:  # Limit to 5 matches
            output.append(f"📄 {n['label']}")
            output.append(self.format_node(n))

            # Outgoing edges
            out_edges = self.outgoing.get(n["id"], [])
            if out_edges:
                output.append(f"\n  → Depends on ({len(out_edges)}):")
                by_type = defaultdict(list)
                for e, tid in out_edges:
                    t = self.nodes.get(tid, {})
                    by_type[e["type"]].append(t.get("label", "?"))
                for etype, labels in sorted(by_type.items()):
                    output.append(f"    [{etype}] {', '.join(labels[:8])}")
                    if len(labels) > 8:
                        output.append(f"      ... and {len(labels) - 8} more")

            # Incoming edges
            in_edges = self.incoming.get(n["id"], [])
            if in_edges:
                output.append(f"\n  ← Depended on by ({len(in_edges)}):")
                by_type = defaultdict(list)
                for e, sid in in_edges:
                    s = self.nodes.get(sid, {})
                    by_type[e["type"]].append(s.get("label", "?"))
                for etype, labels in sorted(by_type.items()):
                    output.append(f"    [{etype}] {', '.join(labels[:8])}")
                    if len(labels) > 8:
                        output.append(f"      ... and {len(labels) - 8} more")

            output.append("")

        return "\n".join(output)

    def cmd_impact(self, path: str) -> str:
        """Full impact analysis — what breaks if this file changes."""
        nodes = self.find_nodes_by_file(path)
        if not nodes:
            return f"❌ No nodes found matching '{path}'"

        output = []
        for n in nodes[:3]:
            risk, risk_detail = self.get_risk_level(n["id"])
            output.append(f"💥 Impact Analysis: {n['label']}")
            output.append(f"   Risk: {risk} — {risk_detail}")
            output.append("")

            # BFS to find all affected nodes (up to depth 3)
            affected = {}  # node_id -> depth
            queue = [(n["id"], 0)]
            visited = {n["id"]}

            while queue:
                current_id, depth = queue.pop(0)
                if depth > 3:
                    continue
                for e, source_id in self.incoming.get(current_id, []):
                    if source_id not in visited:
                        visited.add(source_id)
                        affected[source_id] = depth + 1
                        queue.append((source_id, depth + 1))

            if affected:
                # Group by depth
                by_depth = defaultdict(list)
                for nid, depth in affected.items():
                    node = self.nodes.get(nid, {})
                    by_depth[depth].append(node)

                for depth in sorted(by_depth.keys()):
                    level_nodes = by_depth[depth]
                    label = ["Direct dependents", "2nd-level impact",
                             "3rd-level impact"][min(depth - 1, 2)]
                    output.append(f"  {'→' * depth} {label} ({len(level_nodes)} files):")
                    for ln in level_nodes[:10]:
                        output.append(f"    [{ln.get('type', '?')}] {ln.get('label', '?')} — {ln.get('file', '')}")
                    if len(level_nodes) > 10:
                        output.append(f"    ... and {len(level_nodes) - 10} more")
                    output.append("")

                output.append(f"  📊 Total affected: {len(affected)} files across {len(by_depth)} levels")
            else:
                output.append("  ✅ No other files depend on this — safe to change")

            # Also show what this file depends on (what could break it)
            deps = self.outgoing.get(n["id"], [])
            if deps:
                output.append(f"\n  ⚠️  This file depends on {len(deps)} other nodes:")
                for e, tid in deps[:10]:
                    t = self.nodes.get(tid, {})
                    output.append(f"    [{e['type']}] {t.get('label', '?')} — {t.get('file', '')}")

            output.append("")

        return "\n".join(output)

    def cmd_deps(self, path: str) -> str:
        """Show what a file depends on (outgoing edges)."""
        nodes = self.find_nodes_by_file(path)
        if not nodes:
            return f"❌ No nodes found matching '{path}'"

        output = []
        for n in nodes[:3]:
            output.append(f"📤 Dependencies of: {n['label']} ({n.get('file', '')})")
            out_edges = self.outgoing.get(n["id"], [])
            if not out_edges:
                output.append("  No outgoing dependencies")
            else:
                by_type = defaultdict(list)
                for e, tid in out_edges:
                    t = self.nodes.get(tid, {})
                    by_type[e["type"]].append(
                        f"{t.get('label', '?')} ({t.get('file', '')})"
                    )
                for etype, items in sorted(by_type.items()):
                    output.append(f"\n  [{etype}]:")
                    for item in items:
                        output.append(f"    → {item}")
            output.append("")

        return "\n".join(output)

    def cmd_dependents(self, path: str) -> str:
        """Show what depends on a file (incoming edges)."""
        nodes = self.find_nodes_by_file(path)
        if not nodes:
            return f"❌ No nodes found matching '{path}'"

        output = []
        for n in nodes[:3]:
            output.append(f"📥 Dependents of: {n['label']} ({n.get('file', '')})")
            in_edges = self.incoming.get(n["id"], [])
            if not in_edges:
                output.append("  No files depend on this")
            else:
                by_type = defaultdict(list)
                for e, sid in in_edges:
                    s = self.nodes.get(sid, {})
                    by_type[e["type"]].append(
                        f"{s.get('label', '?')} ({s.get('file', '')})"
                    )
                for etype, items in sorted(by_type.items()):
                    output.append(f"\n  [{etype}]:")
                    for item in items:
                        output.append(f"    ← {item}")
            output.append("")

        return "\n".join(output)

    def cmd_model(self, name: str) -> str:
        """Show all readers/writers of a database model."""
        model_nodes = [n for n in self.nodes.values()
                       if n["type"] == "collection"
                       and name.lower() in n["label"].lower()]

        if not model_nodes:
            return f"❌ No model found matching '{name}'"

        output = []
        for mn in model_nodes:
            output.append(f"🗄️  Model: {mn['label']} ({mn.get('file', '')})")
            risk, detail = self.get_risk_level(mn["id"])
            output.append(f"   Risk: {risk} — {detail}")

            # Readers
            readers = [(e, sid) for e, sid in self.incoming.get(mn["id"], [])
                       if e["type"] == "db_read"]
            if readers:
                output.append(f"\n  📖 Read by ({len(readers)}):")
                for e, sid in readers:
                    s = self.nodes.get(sid, {})
                    output.append(f"    {s.get('label', '?')} [{s.get('type', '')}] — {s.get('file', '')}")

            # Writers
            writers = [(e, sid) for e, sid in self.incoming.get(mn["id"], [])
                       if e["type"] == "db_write"]
            if writers:
                output.append(f"\n  ✏️  Written by ({len(writers)}):")
                for e, sid in writers:
                    s = self.nodes.get(sid, {})
                    output.append(f"    {s.get('label', '?')} [{s.get('type', '')}] — {s.get('file', '')}")

            # Other connections
            other = [(e, sid) for e, sid in self.incoming.get(mn["id"], [])
                     if e["type"] not in ("db_read", "db_write")]
            if other:
                output.append(f"\n  🔗 Other connections ({len(other)}):")
                for e, sid in other[:10]:
                    s = self.nodes.get(sid, {})
                    output.append(f"    [{e['type']}] {s.get('label', '?')} — {s.get('file', '')}")

            output.append("")

        return "\n".join(output)

    def cmd_hubs(self, top: int = 15) -> str:
        """Show the most connected nodes."""
        ranked = self.connection_counts.most_common(top)
        output = [f"🔥 Top {top} Hub Nodes (highest risk to change):\n"]

        for i, (node_id, count) in enumerate(ranked, 1):
            n = self.nodes.get(node_id, {})
            risk, _ = self.get_risk_level(node_id)
            incoming = len(self.incoming.get(node_id, []))
            outgoing = len(self.outgoing.get(node_id, []))
            output.append(
                f"  {i:2d}. {risk} {n.get('label', '?')} [{n.get('type', '')}]"
                f" — {count} total ({incoming}↓ {outgoing}↑)"
                f"\n      {n.get('file', '')}"
            )

        return "\n".join(output)

    def cmd_cluster(self, path: str) -> str:
        """Show the cluster a file belongs to."""
        nodes = self.find_nodes_by_file(path)
        if not nodes:
            return f"❌ No nodes found matching '{path}'"

        target = nodes[0]
        output = [f"🔗 Cluster containing: {target['label']}\n"]

        # BFS to find connected component
        visited = set()
        queue = [target["id"]]
        visited.add(target["id"])

        while queue:
            current = queue.pop(0)
            for e, tid in self.outgoing.get(current, []):
                if tid not in visited:
                    visited.add(tid)
                    queue.append(tid)
            for e, sid in self.incoming.get(current, []):
                if sid not in visited:
                    visited.add(sid)
                    queue.append(sid)

        # Format cluster nodes
        cluster_nodes = [self.nodes[nid] for nid in visited if nid in self.nodes]
        by_type = defaultdict(list)
        for n in cluster_nodes:
            by_type[n["type"]].append(n)

        output.append(f"  Cluster size: {len(cluster_nodes)} nodes\n")
        for ntype, type_nodes in sorted(by_type.items(), key=lambda x: -len(x[1])):
            output.append(f"  [{ntype}] ({len(type_nodes)}):")
            for n in type_nodes[:8]:
                output.append(f"    {n['label']} — {n.get('file', '')}")
            if len(type_nodes) > 8:
                output.append(f"    ... and {len(type_nodes) - 8} more")

        return "\n".join(output)

    def cmd_path(self, from_path: str, to_path: str) -> str:
        """Find connection path between two files."""
        from_nodes = self.find_nodes_by_file(from_path)
        to_nodes = self.find_nodes_by_file(to_path)

        if not from_nodes:
            return f"❌ No nodes found matching '{from_path}'"
        if not to_nodes:
            return f"❌ No nodes found matching '{to_path}'"

        start = from_nodes[0]
        end_ids = {n["id"] for n in to_nodes}

        # BFS shortest path
        queue = [(start["id"], [start["id"]])]
        visited = {start["id"]}

        while queue:
            current, path = queue.pop(0)
            if current in end_ids:
                output = [f"🔗 Path from {start['label']} → {self.nodes[current]['label']}:\n"]
                for i, nid in enumerate(path):
                    n = self.nodes.get(nid, {})
                    prefix = "  → " if i > 0 else "  "
                    output.append(f"{prefix}[{n.get('type', '')}] {n.get('label', '?')} ({n.get('file', '')})")

                    # Show edge type to next node
                    if i < len(path) - 1:
                        next_id = path[i + 1]
                        for e, tid in self.outgoing.get(nid, []):
                            if tid == next_id:
                                output.append(f"    ↓ [{e['type']}]")
                                break
                        else:
                            for e, sid in self.incoming.get(nid, []):
                                if sid == next_id:
                                    output.append(f"    ↑ [{e['type']}]")
                                    break

                return "\n".join(output)

            # Expand both directions
            for e, tid in self.outgoing.get(current, []):
                if tid not in visited:
                    visited.add(tid)
                    queue.append((tid, path + [tid]))
            for e, sid in self.incoming.get(current, []):
                if sid not in visited:
                    visited.add(sid)
                    queue.append((sid, path + [sid]))

            if len(visited) > 500:  # Safety limit
                break

        return f"❌ No path found between '{from_path}' and '{to_path}'"

    def cmd_search(self, query: str) -> str:
        """Search nodes by name/file pattern."""
        q = query.lower()
        matches = [n for n in self.nodes.values()
                   if q in n["label"].lower()
                   or q in (n.get("file") or "").lower()]

        if not matches:
            return f"❌ No nodes matching '{query}'"

        output = [f"🔍 Found {len(matches)} nodes matching '{query}':\n"]
        for n in matches[:20]:
            risk, _ = self.get_risk_level(n["id"])
            conn = self.connection_counts.get(n["id"], 0)
            output.append(f"  {risk} [{n['type']}] {n['label']} ({conn} connections)")
            output.append(f"      {n.get('file', '')}")

        if len(matches) > 20:
            output.append(f"\n  ... and {len(matches) - 20} more results")

        return "\n".join(output)

    def cmd_stats(self) -> str:
        """Show project statistics summary."""
        stats = self.data.get("stats", {})
        output = [
            f"📊 Project: {self.data.get('project', 'Unknown')}",
            f"   Generated: {self.data.get('generated_at', 'Unknown')}",
            f"   Nodes: {stats.get('total_nodes', 0)}",
            f"   Edges: {len(self.edges)}",
        ]
        if self._ghost_edges > 0:
            output.append(f"   ⚠️  Ghost edges filtered: {self._ghost_edges} (edges pointing to non-existent nodes)")

        output.append("\n  Node Types:")
        for ntype, count in sorted((stats.get("node_types") or {}).items(), key=lambda x: -x[1]):
            output.append(f"    {ntype}: {count}")

        output.append("\n  Edge Types:")
        for etype, count in sorted((stats.get("edge_types") or {}).items(), key=lambda x: -x[1]):
            output.append(f"    {etype}: {count}")

        # Most connected
        top5 = self.connection_counts.most_common(5)
        output.append("\n  Top 5 Hub Nodes:")
        for nid, count in top5:
            n = self.nodes.get(nid, {})
            output.append(f"    {n.get('label', '?')} [{n.get('type', '')}] — {count} connections")

        return "\n".join(output)

    def cmd_dead_code(self, show_all: bool = False) -> str:
        """Find potentially unused/isolated nodes."""
        connected = set()
        for e in self.edges:
            connected.add(e["source"])
            connected.add(e["target"])

        isolated = [n for n in self.nodes.values()
                    if n["id"] not in connected
                    and n["type"] not in ("config",)]

        # Also find nodes with only outgoing (nothing depends on them)
        no_dependents = []
        for n in self.nodes.values():
            if (n["id"] in connected
                    and not self.incoming.get(n["id"])
                    and self.outgoing.get(n["id"])
                    and n["type"] not in ("config", "test", "script")):
                no_dependents.append(n)

        output = [f"🗑️  Potential Dead Code Analysis:\n"]

        if isolated:
            # Group by type for readability
            by_type = defaultdict(list)
            for n in isolated:
                by_type[n["type"]].append(n)

            output.append(f"  Completely isolated ({len(isolated)} nodes):\n")
            for ntype, type_nodes in sorted(by_type.items(), key=lambda x: -len(x[1])):
                output.append(f"  [{ntype}] ({len(type_nodes)}):")
                limit = len(type_nodes) if show_all else min(len(type_nodes), 8)
                for n in type_nodes[:limit]:
                    output.append(f"    {n['label']} — {n.get('file', '')}")
                if not show_all and len(type_nodes) > 8:
                    output.append(f"    ... +{len(type_nodes) - 8} more (use --all to see all)")
                output.append("")
        else:
            output.append("  No completely isolated nodes ✅")

        if no_dependents:
            output.append(f"\n  No incoming dependencies ({len(no_dependents)} nodes):")
            limit = len(no_dependents) if show_all else min(len(no_dependents), 15)
            for n in no_dependents[:limit]:
                output.append(f"    [{n['type']}] {n['label']} — {n.get('file', '')}")
            if not show_all and len(no_dependents) > 15:
                output.append(f"    ... +{len(no_dependents) - 15} more (use --all to see all)")

        return "\n".join(output)

    def cmd_risky_files(self, top: int = 20) -> str:
        """Rank files by change risk."""
        # Calculate risk score: weighted connections
        risk_scores = {}
        for nid, n in self.nodes.items():
            incoming = len(self.incoming.get(nid, []))
            outgoing = len(self.outgoing.get(nid, []))
            total = self.connection_counts.get(nid, 0)

            # Weight: incoming dependencies are riskier
            score = incoming * 3 + outgoing * 1 + total

            # Boost for certain types
            if n["type"] in ("collection", "service"):
                score *= 1.5
            elif n["type"] in ("router", "config"):
                score *= 2.0
            elif n["type"] == "test":
                score *= 0.1

            risk_scores[nid] = score

        ranked = sorted(risk_scores.items(), key=lambda x: -x[1])[:top]
        output = [f"⚠️  Top {top} Riskiest Files to Change:\n"]

        for i, (nid, score) in enumerate(ranked, 1):
            n = self.nodes.get(nid, {})
            risk, _ = self.get_risk_level(nid)
            incoming = len(self.incoming.get(nid, []))
            output.append(
                f"  {i:2d}. {risk} {n.get('label', '?')} [{n.get('type', '')}]"
                f" — risk score: {score:.0f} ({incoming} dependents)"
                f"\n      {n.get('file', '')}"
            )

        return "\n".join(output)

    def cmd_endpoint(self, path: str) -> str:
        """Show endpoint details and full request chain."""
        nodes = self.find_nodes_by_file(path)
        endpoints = [n for n in nodes if n["type"] == "endpoint"]

        if not endpoints:
            # Try matching by label
            endpoints = [n for n in self.nodes.values()
                         if n["type"] == "endpoint"
                         and path.lower() in n["label"].lower()]

        if not endpoints:
            return f"❌ No endpoints found matching '{path}'"

        output = []
        for ep in endpoints[:5]:
            output.append(f"🌐 Endpoint: {ep['label']}")
            output.append(f"   File: {ep.get('file', '')}")
            meta = ep.get("metadata", {})
            if meta.get("method"):
                output.append(f"   Method: {meta['method']}")
            if meta.get("path"):
                output.append(f"   Path: {meta['path']}")

            # Trace the full chain: endpoint → services → models → cache/api
            output.append("\n   Request chain:")
            self._trace_chain(ep["id"], output, visited=set(), depth=0, max_depth=4)
            output.append("")

        return "\n".join(output)

    def _trace_chain(self, node_id: str, output: list, visited: set,
                     depth: int, max_depth: int):
        """Recursively trace the dependency chain."""
        if depth > max_depth or node_id in visited:
            return
        visited.add(node_id)

        indent = "   " + "  " * depth
        for e, tid in self.outgoing.get(node_id, []):
            t = self.nodes.get(tid, {})
            if t:
                marker = "→"
                output.append(f"{indent}{marker} [{e['type']}] {t['label']} [{t['type']}]")
                self._trace_chain(tid, output, visited, depth + 1, max_depth)

    def cmd_overview(self) -> str:
        """Compact architecture overview."""
        stats = self.data.get("stats", {})
        output = [
            f"🏗️  Architecture Overview: {self.data.get('project', '?')}",
            f"   {stats.get('total_nodes', 0)} nodes, {stats.get('total_edges', 0)} edges",
            "",
        ]

        # Group files by top-level directory
        dir_groups = defaultdict(lambda: {"count": 0, "types": Counter()})
        for n in self.nodes.values():
            file_path = n.get("file") or ""
            parts = file_path.split("/")
            top_dir = parts[0] if parts else "root"
            dir_groups[top_dir]["count"] += 1
            dir_groups[top_dir]["types"][n["type"]] += 1

        output.append("  📁 Directory breakdown:")
        for dir_name, info in sorted(dir_groups.items(), key=lambda x: -x[1]["count"]):
            if info["count"] < 2:
                continue
            types_str = ", ".join(f"{t}:{c}" for t, c in info["types"].most_common(3))
            output.append(f"    {dir_name}/ — {info['count']} nodes ({types_str})")

        # Key architectural connections
        output.append("\n  🔗 Key relationships:")
        edge_types = stats.get("edge_types", {})
        for etype, count in sorted(edge_types.items(), key=lambda x: -x[1]):
            output.append(f"    {etype}: {count}")

        # Identify architectural layers
        output.append("\n  🏛️  Layers:")
        type_counts = stats.get("node_types", {})
        layers = [
            ("API Layer", ["endpoint", "router", "serializer", "middleware"]),
            ("Business Logic", ["service", "task", "utility"]),
            ("Data Layer", ["collection", "cache_key"]),
            ("Frontend", ["component", "template"]),
            ("Integration", ["webhook", "external_api", "event"]),
            ("Quality", ["test"]),
        ]
        for layer_name, types in layers:
            count = sum(type_counts.get(t, 0) for t in types)
            if count > 0:
                detail = ", ".join(f"{t}:{type_counts[t]}" for t in types if type_counts.get(t, 0) > 0)
                output.append(f"    {layer_name}: {count} nodes ({detail})")

        return "\n".join(output)

    def cmd_report(self) -> str:
        """Full project report — everything Claude needs in one call."""
        sections = []

        # 1. Overview
        sections.append(self.cmd_overview())
        sections.append("")

        # 2. Ghost edges warning
        if self._ghost_edges > 0:
            sections.append(f"⚠️  {self._ghost_edges} ghost edges filtered (edges pointing to non-existent nodes)")
            sections.append("")

        # 3. Top 10 riskiest files
        sections.append(self.cmd_risky_files(10))
        sections.append("")

        # 4. Top 10 hubs
        sections.append(self.cmd_hubs(10))
        sections.append("")

        # 5. Dead code summary (compact)
        connected = set()
        for e in self.edges:
            connected.add(e["source"])
            connected.add(e["target"])
        isolated = [n for n in self.nodes.values()
                    if n["id"] not in connected and n["type"] not in ("config",)]
        by_type = defaultdict(list)
        for n in isolated:
            by_type[n["type"]].append(n)
        sections.append(f"🗑️  Dead Code: {len(isolated)} isolated nodes")
        for ntype, nodes in sorted(by_type.items(), key=lambda x: -len(x[1])):
            labels = [n["label"] for n in nodes[:5]]
            more = f" +{len(nodes)-5}" if len(nodes) > 5 else ""
            sections.append(f"  [{ntype}] ({len(nodes)}): {', '.join(labels)}{more}")
        sections.append("")

        # 6. Weak spots — high-risk nodes with no tests nearby
        sections.append("🧪 Coverage Gaps (high-risk files without test connections):")
        test_connected = set()
        for e in self.edges:
            src = self.nodes.get(e["source"], {})
            tgt = self.nodes.get(e["target"], {})
            if src.get("type") == "test":
                test_connected.add(e["target"])
            if tgt.get("type") == "test":
                test_connected.add(e["source"])
        gaps = []
        for nid, count in self.connection_counts.most_common(50):
            n = self.nodes.get(nid, {})
            if (count >= 8 and n.get("type") not in ("test", "config", "router", "component")
                    and nid not in test_connected):
                gaps.append(n)
        if gaps:
            for n in gaps[:10]:
                risk, _ = self.get_risk_level(n["id"])
                sections.append(f"  {risk} {n['label']} [{n['type']}] — {n.get('file', '')}")
        else:
            sections.append("  All high-risk files have test coverage ✅")

        return "\n".join(sections)

    def cmd_changes(self, *paths: str) -> str:
        """Pre-change analysis for multiple files at once."""
        if not paths:
            return "❌ Provide file paths to analyze"

        output = [f"📋 Pre-Change Analysis for {len(paths)} files:\n"]
        all_affected = set()

        for path in paths:
            nodes = self.find_nodes_by_file(path)
            if not nodes:
                output.append(f"  ❌ '{path}' — not found in graph")
                continue

            n = nodes[0]
            risk, detail = self.get_risk_level(n["id"])
            incoming = len(self.incoming.get(n["id"], []))
            outgoing = len(self.outgoing.get(n["id"], []))
            output.append(f"  {risk} {n['label']} ({incoming}↓ {outgoing}↑) — {n.get('file', '')}")

            # Collect affected
            for e, sid in self.incoming.get(n["id"], []):
                all_affected.add(sid)

        if all_affected:
            output.append(f"\n  📊 Total files potentially affected: {len(all_affected)}")
            # Group by type
            by_type = defaultdict(list)
            for nid in all_affected:
                node = self.nodes.get(nid, {})
                by_type[node.get("type", "?")].append(node)
            for ntype, nodes in sorted(by_type.items(), key=lambda x: -len(x[1])):
                labels = [n.get("label", "?") for n in nodes[:5]]
                more = f" +{len(nodes)-5}" if len(nodes) > 5 else ""
                output.append(f"    [{ntype}] {', '.join(labels)}{more}")

        return "\n".join(output)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Query the code graph without loading it all into context.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("command", help="Query command")
    parser.add_argument("args", nargs="*", help="Command arguments")
    parser.add_argument("--graph", "-g", default=".code_graph.json",
                        help="Path to code_graph.json (default: .code_graph.json)")
    parser.add_argument("--top", "-n", type=int, default=None,
                        help="Number of results for ranked commands")
    parser.add_argument("--all", "-a", action="store_true",
                        help="Show all results (no truncation)")

    args = parser.parse_args()

    # Find graph file
    graph_path = args.graph
    if not os.path.isfile(graph_path):
        # Try common locations
        candidates = [
            ".code_graph.json",
            "code_graph.json",
            ".claude/code_graph.json",
        ]
        for c in candidates:
            if os.path.isfile(c):
                graph_path = c
                break
        else:
            print(f"❌ Graph not found at '{args.graph}'")
            print("   Run analyze_codebase.py first to generate it.")
            sys.exit(1)

    gq = GraphQuery(graph_path)

    # Route commands
    cmd = args.command.lower().replace("-", "_")
    cmd_args = args.args

    try:
        if cmd == "file" and cmd_args:
            print(gq.cmd_file(cmd_args[0]))
        elif cmd == "impact" and cmd_args:
            print(gq.cmd_impact(cmd_args[0]))
        elif cmd == "deps" and cmd_args:
            print(gq.cmd_deps(cmd_args[0]))
        elif cmd == "dependents" and cmd_args:
            print(gq.cmd_dependents(cmd_args[0]))
        elif cmd == "model" and cmd_args:
            print(gq.cmd_model(cmd_args[0]))
        elif cmd == "hubs":
            print(gq.cmd_hubs(args.top or 15))
        elif cmd == "cluster" and cmd_args:
            print(gq.cmd_cluster(cmd_args[0]))
        elif cmd == "path" and len(cmd_args) >= 2:
            print(gq.cmd_path(cmd_args[0], cmd_args[1]))
        elif cmd == "search" and cmd_args:
            print(gq.cmd_search(" ".join(cmd_args)))
        elif cmd == "stats":
            print(gq.cmd_stats())
        elif cmd == "dead_code":
            print(gq.cmd_dead_code(show_all=args.all))
        elif cmd == "risky_files":
            print(gq.cmd_risky_files(args.top or 20))
        elif cmd == "endpoint" and cmd_args:
            print(gq.cmd_endpoint(cmd_args[0]))
        elif cmd == "overview":
            print(gq.cmd_overview())
        elif cmd == "report":
            print(gq.cmd_report())
        elif cmd == "changes" and cmd_args:
            print(gq.cmd_changes(*cmd_args))
        else:
            parser.print_help()
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
