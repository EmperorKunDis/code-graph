#!/usr/bin/env python3
"""
Code Graph Viewer Generator - Creates an interactive HTML visualization
from a code_graph.json file.

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
<title>Code Graph Viewer — {{PROJECT_NAME}}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600&family=Outfit:wght@300;400;500;600;700&display=swap');

  * { margin: 0; padding: 0; box-sizing: border-box; }

  :root {
    --bg-primary: #0a0e1a;
    --bg-secondary: #111827;
    --bg-panel: #0f1729;
    --border: #1e2940;
    --text-primary: #e2e8f0;
    --text-secondary: #8892a8;
    --text-muted: #4a5568;
    --accent: #00d4ff;
    --accent-dim: #00d4ff33;
    --danger: #ff4466;
    --success: #44ff88;
    --warning: #ffaa00;
  }

  body {
    font-family: 'Outfit', sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    overflow: hidden;
    height: 100vh;
    width: 100vw;
  }

  /* ── Sidebar ── */
  #sidebar {
    position: fixed;
    left: 0; top: 0; bottom: 0;
    width: 280px;
    background: var(--bg-panel);
    border-right: 1px solid var(--border);
    overflow-y: auto;
    z-index: 100;
    padding: 16px;
    scrollbar-width: thin;
    scrollbar-color: var(--border) transparent;
  }

  #sidebar::-webkit-scrollbar { width: 6px; }
  #sidebar::-webkit-scrollbar-track { background: transparent; }
  #sidebar::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

  #sidebar h1 {
    font-family: 'JetBrains Mono', monospace;
    font-size: 16px;
    font-weight: 600;
    color: var(--accent);
    margin-bottom: 16px;
    letter-spacing: 0.5px;
  }

  #sidebar h1 span {
    color: var(--text-secondary);
    font-weight: 300;
    font-size: 12px;
    display: block;
    margin-top: 4px;
  }

  /* Upload zone */
  .upload-zone {
    border: 2px dashed var(--border);
    border-radius: 8px;
    padding: 12px;
    text-align: center;
    margin-bottom: 16px;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 13px;
    color: var(--text-secondary);
  }
  .upload-zone:hover { border-color: var(--accent); color: var(--accent); }
  .upload-zone.loaded { border-color: var(--success); border-style: solid; }
  .upload-zone .loaded-file { color: var(--success); font-size: 11px; margin-top: 4px; }

  /* Search */
  #search {
    width: 100%;
    padding: 8px 12px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text-primary);
    font-family: 'Outfit', sans-serif;
    font-size: 13px;
    margin-bottom: 16px;
    outline: none;
    transition: border-color 0.2s;
  }
  #search:focus { border-color: var(--accent); }
  #search::placeholder { color: var(--text-muted); }

  /* Section headers */
  .section-header {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 600;
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin: 16px 0 8px 0;
  }

  /* Checkbox filters */
  .filter-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
    cursor: pointer;
    font-size: 13px;
    user-select: none;
  }

  .filter-item input[type="checkbox"] {
    appearance: none;
    width: 16px; height: 16px;
    border: 2px solid var(--border);
    border-radius: 3px;
    cursor: pointer;
    position: relative;
    flex-shrink: 0;
  }
  .filter-item input[type="checkbox"]:checked {
    background: var(--accent);
    border-color: var(--accent);
  }
  .filter-item input[type="checkbox"]:checked::after {
    content: '✓';
    position: absolute;
    top: -2px; left: 2px;
    font-size: 12px;
    color: var(--bg-primary);
    font-weight: 700;
  }

  .filter-dot {
    width: 10px; height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .filter-label { flex: 1; color: var(--text-secondary); }
  .filter-count {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--accent);
    background: var(--accent-dim);
    padding: 1px 6px;
    border-radius: 10px;
  }

  /* Toggle switches */
  .toggle-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 0;
    font-size: 13px;
    color: var(--text-secondary);
  }

  .toggle {
    width: 40px; height: 22px;
    background: var(--border);
    border-radius: 11px;
    position: relative;
    cursor: pointer;
    transition: background 0.2s;
  }
  .toggle.active { background: var(--accent); }
  .toggle::after {
    content: '';
    position: absolute;
    top: 3px; left: 3px;
    width: 16px; height: 16px;
    background: white;
    border-radius: 50%;
    transition: transform 0.2s;
  }
  .toggle.active::after { transform: translateX(18px); }

  /* Stats */
  .stats-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin-top: 8px;
  }

  .stat-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 10px;
    text-align: center;
  }
  .stat-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 20px;
    font-weight: 600;
    color: var(--accent);
  }
  .stat-label {
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 2px;
  }

  /* ── Canvas area ── */
  #graph-container {
    position: fixed;
    left: 280px; top: 0; right: 0; bottom: 0;
    background: var(--bg-primary);
  }

  canvas {
    display: block;
    width: 100%;
    height: 100%;
  }

  /* ── Tooltip ── */
  #tooltip {
    position: fixed;
    display: none;
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 13px;
    color: var(--text-primary);
    max-width: 350px;
    z-index: 200;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
    pointer-events: none;
  }
  #tooltip .tt-label {
    font-weight: 600;
    font-size: 14px;
    margin-bottom: 4px;
  }
  #tooltip .tt-type {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 4px;
    display: inline-block;
    margin-bottom: 6px;
  }
  #tooltip .tt-file {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--text-muted);
    word-break: break-all;
  }
  #tooltip .tt-connections {
    margin-top: 6px;
    font-size: 12px;
    color: var(--text-secondary);
  }

  /* ── Detail panel ── */
  #detail-panel {
    position: fixed;
    right: 0; top: 0; bottom: 0;
    width: 320px;
    background: var(--bg-panel);
    border-left: 1px solid var(--border);
    z-index: 100;
    padding: 16px;
    overflow-y: auto;
    transform: translateX(100%);
    transition: transform 0.3s ease;
  }
  #detail-panel.open { transform: translateX(0); }

  #detail-panel .close-btn {
    position: absolute;
    top: 12px; right: 12px;
    width: 28px; height: 28px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text-secondary);
    cursor: pointer;
    font-size: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  #detail-panel h2 {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 4px;
    padding-right: 36px;
  }

  #detail-panel .detail-type {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 4px;
    display: inline-block;
    margin-bottom: 12px;
  }

  #detail-panel .detail-section {
    margin-top: 12px;
  }
  #detail-panel .detail-section-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 6px;
  }

  .connection-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px;
    margin: 2px 0;
    background: var(--bg-secondary);
    border-radius: 4px;
    font-size: 12px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .connection-item:hover { background: var(--accent-dim); }
  .connection-item .conn-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .connection-item .conn-type {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: var(--text-muted);
    margin-left: auto;
  }

  /* ── Loading ── */
  #loading {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-primary);
    z-index: 1000;
    flex-direction: column;
    gap: 16px;
  }
  #loading.hidden { display: none; }
  .spinner {
    width: 40px; height: 40px;
    border: 3px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Minimap ── */
  #minimap {
    position: fixed;
    bottom: 16px; right: 16px;
    width: 180px; height: 120px;
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    z-index: 50;
    overflow: hidden;
  }
  #minimap canvas { width: 100%; height: 100%; }
</style>
</head>
<body>

<!-- Sidebar -->
<div id="sidebar">
  <h1>Code Graph Viewer <span id="project-name">{{PROJECT_NAME}}</span></h1>

  <div class="upload-zone loaded" id="upload-zone" onclick="document.getElementById('file-input').click()">
    Upload Graph JSON
    <div class="loaded-file" id="loaded-file">Loaded: embedded data</div>
  </div>
  <input type="file" id="file-input" accept=".json" style="display:none">

  <input type="text" id="search" placeholder="Search nodes...">

  <div class="section-header">Node Types</div>
  <div id="node-filters"></div>

  <div class="section-header">Edge Types</div>
  <div id="edge-filters"></div>

  <div class="section-header">Display Options</div>
  <div class="toggle-row">
    Show Labels
    <div class="toggle" id="toggle-labels" onclick="toggleOption('labels')"></div>
  </div>
  <div class="toggle-row">
    Show Arrows
    <div class="toggle active" id="toggle-arrows" onclick="toggleOption('arrows')"></div>
  </div>
  <div class="toggle-row">
    Freeze Layout
    <div class="toggle" id="toggle-freeze" onclick="toggleOption('freeze')"></div>
  </div>
  <div class="toggle-row">
    Highlight Clusters
    <div class="toggle" id="toggle-clusters" onclick="toggleOption('clusters')"></div>
  </div>

  <div class="section-header">Statistics</div>
  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-value" id="stat-nodes">0</div>
      <div class="stat-label">Nodes</div>
    </div>
    <div class="stat-card">
      <div class="stat-value" id="stat-edges">0</div>
      <div class="stat-label">Edges</div>
    </div>
    <div class="stat-card">
      <div class="stat-value" id="stat-visible-nodes">0</div>
      <div class="stat-label">Visible</div>
    </div>
    <div class="stat-card">
      <div class="stat-value" id="stat-components">0</div>
      <div class="stat-label">Clusters</div>
    </div>
  </div>
</div>

<!-- Graph Canvas -->
<div id="graph-container">
  <canvas id="graph-canvas"></canvas>
</div>

<!-- Tooltip -->
<div id="tooltip">
  <div class="tt-label" id="tt-label"></div>
  <div class="tt-type" id="tt-type"></div>
  <div class="tt-file" id="tt-file"></div>
  <div class="tt-connections" id="tt-connections"></div>
</div>

<!-- Detail Panel -->
<div id="detail-panel">
  <button class="close-btn" onclick="closeDetail()">×</button>
  <div id="detail-content"></div>
</div>

<!-- Loading -->
<div id="loading">
  <div class="spinner"></div>
  <div style="color: var(--text-secondary); font-size: 14px;">Initializing graph...</div>
</div>

<!-- Minimap -->
<div id="minimap">
  <canvas id="minimap-canvas"></canvas>
</div>

<script>
// ─── Embedded Graph Data ────────────────────────────────────────────────────
const EMBEDDED_DATA = {{GRAPH_JSON}};

// ─── State ──────────────────────────────────────────────────────────────────
let graphData = null;
let nodes = [];
let edges = [];
let simulation = null;

// Display state
const state = {
  showLabels: false,
  showArrows: true,
  frozen: false,
  showClusters: false,
  nodeFilters: {},
  edgeFilters: {},
  searchQuery: '',
  hoveredNode: null,
  selectedNode: null,
  transform: { x: 0, y: 0, scale: 1 },
  dragging: null,
  panning: false,
  panStart: { x: 0, y: 0 },
};

// Node colors (from data or defaults)
const DEFAULT_NODE_COLORS = {
  endpoint: '#00d4ff', collection: '#ff4466', file: '#44ff88',
  router: '#4488ff', script: '#aa66ff', task: '#ffaa00',
  cache_key: '#ff44ff', service: '#00cc99', utility: '#aabbcc',
  webhook: '#ff6644', event: '#ff88cc', external_api: '#ffdd44',
  middleware: '#6666ff', serializer: '#ffbb44', test: '#888899',
  config: '#aa8866', component: '#44ddaa', template: '#cc88ff',
};

const DEFAULT_EDGE_COLORS = {
  imports: '#556677', db_read: '#00aaff', db_write: '#ff8800',
  endpoint_handler: '#44ff88', api_call: '#ffdd44', cache_read: '#6688aa',
  cache_write: '#8866aa', webhook_receive: '#ff6644', webhook_send: '#ff4422',
  event_publish: '#ff88cc', event_subscribe: '#cc88ff', inherits: '#aaaaff',
  calls: '#778899', middleware_chain: '#6666ff',
};

let nodeColors = {};
let edgeColors = {};

// Canvas
const canvas = document.getElementById('graph-canvas');
const ctx = canvas.getContext('2d');
const mmCanvas = document.getElementById('minimap-canvas');
const mmCtx = mmCanvas.getContext('2d');

// ─── Initialization ─────────────────────────────────────────────────────────

function init() {
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);

  // Canvas events
  canvas.addEventListener('mousemove', onMouseMove);
  canvas.addEventListener('mousedown', onMouseDown);
  canvas.addEventListener('mouseup', onMouseUp);
  canvas.addEventListener('wheel', onWheel, { passive: false });
  canvas.addEventListener('dblclick', onDoubleClick);

  // File upload
  document.getElementById('file-input').addEventListener('change', onFileUpload);

  // Search
  document.getElementById('search').addEventListener('input', (e) => {
    state.searchQuery = e.target.value.toLowerCase();
    render();
  });

  // Load embedded data
  if (EMBEDDED_DATA && EMBEDDED_DATA.nodes) {
    loadGraph(EMBEDDED_DATA);
  }

  document.getElementById('loading').classList.add('hidden');
}

function resizeCanvas() {
  const container = document.getElementById('graph-container');
  const dpr = window.devicePixelRatio || 1;
  canvas.width = container.clientWidth * dpr;
  canvas.height = container.clientHeight * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  mmCanvas.width = 180 * dpr;
  mmCanvas.height = 120 * dpr;
  mmCtx.setTransform(dpr, 0, 0, dpr, 0, 0);

  if (nodes.length > 0) render();
}

// ─── Graph Loading ──────────────────────────────────────────────────────────

function loadGraph(data) {
  graphData = data;
  nodeColors = { ...DEFAULT_NODE_COLORS, ...(data.node_colors || {}) };
  edgeColors = { ...DEFAULT_EDGE_COLORS, ...(data.edge_colors || {}) };

  // Initialize nodes with positions
  const cx = (canvas.width / (window.devicePixelRatio || 1)) / 2;
  const cy = (canvas.height / (window.devicePixelRatio || 1)) / 2;
  const spread = Math.min(cx, cy) * 0.8;

  nodes = data.nodes.map((n, i) => ({
    ...n,
    x: cx + (Math.random() - 0.5) * spread * 2,
    y: cy + (Math.random() - 0.5) * spread * 2,
    vx: 0, vy: 0,
    radius: 4,
    connections: 0,
  }));

  // Build node lookup
  const nodeMap = new Map();
  nodes.forEach(n => nodeMap.set(n.id, n));

  // Process edges
  edges = data.edges.filter(e => nodeMap.has(e.source) && nodeMap.has(e.target))
    .map(e => ({
      ...e,
      sourceNode: nodeMap.get(e.source),
      targetNode: nodeMap.get(e.target),
    }));

  // Count connections for node sizing
  edges.forEach(e => {
    if (e.sourceNode) e.sourceNode.connections++;
    if (e.targetNode) e.targetNode.connections++;
  });

  // Set radius based on connections
  nodes.forEach(n => {
    n.radius = Math.max(3, Math.min(20, 3 + Math.sqrt(n.connections) * 1.5));
  });

  // Initialize filters
  state.nodeFilters = {};
  state.edgeFilters = {};
  if (data.stats) {
    Object.keys(data.stats.node_types || {}).forEach(t => state.nodeFilters[t] = true);
    Object.keys(data.stats.edge_types || {}).forEach(t => state.edgeFilters[t] = true);
  }

  buildFiltersUI();
  updateStats();
  startSimulation();

  // Center view
  state.transform = { x: 0, y: 0, scale: 1 };
}

// ─── Force Simulation ───────────────────────────────────────────────────────

function startSimulation() {
  if (simulation) cancelAnimationFrame(simulation);

  let alpha = 1.0;
  const decay = 0.995;
  const minAlpha = 0.001;

  function tick() {
    if (state.frozen || alpha < minAlpha) {
      render();
      simulation = requestAnimationFrame(tick);
      return;
    }

    // Force calculation
    const n = nodes.length;

    // Repulsion (Barnes-Hut approximation using grid)
    const repulsionStrength = 800;
    const gridSize = 100;
    const grid = new Map();

    nodes.forEach(node => {
      if (!isVisible(node)) return;
      const gx = Math.floor(node.x / gridSize);
      const gy = Math.floor(node.y / gridSize);
      const key = `${gx},${gy}`;
      if (!grid.has(key)) grid.set(key, []);
      grid.get(key).push(node);
    });

    nodes.forEach(node => {
      if (!isVisible(node)) return;
      let fx = 0, fy = 0;
      const gx = Math.floor(node.x / gridSize);
      const gy = Math.floor(node.y / gridSize);

      // Check neighboring cells
      for (let dx = -2; dx <= 2; dx++) {
        for (let dy = -2; dy <= 2; dy++) {
          const key = `${gx + dx},${gy + dy}`;
          const cell = grid.get(key);
          if (!cell) continue;
          for (const other of cell) {
            if (other === node) continue;
            const ddx = node.x - other.x;
            const ddy = node.y - other.y;
            const dist = Math.sqrt(ddx * ddx + ddy * ddy) || 1;
            if (dist < 300) {
              const force = repulsionStrength / (dist * dist);
              fx += (ddx / dist) * force;
              fy += (ddy / dist) * force;
            }
          }
        }
      }

      node.vx += fx * alpha;
      node.vy += fy * alpha;
    });

    // Attraction (spring force on edges)
    const springStrength = 0.02;
    const idealLength = 80;

    edges.forEach(e => {
      if (!e.sourceNode || !e.targetNode) return;
      if (!isVisible(e.sourceNode) || !isVisible(e.targetNode)) return;

      const dx = e.targetNode.x - e.sourceNode.x;
      const dy = e.targetNode.y - e.sourceNode.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = (dist - idealLength) * springStrength * alpha;

      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;

      e.sourceNode.vx += fx;
      e.sourceNode.vy += fy;
      e.targetNode.vx -= fx;
      e.targetNode.vy -= fy;
    });

    // Center gravity
    const centerX = (canvas.width / (window.devicePixelRatio || 1)) / 2;
    const centerY = (canvas.height / (window.devicePixelRatio || 1)) / 2;
    const gravity = 0.01 * alpha;

    nodes.forEach(node => {
      if (!isVisible(node)) return;
      node.vx += (centerX - node.x) * gravity;
      node.vy += (centerY - node.y) * gravity;
    });

    // Update positions
    const damping = 0.85;
    nodes.forEach(node => {
      if (node === state.dragging) return;
      if (!isVisible(node)) return;
      node.vx *= damping;
      node.vy *= damping;
      node.x += node.vx;
      node.y += node.vy;
    });

    alpha *= decay;
    render();
    simulation = requestAnimationFrame(tick);
  }

  simulation = requestAnimationFrame(tick);
}

// ─── Visibility ─────────────────────────────────────────────────────────────

function isVisible(node) {
  if (!state.nodeFilters[node.type]) return false;
  if (state.searchQuery && !node.label.toLowerCase().includes(state.searchQuery) &&
      !(node.file && node.file.toLowerCase().includes(state.searchQuery))) return false;
  return true;
}

function isEdgeVisible(edge) {
  if (!state.edgeFilters[edge.type]) return false;
  if (!edge.sourceNode || !edge.targetNode) return false;
  return isVisible(edge.sourceNode) && isVisible(edge.targetNode);
}

// ─── Rendering ──────────────────────────────────────────────────────────────

function render() {
  const w = canvas.width / (window.devicePixelRatio || 1);
  const h = canvas.height / (window.devicePixelRatio || 1);

  ctx.clearRect(0, 0, w, h);
  ctx.save();
  ctx.translate(state.transform.x, state.transform.y);
  ctx.scale(state.transform.scale, state.transform.scale);

  // Draw edges
  edges.forEach(e => {
    if (!isEdgeVisible(e)) return;
    const color = edgeColors[e.type] || '#334455';
    const isHighlighted = state.hoveredNode &&
      (e.source === state.hoveredNode.id || e.target === state.hoveredNode.id);
    const isSelected = state.selectedNode &&
      (e.source === state.selectedNode.id || e.target === state.selectedNode.id);

    ctx.beginPath();
    ctx.moveTo(e.sourceNode.x, e.sourceNode.y);
    ctx.lineTo(e.targetNode.x, e.targetNode.y);

    if (isHighlighted || isSelected) {
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.globalAlpha = 0.9;
    } else if (state.hoveredNode || state.selectedNode) {
      ctx.strokeStyle = color;
      ctx.lineWidth = 0.3;
      ctx.globalAlpha = 0.1;
    } else {
      ctx.strokeStyle = color;
      ctx.lineWidth = 0.5;
      ctx.globalAlpha = 0.25;
    }
    ctx.stroke();
    ctx.globalAlpha = 1;

    // Arrows
    if (state.showArrows && (isHighlighted || isSelected || (!state.hoveredNode && !state.selectedNode))) {
      const dx = e.targetNode.x - e.sourceNode.x;
      const dy = e.targetNode.y - e.sourceNode.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist > 30) {
        const t = 1 - (e.targetNode.radius + 4) / dist;
        const ax = e.sourceNode.x + dx * t;
        const ay = e.sourceNode.y + dy * t;
        const angle = Math.atan2(dy, dx);
        const arrowSize = isHighlighted || isSelected ? 6 : 3;

        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.lineTo(ax - arrowSize * Math.cos(angle - 0.4), ay - arrowSize * Math.sin(angle - 0.4));
        ctx.lineTo(ax - arrowSize * Math.cos(angle + 0.4), ay - arrowSize * Math.sin(angle + 0.4));
        ctx.closePath();
        ctx.fillStyle = color;
        ctx.globalAlpha = isHighlighted || isSelected ? 0.8 : 0.15;
        ctx.fill();
        ctx.globalAlpha = 1;
      }
    }
  });

  // Draw nodes
  nodes.forEach(n => {
    if (!isVisible(n)) return;
    const color = nodeColors[n.type] || '#aabbcc';
    const isHovered = state.hoveredNode === n;
    const isSelected = state.selectedNode === n;
    const isConnected = (state.hoveredNode || state.selectedNode) &&
      edges.some(e =>
        ((e.source === (state.hoveredNode || state.selectedNode).id && e.target === n.id) ||
         (e.target === (state.hoveredNode || state.selectedNode).id && e.source === n.id)) &&
        isEdgeVisible(e)
      );

    let alpha = 1;
    let radius = n.radius;

    if (state.hoveredNode || state.selectedNode) {
      if (isHovered || isSelected || isConnected) {
        alpha = 1;
        radius = isHovered || isSelected ? n.radius * 1.3 : n.radius;
      } else {
        alpha = 0.1;
      }
    }

    // Glow for hovered/selected
    if (isHovered || isSelected) {
      ctx.beginPath();
      ctx.arc(n.x, n.y, radius + 8, 0, Math.PI * 2);
      const gradient = ctx.createRadialGradient(n.x, n.y, radius, n.x, n.y, radius + 8);
      gradient.addColorStop(0, color + '44');
      gradient.addColorStop(1, color + '00');
      ctx.fillStyle = gradient;
      ctx.fill();
    }

    // Node circle
    ctx.beginPath();
    ctx.arc(n.x, n.y, radius, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.globalAlpha = alpha;
    ctx.fill();

    // Border
    ctx.strokeStyle = isHovered || isSelected ? '#ffffff' : color;
    ctx.lineWidth = isHovered || isSelected ? 2 : 0.5;
    ctx.stroke();
    ctx.globalAlpha = 1;

    // Labels
    if (state.showLabels || isHovered || isSelected || (isConnected && state.transform.scale > 0.8)) {
      ctx.font = `${isHovered || isSelected ? '12' : '10'}px 'JetBrains Mono', monospace`;
      ctx.fillStyle = isHovered || isSelected ? '#ffffff' : '#8892a8';
      ctx.globalAlpha = isHovered || isSelected ? 1 : alpha * 0.7;
      ctx.textAlign = 'center';
      ctx.fillText(n.label, n.x, n.y - radius - 5);
      ctx.globalAlpha = 1;
    }
  });

  ctx.restore();

  // Update minimap
  renderMinimap();
  updateVisibleStats();
}

function renderMinimap() {
  const w = 180;
  const h = 120;
  mmCtx.clearRect(0, 0, w, h);
  mmCtx.fillStyle = '#0f172266';
  mmCtx.fillRect(0, 0, w, h);

  if (nodes.length === 0) return;

  // Find bounds
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  nodes.forEach(n => {
    if (!isVisible(n)) return;
    minX = Math.min(minX, n.x); maxX = Math.max(maxX, n.x);
    minY = Math.min(minY, n.y); maxY = Math.max(maxY, n.y);
  });

  const padding = 20;
  const rangeX = (maxX - minX) || 1;
  const rangeY = (maxY - minY) || 1;
  const scaleX = (w - padding * 2) / rangeX;
  const scaleY = (h - padding * 2) / rangeY;
  const scale = Math.min(scaleX, scaleY);

  nodes.forEach(n => {
    if (!isVisible(n)) return;
    const x = padding + (n.x - minX) * scale;
    const y = padding + (n.y - minY) * scale;
    mmCtx.beginPath();
    mmCtx.arc(x, y, 1.5, 0, Math.PI * 2);
    mmCtx.fillStyle = nodeColors[n.type] || '#aabbcc';
    mmCtx.fill();
  });
}

// ─── Interaction ────────────────────────────────────────────────────────────

function screenToWorld(sx, sy) {
  return {
    x: (sx - state.transform.x) / state.transform.scale,
    y: (sy - state.transform.y) / state.transform.scale,
  };
}

function findNodeAt(wx, wy) {
  // Search in reverse (top nodes drawn last)
  for (let i = nodes.length - 1; i >= 0; i--) {
    const n = nodes[i];
    if (!isVisible(n)) continue;
    const dx = n.x - wx;
    const dy = n.y - wy;
    if (dx * dx + dy * dy < (n.radius + 4) * (n.radius + 4)) return n;
  }
  return null;
}

function onMouseMove(e) {
  const rect = canvas.getBoundingClientRect();
  const sx = e.clientX - rect.left;
  const sy = e.clientY - rect.top;

  if (state.panning) {
    state.transform.x += (e.clientX - state.panStart.x);
    state.transform.y += (e.clientY - state.panStart.y);
    state.panStart = { x: e.clientX, y: e.clientY };
    render();
    return;
  }

  if (state.dragging) {
    const w = screenToWorld(sx, sy);
    state.dragging.x = w.x;
    state.dragging.y = w.y;
    state.dragging.vx = 0;
    state.dragging.vy = 0;
    render();
    return;
  }

  const w = screenToWorld(sx, sy);
  const node = findNodeAt(w.x, w.y);

  if (node !== state.hoveredNode) {
    state.hoveredNode = node;
    canvas.style.cursor = node ? 'pointer' : 'grab';

    if (node) {
      showTooltip(e.clientX, e.clientY, node);
    } else {
      hideTooltip();
    }
    render();
  } else if (node) {
    moveTooltip(e.clientX, e.clientY);
  }
}

function onMouseDown(e) {
  const rect = canvas.getBoundingClientRect();
  const sx = e.clientX - rect.left;
  const sy = e.clientY - rect.top;
  const w = screenToWorld(sx, sy);
  const node = findNodeAt(w.x, w.y);

  if (node) {
    state.dragging = node;
    canvas.style.cursor = 'grabbing';
  } else {
    state.panning = true;
    state.panStart = { x: e.clientX, y: e.clientY };
    canvas.style.cursor = 'grabbing';
  }
}

function onMouseUp(e) {
  if (state.dragging) {
    // If it was a click (not a drag), select the node
    state.dragging = null;
  }
  if (state.panning) {
    state.panning = false;
    canvas.style.cursor = 'grab';
  }
}

function onDoubleClick(e) {
  const rect = canvas.getBoundingClientRect();
  const sx = e.clientX - rect.left;
  const sy = e.clientY - rect.top;
  const w = screenToWorld(sx, sy);
  const node = findNodeAt(w.x, w.y);

  if (node) {
    state.selectedNode = node;
    showDetailPanel(node);
    render();
  } else {
    state.selectedNode = null;
    closeDetail();
    render();
  }
}

function onWheel(e) {
  e.preventDefault();
  const rect = canvas.getBoundingClientRect();
  const sx = e.clientX - rect.left;
  const sy = e.clientY - rect.top;

  const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
  const newScale = state.transform.scale * zoomFactor;

  if (newScale < 0.05 || newScale > 10) return;

  // Zoom towards mouse position
  state.transform.x = sx - (sx - state.transform.x) * zoomFactor;
  state.transform.y = sy - (sy - state.transform.y) * zoomFactor;
  state.transform.scale = newScale;

  render();
}

// ─── Tooltip ────────────────────────────────────────────────────────────────

function showTooltip(x, y, node) {
  const tt = document.getElementById('tooltip');
  const color = nodeColors[node.type] || '#aabbcc';

  document.getElementById('tt-label').textContent = node.label;
  const ttType = document.getElementById('tt-type');
  ttType.textContent = node.type;
  ttType.style.background = color + '22';
  ttType.style.color = color;

  document.getElementById('tt-file').textContent = node.file || '';

  const inEdges = edges.filter(e => e.target === node.id && isEdgeVisible(e));
  const outEdges = edges.filter(e => e.source === node.id && isEdgeVisible(e));
  document.getElementById('tt-connections').textContent =
    `${inEdges.length} incoming · ${outEdges.length} outgoing`;

  tt.style.display = 'block';
  moveTooltip(x, y);
}

function moveTooltip(x, y) {
  const tt = document.getElementById('tooltip');
  const ttRect = tt.getBoundingClientRect();
  const vw = window.innerWidth;
  const vh = window.innerHeight;

  let tx = x + 16;
  let ty = y + 16;

  if (tx + ttRect.width > vw - 10) tx = x - ttRect.width - 16;
  if (ty + ttRect.height > vh - 10) ty = y - ttRect.height - 16;

  tt.style.left = tx + 'px';
  tt.style.top = ty + 'px';
}

function hideTooltip() {
  document.getElementById('tooltip').style.display = 'none';
}

// ─── Detail Panel ───────────────────────────────────────────────────────────

function showDetailPanel(node) {
  const panel = document.getElementById('detail-panel');
  const content = document.getElementById('detail-content');
  const color = nodeColors[node.type] || '#aabbcc';

  const inEdges = edges.filter(e => e.target === node.id && isEdgeVisible(e));
  const outEdges = edges.filter(e => e.source === node.id && isEdgeVisible(e));

  let html = `
    <h2>${node.label}</h2>
    <div class="detail-type" style="background:${color}22;color:${color}">${node.type}</div>
  `;

  if (node.file) {
    html += `<div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text-muted);margin-bottom:12px;word-break:break-all">${node.file}${node.line ? ':' + node.line : ''}</div>`;
  }

  // Metadata
  if (node.metadata && Object.keys(node.metadata).length > 0) {
    html += `<div class="detail-section"><div class="detail-section-title">Metadata</div>`;
    for (const [key, value] of Object.entries(node.metadata)) {
      html += `<div style="font-size:12px;color:var(--text-secondary);padding:2px 0"><span style="color:var(--text-muted)">${key}:</span> ${value}</div>`;
    }
    html += `</div>`;
  }

  // Incoming connections
  if (inEdges.length > 0) {
    html += `<div class="detail-section"><div class="detail-section-title">Incoming (${inEdges.length})</div>`;
    inEdges.forEach(e => {
      const src = nodes.find(n => n.id === e.source);
      if (src) {
        const c = nodeColors[src.type] || '#aabbcc';
        html += `<div class="connection-item" onclick="focusNode('${src.id}')">
          <div class="conn-dot" style="background:${c}"></div>
          ${src.label}
          <span class="conn-type">${e.type}</span>
        </div>`;
      }
    });
    html += `</div>`;
  }

  // Outgoing connections
  if (outEdges.length > 0) {
    html += `<div class="detail-section"><div class="detail-section-title">Outgoing (${outEdges.length})</div>`;
    outEdges.forEach(e => {
      const tgt = nodes.find(n => n.id === e.target);
      if (tgt) {
        const c = nodeColors[tgt.type] || '#aabbcc';
        html += `<div class="connection-item" onclick="focusNode('${tgt.id}')">
          <div class="conn-dot" style="background:${c}"></div>
          ${tgt.label}
          <span class="conn-type">${e.type}</span>
        </div>`;
      }
    });
    html += `</div>`;
  }

  content.innerHTML = html;
  panel.classList.add('open');
}

function closeDetail() {
  document.getElementById('detail-panel').classList.remove('open');
  state.selectedNode = null;
  render();
}

function focusNode(nodeId) {
  const node = nodes.find(n => n.id === nodeId);
  if (!node) return;

  state.selectedNode = node;
  showDetailPanel(node);

  // Center on node
  const containerW = canvas.width / (window.devicePixelRatio || 1);
  const containerH = canvas.height / (window.devicePixelRatio || 1);
  state.transform.x = containerW / 2 - node.x * state.transform.scale;
  state.transform.y = containerH / 2 - node.y * state.transform.scale;

  render();
}

// ─── UI Controls ────────────────────────────────────────────────────────────

function buildFiltersUI() {
  const nodeContainer = document.getElementById('node-filters');
  const edgeContainer = document.getElementById('edge-filters');

  nodeContainer.innerHTML = '';
  edgeContainer.innerHTML = '';

  if (!graphData || !graphData.stats) return;

  // Node type filters
  const nodeTypes = Object.entries(graphData.stats.node_types || {})
    .sort((a, b) => b[1] - a[1]);

  nodeTypes.forEach(([type, count]) => {
    const color = nodeColors[type] || '#aabbcc';
    const item = document.createElement('label');
    item.className = 'filter-item';
    item.innerHTML = `
      <input type="checkbox" checked onchange="toggleNodeType('${type}', this.checked)">
      <div class="filter-dot" style="background:${color}"></div>
      <span class="filter-label">${type}</span>
      <span class="filter-count">${count}</span>
    `;
    nodeContainer.appendChild(item);
  });

  // Edge type filters
  const edgeTypes = Object.entries(graphData.stats.edge_types || {})
    .sort((a, b) => b[1] - a[1]);

  edgeTypes.forEach(([type, count]) => {
    const color = edgeColors[type] || '#556677';
    const item = document.createElement('label');
    item.className = 'filter-item';
    item.innerHTML = `
      <input type="checkbox" checked onchange="toggleEdgeType('${type}', this.checked)">
      <div class="filter-dot" style="background:${color}"></div>
      <span class="filter-label">${type}</span>
      <span class="filter-count">${count}</span>
    `;
    edgeContainer.appendChild(item);
  });
}

function toggleNodeType(type, checked) {
  state.nodeFilters[type] = checked;
  render();
  updateVisibleStats();
}

function toggleEdgeType(type, checked) {
  state.edgeFilters[type] = checked;
  render();
}

function toggleOption(option) {
  const el = document.getElementById(`toggle-${option}`);
  switch (option) {
    case 'labels':
      state.showLabels = !state.showLabels;
      break;
    case 'arrows':
      state.showArrows = !state.showArrows;
      break;
    case 'freeze':
      state.frozen = !state.frozen;
      break;
    case 'clusters':
      state.showClusters = !state.showClusters;
      break;
  }
  el.classList.toggle('active');
  render();
}

function updateStats() {
  if (!graphData || !graphData.stats) return;
  document.getElementById('stat-nodes').textContent = graphData.stats.total_nodes;
  document.getElementById('stat-edges').textContent = graphData.stats.total_edges;
  updateVisibleStats();
}

function updateVisibleStats() {
  const visibleNodes = nodes.filter(isVisible).length;
  document.getElementById('stat-visible-nodes').textContent = visibleNodes;

  // Count connected components (simplified)
  const components = countComponents();
  document.getElementById('stat-components').textContent = components;
}

function countComponents() {
  const visited = new Set();
  const visibleSet = new Set(nodes.filter(isVisible).map(n => n.id));
  let count = 0;

  function bfs(startId) {
    const queue = [startId];
    visited.add(startId);
    while (queue.length > 0) {
      const id = queue.shift();
      edges.forEach(e => {
        if (!isEdgeVisible(e)) return;
        let neighbor = null;
        if (e.source === id && visibleSet.has(e.target)) neighbor = e.target;
        if (e.target === id && visibleSet.has(e.source)) neighbor = e.source;
        if (neighbor && !visited.has(neighbor)) {
          visited.add(neighbor);
          queue.push(neighbor);
        }
      });
    }
  }

  visibleSet.forEach(id => {
    if (!visited.has(id)) {
      bfs(id);
      count++;
    }
  });

  return count;
}

// ─── File Upload ────────────────────────────────────────────────────────────

function onFileUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (event) => {
    try {
      const data = JSON.parse(event.target.result);
      loadGraph(data);
      document.getElementById('loaded-file').textContent = 'Loaded: ' + file.name;
      document.getElementById('project-name').textContent = data.project || file.name;
    } catch (err) {
      alert('Error parsing JSON: ' + err.message);
    }
  };
  reader.readAsText(file);
}

// ─── Start ──────────────────────────────────────────────────────────────────
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
        print(f"❌ Error: {graph_path} not found")
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

    print(f"✅ Viewer saved to: {output_path}")
    print(f"   Open in browser to explore the graph interactively.")


if __name__ == "__main__":
    main()
