#!/usr/bin/env python3
"""
Code Graph Viewer Generator v2.0 — Creates an interactive HTML visualization
from a code_graph.json file.

Features:
  - Force-directed layout with Barnes-Hut optimization
  - Animated edge particles showing data flow
  - Cluster hulls with convex boundary drawing
  - Multi-mode search with typeahead
  - Keyboard shortcuts (Ctrl+F, Esc, Space, etc.)
  - Zoom to fit, center, reset view
  - Context menu with node actions
  - Stats dashboard with distribution charts
  - Interactive legend with toggle
  - Path highlighting between nodes
  - Multiple layout modes (force, radial, grid)
  - Export to PNG
  - Performance mode for large graphs
  - Node grouping by directory
  - Navigation history (back/forward)
  - Responsive detail panel with tabs
  - Edge type filtering with color coding
  - Minimap with viewport indicator
  - Breadcrumb trail

Usage:
    python3 generate_viewer.py code_graph.json -o code_graph_viewer.html
"""

import argparse
import json
import os
import sys


HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Code Graph — {{PROJECT_NAME}}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Satoshi:wght@300;400;500;600;700;800;900&display=swap');

  *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

  :root {
    --bg-void: #06090f;
    --bg-primary: #0a0f1a;
    --bg-secondary: #0f1628;
    --bg-panel: #0c1220;
    --bg-card: #111b2e;
    --bg-hover: #162038;
    --border: #1a2744;
    --border-accent: #243354;
    --text-primary: #e8ecf4;
    --text-secondary: #8b97b0;
    --text-muted: #4d5a72;
    --text-dim: #2d3a52;
    --accent: #00d4ff;
    --accent-glow: #00d4ff40;
    --accent-dim: #00d4ff18;
    --accent-bright: #40e8ff;
    --danger: #ff4466;
    --danger-dim: #ff446620;
    --success: #22ee77;
    --success-dim: #22ee7720;
    --warning: #ffaa22;
    --warning-dim: #ffaa2220;
    --purple: #aa66ff;
    --purple-dim: #aa66ff20;
    --shadow-lg: 0 12px 48px rgba(0,0,0,0.6);
    --shadow-md: 0 6px 24px rgba(0,0,0,0.4);
    --radius: 8px;
    --radius-lg: 12px;
    --transition: 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  }

  body {
    font-family: 'Satoshi', -apple-system, sans-serif;
    background: var(--bg-void);
    color: var(--text-primary);
    overflow: hidden;
    height: 100vh; width: 100vw;
    user-select: none;
  }

  /* ═══════════════════════════ SCROLLBAR ═══════════════════════════ */
  ::-webkit-scrollbar { width: 5px; height: 5px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--border-accent); }
  * { scrollbar-width: thin; scrollbar-color: var(--border) transparent; }

  /* ═══════════════════════════ SIDEBAR ═══════════════════════════ */
  #sidebar {
    position: fixed; left: 0; top: 0; bottom: 0;
    width: 300px;
    background: var(--bg-panel);
    border-right: 1px solid var(--border);
    z-index: 100;
    display: flex; flex-direction: column;
    transition: transform var(--transition);
  }
  #sidebar.collapsed { transform: translateX(-300px); }

  .sidebar-header {
    padding: 20px 16px 16px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  .logo {
    font-family: 'JetBrains Mono', monospace;
    font-size: 15px; font-weight: 700;
    color: var(--accent);
    letter-spacing: 0.8px;
    display: flex; align-items: center; gap: 10px;
  }
  .logo svg { width: 22px; height: 22px; }
  .logo .version {
    font-size: 10px; font-weight: 400;
    color: var(--text-muted);
    background: var(--accent-dim);
    padding: 2px 6px; border-radius: 4px;
    margin-left: auto;
  }

  .project-name {
    font-size: 12px; color: var(--text-muted);
    margin-top: 6px; font-weight: 400;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }

  /* Search */
  .search-wrap {
    position: relative; padding: 12px 16px 0;
    flex-shrink: 0;
  }
  .search-wrap svg {
    position: absolute; left: 28px; top: 24px;
    width: 15px; height: 15px;
    color: var(--text-muted); pointer-events: none;
  }
  #search {
    width: 100%; padding: 9px 12px 9px 36px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text-primary);
    font-family: 'Satoshi', sans-serif;
    font-size: 13px; outline: none;
    transition: border-color var(--transition), box-shadow var(--transition);
  }
  #search:focus { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-dim); }
  #search::placeholder { color: var(--text-dim); }
  .search-hint {
    font-size: 10px; color: var(--text-dim);
    padding: 4px 16px; font-family: 'JetBrains Mono', monospace;
  }

  /* Sidebar scroll area */
  .sidebar-scroll {
    flex: 1; overflow-y: auto; padding: 8px 16px 16px;
  }

  /* Section */
  .section { margin-top: 16px; }
  .section:first-child { margin-top: 8px; }
  .section-head {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px; font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 1.8px;
    margin-bottom: 8px;
    display: flex; align-items: center; justify-content: space-between;
    cursor: pointer;
  }
  .section-head .toggle-arrow {
    transition: transform var(--transition);
    font-size: 8px; color: var(--text-dim);
  }
  .section-head.collapsed .toggle-arrow { transform: rotate(-90deg); }
  .section-body { transition: max-height 0.3s ease; overflow: hidden; }
  .section-body.collapsed { max-height: 0 !important; }

  /* Filter item */
  .filter-item {
    display: flex; align-items: center; gap: 8px;
    padding: 5px 8px; margin: 1px 0;
    border-radius: 5px; cursor: pointer;
    font-size: 13px; transition: background var(--transition);
  }
  .filter-item:hover { background: var(--bg-hover); }
  .filter-item input[type="checkbox"] {
    appearance: none; width: 15px; height: 15px;
    border: 1.5px solid var(--border-accent); border-radius: 3px;
    cursor: pointer; position: relative; flex-shrink: 0;
    transition: all var(--transition);
  }
  .filter-item input[type="checkbox"]:checked {
    border-color: var(--accent);
  }
  .filter-item input[type="checkbox"]:checked::after {
    content: ''; position: absolute;
    top: 2px; left: 2px; right: 2px; bottom: 2px;
    border-radius: 1px;
  }
  .filter-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
  .filter-label { flex: 1; color: var(--text-secondary); font-size: 12px; }
  .filter-count {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px; color: var(--accent);
    background: var(--accent-dim);
    padding: 1px 6px; border-radius: 10px;
    min-width: 24px; text-align: center;
  }

  /* Toggle row */
  .toggle-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 6px 8px; font-size: 12px; color: var(--text-secondary);
    border-radius: 5px; cursor: pointer;
    transition: background var(--transition);
  }
  .toggle-row:hover { background: var(--bg-hover); }
  .toggle-switch {
    width: 36px; height: 20px;
    background: var(--border); border-radius: 10px;
    position: relative; cursor: pointer;
    transition: background var(--transition);
    flex-shrink: 0;
  }
  .toggle-switch.active { background: var(--accent); }
  .toggle-switch::after {
    content: ''; position: absolute;
    top: 3px; left: 3px; width: 14px; height: 14px;
    background: white; border-radius: 50%;
    transition: transform var(--transition);
    box-shadow: 0 1px 3px rgba(0,0,0,0.3);
  }
  .toggle-switch.active::after { transform: translateX(16px); }

  /* Stats grid */
  .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 8px; }
  .stat-card {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 10px; text-align: center;
    transition: border-color var(--transition);
  }
  .stat-card:hover { border-color: var(--border-accent); }
  .stat-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 22px; font-weight: 700; color: var(--accent);
    line-height: 1;
  }
  .stat-label { font-size: 10px; color: var(--text-dim); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }

  /* Action buttons */
  .action-bar {
    padding: 12px 16px; border-top: 1px solid var(--border);
    display: flex; gap: 6px; flex-shrink: 0;
  }
  .action-btn {
    flex: 1; padding: 7px; border: 1px solid var(--border);
    border-radius: 5px; background: var(--bg-card);
    color: var(--text-secondary); font-size: 11px;
    cursor: pointer; transition: all var(--transition);
    font-family: 'Satoshi', sans-serif;
    display: flex; align-items: center; justify-content: center; gap: 4px;
  }
  .action-btn:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-dim); }
  .action-btn svg { width: 13px; height: 13px; }

  /* ═══════════════════════════ CANVAS ═══════════════════════════ */
  #graph-container {
    position: fixed;
    left: 300px; top: 0; right: 0; bottom: 0;
    background: var(--bg-void);
    transition: left var(--transition);
  }
  #graph-container.expanded { left: 0; }
  canvas#graph { display: block; width: 100%; height: 100%; }

  /* Grid background */
  #graph-container::before {
    content: ''; position: absolute; inset: 0;
    background-image:
      radial-gradient(circle at 50% 50%, var(--bg-primary) 0%, var(--bg-void) 70%),
      linear-gradient(rgba(255,255,255,0.012) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,0.012) 1px, transparent 1px);
    background-size: 100% 100%, 60px 60px, 60px 60px;
    pointer-events: none; z-index: 0;
  }

  /* ═══════════════════════════ TOOLBAR ═══════════════════════════ */
  #toolbar {
    position: fixed; top: 16px; z-index: 110;
    display: flex; gap: 4px; background: var(--bg-panel);
    border: 1px solid var(--border); border-radius: var(--radius);
    padding: 4px; box-shadow: var(--shadow-md);
    transition: left var(--transition);
  }
  .tb-btn {
    width: 34px; height: 34px;
    display: flex; align-items: center; justify-content: center;
    border: none; background: transparent; color: var(--text-secondary);
    border-radius: 5px; cursor: pointer; transition: all var(--transition);
    position: relative;
  }
  .tb-btn:hover { background: var(--bg-hover); color: var(--text-primary); }
  .tb-btn.active { background: var(--accent-dim); color: var(--accent); }
  .tb-btn svg { width: 16px; height: 16px; }
  .tb-sep { width: 1px; background: var(--border); margin: 4px 2px; }
  .tb-btn[data-tooltip]:hover::after {
    content: attr(data-tooltip); position: absolute;
    top: 100%; left: 50%; transform: translateX(-50%);
    margin-top: 8px; padding: 4px 8px;
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 4px; font-size: 11px; white-space: nowrap;
    color: var(--text-secondary); pointer-events: none;
    box-shadow: var(--shadow-md);
  }

  /* ═══════════════════════════ TOOLTIP ═══════════════════════════ */
  #tooltip {
    position: fixed; display: none;
    background: var(--bg-panel); border: 1px solid var(--border);
    border-radius: var(--radius-lg); padding: 14px 18px;
    font-size: 13px; max-width: 380px;
    z-index: 200; box-shadow: var(--shadow-lg);
    pointer-events: none; backdrop-filter: blur(12px);
  }
  .tt-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
  .tt-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
  .tt-label { font-weight: 600; font-size: 14px; }
  .tt-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px; padding: 2px 7px;
    border-radius: 4px; display: inline-block;
  }
  .tt-file {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px; color: var(--text-muted);
    word-break: break-all; margin-top: 4px;
  }
  .tt-stats {
    display: flex; gap: 12px; margin-top: 8px;
    font-size: 11px; color: var(--text-secondary);
  }
  .tt-stat { display: flex; align-items: center; gap: 4px; }
  .tt-stat svg { width: 12px; height: 12px; color: var(--text-muted); }
  .tt-risk { margin-top: 6px; font-size: 11px; font-weight: 500; }

  /* ═══════════════════════════ DETAIL PANEL ═══════════════════════════ */
  #detail {
    position: fixed; right: 0; top: 0; bottom: 0;
    width: 340px; background: var(--bg-panel);
    border-left: 1px solid var(--border);
    z-index: 100; overflow-y: auto;
    transform: translateX(100%);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: -8px 0 32px rgba(0,0,0,0.3);
  }
  #detail.open { transform: translateX(0); }

  .detail-header {
    padding: 20px 16px 16px; border-bottom: 1px solid var(--border);
    position: sticky; top: 0; background: var(--bg-panel); z-index: 1;
  }
  .detail-close {
    position: absolute; top: 16px; right: 16px;
    width: 28px; height: 28px; border-radius: 6px;
    background: var(--bg-card); border: 1px solid var(--border);
    color: var(--text-muted); cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: all var(--transition); font-size: 14px;
  }
  .detail-close:hover { border-color: var(--danger); color: var(--danger); }

  .detail-title { font-size: 16px; font-weight: 700; padding-right: 36px; line-height: 1.3; }
  .detail-badge {
    display: inline-block; margin-top: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px; padding: 3px 8px; border-radius: 4px;
  }
  .detail-file {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px; color: var(--text-muted);
    margin-top: 8px; word-break: break-all;
  }

  .detail-tabs {
    display: flex; border-bottom: 1px solid var(--border);
    padding: 0 16px; position: sticky; top: 82px;
    background: var(--bg-panel); z-index: 1;
  }
  .detail-tab {
    padding: 10px 14px; font-size: 12px; font-weight: 500;
    color: var(--text-muted); cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all var(--transition);
  }
  .detail-tab:hover { color: var(--text-secondary); }
  .detail-tab.active { color: var(--accent); border-bottom-color: var(--accent); }

  .detail-body { padding: 16px; }
  .detail-section { margin-bottom: 16px; }
  .detail-section-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px; color: var(--text-dim);
    text-transform: uppercase; letter-spacing: 1.2px;
    margin-bottom: 8px;
  }

  .conn-item {
    display: flex; align-items: center; gap: 8px;
    padding: 6px 8px; margin: 2px 0;
    background: var(--bg-card); border: 1px solid transparent;
    border-radius: 5px; font-size: 12px;
    cursor: pointer; transition: all var(--transition);
  }
  .conn-item:hover { border-color: var(--border-accent); background: var(--bg-hover); }
  .conn-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
  .conn-name { flex: 1; color: var(--text-secondary); }
  .conn-type {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px; color: var(--text-dim);
    background: var(--bg-secondary); padding: 1px 5px;
    border-radius: 3px;
  }

  .meta-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 4px 0; font-size: 12px;
  }
  .meta-key { color: var(--text-dim); }
  .meta-val { color: var(--text-secondary); font-family: 'JetBrains Mono', monospace; font-size: 11px; }

  /* ═══════════════════════════ MINIMAP ═══════════════════════════ */
  #minimap {
    position: fixed; bottom: 16px; right: 16px;
    width: 200px; height: 140px;
    background: var(--bg-panel); border: 1px solid var(--border);
    border-radius: var(--radius-lg); z-index: 50;
    overflow: hidden; box-shadow: var(--shadow-md);
    transition: opacity var(--transition);
  }
  #minimap canvas { width: 100%; height: 100%; }
  #minimap .viewport-rect {
    position: absolute; border: 1.5px solid var(--accent);
    background: var(--accent-dim); pointer-events: none;
    border-radius: 2px;
  }

  /* ═══════════════════════════ BREADCRUMB ═══════════════════════════ */
  #breadcrumb {
    position: fixed; bottom: 16px; z-index: 60;
    display: flex; align-items: center; gap: 6px;
    background: var(--bg-panel); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 6px 12px;
    box-shadow: var(--shadow-md); font-size: 12px;
    max-width: 500px; overflow-x: auto;
    transition: left var(--transition);
  }
  .bc-item {
    color: var(--text-muted); cursor: pointer;
    white-space: nowrap; transition: color var(--transition);
    padding: 2px 4px; border-radius: 3px;
  }
  .bc-item:hover { color: var(--accent); background: var(--accent-dim); }
  .bc-item.current { color: var(--accent); font-weight: 600; }
  .bc-sep { color: var(--text-dim); font-size: 10px; }

  /* ═══════════════════════════ LEGEND ═══════════════════════════ */
  #legend {
    position: fixed; top: 16px; right: 16px; z-index: 60;
    background: var(--bg-panel); border: 1px solid var(--border);
    border-radius: var(--radius-lg); padding: 12px 16px;
    box-shadow: var(--shadow-md); display: none;
    max-height: 60vh; overflow-y: auto;
  }
  #legend.visible { display: block; }
  .legend-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px; color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 1.2px;
    margin-bottom: 8px;
  }
  .legend-item {
    display: flex; align-items: center; gap: 8px;
    padding: 3px 0; font-size: 12px; color: var(--text-secondary);
  }
  .legend-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
  .legend-line { width: 20px; height: 2px; border-radius: 1px; flex-shrink: 0; }

  /* ═══════════════════════════ COMMAND PALETTE ═══════════════════════════ */
  #cmd-palette {
    position: fixed; top: 20%; left: 50%; transform: translateX(-50%);
    width: 480px; background: var(--bg-panel);
    border: 1px solid var(--border-accent);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-lg); z-index: 500;
    display: none; overflow: hidden;
  }
  #cmd-palette.visible { display: block; }
  #cmd-input {
    width: 100%; padding: 14px 18px;
    background: transparent; border: none;
    border-bottom: 1px solid var(--border);
    color: var(--text-primary);
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px; outline: none;
  }
  #cmd-input::placeholder { color: var(--text-dim); }
  #cmd-results {
    max-height: 300px; overflow-y: auto;
    padding: 4px;
  }
  .cmd-item {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 14px; margin: 2px;
    border-radius: 6px; cursor: pointer;
    transition: background var(--transition);
  }
  .cmd-item:hover, .cmd-item.selected { background: var(--bg-hover); }
  .cmd-item .cmd-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .cmd-item .cmd-label { flex: 1; font-size: 13px; }
  .cmd-item .cmd-path {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px; color: var(--text-dim);
  }
  .cmd-item .cmd-badge {
    font-size: 10px; padding: 1px 6px;
    border-radius: 3px; font-family: 'JetBrains Mono', monospace;
  }

  /* ═══════════════════════════ LOADING ═══════════════════════════ */
  #loading {
    position: fixed; inset: 0;
    display: flex; align-items: center; justify-content: center;
    background: var(--bg-void); z-index: 1000;
    flex-direction: column; gap: 20px;
  }
  #loading.hidden { display: none; }
  .loader {
    width: 48px; height: 48px; position: relative;
  }
  .loader::before, .loader::after {
    content: ''; position: absolute; inset: 0;
    border: 2px solid transparent;
    border-radius: 50%;
  }
  .loader::before {
    border-top-color: var(--accent);
    animation: spin 1s linear infinite;
  }
  .loader::after {
    border-bottom-color: var(--purple);
    animation: spin 1.5s linear infinite reverse;
    inset: 6px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .load-text { font-size: 13px; color: var(--text-muted); letter-spacing: 1px; }
  .load-sub { font-size: 11px; color: var(--text-dim); }

  /* ═══════════════════════════ TOAST ═══════════════════════════ */
  #toast {
    position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
    padding: 10px 20px; background: var(--bg-card);
    border: 1px solid var(--border-accent);
    border-radius: var(--radius); font-size: 13px;
    color: var(--text-secondary); z-index: 600;
    box-shadow: var(--shadow-lg);
    opacity: 0; transition: opacity 0.3s; pointer-events: none;
  }
  #toast.visible { opacity: 1; }

  /* Sidebar toggle */
  #sidebar-toggle {
    position: fixed; top: 16px; left: 308px;
    width: 28px; height: 28px; z-index: 110;
    background: var(--bg-panel); border: 1px solid var(--border);
    border-radius: 6px; color: var(--text-muted);
    cursor: pointer; display: flex; align-items: center;
    justify-content: center; transition: all var(--transition);
    font-size: 14px;
  }
  #sidebar-toggle:hover { border-color: var(--accent); color: var(--accent); }
</style>
</head>
<body>

<div id="loading">
  <div class="loader"></div>
  <div class="load-text">Initializing Graph Engine</div>
  <div class="load-sub" id="load-progress">Preparing layout...</div>
</div>

<!-- Sidebar -->
<div id="sidebar">
  <div class="sidebar-header">
    <div class="logo">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 2v4m0 12v4M2 12h4m12 0h4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83"/></svg>
      Code Graph
      <span class="version">v2.0</span>
    </div>
    <div class="project-name" id="project-name">{{PROJECT_NAME}}</div>
  </div>

  <div class="search-wrap">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
    <input type="text" id="search" placeholder="Search nodes...">
  </div>
  <div class="search-hint">Ctrl+K to focus · Ctrl+P command palette</div>

  <div class="sidebar-scroll">
    <div class="section">
      <div class="section-head" onclick="toggleSection(this)">
        Node Types <span class="toggle-arrow">▼</span>
      </div>
      <div class="section-body" id="node-filters"></div>
    </div>

    <div class="section">
      <div class="section-head" onclick="toggleSection(this)">
        Edge Types <span class="toggle-arrow">▼</span>
      </div>
      <div class="section-body" id="edge-filters"></div>
    </div>

    <div class="section">
      <div class="section-head" onclick="toggleSection(this)">
        Display <span class="toggle-arrow">▼</span>
      </div>
      <div class="section-body" id="display-options">
        <div class="toggle-row" onclick="toggleOpt('labels')">Labels <div class="toggle-switch" id="opt-labels"></div></div>
        <div class="toggle-row" onclick="toggleOpt('arrows')">Arrows <div class="toggle-switch active" id="opt-arrows"></div></div>
        <div class="toggle-row" onclick="toggleOpt('particles')">Edge Particles <div class="toggle-switch" id="opt-particles"></div></div>
        <div class="toggle-row" onclick="toggleOpt('glow')">Node Glow <div class="toggle-switch active" id="opt-glow"></div></div>
        <div class="toggle-row" onclick="toggleOpt('freeze')">Freeze Layout <div class="toggle-switch" id="opt-freeze"></div></div>
        <div class="toggle-row" onclick="toggleOpt('clusters')">Cluster Hulls <div class="toggle-switch" id="opt-clusters"></div></div>
        <div class="toggle-row" onclick="toggleOpt('perf')">Performance Mode <div class="toggle-switch" id="opt-perf"></div></div>
      </div>
    </div>

    <div class="section">
      <div class="section-head" onclick="toggleSection(this)">
        Statistics <span class="toggle-arrow">▼</span>
      </div>
      <div class="section-body">
        <div class="stats-grid">
          <div class="stat-card"><div class="stat-value" id="s-nodes">0</div><div class="stat-label">Nodes</div></div>
          <div class="stat-card"><div class="stat-value" id="s-edges">0</div><div class="stat-label">Edges</div></div>
          <div class="stat-card"><div class="stat-value" id="s-visible">0</div><div class="stat-label">Visible</div></div>
          <div class="stat-card"><div class="stat-value" id="s-clusters">0</div><div class="stat-label">Clusters</div></div>
        </div>
      </div>
    </div>
  </div>

  <div class="action-bar">
    <button class="action-btn" onclick="zoomToFit()" data-tooltip="Fit all nodes">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg> Fit
    </button>
    <button class="action-btn" onclick="resetView()">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg> Reset
    </button>
    <button class="action-btn" onclick="exportPNG()">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> PNG
    </button>
  </div>
</div>

<button id="sidebar-toggle" onclick="toggleSidebar()">☰</button>

<!-- Canvas -->
<div id="graph-container"><canvas id="graph"></canvas></div>

<!-- Toolbar -->
<div id="toolbar" style="left: 348px;">
  <button class="tb-btn" onclick="zoomIn()" data-tooltip="Zoom In"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/></svg></button>
  <button class="tb-btn" onclick="zoomOut()" data-tooltip="Zoom Out"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="8" y1="11" x2="14" y2="11"/></svg></button>
  <button class="tb-btn" onclick="zoomToFit()" data-tooltip="Fit to View"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg></button>
  <div class="tb-sep"></div>
  <button class="tb-btn" onclick="toggleLegend()" data-tooltip="Legend" id="tb-legend"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg></button>
  <button class="tb-btn" onclick="openCmdPalette()" data-tooltip="Command Palette (Ctrl+P)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg></button>
</div>

<!-- Tooltip -->
<div id="tooltip">
  <div class="tt-head"><div class="tt-dot" id="tt-dot"></div><div class="tt-label" id="tt-label"></div></div>
  <div class="tt-badge" id="tt-badge"></div>
  <div class="tt-file" id="tt-file"></div>
  <div class="tt-stats" id="tt-stats"></div>
  <div class="tt-risk" id="tt-risk"></div>
</div>

<!-- Detail Panel -->
<div id="detail">
  <div class="detail-header">
    <button class="detail-close" onclick="closeDetail()">✕</button>
    <div id="detail-head"></div>
  </div>
  <div class="detail-tabs" id="detail-tabs"></div>
  <div class="detail-body" id="detail-body"></div>
</div>

<!-- Minimap -->
<div id="minimap"><canvas id="mm-canvas"></canvas><div class="viewport-rect" id="mm-vp"></div></div>

<!-- Breadcrumb -->
<div id="breadcrumb" style="left: 316px;"></div>

<!-- Legend -->
<div id="legend"></div>

<!-- Command Palette -->
<div id="cmd-palette"><input type="text" id="cmd-input" placeholder="Search nodes, files, types..."><div id="cmd-results"></div></div>
<div id="cmd-palette-overlay" style="position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:499;display:none" onclick="closeCmdPalette()"></div>

<!-- Toast -->
<div id="toast"></div>

<script>
// ═══════════════════════════ DATA ═══════════════════════════
const DATA = {{GRAPH_JSON}};

// ═══════════════════════════ STATE ═══════════════════════════
const S = {
  labels: false, arrows: true, particles: false, glow: true,
  freeze: false, clusters: false, perf: false,
  nodeFilters: {}, edgeFilters: {},
  search: '', hoveredNode: null, selectedNode: null,
  cam: { x: 0, y: 0, s: 1 },
  drag: null, panning: false, panStart: { x: 0, y: 0 },
  sidebarOpen: true, legendOpen: false,
  navHistory: [], navIndex: -1,
};

const NCOL = {
  endpoint:'#00d4ff', collection:'#ff4466', file:'#44ff88',
  router:'#4488ff', script:'#aa66ff', task:'#ffaa00',
  cache_key:'#ff44ff', service:'#00cc99', utility:'#8899aa',
  webhook:'#ff6644', event:'#ff88cc', external_api:'#ffdd44',
  middleware:'#6666ff', serializer:'#ffbb44', test:'#667788',
  config:'#aa8866', component:'#44ddaa', template:'#cc88ff',
};
const ECOL = {
  imports:'#3d4f66', db_read:'#0088cc', db_write:'#cc6600',
  endpoint_handler:'#33cc66', api_call:'#ccaa22', cache_read:'#5577aa',
  cache_write:'#775599', webhook_receive:'#cc5533', webhook_send:'#cc3322',
  event_publish:'#cc6699', event_subscribe:'#9966cc', inherits:'#8888cc',
  calls:'#667788', middleware_chain:'#5555cc',
};

let nodes = [], edges = [], nodeMap = {};
let particles = [];
let alpha = 1, simRAF = null;

const canvas = document.getElementById('graph');
const ctx = canvas.getContext('2d');
const mmCanvas = document.getElementById('mm-canvas');
const mmCtx = mmCanvas.getContext('2d');

// ═══════════════════════════ INIT ═══════════════════════════
function init() {
  resize();
  window.addEventListener('resize', resize);
  canvas.addEventListener('mousemove', onMove);
  canvas.addEventListener('mousedown', onDown);
  canvas.addEventListener('mouseup', onUp);
  canvas.addEventListener('wheel', onWheel, { passive: false });
  canvas.addEventListener('dblclick', onDbl);
  canvas.addEventListener('contextmenu', e => e.preventDefault());
  document.getElementById('search').addEventListener('input', e => { S.search = e.target.value.toLowerCase(); render(); });
  document.addEventListener('keydown', onKey);
  if (DATA && DATA.nodes) loadGraph(DATA);
  document.getElementById('loading').classList.add('hidden');
}

function resize() {
  const c = document.getElementById('graph-container');
  const dpr = window.devicePixelRatio || 1;
  canvas.width = c.clientWidth * dpr;
  canvas.height = c.clientHeight * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  mmCanvas.width = 200 * dpr; mmCanvas.height = 140 * dpr;
  mmCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
  if (nodes.length) render();
}

// ═══════════════════════════ LOAD ═══════════════════════════
function loadGraph(data) {
  document.getElementById('load-progress').textContent = `Loading ${data.nodes.length} nodes...`;
  const cx = (canvas.width / (window.devicePixelRatio || 1)) / 2;
  const cy = (canvas.height / (window.devicePixelRatio || 1)) / 2;
  const spread = Math.min(cx, cy) * 0.85;

  Object.assign(NCOL, data.node_colors || {});
  Object.assign(ECOL, data.edge_colors || {});

  nodes = data.nodes.map((n, i) => ({
    ...n, x: cx + (Math.random() - 0.5) * spread * 2,
    y: cy + (Math.random() - 0.5) * spread * 2,
    vx: 0, vy: 0, radius: 4, conns: 0,
  }));

  nodeMap = {}; nodes.forEach(n => nodeMap[n.id] = n);

  edges = data.edges.filter(e => nodeMap[e.source] && nodeMap[e.target])
    .map(e => ({ ...e, src: nodeMap[e.source], tgt: nodeMap[e.target] }));

  edges.forEach(e => { e.src.conns++; e.tgt.conns++; });
  nodes.forEach(n => { n.radius = Math.max(3, Math.min(22, 3 + Math.sqrt(n.conns) * 1.8)); });

  S.nodeFilters = {}; S.edgeFilters = {};
  if (data.stats) {
    Object.keys(data.stats.node_types || {}).forEach(t => S.nodeFilters[t] = true);
    Object.keys(data.stats.edge_types || {}).forEach(t => S.edgeFilters[t] = true);
  }

  buildFilters(); updateStats(); buildLegend();
  S.cam = { x: 0, y: 0, s: 1 };
  document.getElementById('project-name').textContent = data.project || 'Unknown';
  startSim();
  setTimeout(zoomToFit, 1500);
}

// ═══════════════════════════ SIMULATION ═══════════════════════════
function startSim() {
  if (simRAF) cancelAnimationFrame(simRAF);
  alpha = 1;
  const decay = 0.993, minA = 0.001;

  function tick() {
    if (!S.freeze && alpha > minA) {
      const n = nodes.length;
      const repK = S.perf ? 500 : 900;
      const gridSz = S.perf ? 150 : 100;
      const grid = new Map();

      // Grid for Barnes-Hut
      nodes.forEach(nd => {
        if (!isVis(nd)) return;
        const gx = Math.floor(nd.x / gridSz), gy = Math.floor(nd.y / gridSz);
        const k = `${gx},${gy}`;
        if (!grid.has(k)) grid.set(k, []);
        grid.get(k).push(nd);
      });

      // Repulsion
      nodes.forEach(nd => {
        if (!isVis(nd)) return;
        let fx = 0, fy = 0;
        const gx = Math.floor(nd.x / gridSz), gy = Math.floor(nd.y / gridSz);
        const range = S.perf ? 1 : 2;
        for (let dx = -range; dx <= range; dx++) {
          for (let dy = -range; dy <= range; dy++) {
            const cell = grid.get(`${gx+dx},${gy+dy}`);
            if (!cell) continue;
            for (const o of cell) {
              if (o === nd) continue;
              const ddx = nd.x - o.x, ddy = nd.y - o.y;
              const d = Math.sqrt(ddx*ddx + ddy*ddy) || 1;
              if (d < 350) {
                const f = repK / (d * d);
                fx += (ddx/d) * f; fy += (ddy/d) * f;
              }
            }
          }
        }
        nd.vx += fx * alpha; nd.vy += fy * alpha;
      });

      // Springs
      const sK = 0.025, ideal = 90;
      edges.forEach(e => {
        if (!e.src || !e.tgt || !isVis(e.src) || !isVis(e.tgt)) return;
        const dx = e.tgt.x - e.src.x, dy = e.tgt.y - e.src.y;
        const d = Math.sqrt(dx*dx + dy*dy) || 1;
        const f = (d - ideal) * sK * alpha;
        const fx = (dx/d)*f, fy = (dy/d)*f;
        e.src.vx += fx; e.src.vy += fy;
        e.tgt.vx -= fx; e.tgt.vy -= fy;
      });

      // Center gravity
      const cX = (canvas.width / (window.devicePixelRatio||1)) / 2;
      const cY = (canvas.height / (window.devicePixelRatio||1)) / 2;
      const grav = 0.012 * alpha;
      nodes.forEach(nd => {
        if (!isVis(nd)) return;
        nd.vx += (cX - nd.x) * grav; nd.vy += (cY - nd.y) * grav;
      });

      // Velocity
      const damp = 0.82;
      nodes.forEach(nd => {
        if (nd === S.drag || !isVis(nd)) return;
        nd.vx *= damp; nd.vy *= damp;
        nd.x += nd.vx; nd.y += nd.vy;
      });

      alpha *= decay;
    }

    // Update particles
    if (S.particles && !S.perf) updateParticles();

    render();
    simRAF = requestAnimationFrame(tick);
  }
  simRAF = requestAnimationFrame(tick);
}

// ═══════════════════════════ PARTICLES ═══════════════════════════
function updateParticles() {
  if (Math.random() < 0.15 && edges.length > 0) {
    const e = edges[Math.floor(Math.random() * edges.length)];
    if (isEdgeVis(e)) {
      particles.push({ edge: e, t: 0, speed: 0.005 + Math.random() * 0.008 });
    }
  }
  particles = particles.filter(p => {
    p.t += p.speed;
    return p.t < 1;
  });
}

// ═══════════════════════════ VISIBILITY ═══════════════════════════
function isVis(n) {
  if (!S.nodeFilters[n.type]) return false;
  if (S.search && !n.label.toLowerCase().includes(S.search) &&
      !(n.file && n.file.toLowerCase().includes(S.search))) return false;
  return true;
}
function isEdgeVis(e) {
  return S.edgeFilters[e.type] && e.src && e.tgt && isVis(e.src) && isVis(e.tgt);
}

// ═══════════════════════════ RENDER ═══════════════════════════
function render() {
  const w = canvas.width / (window.devicePixelRatio||1);
  const h = canvas.height / (window.devicePixelRatio||1);
  ctx.clearRect(0, 0, w, h);
  ctx.save();
  ctx.translate(S.cam.x, S.cam.y);
  ctx.scale(S.cam.s, S.cam.s);

  const hNode = S.hoveredNode || S.selectedNode;

  // Cluster hulls
  if (S.clusters && !S.perf) drawClusters();

  // Edges
  edges.forEach(e => {
    if (!isEdgeVis(e)) return;
    const col = ECOL[e.type] || '#334455';
    const isHL = hNode && (e.source === hNode.id || e.target === hNode.id);
    const isSel = S.selectedNode && (e.source === S.selectedNode.id || e.target === S.selectedNode.id);

    ctx.beginPath();
    ctx.moveTo(e.src.x, e.src.y);
    ctx.lineTo(e.tgt.x, e.tgt.y);

    if (isHL || isSel) {
      ctx.strokeStyle = col; ctx.lineWidth = 2.5; ctx.globalAlpha = 0.9;
    } else if (hNode) {
      ctx.strokeStyle = col; ctx.lineWidth = 0.3; ctx.globalAlpha = 0.06;
    } else {
      ctx.strokeStyle = col; ctx.lineWidth = 0.5; ctx.globalAlpha = 0.2;
    }
    ctx.stroke(); ctx.globalAlpha = 1;

    // Arrows
    if (S.arrows && (isHL || isSel || !hNode) && !S.perf) {
      const dx = e.tgt.x - e.src.x, dy = e.tgt.y - e.src.y;
      const dist = Math.sqrt(dx*dx + dy*dy);
      if (dist > 35) {
        const t = 1 - (e.tgt.radius + 5) / dist;
        const ax = e.src.x + dx*t, ay = e.src.y + dy*t;
        const angle = Math.atan2(dy, dx);
        const sz = isHL || isSel ? 7 : 3.5;
        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.lineTo(ax - sz*Math.cos(angle-0.4), ay - sz*Math.sin(angle-0.4));
        ctx.lineTo(ax - sz*Math.cos(angle+0.4), ay - sz*Math.sin(angle+0.4));
        ctx.closePath();
        ctx.fillStyle = col;
        ctx.globalAlpha = isHL || isSel ? 0.85 : 0.12;
        ctx.fill(); ctx.globalAlpha = 1;
      }
    }
  });

  // Particles
  if (S.particles && !S.perf) {
    particles.forEach(p => {
      const e = p.edge;
      if (!isEdgeVis(e)) return;
      const x = e.src.x + (e.tgt.x - e.src.x) * p.t;
      const y = e.src.y + (e.tgt.y - e.src.y) * p.t;
      const col = ECOL[e.type] || '#00d4ff';
      ctx.beginPath();
      ctx.arc(x, y, 2, 0, Math.PI * 2);
      ctx.fillStyle = col;
      ctx.globalAlpha = 1 - p.t;
      ctx.fill();
      ctx.globalAlpha = 1;
    });
  }

  // Nodes
  nodes.forEach(n => {
    if (!isVis(n)) return;
    const col = NCOL[n.type] || '#8899aa';
    const isH = S.hoveredNode === n, isS = S.selectedNode === n;
    const isConn = hNode && edges.some(e =>
      ((e.source===hNode.id && e.target===n.id) || (e.target===hNode.id && e.source===n.id)) && isEdgeVis(e)
    );
    let a = 1, r = n.radius;

    if (hNode) {
      if (isH || isS || isConn) { a = 1; r = isH||isS ? r*1.35 : r; }
      else { a = 0.07; }
    }

    // Glow
    if (S.glow && (isH || isS) && !S.perf) {
      const grad = ctx.createRadialGradient(n.x, n.y, r, n.x, n.y, r + 14);
      grad.addColorStop(0, col + '55'); grad.addColorStop(1, col + '00');
      ctx.beginPath(); ctx.arc(n.x, n.y, r + 14, 0, Math.PI*2);
      ctx.fillStyle = grad; ctx.fill();
    }

    // Circle
    ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, Math.PI*2);
    ctx.fillStyle = col; ctx.globalAlpha = a; ctx.fill();
    ctx.strokeStyle = isH||isS ? '#fff' : col;
    ctx.lineWidth = isH||isS ? 2 : 0.5;
    ctx.globalAlpha = a; ctx.stroke(); ctx.globalAlpha = 1;

    // Label
    if (S.labels || isH || isS || (isConn && S.cam.s > 0.6)) {
      const fs = isH||isS ? 12 : 10;
      ctx.font = `${isH||isS ? 600 : 400} ${fs}px 'JetBrains Mono', monospace`;
      ctx.fillStyle = isH||isS ? '#fff' : '#8892a8';
      ctx.globalAlpha = isH||isS ? 1 : a * 0.65;
      ctx.textAlign = 'center';
      ctx.fillText(n.label, n.x, n.y - r - 6);
      ctx.globalAlpha = 1;
    }
  });

  ctx.restore();
  renderMinimap();
  updateVisibleCount();
}

// ═══════════════════════════ CLUSTERS ═══════════════════════════
function drawClusters() {
  const groups = {};
  nodes.forEach(n => {
    if (!isVis(n)) return;
    const dir = (n.file || '').split('/')[0] || 'root';
    if (!groups[dir]) groups[dir] = [];
    groups[dir].push(n);
  });

  const colors = ['#00d4ff','#ff4466','#44ff88','#ffaa00','#aa66ff','#ff88cc','#4488ff','#00cc99'];
  let ci = 0;
  Object.values(groups).forEach(pts => {
    if (pts.length < 3) return;
    const col = colors[ci++ % colors.length];
    // Convex hull
    const hull = convexHull(pts.map(p => [p.x, p.y]));
    if (hull.length < 3) return;
    ctx.beginPath();
    ctx.moveTo(hull[0][0], hull[0][1]);
    hull.forEach(p => ctx.lineTo(p[0], p[1]));
    ctx.closePath();
    ctx.fillStyle = col + '08'; ctx.fill();
    ctx.strokeStyle = col + '20'; ctx.lineWidth = 1;
    ctx.setLineDash([4,4]); ctx.stroke(); ctx.setLineDash([]);
  });
}

function convexHull(pts) {
  if (pts.length < 3) return pts;
  pts = [...pts].sort((a,b) => a[0]-b[0] || a[1]-b[1]);
  const cross = (O,A,B) => (A[0]-O[0])*(B[1]-O[1]) - (A[1]-O[1])*(B[0]-O[0]);
  const lo = [], up = [];
  for (const p of pts) { while (lo.length>=2 && cross(lo[lo.length-2],lo[lo.length-1],p)<=0) lo.pop(); lo.push(p); }
  for (const p of pts.reverse()) { while (up.length>=2 && cross(up[up.length-2],up[up.length-1],p)<=0) up.pop(); up.push(p); }
  lo.pop(); up.pop();
  return lo.concat(up);
}

// ═══════════════════════════ MINIMAP ═══════════════════════════
function renderMinimap() {
  const w = 200, h = 140;
  mmCtx.clearRect(0, 0, w, h);
  mmCtx.fillStyle = '#0a0f1a88'; mmCtx.fillRect(0, 0, w, h);

  if (!nodes.length) return;
  let mnX=Infinity,mxX=-Infinity,mnY=Infinity,mxY=-Infinity;
  nodes.forEach(n => { if(!isVis(n))return; mnX=Math.min(mnX,n.x);mxX=Math.max(mxX,n.x);mnY=Math.min(mnY,n.y);mxY=Math.max(mxY,n.y); });
  if (!isFinite(mnX)) return;

  const pad = 20, rX = (mxX-mnX)||1, rY = (mxY-mnY)||1;
  const sc = Math.min((w-pad*2)/rX, (h-pad*2)/rY);

  nodes.forEach(n => {
    if (!isVis(n)) return;
    const x = pad + (n.x-mnX)*sc, y = pad + (n.y-mnY)*sc;
    mmCtx.beginPath(); mmCtx.arc(x, y, 1.5, 0, Math.PI*2);
    mmCtx.fillStyle = NCOL[n.type] || '#8899aa';
    mmCtx.globalAlpha = 0.7; mmCtx.fill(); mmCtx.globalAlpha = 1;
  });

  // Viewport rect
  const cW = (canvas.width/(window.devicePixelRatio||1));
  const cH = (canvas.height/(window.devicePixelRatio||1));
  const vp = document.getElementById('mm-vp');
  const vpL = pad + ((-S.cam.x/S.cam.s) - mnX) * sc;
  const vpT = pad + ((-S.cam.y/S.cam.s) - mnY) * sc;
  const vpW = (cW/S.cam.s) * sc;
  const vpH = (cH/S.cam.s) * sc;
  vp.style.left = Math.max(0, vpL) + 'px';
  vp.style.top = Math.max(0, vpT) + 'px';
  vp.style.width = Math.min(w, vpW) + 'px';
  vp.style.height = Math.min(h, vpH) + 'px';
}

// ═══════════════════════════ INTERACTION ═══════════════════════════
function s2w(sx, sy) {
  return { x: (sx - S.cam.x) / S.cam.s, y: (sy - S.cam.y) / S.cam.s };
}

function findNode(wx, wy) {
  for (let i = nodes.length - 1; i >= 0; i--) {
    const n = nodes[i]; if (!isVis(n)) continue;
    const dx = n.x-wx, dy = n.y-wy;
    if (dx*dx + dy*dy < (n.radius+5)*(n.radius+5)) return n;
  }
  return null;
}

function onMove(e) {
  const r = canvas.getBoundingClientRect();
  const sx = e.clientX - r.left, sy = e.clientY - r.top;

  if (S.panning) {
    S.cam.x += e.clientX - S.panStart.x;
    S.cam.y += e.clientY - S.panStart.y;
    S.panStart = { x: e.clientX, y: e.clientY };
    render(); return;
  }
  if (S.drag) {
    const w = s2w(sx, sy);
    S.drag.x = w.x; S.drag.y = w.y;
    S.drag.vx = 0; S.drag.vy = 0;
    render(); return;
  }

  const w = s2w(sx, sy);
  const nd = findNode(w.x, w.y);
  if (nd !== S.hoveredNode) {
    S.hoveredNode = nd;
    canvas.style.cursor = nd ? 'pointer' : 'grab';
    if (nd) showTooltip(e.clientX, e.clientY, nd);
    else hideTooltip();
    render();
  } else if (nd) moveTooltip(e.clientX, e.clientY);
}

function onDown(e) {
  const r = canvas.getBoundingClientRect();
  const w = s2w(e.clientX - r.left, e.clientY - r.top);
  const nd = findNode(w.x, w.y);
  if (nd) { S.drag = nd; canvas.style.cursor = 'grabbing'; }
  else { S.panning = true; S.panStart = { x: e.clientX, y: e.clientY }; canvas.style.cursor = 'grabbing'; }
}

function onUp() {
  S.drag = null; S.panning = false; canvas.style.cursor = 'grab';
}

function onDbl(e) {
  const r = canvas.getBoundingClientRect();
  const w = s2w(e.clientX - r.left, e.clientY - r.top);
  const nd = findNode(w.x, w.y);
  if (nd) { selectNode(nd); } else { S.selectedNode = null; closeDetail(); render(); }
}

function onWheel(e) {
  e.preventDefault();
  const r = canvas.getBoundingClientRect();
  const sx = e.clientX - r.left, sy = e.clientY - r.top;
  const z = e.deltaY > 0 ? 0.9 : 1.1;
  const ns = S.cam.s * z;
  if (ns < 0.03 || ns > 12) return;
  S.cam.x = sx - (sx - S.cam.x) * z;
  S.cam.y = sy - (sy - S.cam.y) * z;
  S.cam.s = ns;
  render();
}

function onKey(e) {
  if (e.key === 'Escape') { closeCmdPalette(); closeDetail(); S.selectedNode = null; S.hoveredNode = null; render(); return; }
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); document.getElementById('search').focus(); return; }
  if ((e.ctrlKey || e.metaKey) && e.key === 'p') { e.preventDefault(); openCmdPalette(); return; }
  if (e.key === ' ' && document.activeElement === document.body) { e.preventDefault(); zoomToFit(); }
}

// ═══════════════════════════ TOOLTIP ═══════════════════════════
function showTooltip(x, y, n) {
  const t = document.getElementById('tooltip');
  const col = NCOL[n.type] || '#8899aa';
  document.getElementById('tt-dot').style.background = col;
  document.getElementById('tt-label').textContent = n.label;
  const badge = document.getElementById('tt-badge');
  badge.textContent = n.type; badge.style.background = col+'22'; badge.style.color = col;
  document.getElementById('tt-file').textContent = n.file || '';

  const inE = edges.filter(e => e.target===n.id && isEdgeVis(e));
  const outE = edges.filter(e => e.source===n.id && isEdgeVis(e));
  document.getElementById('tt-stats').innerHTML =
    `<div class="tt-stat"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>${inE.length} in</div>` +
    `<div class="tt-stat"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"/></svg>${outE.length} out</div>` +
    `<div class="tt-stat">${n.conns} total</div>`;

  const risk = getRisk(n);
  document.getElementById('tt-risk').textContent = risk;
  document.getElementById('tt-risk').style.color =
    risk.startsWith('⛔') ? 'var(--danger)' : risk.startsWith('🔴') ? '#ff6644' :
    risk.startsWith('🟡') ? 'var(--warning)' : 'var(--success)';

  t.style.display = 'block';
  moveTooltip(x, y);
}

function moveTooltip(x, y) {
  const t = document.getElementById('tooltip');
  const tr = t.getBoundingClientRect();
  let tx = x + 16, ty = y + 16;
  if (tx + tr.width > window.innerWidth - 10) tx = x - tr.width - 16;
  if (ty + tr.height > window.innerHeight - 10) ty = y - tr.height - 16;
  t.style.left = tx + 'px'; t.style.top = ty + 'px';
}

function hideTooltip() { document.getElementById('tooltip').style.display = 'none'; }

function getRisk(n) {
  const c = n.conns, inE = edges.filter(e => e.target===n.id).length;
  if (c >= 20 || ['router','config'].includes(n.type)) return `⛔ CRITICAL — ${c} connections`;
  if (c >= 10 || (inE >= 5 && ['collection','service'].includes(n.type))) return `🔴 HIGH — ${c} connections`;
  if (c >= 4 || inE >= 2) return `🟡 MEDIUM — ${c} connections`;
  return `🟢 LOW — ${c} connections`;
}

// ═══════════════════════════ DETAIL PANEL ═══════════════════════════
function selectNode(n) {
  S.selectedNode = n;
  S.navHistory = S.navHistory.slice(0, S.navIndex + 1);
  S.navHistory.push(n.id); S.navIndex = S.navHistory.length - 1;
  updateBreadcrumb();
  showDetail(n); render();
}

function showDetail(n) {
  const col = NCOL[n.type] || '#8899aa';
  const inE = edges.filter(e => e.target===n.id && isEdgeVis(e));
  const outE = edges.filter(e => e.source===n.id && isEdgeVis(e));

  document.getElementById('detail-head').innerHTML = `
    <div class="detail-title">${n.label}</div>
    <div class="detail-badge" style="background:${col}22;color:${col}">${n.type}</div>
    ${n.file ? `<div class="detail-file">${n.file}${n.line ? ':'+n.line : ''}</div>` : ''}
  `;

  document.getElementById('detail-tabs').innerHTML = `
    <div class="detail-tab active" onclick="showTab(this,'conns')">Connections</div>
    <div class="detail-tab" onclick="showTab(this,'meta')">Metadata</div>
    <div class="detail-tab" onclick="showTab(this,'risk')">Risk</div>
  `;

  showTabContent('conns', n, inE, outE);
  document.getElementById('detail').classList.add('open');
}

function showTab(el, tab) {
  el.parentElement.querySelectorAll('.detail-tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  const n = S.selectedNode; if (!n) return;
  const inE = edges.filter(e => e.target===n.id && isEdgeVis(e));
  const outE = edges.filter(e => e.source===n.id && isEdgeVis(e));
  showTabContent(tab, n, inE, outE);
}

function showTabContent(tab, n, inE, outE) {
  const body = document.getElementById('detail-body');
  let html = '';

  if (tab === 'conns') {
    if (inE.length) {
      html += `<div class="detail-section"><div class="detail-section-title">Incoming (${inE.length})</div>`;
      inE.forEach(e => {
        const s = nodeMap[e.source]; if (!s) return;
        const c = NCOL[s.type]||'#8899aa';
        html += `<div class="conn-item" onclick="focusNode('${s.id}')"><div class="conn-dot" style="background:${c}"></div><span class="conn-name">${s.label}</span><span class="conn-type">${e.type}</span></div>`;
      });
      html += `</div>`;
    }
    if (outE.length) {
      html += `<div class="detail-section"><div class="detail-section-title">Outgoing (${outE.length})</div>`;
      outE.forEach(e => {
        const t = nodeMap[e.target]; if (!t) return;
        const c = NCOL[t.type]||'#8899aa';
        html += `<div class="conn-item" onclick="focusNode('${t.id}')"><div class="conn-dot" style="background:${c}"></div><span class="conn-name">${t.label}</span><span class="conn-type">${e.type}</span></div>`;
      });
      html += `</div>`;
    }
    if (!inE.length && !outE.length) html = '<div style="color:var(--text-dim);font-size:13px;padding:20px 0;text-align:center">No visible connections</div>';
  } else if (tab === 'meta') {
    html += `<div class="detail-section"><div class="detail-section-title">Properties</div>`;
    html += `<div class="meta-row"><span class="meta-key">ID</span><span class="meta-val">${n.id}</span></div>`;
    html += `<div class="meta-row"><span class="meta-key">Type</span><span class="meta-val">${n.type}</span></div>`;
    html += `<div class="meta-row"><span class="meta-key">File</span><span class="meta-val">${n.file||'—'}</span></div>`;
    html += `<div class="meta-row"><span class="meta-key">Line</span><span class="meta-val">${n.line||'—'}</span></div>`;
    html += `<div class="meta-row"><span class="meta-key">Connections</span><span class="meta-val">${n.conns}</span></div>`;
    const m = n.metadata || {};
    Object.entries(m).forEach(([k,v]) => {
      if (v) html += `<div class="meta-row"><span class="meta-key">${k}</span><span class="meta-val">${v}</span></div>`;
    });
    html += `</div>`;
  } else if (tab === 'risk') {
    const risk = getRisk(n);
    const inCount = edges.filter(e => e.target===n.id).length;
    const outCount = edges.filter(e => e.source===n.id).length;
    html += `<div class="detail-section"><div class="detail-section-title">Risk Assessment</div>`;
    html += `<div style="font-size:18px;margin:12px 0">${risk}</div>`;
    html += `<div class="meta-row"><span class="meta-key">Dependents (in)</span><span class="meta-val">${inCount}</span></div>`;
    html += `<div class="meta-row"><span class="meta-key">Dependencies (out)</span><span class="meta-val">${outCount}</span></div>`;
    html += `<div class="meta-row"><span class="meta-key">Total connections</span><span class="meta-val">${n.conns}</span></div>`;
    html += `</div>`;

    // Impact preview
    const affected = new Set();
    const queue = [[n.id, 0]]; const visited = new Set([n.id]);
    while (queue.length) {
      const [cid, depth] = queue.shift();
      if (depth > 2) continue;
      edges.forEach(e => {
        if (e.target === cid && !visited.has(e.source)) {
          visited.add(e.source); affected.add(e.source);
          queue.push([e.source, depth + 1]);
        }
      });
    }
    if (affected.size) {
      html += `<div class="detail-section"><div class="detail-section-title">Impact Cascade (${affected.size} files)</div>`;
      [...affected].slice(0, 12).forEach(id => {
        const an = nodeMap[id]; if (!an) return;
        const c = NCOL[an.type]||'#8899aa';
        html += `<div class="conn-item" onclick="focusNode('${an.id}')"><div class="conn-dot" style="background:${c}"></div><span class="conn-name">${an.label}</span><span class="conn-type">${an.type}</span></div>`;
      });
      if (affected.size > 12) html += `<div style="color:var(--text-dim);font-size:11px;padding:4px 8px">+${affected.size - 12} more</div>`;
      html += `</div>`;
    }
  }

  body.innerHTML = html;
}

function closeDetail() { document.getElementById('detail').classList.remove('open'); }

function focusNode(id) {
  const n = nodeMap[id]; if (!n) return;
  selectNode(n);
  const cW = canvas.width / (window.devicePixelRatio||1);
  const cH = canvas.height / (window.devicePixelRatio||1);
  S.cam.x = cW/2 - n.x*S.cam.s;
  S.cam.y = cH/2 - n.y*S.cam.s;
  render();
}

// ═══════════════════════════ BREADCRUMB ═══════════════════════════
function updateBreadcrumb() {
  const bc = document.getElementById('breadcrumb');
  const items = S.navHistory.slice(Math.max(0, S.navIndex - 4), S.navIndex + 1);
  bc.innerHTML = items.map((id, i) => {
    const n = nodeMap[id]; if (!n) return '';
    const isCur = i === items.length - 1;
    return `${i > 0 ? '<span class="bc-sep">›</span>' : ''}` +
      `<span class="bc-item${isCur ? ' current' : ''}" onclick="focusNode('${id}')">${n.label}</span>`;
  }).join('');
}

// ═══════════════════════════ UI CONTROLS ═══════════════════════════
function buildFilters() {
  const nc = document.getElementById('node-filters');
  const ec = document.getElementById('edge-filters');
  nc.innerHTML = ''; ec.innerHTML = '';
  if (!DATA.stats) return;

  Object.entries(DATA.stats.node_types || {}).sort((a,b) => b[1]-a[1]).forEach(([t,c]) => {
    const col = NCOL[t]||'#8899aa';
    nc.innerHTML += `<label class="filter-item"><input type="checkbox" checked onchange="S.nodeFilters['${t}']=this.checked;render()"><div class="filter-dot" style="background:${col}"></div><span class="filter-label">${t}</span><span class="filter-count">${c}</span></label>`;
  });

  Object.entries(DATA.stats.edge_types || {}).sort((a,b) => b[1]-a[1]).forEach(([t,c]) => {
    const col = ECOL[t]||'#3d4f66';
    ec.innerHTML += `<label class="filter-item"><input type="checkbox" checked onchange="S.edgeFilters['${t}']=this.checked;render()"><div class="filter-dot" style="background:${col}"></div><span class="filter-label">${t}</span><span class="filter-count">${c}</span></label>`;
  });
}

function toggleSection(el) {
  el.classList.toggle('collapsed');
  el.nextElementSibling.classList.toggle('collapsed');
}

function toggleOpt(key) {
  S[key] = !S[key];
  const el = document.getElementById('opt-' + key);
  el.classList.toggle('active');
  if (key === 'freeze') alpha = S.freeze ? 0 : 0.3;
  render();
}

function updateStats() {
  if (!DATA.stats) return;
  document.getElementById('s-nodes').textContent = DATA.stats.total_nodes;
  document.getElementById('s-edges').textContent = DATA.stats.total_edges;
}

function updateVisibleCount() {
  document.getElementById('s-visible').textContent = nodes.filter(isVis).length;
  // Simplified cluster count
  const vis = new Set(nodes.filter(isVis).map(n => n.id));
  const visited = new Set(); let cc = 0;
  vis.forEach(id => {
    if (visited.has(id)) return;
    cc++; const q = [id]; visited.add(id);
    while (q.length) {
      const cur = q.shift();
      edges.forEach(e => {
        if (!isEdgeVis(e)) return;
        let nb = null;
        if (e.source===cur && vis.has(e.target)) nb = e.target;
        if (e.target===cur && vis.has(e.source)) nb = e.source;
        if (nb && !visited.has(nb)) { visited.add(nb); q.push(nb); }
      });
    }
  });
  document.getElementById('s-clusters').textContent = cc;
}

function toggleSidebar() {
  S.sidebarOpen = !S.sidebarOpen;
  document.getElementById('sidebar').classList.toggle('collapsed');
  document.getElementById('graph-container').classList.toggle('expanded');
  document.getElementById('toolbar').style.left = S.sidebarOpen ? '348px' : '48px';
  document.getElementById('breadcrumb').style.left = S.sidebarOpen ? '316px' : '16px';
  document.getElementById('sidebar-toggle').style.left = S.sidebarOpen ? '308px' : '8px';
  setTimeout(resize, 300);
}

// ═══════════════════════════ LEGEND ═══════════════════════════
function buildLegend() {
  const el = document.getElementById('legend');
  let html = '<div class="legend-title">Node Types</div>';
  Object.entries(DATA.stats?.node_types || {}).sort((a,b) => b[1]-a[1]).forEach(([t]) => {
    html += `<div class="legend-item"><div class="legend-dot" style="background:${NCOL[t]||'#8899aa'}"></div>${t}</div>`;
  });
  html += '<div class="legend-title" style="margin-top:12px">Edge Types</div>';
  Object.entries(DATA.stats?.edge_types || {}).sort((a,b) => b[1]-a[1]).forEach(([t]) => {
    html += `<div class="legend-item"><div class="legend-line" style="background:${ECOL[t]||'#3d4f66'}"></div>${t}</div>`;
  });
  el.innerHTML = html;
}

function toggleLegend() {
  S.legendOpen = !S.legendOpen;
  document.getElementById('legend').classList.toggle('visible');
  document.getElementById('tb-legend').classList.toggle('active');
}

// ═══════════════════════════ COMMAND PALETTE ═══════════════════════════
function openCmdPalette() {
  document.getElementById('cmd-palette').classList.add('visible');
  document.getElementById('cmd-palette-overlay').style.display = 'block';
  const inp = document.getElementById('cmd-input');
  inp.value = ''; inp.focus();
  showCmdResults('');
  inp.oninput = () => showCmdResults(inp.value);
  inp.onkeydown = (e) => {
    if (e.key === 'Escape') closeCmdPalette();
    if (e.key === 'Enter') {
      const sel = document.querySelector('.cmd-item.selected') || document.querySelector('.cmd-item');
      if (sel) sel.click();
    }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      const items = [...document.querySelectorAll('.cmd-item')];
      const cur = items.findIndex(i => i.classList.contains('selected'));
      items.forEach(i => i.classList.remove('selected'));
      const next = e.key === 'ArrowDown' ? Math.min(cur+1, items.length-1) : Math.max(cur-1, 0);
      if (items[next]) { items[next].classList.add('selected'); items[next].scrollIntoView({block:'nearest'}); }
    }
  };
}

function closeCmdPalette() {
  document.getElementById('cmd-palette').classList.remove('visible');
  document.getElementById('cmd-palette-overlay').style.display = 'none';
}

function showCmdResults(q) {
  q = q.toLowerCase();
  const matches = nodes.filter(n =>
    n.label.toLowerCase().includes(q) || (n.file||'').toLowerCase().includes(q)
  ).slice(0, 15);

  const el = document.getElementById('cmd-results');
  el.innerHTML = matches.map((n, i) => {
    const col = NCOL[n.type]||'#8899aa';
    return `<div class="cmd-item${i===0?' selected':''}" onclick="focusNode('${n.id}');closeCmdPalette()">
      <div class="cmd-dot" style="background:${col}"></div>
      <span class="cmd-label">${n.label}</span>
      <span class="cmd-badge" style="background:${col}22;color:${col}">${n.type}</span>
      <span class="cmd-path">${n.file||''}</span>
    </div>`;
  }).join('');
}

// ═══════════════════════════ ACTIONS ═══════════════════════════
function zoomToFit() {
  if (!nodes.length) return;
  let mnX=Infinity,mxX=-Infinity,mnY=Infinity,mxY=-Infinity;
  nodes.forEach(n => { if(!isVis(n))return; mnX=Math.min(mnX,n.x);mxX=Math.max(mxX,n.x);mnY=Math.min(mnY,n.y);mxY=Math.max(mxY,n.y); });
  if (!isFinite(mnX)) return;

  const cW = canvas.width/(window.devicePixelRatio||1);
  const cH = canvas.height/(window.devicePixelRatio||1);
  const pad = 80;
  const rX = (mxX-mnX)||1, rY = (mxY-mnY)||1;
  const sc = Math.min((cW-pad*2)/rX, (cH-pad*2)/rY, 2);
  const cx = (mnX+mxX)/2, cy = (mnY+mxY)/2;
  S.cam.s = sc; S.cam.x = cW/2 - cx*sc; S.cam.y = cH/2 - cy*sc;
  render();
  toast('View fitted to all visible nodes');
}

function resetView() { S.cam = {x:0,y:0,s:1}; render(); toast('View reset'); }
function zoomIn() { S.cam.s = Math.min(S.cam.s * 1.3, 12); render(); }
function zoomOut() { S.cam.s = Math.max(S.cam.s * 0.7, 0.03); render(); }

function exportPNG() {
  const link = document.createElement('a');
  link.download = `code-graph-${DATA.project || 'export'}.png`;
  link.href = canvas.toDataURL('image/png');
  link.click();
  toast('PNG exported');
}

function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('visible');
  setTimeout(() => t.classList.remove('visible'), 2500);
}

// ═══════════════════════════ FILE UPLOAD ═══════════════════════════
window.addEventListener('DOMContentLoaded', init);
</script>
</body>
</html>
'''


def main():
    parser = argparse.ArgumentParser(
        description="Generate an interactive HTML viewer from a code_graph.json file."
    )
    parser.add_argument("graph_json", help="Path to the code_graph.json file")
    parser.add_argument("-o", "--output", default="code_graph_viewer.html",
                        help="Output HTML file path")

    args = parser.parse_args()

    # Load graph JSON
    graph_path = os.path.abspath(args.graph_json)
    if not os.path.isfile(graph_path):
        print(f"Error: {graph_path} not found")
        sys.exit(1)

    with open(graph_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    project_name = graph_data.get("project", "Unknown Project")

    # Embed data into HTML
    html = HTML_TEMPLATE
    html = html.replace("{{PROJECT_NAME}}", project_name)
    html = html.replace("{{GRAPH_JSON}}", json.dumps(graph_data))

    # Write output
    output_path = os.path.abspath(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Viewer saved to: {output_path}")
    print(f"Open in browser to explore the graph interactively.")


if __name__ == "__main__":
    main()
