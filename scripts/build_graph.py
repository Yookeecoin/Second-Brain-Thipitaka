#!/usr/bin/env python3
"""สแกน wiki/*.md (frontmatter + [[wikilink]]) แล้วสร้าง graph/index.html แบบ interactive
รัน: python3 scripts/build_graph.py
"""
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "wiki"
OUT_DIR = ROOT / "graph"

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)

TYPE_COLORS = {
    "movement": "#e07a5f",
    "artist": "#3d5a80",
    "artwork": "#81b29a",
    "place": "#f2cc8f",
    "term": "#9d8189",
    "source": "#6c757d",
    "sutta": "#3d5a80",
    "person": "#e07a5f",
    "dhamma": "#81b29a",
    "redlink": "#444444",
}
DEFAULT_COLOR = "#8888aa"


def parse_file(path: Path):
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    fm_raw, body = m.group(1), m.group(2)
    try:
        fm = yaml.safe_load(fm_raw) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(fm, dict) or "type" not in fm:
        return None
    links = sorted(set(WIKILINK_RE.findall(body)))
    return fm, links


def main():
    nodes = {}
    edges = []
    seen_edges = set()

    md_files = sorted(WIKI.rglob("*.md"))
    for path in md_files:
        parsed = parse_file(path)
        if not parsed:
            continue
        fm, links = parsed
        node_id = path.stem
        folder = path.parent.relative_to(WIKI).as_posix()
        if folder == ".":
            folder = "root"
        title = str(fm.get("title", node_id))
        node_type = str(fm.get("type", "unknown"))
        tags = fm.get("tags") or []
        if not isinstance(tags, list):
            tags = [str(tags)]
        nodes[node_id] = {
            "id": node_id,
            "label": title,
            "type": node_type,
            "folder": folder,
            "tags": tags,
            "redlink": False,
        }
        for target in links:
            target = target.strip()
            if not target or target == node_id:
                continue
            key = (node_id, target)
            if key not in seen_edges:
                seen_edges.add(key)
                edges.append({"from": node_id, "to": target})

    # add ghost nodes for redlinks (wikilinks pointing to pages that don't exist yet)
    for e in edges:
        for side in ("from", "to"):
            tid = e[side]
            if tid not in nodes:
                nodes[tid] = {
                    "id": tid,
                    "label": tid,
                    "type": "redlink",
                    "folder": "redlink",
                    "tags": [],
                    "redlink": True,
                }

    graph = {"nodes": list(nodes.values()), "edges": edges}

    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "data.json").write_text(
        json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    types_present = sorted({n["type"] for n in graph["nodes"]})
    html = render_html(graph, types_present)
    (OUT_DIR / "index.html").write_text(html, encoding="utf-8")

    print(f"nodes: {len(graph['nodes'])}  edges: {len(graph['edges'])}")
    print(f"types: {types_present}")
    print(f"wrote {OUT_DIR / 'index.html'}")


def render_html(graph, types_present):
    data_json = json.dumps(graph, ensure_ascii=False)
    colors_json = json.dumps(TYPE_COLORS, ensure_ascii=False)
    legend_items = "\n".join(
        f'<label class="legend-item"><input type="checkbox" checked data-type="{t}">'
        f'<span class="dot" style="background:{TYPE_COLORS.get(t, DEFAULT_COLOR)}"></span>{t}</label>'
        for t in types_present
    )
    return f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<title>Wiki Graph Explorer</title>
<script src="https://unpkg.com/vis-network@9/standalone/umd/vis-network.min.js"></script>
<style>
  html, body {{ margin: 0; height: 100%; font-family: -apple-system, "Noto Sans Thai", sans-serif; background: #1b1b1f; color: #eee; }}
  #app {{ display: flex; height: 100%; }}
  #sidebar {{ width: 260px; padding: 14px; box-sizing: border-box; background: #24242b; overflow-y: auto; border-right: 1px solid #333; }}
  #network {{ flex: 1; }}
  h1 {{ font-size: 15px; margin: 0 0 10px; }}
  #search {{ width: 100%; padding: 6px 8px; box-sizing: border-box; border-radius: 6px; border: 1px solid #444; background: #1b1b1f; color: #eee; margin-bottom: 12px; }}
  .legend-item {{ display: flex; align-items: center; gap: 6px; font-size: 13px; margin-bottom: 6px; cursor: pointer; }}
  .dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
  #info {{ margin-top: 16px; padding-top: 12px; border-top: 1px solid #333; font-size: 13px; line-height: 1.5; }}
  #info a {{ color: #9db4ff; }}
  #reset {{ margin-top: 10px; width: 100%; padding: 6px; border-radius: 6px; border: 1px solid #444; background: #2e2e38; color: #eee; cursor: pointer; }}
  #stats {{ font-size: 11px; color: #888; margin-top: 10px; }}
</style>
</head>
<body>
<div id="app">
  <div id="sidebar">
    <h1>Wiki Graph Explorer</h1>
    <input id="search" placeholder="ค้นหา...">
    <div id="legend">{legend_items}</div>
    <button id="reset">รีเซ็ต / แสดงทั้งหมด</button>
    <div id="info">คลิกที่ node เพื่อดูรายละเอียดและโฟกัสเครือข่ายของมัน</div>
    <div id="stats"></div>
  </div>
  <div id="network"></div>
</div>
<script>
const graph = {data_json};
const TYPE_COLORS = {colors_json};
const DEFAULT_COLOR = "{DEFAULT_COLOR}";

const degree = {{}};
graph.edges.forEach(e => {{
  degree[e.from] = (degree[e.from]||0)+1;
  degree[e.to] = (degree[e.to]||0)+1;
}});

const nodesDataset = new vis.DataSet(graph.nodes.map(n => ({{
  id: n.id,
  label: n.label,
  group: n.type,
  shape: n.redlink ? "dot" : "dot",
  size: n.redlink ? 6 : Math.min(10 + (degree[n.id]||0) * 2, 40),
  color: {{
    background: TYPE_COLORS[n.type] || DEFAULT_COLOR,
    border: n.redlink ? "#ff5555" : "#111",
  }},
  borderWidth: n.redlink ? 2 : 1,
  shapeProperties: {{ borderDashes: n.redlink ? [4,3] : false }},
  font: {{ color: "#eee", size: n.redlink ? 10 : 12 }},
  title: n.type + (n.tags && n.tags.length ? " · " + n.tags.join(", ") : ""),
  raw: n,
}})));
const edgesDataset = new vis.DataSet(graph.edges.map((e,i) => ({{
  id: i, from: e.from, to: e.to, arrows: "to", color: {{ color: "#3a3a44", opacity: 0.5 }}, width: 1,
}})));

const container = document.getElementById("network");
const bigGraph = graph.nodes.length > 300;
const network = new vis.Network(container, {{ nodes: nodesDataset, edges: edgesDataset }}, {{
  layout: {{ improvedLayout: false }},
  physics: {{
    stabilization: {{ iterations: bigGraph ? 120 : 200, updateInterval: 25 }},
    barnesHut: {{ gravitationalConstant: -12000, springLength: 120 }},
  }},
  edges: {{ smooth: false }},
  interaction: {{ hover: true }},
}});
network.once("stabilizationIterationsDone", () => network.setOptions({{ physics: false }}));

document.getElementById("stats").textContent = graph.nodes.length + " nodes, " + graph.edges.length + " edges";

function neighborsOf(id) {{
  const s = new Set([id]);
  graph.edges.forEach(e => {{
    if (e.from === id) s.add(e.to);
    if (e.to === id) s.add(e.from);
  }});
  return s;
}}

function focusNode(id) {{
  const keep = neighborsOf(id);
  nodesDataset.update(nodesDataset.getIds().map(nid => ({{ id: nid, opacity: keep.has(nid) ? 1 : 0.12 }})));
  edgesDataset.update(edgesDataset.getIds().map(eid => {{
    const e = edgesDataset.get(eid);
    const on = keep.has(e.from) && keep.has(e.to);
    return {{ id: eid, color: {{ color: on ? "#7fa8ff" : "#3a3a44", opacity: on ? 0.9 : 0.08 }}, width: on ? 2 : 1 }};
  }}));
  const n = nodesDataset.get(id);
  const links = [...new Set(
    graph.edges.filter(e => e.from === id || e.to === id)
      .map(e => e.from === id ? e.to : e.from)
  )];
  document.getElementById("info").innerHTML =
    "<b>" + n.label + "</b><br>ประเภท: " + n.raw.type +
    (n.raw.tags.length ? "<br>tags: " + n.raw.tags.join(", ") : "") +
    "<br><br>เชื่อมกับ (" + links.length + "):<br>" +
    links.map(l => "· " + (nodesDataset.get(l) ? nodesDataset.get(l).label : l)).join("<br>");
}}

function resetView() {{
  nodesDataset.update(nodesDataset.getIds().map(nid => ({{ id: nid, opacity: 1 }})));
  edgesDataset.update(edgesDataset.getIds().map(eid => ({{ id: eid, color: {{ color: "#3a3a44", opacity: 0.5 }}, width: 1 }})));
  document.getElementById("info").textContent = "คลิกที่ node เพื่อดูรายละเอียดและโฟกัสเครือข่ายของมัน";
}}

network.on("click", params => {{
  if (params.nodes.length) focusNode(params.nodes[0]);
  else resetView();
}});

document.getElementById("reset").addEventListener("click", resetView);

document.getElementById("search").addEventListener("input", e => {{
  const q = e.target.value.trim().toLowerCase();
  if (!q) {{ resetView(); return; }}
  const matchSet = new Set(graph.nodes.filter(n => n.label.toLowerCase().includes(q)).map(n => n.id));
  const matches = [...matchSet];
  nodesDataset.update(nodesDataset.getIds().map(nid => ({{ id: nid, opacity: matchSet.has(nid) ? 1 : 0.08 }})));
  if (matches.length === 1) {{
    focusNode(matches[0]);
    network.focus(matches[0], {{ scale: 1.2, animation: {{ duration: 300 }} }});
  }} else if (matches.length > 1 && matches.length <= 40) {{
    network.fit({{ nodes: matches, animation: {{ duration: 300 }} }});
  }}
}});

document.querySelectorAll('#legend input[type=checkbox]').forEach(cb => {{
  cb.addEventListener('change', () => {{
    const activeTypes = new Set(
      Array.from(document.querySelectorAll('#legend input:checked')).map(c => c.dataset.type)
    );
    const visibleIds = new Set(graph.nodes.filter(n => activeTypes.has(n.type)).map(n => n.id));
    nodesDataset.update(nodesDataset.getIds().map(nid => ({{ id: nid, hidden: !visibleIds.has(nid) }})));
    edgesDataset.update(edgesDataset.getIds().map(eid => {{
      const e = edgesDataset.get(eid);
      return {{ id: eid, hidden: !(visibleIds.has(e.from) && visibleIds.has(e.to)) }};
    }}));
  }});
}});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    sys.exit(main())
