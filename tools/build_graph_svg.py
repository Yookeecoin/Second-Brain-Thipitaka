#!/usr/bin/env python3
"""
Scan ~/second-brain/wiki/ and render an SVG graph of all pages + wikilinks.
Output: ~/second-brain/wiki/_graph.svg

Usage: python3 build_graph_svg.py
Re-run anytime to refresh after adding pages.
"""
import math
import random
import re
import urllib.parse
from pathlib import Path

VAULT_NAME = "second-brain"  # Obsidian vault folder name

WIKI = Path(__file__).resolve().parent.parent / "wiki"
OUT = WIKI / "_graph.svg"

CATS = ["suttas", "persons", "places", "dhamma", "sources"]
COLORS = {
    "suttas":  "#58F1F9",   # cyan
    "dhamma":  "#FCFF2E",   # yellow
    "persons": "#5FFF42",   # green
    "places":  "#F2AA73",   # orange
    "sources": "#936BFF",   # violet
}

WIKILINK = re.compile(r"\[\[([^\]\|#]+?)(?:#[^\]\|]+)?(?:\|[^\]]+)?\]\]")

def key_of(name):
    """'brahmajala-sutta-page (พรหมชาลสูตร)' -> 'brahmajala-sutta-page'"""
    return name.split(" (")[0].strip()

# --- 1. Scan files ---
nodes = {}   # key -> {label, cat, href}
files = {}   # key -> file path

for cat in CATS:
    for f in (WIKI / cat).glob("*.md"):
        stem = f.stem
        k = key_of(stem)
        label = stem.split("(")[-1].rstrip(")").strip() if "(" in stem else stem
        # obsidian:// URI: clicking the node opens the file in Obsidian
        file_path = f"wiki/{cat}/{stem}.md"
        # &amp; needed for SVG/XML strictness
        href = (
            f"obsidian://open?vault={urllib.parse.quote(VAULT_NAME)}"
            f"&amp;file={urllib.parse.quote(file_path)}"
        )
        nodes[k] = {"label": label, "cat": cat, "href": href}
        files[k] = f

# --- 2. Parse links ---
edges = set()
for k, f in files.items():
    for m in WIKILINK.finditer(f.read_text(encoding="utf-8")):
        tgt = key_of(m.group(1))
        if tgt in nodes and tgt != k:
            edges.add(tuple(sorted([k, tgt])))

degree = {k: 0 for k in nodes}
for a, b in edges:
    degree[a] += 1
    degree[b] += 1

# --- 3. Force-directed layout (Fruchterman-Reingold) ---
random.seed(42)
W = H = 1400
keys = list(nodes)
N = len(keys)
idx = {k: i for i, k in enumerate(keys)}

# initial positions: scattered by category in arcs
pos = []
for k in keys:
    cat_i = CATS.index(nodes[k]["cat"])
    a = (cat_i / len(CATS)) * 2 * math.pi + random.uniform(0, 2 * math.pi / len(CATS))
    r = random.uniform(200, 500)
    pos.append([W/2 + r * math.cos(a), H/2 + r * math.sin(a)])

# pin pระพุทธเจ้า to center if exists
if "buddha" in idx:
    pos[idx["buddha"]] = [W/2, H/2]

area = W * H
k_const = math.sqrt(area / N) * 0.6
iters = 120
t_init = W / 6

for it in range(iters):
    t = t_init * (1 - it / iters)
    disp = [[0.0, 0.0] for _ in range(N)]
    # repulsive: O(N^2)
    for i in range(N):
        xi, yi = pos[i]
        for j in range(i+1, N):
            dx = xi - pos[j][0]
            dy = yi - pos[j][1]
            d2 = dx*dx + dy*dy
            if d2 < 0.01:
                dx, dy = random.uniform(-1, 1), random.uniform(-1, 1)
                d2 = dx*dx + dy*dy + 0.01
            d = math.sqrt(d2)
            f = k_const * k_const / d
            ux, uy = dx/d, dy/d
            disp[i][0] += ux * f
            disp[i][1] += uy * f
            disp[j][0] -= ux * f
            disp[j][1] -= uy * f
    # attractive
    for a, b in edges:
        i, j = idx[a], idx[b]
        dx = pos[i][0] - pos[j][0]
        dy = pos[i][1] - pos[j][1]
        d = math.sqrt(dx*dx + dy*dy) + 0.01
        f = d * d / k_const
        ux, uy = dx/d, dy/d
        disp[i][0] -= ux * f
        disp[i][1] -= uy * f
        disp[j][0] += ux * f
        disp[j][1] += uy * f
    # apply
    for i in range(N):
        if keys[i] == "buddha":  # pin
            continue
        dx, dy = disp[i]
        d = math.sqrt(dx*dx + dy*dy) + 0.01
        m = min(d, t)
        pos[i][0] += dx/d * m
        pos[i][1] += dy/d * m
        # keep within canvas
        pos[i][0] = max(40, min(W - 40, pos[i][0]))
        pos[i][1] = max(40, min(H - 40, pos[i][1]))

# --- 4. Emit SVG ---
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
    f'style="background:#0a0a1a;font-family:sans-serif">',
    # subtle starfield
    '<defs><radialGradient id="g" cx="50%" cy="50%"><stop offset="0%" stop-color="#1a1a3a"/>'
    '<stop offset="100%" stop-color="#0a0a1a"/></radialGradient></defs>',
    f'<rect width="{W}" height="{H}" fill="url(#g)"/>',
]

# edges first (so nodes on top)
for a, b in edges:
    i, j = idx[a], idx[b]
    x1, y1 = pos[i]; x2, y2 = pos[j]
    parts.append(
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="#4488cc" stroke-width="0.5" opacity="0.25"/>'
    )

# nodes
max_deg = max(degree.values()) if degree else 1
for k in keys:
    i = idx[k]
    x, y = pos[i]
    cat = nodes[k]["cat"]
    color = COLORS[cat]
    deg = degree[k]
    r = 3 + math.sqrt(deg) * 1.8   # 3..~15
    if k == "buddha":
        r = max(r, 14)
    parts.append(
        f'<a href="{nodes[k]["href"]}" target="_blank">'
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{color}" '
        f'stroke="#000" stroke-width="0.4" opacity="0.92">'
        f'<title>{esc(nodes[k]["label"])} ({cat}, {deg} links)</title>'
        f'</circle></a>'
    )

# labels: only for high-degree nodes to keep readable
label_threshold = sorted(degree.values(), reverse=True)[min(40, N-1)]
for k in keys:
    if degree[k] < label_threshold and k != "buddha":
        continue
    i = idx[k]
    x, y = pos[i]
    cat = nodes[k]["cat"]
    parts.append(
        f'<a href="{nodes[k]["href"]}" target="_blank">'
        f'<text x="{x:.1f}" y="{y-12:.1f}" text-anchor="middle" '
        f'font-size="11" fill="{COLORS[cat]}" opacity="0.95" '
        f'style="paint-order:stroke;stroke:#000;stroke-width:2.5;cursor:pointer">{esc(nodes[k]["label"])}</text>'
        f'</a>'
    )

# legend
legend_y = H - 40
for i, cat in enumerate(CATS):
    x = 60 + i * 240
    cnt = sum(1 for n in nodes.values() if n["cat"] == cat)
    parts.append(
        f'<circle cx="{x}" cy="{legend_y}" r="7" fill="{COLORS[cat]}"/>'
        f'<text x="{x+15}" y="{legend_y+5}" font-size="14" fill="#ddd">{cat} ({cnt})</text>'
    )
parts.append(
    f'<text x="{W-20}" y="{legend_y+5}" text-anchor="end" font-size="13" fill="#888">'
    f'{N} nodes · {len(edges)} edges</text>'
)

parts.append("</svg>")
OUT.write_text("\n".join(parts), encoding="utf-8")
print(f"wrote {OUT} ({N} nodes, {len(edges)} edges)")
