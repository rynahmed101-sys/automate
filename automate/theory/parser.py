"""
Parser: Translates declarative YAML or JSON theory files into canonical DerivationGraphs.
"""

from pathlib import Path
from typing import Dict, Any, Union
import yaml
import json

from automate.core.status import VerificationStatus
from automate.core.node import DerivationNode
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.ir.ast import MathematicalExpression
from automate.ir.assumptions import Assumption


def parse_theory_file(file_path: Union[str, Path]) -> DerivationGraph:
    """
    Parses a YAML or JSON theory file and returns a DerivationGraph.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Theory file not found: {path}")

    content = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        data = yaml.safe_load(content)
    elif path.suffix == ".json":
        data = json.loads(content)
    else:
        # Try YAML parser as fallback
        data = yaml.safe_load(content)

    return parse_theory_dict(data)


def parse_theory_dict(data: Dict[str, Any]) -> DerivationGraph:
    """
    Converts a dictionary representation into a DerivationGraph.
    """
    graph_id = data.get("theory", data.get("id", "theory_derivation"))
    name = data.get("name", graph_id)
    description = data.get("description", "")

    graph = DerivationGraph(
        id=graph_id,
        name=name,
        description=description,
        metadata=data.get("metadata", {})
    )

    # 1. Parse Assumptions
    assumptions_dict = data.get("assumptions", {})
    for aid, ainfo in assumptions_dict.items():
        if isinstance(ainfo, str):
            asm = Assumption(
                id=aid,
                description=ainfo,
                formal_predicate=ainfo
            )
        else:
            asm = Assumption(
                id=aid,
                description=ainfo.get("description", aid),
                category=ainfo.get("category", "domain_restriction"),
                formal_predicate=ainfo.get("formal_predicate", ainfo.get("predicate", aid)),
                active=ainfo.get("active", True)
            )
        graph.add_assumption(asm)

    # 2. Parse Nodes
    nodes_dict = data.get("nodes", {})
    for nid, ninfo in nodes_dict.items():
        raw_expr = ninfo.get("expression", "")
        dim_str = ninfo.get("dimension", "")
        math_expr = MathematicalExpression(
            raw_str=raw_expr,
            dimension=dim_str,
            latex=ninfo.get("latex"),
            sympy_str=ninfo.get("sympy")
        )
        node = DerivationNode(
            id=nid,
            expression=math_expr,
            representations=ninfo.get("representations", {}),
            domain=ninfo.get("domain", data.get("domain", "general_physics")),
            assumptions=ninfo.get("assumptions", []),
            source=ninfo.get("source", "definition"),
            status=VerificationStatus(ninfo.get("status", "PARSED")),
            metadata=ninfo.get("metadata", {})
        )
        if ninfo.get("latex"):
            node.representations["latex"] = ninfo["latex"]
        graph.add_node(node)

    # 3. Parse Derivation Edges
    edges_dict = data.get("derivations", data.get("edges", {}))
    for eid, einfo in edges_dict.items():
        edge = DerivationEdge(
            id=eid,
            input_nodes=einfo.get("input_nodes", []),
            output_nodes=einfo.get("output_nodes", []),
            transformation_rule=einfo.get("transformation_rule", einfo.get("rule", "algebraic_identity")),
            justification=einfo.get("justification", "Transformation rule"),
            checker=einfo.get("checker", "sympy"),
            status=VerificationStatus(einfo.get("status", "UNVERIFIED")),
            parameters=einfo.get("parameters", {}),
            metadata=einfo.get("metadata", {})
        )
        graph.add_edge(edge)

    # Validate graph structure
    if not graph.validate_dag():
        raise ValueError("Theory definition contains a cycle; derivation must be a DAG.")

    return graph
