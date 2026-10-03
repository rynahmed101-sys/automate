"""
HTMLGraphVisualizer: Produces an interactive, standalone HTML derivation graph
with vis.js, showing nodes, edges, verification statuses, assumptions, and proof certificates.
"""

import json
from pathlib import Path
from typing import Dict, Any, Union
from automate.core.graph import DerivationGraph
from automate.core.status import VerificationStatus


STATUS_COLORS = {
    VerificationStatus.FORMALLY_PROVED: {"bg": "#10b981", "border": "#059669", "font": "#ffffff"},
    VerificationStatus.SYMBOLIC_CHECKED: {"bg": "#3b82f6", "border": "#2563eb", "font": "#ffffff"},
    VerificationStatus.NUMERICALLY_CHECKED: {"bg": "#06b6d4", "border": "#0891b2", "font": "#ffffff"},
    VerificationStatus.STATISTICALLY_CHECKED: {"bg": "#8b5cf6", "border": "#7c3aed", "font": "#ffffff"},
    VerificationStatus.CONDITIONAL: {"bg": "#f59e0b", "border": "#d97706", "font": "#ffffff"},
    VerificationStatus.PARSED: {"bg": "#9ca3af", "border": "#6b7280", "font": "#111827"},
    VerificationStatus.UNVERIFIED: {"bg": "#6b7280", "border": "#4b5563", "font": "#ffffff"},
    VerificationStatus.FAILED: {"bg": "#ef4444", "border": "#dc2626", "font": "#ffffff"},
}


def generate_interactive_html(graph: DerivationGraph, output_path: Union[str, Path]) -> str:
    """
    Generates a standalone, beautiful HTML file visualizing the DerivationGraph.
    """
    nodes_data = []
    for nid, node in graph.nodes.items():
        inherited_asms = list(graph.compute_inherited_assumptions(nid))
        color = STATUS_COLORS.get(node.status, {"bg": "#6b7280", "border": "#4b5563", "font": "#ffffff"})

        label = f"[{node.id}]\n{node.expression.raw_str}"
        if node.expression.dimension:
            label += f"\nDim: {node.expression.dimension}"

        nodes_data.append({
            "id": nid,
            "label": label,
            "title": f"Expression: {node.expression.raw_str}<br>Status: {node.status.value}<br>Domain: {node.domain}<br>Assumptions: {', '.join(inherited_asms) or 'None'}",
            "color": {
                "background": color["bg"],
                "border": color["border"],
                "highlight": {"background": color["bg"], "border": "#ffffff"}
            },
            "font": {"color": color["font"], "size": 13, "face": "monospace"},
            "shape": "box",
            "margin": 10,
            "raw_str": node.expression.raw_str,
            "latex": node.representations.get("latex", ""),
            "domain": node.domain,
            "status": node.status.value,
            "assumptions": inherited_asms,
            "source": node.source
        })

    edges_data = []
    for eid, edge in graph.edges.items():
        color = STATUS_COLORS.get(edge.status, {"bg": "#6b7280", "border": "#4b5563"})
        for inp in edge.input_nodes:
            for out in edge.output_nodes:
                cert_info = ""
                if edge.certificate:
                    cert_info = f"<br>Cert Steps: {len(edge.certificate.steps)}"

                edges_data.append({
                    "id": f"{eid}_{inp}_{out}",
                    "from": inp,
                    "to": out,
                    "label": f"{edge.transformation_rule}\n({edge.checker})",
                    "title": f"Rule: {edge.transformation_rule}<br>Status: {edge.status.value}<br>Backend: {edge.checker}<br>Justification: {edge.justification}{cert_info}",
                    "arrows": "to",
                    "color": {"color": color["bg"], "highlight": color["border"]},
                    "font": {"size": 11, "align": "middle", "color": "#cbd5e1", "strokeWidth": 0},
                    "smooth": {"type": "cubicBezier", "roundness": 0.3},
                    "rule": edge.transformation_rule,
                    "justification": edge.justification,
                    "checker": edge.checker,
                    "status": edge.status.value,
                    "certificate": edge.certificate.model_dump() if edge.certificate else None
                })

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Automate Derivation Graph - {graph.name}</title>
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    body {{
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: #0f172a;
      color: #f8fafc;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      height: 100vh;
    }}
    header {{
      background: #1e293b;
      padding: 12px 24px;
      border-bottom: 1px solid #334155;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    h1 {{
      font-size: 1.15rem;
      margin: 0;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .badge {{
      background: #3b82f6;
      font-size: 0.75rem;
      padding: 3px 8px;
      border-radius: 9999px;
      font-weight: 600;
    }}
    .legend {{
      display: flex;
      gap: 14px;
      font-size: 0.8rem;
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .dot {{
      width: 10px;
      height: 10px;
      border-radius: 50%;
    }}
    #main-container {{
      display: flex;
      flex: 1;
      height: calc(100vh - 55px);
    }}
    #network-container {{
      flex: 1;
      height: 100%;
      background: radial-gradient(#1e293b 1px, transparent 1px);
      background-size: 24px 24px;
    }}
    #sidebar {{
      width: 380px;
      background: #1e293b;
      border-left: 1px solid #334155;
      padding: 20px;
      box-sizing: border-box;
      overflow-y: auto;
    }}
    .card {{
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 16px;
    }}
    .card-title {{
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #94a3b8;
      margin-bottom: 8px;
    }}
    pre {{
      background: #1e293b;
      padding: 10px;
      border-radius: 6px;
      overflow-x: auto;
      font-size: 0.85rem;
      color: #38bdf8;
    }}
    .tag {{
      display: inline-block;
      background: #334155;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 0.75rem;
      margin: 2px;
    }}
  </style>
</head>
<body>
  <header>
    <h1>Automate Engine <span class="badge">{graph.name}</span></h1>
    <div class="legend">
      <div class="legend-item"><span class="dot" style="background: #10b981"></span> Formally Proved (Lean 4)</div>
      <div class="legend-item"><span class="dot" style="background: #3b82f6"></span> Symbolic Checked (SymPy)</div>
      <div class="legend-item"><span class="dot" style="background: #06b6d4"></span> Numerically Checked (SciPy)</div>
      <div class="legend-item"><span class="dot" style="background: #8b5cf6"></span> Statistically Checked (SciPy)</div>
      <div class="legend-item"><span class="dot" style="background: #f59e0b"></span> Conditional</div>
    </div>
  </header>
  <div id="main-container">
    <div id="network-container"></div>
    <div id="sidebar">
      <div class="card">
        <div class="card-title">Derivation Overview</div>
        <p style="font-size: 0.9rem; margin-top: 0;">{graph.description or 'Machine-auditable derivation graph'}</p>
        <p style="font-size: 0.8rem; color: #94a3b8;">Nodes: {len(graph.nodes)} | Edges: {len(graph.edges)} | Assumptions: {len(graph.assumptions)}</p>
      </div>
      <div id="detail-card" class="card">
        <div class="card-title">Inspector</div>
        <p style="font-size: 0.85rem; color: #94a3b8;">Click on any node or transformation edge to inspect its mathematical formula, verification certificate, or assumptions.</p>
      </div>
    </div>
  </div>

  <script>
    const nodes = new vis.DataSet({json.dumps(nodes_data)});
    const edges = new vis.DataSet({json.dumps(edges_data)});

    const container = document.getElementById("network-container");
    const data = {{ nodes: nodes, edges: edges }};
    const options = {{
      layout: {{
        hierarchical: {{
          enabled: true,
          direction: "UD",
          sortMethod: "directed",
          levelSeparation: 120,
          nodeSpacing: 180
        }}
      }},
      physics: false,
      interaction: {{ hover: true }}
    }};

    const network = new vis.Network(container, data, options);

    network.on("selectNode", function(params) {{
      const nodeId = params.nodes[0];
      const nodeData = nodes.get(nodeId);
      const inspector = document.getElementById("detail-card");

      let asmsHtml = "None";
      if (nodeData.assumptions && nodeData.assumptions.length > 0) {{
        asmsHtml = nodeData.assumptions.map(a => `<span class="tag">${{a}}</span>`).join(" ");
      }}

      inspector.innerHTML = `
        <div class="card-title">Node Inspector: ${{nodeData.id}}</div>
        <p><strong>Status:</strong> <span class="tag" style="background: ${{nodeData.color.background}}; color: #fff;">${{nodeData.status}}</span></p>
        <p><strong>Domain:</strong> ${{nodeData.domain}}</p>
        <p><strong>Canonical Expression:</strong></p>
        <pre>${{nodeData.raw_str}}</pre>
        ${{nodeData.latex ? `<p><strong>LaTeX:</strong></p><pre>${{nodeData.latex}}</pre>` : ""}}
        <p><strong>Inherited Assumptions:</strong></p>
        <div>${{asmsHtml}}</div>
      `;
    }});

    network.on("selectEdge", function(params) {{
      const edgeId = params.edges[0];
      const edgeData = edges.get(edgeId);
      const inspector = document.getElementById("detail-card");

      let certHtml = "";
      if (edgeData.certificate) {{
        certHtml = `
          <p><strong>Certificate Details:</strong></p>
          <pre>${{JSON.stringify(edgeData.certificate, null, 2)}}</pre>
        `;
      }}

      inspector.innerHTML = `
        <div class="card-title">Transformation Step: ${{edgeData.rule}}</div>
        <p><strong>Status:</strong> <span class="tag" style="background: ${{edgeData.color.color}}; color: #fff;">${{edgeData.status}}</span></p>
        <p><strong>Backend:</strong> ${{edgeData.checker}}</p>
        <p><strong>Justification:</strong></p>
        <p style="font-size: 0.9rem;">${{edgeData.justification}}</p>
        ${{certHtml}}
      `;
    }});
  </script>
</body>
</html>"""

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(html_template, encoding="utf-8")
    return str(out_file)
