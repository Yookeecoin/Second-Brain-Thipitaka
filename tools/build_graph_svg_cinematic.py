#!/usr/bin/env python3
"""
Cinematic / Morning Wealth style graph.
Pure black bg, peach/coral nodes with glow, thin lines, one 'hero' node highlighted.
Output: ~/second-brain/wiki/_graph_cinematic.svg
"""
import math, random, re, urllib.parse
from pathlib import Path

WIKI = Path(__file__).resolve().parent.parent / "wiki"
OUT = WIKI / "_graph_cinematic.svg"
VAULT_NAME = "second-brain"
HERO = "buddha"   # node to highlight as the bright center star

CATS = ["suttas", "persons", "places", "dhamma", "sources"]
# Cinematic peach palette — subtle variation, all warm
PEACH = "#E8A998"
PEACH_DIM = "#A8786A"
HERO_COLOR = "#FFE5DA"

WIKILINK = re.compile(r"\[\[([^\]\|#]+?)(?:#[^\]\|]+)?(?:\|[^\]]+)?\]\]")

def key_of(name):
    return name.split(" (")[0].strip()

# --- scan ---
nodes, files = {}, {}
for cat in CATS:
    for f in (WIKI / cat).glob("*.md"):
        stem = f.stem
        k = key_of(stem)
        label = stem.split("(")[-1].rstrip(")").strip() if "(" in stem else stem
        href = (
            f"obsidian://open?vault={urllib.parse.quote(VAULT_NAME)}"
            f"&amp;file={urllib.parse.quote(f'wiki/{cat}/{stem}.md')}"
        )
        nodes[k] = {"label": label, "cat": cat, "href": href}
        files[k] = f

edges = set()
for k, f in files.items():
    for m in WIKILINK.finditer(f.read_text(encoding="utf-8")):
        tgt = key_of(m.group(1))
        if tgt in nodes and tgt != k:
            edges.add(tuple(sorted([k, tgt])))

degree = {k: 0 for k in nodes}
for a, b in edges:
    degree[a] += 1; degree[b] += 1

# --- layout (FR) ---
random.seed(7)
W = H = 1600
keys = list(nodes); N = len(keys)
idx = {k: i for i, k in enumerate(keys)}
pos = []
for k in keys:
    ci = CATS.index(nodes[k]["cat"])
    a = ci/len(CATS)*2*math.pi + random.uniform(0, 2*math.pi/len(CATS))
    r = random.uniform(250, 600)
    pos.append([W/2 + r*math.cos(a), H/2 + r*math.sin(a)])
if HERO in idx:
    pos[idx[HERO]] = [W*0.62, H*0.42]   # off-center, top-right-ish like reference

area = W*H
k_const = math.sqrt(area/N)*0.7
iters = 140
t_init = W/5
for it in range(iters):
    t = t_init * (1 - it/iters)
    disp = [[0.0,0.0] for _ in range(N)]
    for i in range(N):
        xi, yi = pos[i]
        for j in range(i+1, N):
            dx = xi - pos[j][0]; dy = yi - pos[j][1]
            d2 = dx*dx + dy*dy
            if d2 < 0.01:
                dx, dy = random.uniform(-1,1), random.uniform(-1,1)
                d2 = dx*dx + dy*dy + 0.01
            d = math.sqrt(d2)
            f = k_const*k_const/d
            ux, uy = dx/d, dy/d
            disp[i][0] += ux*f; disp[i][1] += uy*f
            disp[j][0] -= ux*f; disp[j][1] -= uy*f
    for a, b in edges:
        i, j = idx[a], idx[b]
        dx = pos[i][0]-pos[j][0]; dy = pos[i][1]-pos[j][1]
        d = math.sqrt(dx*dx+dy*dy)+0.01
        f = d*d/k_const
        ux, uy = dx/d, dy/d
        disp[i][0] -= ux*f; disp[i][1] -= uy*f
        disp[j][0] += ux*f; disp[j][1] += uy*f
    for i in range(N):
        if keys[i] == HERO: continue
        dx, dy = disp[i]
        d = math.sqrt(dx*dx+dy*dy)+0.01
        m = min(d, t)
        pos[i][0] += dx/d*m; pos[i][1] += dy/d*m
        pos[i][0] = max(60, min(W-60, pos[i][0]))
        pos[i][1] = max(60, min(H-60, pos[i][1]))

# --- emit SVG ---
def esc(s):
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

p = [
  f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
  f'style="background:#000;font-family:\'IBM Plex Sans Thai\',\'Sukhumvit Set\',sans-serif">',
  # filters: glow for nodes, soft glow for hero
  '<defs>',
  '  <filter id="glow" x="-200%" y="-200%" width="500%" height="500%">'
  '    <feGaussianBlur stdDeviation="3" result="b"/>'
  '    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
  '  </filter>',
  '  <filter id="hero" x="-300%" y="-300%" width="700%" height="700%">'
  '    <feGaussianBlur stdDeviation="14" result="b1"/>'
  '    <feGaussianBlur stdDeviation="40" result="b2"/>'
  '    <feMerge>'
  '      <feMergeNode in="b2"/><feMergeNode in="b1"/><feMergeNode in="SourceGraphic"/>'
  '    </feMerge>'
  '  </filter>',
  '  <radialGradient id="vignette" cx="50%" cy="50%">'
  '    <stop offset="0%" stop-color="#0a0a0a"/>'
  '    <stop offset="100%" stop-color="#000"/>'
  '  </radialGradient>',
  '</defs>',
  f'<rect width="{W}" height="{H}" fill="url(#vignette)"/>',
]

# edges — thin and faint
for a, b in edges:
    i, j = idx[a], idx[b]
    x1, y1 = pos[i]; x2, y2 = pos[j]
    # if either endpoint is hero -> brighter line
    is_hero = (keys[i] == HERO or keys[j] == HERO)
    stroke = PEACH if is_hero else PEACH_DIM
    op = 0.55 if is_hero else 0.18
    sw = 0.7 if is_hero else 0.4
    p.append(
      f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
      f'stroke="{stroke}" stroke-width="{sw}" opacity="{op}"/>'
    )

# nodes — all same warm palette, varying size by degree
max_deg = max(degree.values()) or 1
for k in keys:
    i = idx[k]; x, y = pos[i]
    deg = degree[k]
    if k == HERO:
        # big bright halo
        p.append(
          f'<a href="{nodes[k]["href"]}" target="_blank">'
          f'<circle cx="{x:.1f}" cy="{y:.1f}" r="22" fill="{HERO_COLOR}" '
          f'filter="url(#hero)" opacity="0.95">'
          f'<title>{esc(nodes[k]["label"])} ({deg} links)</title>'
          f'</circle></a>'
        )
        continue
    r = 2.5 + math.sqrt(deg) * 1.6
    # near-hero nodes get a touch brighter
    op = 0.95 if deg > max_deg*0.4 else 0.7
    p.append(
      f'<a href="{nodes[k]["href"]}" target="_blank">'
      f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{PEACH}" '
      f'filter="url(#glow)" opacity="{op}">'
      f'<title>{esc(nodes[k]["label"])} ({nodes[k]["cat"]}, {deg} links)</title>'
      f'</circle></a>'
    )

# label only HERO + 1-line caption
if HERO in idx:
    hx, hy = pos[idx[HERO]]
    p.append(
      f'<text x="{hx+30:.1f}" y="{hy+8:.1f}" font-size="26" fill="{HERO_COLOR}" '
      f'opacity="0.95" style="paint-order:stroke;stroke:#000;stroke-width:3">'
      f'{esc(nodes[HERO]["label"])}</text>'
    )

# minimal corner caption (like 'MORNING WEALTH' in ref)
p.append(
  f'<text x="{W-50}" y="60" text-anchor="end" font-size="22" '
  f'fill="{PEACH}" opacity="0.9" letter-spacing="3" font-weight="600">SECOND BRAIN</text>'
)
p.append(
  f'<text x="{W-50}" y="88" text-anchor="end" font-size="14" '
  f'fill="{PEACH_DIM}" opacity="0.75" letter-spacing="2">TIPITAKA WIKI</text>'
)
p.append(
  f'<text x="50" y="{H-40}" font-size="13" fill="{PEACH_DIM}" '
  f'opacity="0.6">{N} nodes · {len(edges)} edges</text>'
)
p.append('</svg>')
OUT.write_text("\n".join(p), encoding="utf-8")
print(f"wrote {OUT} ({N} nodes, {len(edges)} edges)")
