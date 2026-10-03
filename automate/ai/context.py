"""
Controlled Mathematical Context Generation for AI Agents.
Filters and formats derivation graph state into structured mathematical context.
Strictly isolates mathematical data from local environment secrets, credentials, or file paths.
"""

from typing import Dict, Any, List, Optional
import hashlib
import json

from automate.core.graph import DerivationGraph
from automate.ai.schemas import AIContext
from automate.theory.rules import RuleRegistry
from automate.core.status import VerificationStatus


def compute_semantic_graph_hash(graph: DerivationGraph) -> str:
    """
    Computes a deterministic SHA-256 hash of the mathematical structure of the graph.
    Ignores non-deterministic timestamps and machine-specific local paths.
    """
    normalized_data = {
        "id": graph.id,
        "name": graph.name,
        "nodes": {
            nid: {
                "expr": n.expression.raw_str,
                "dimension": n.expression.dimension,
                "domain": n.domain,
                "assumptions": sorted(n.assumptions)
            }
            for nid, n in sorted(graph.nodes.items())
        },
        "edges": {
            eid: {
                "inputs": sorted(e.input_nodes),
                "outputs": sorted(e.output_nodes),
                "rule": e.transformation_rule,
                "checker": e.checker,
                "side_conditions": sorted(e.side_conditions)
            }
            for eid, e in sorted(graph.edges.items())
        },
        "assumptions": {
            aid: {
                "predicate": a.formal_predicate,
                "category": a.category,
                "active": a.active
            }
            for aid, a in sorted(graph.assumptions.items())
        }
    }
    canonical_json = json.dumps(normalized_data, sort_keys=True)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def build_ai_context(graph: DerivationGraph, registry: Optional[RuleRegistry] = None) -> AIContext:
    """
    Constructs a controlled, sanitized AIContext object from a DerivationGraph.
    """
    reg = registry or RuleRegistry()
    g_hash = compute_semantic_graph_hash(graph)

    # 1. Format nodes
    formatted_nodes = []
    equations = []
    for nid, node in sorted(graph.nodes.items()):
        node_summary = {
            "id": nid,
            "expression": node.expression.raw_str,
            "dimension": node.expression.dimension,
            "domain": node.domain,
            "node_kind": node.node_kind,
            "status": node.status.value,
            "assumptions": node.assumptions,
            "latex": node.representations.get("latex") or node.expression.latex
        }
        formatted_nodes.append(node_summary)
        if node.node_kind in ("equation", "differential_equation", "pde"):
            equations.append({"id": nid, "expression": node.expression.raw_str})

    # 2. Format edges
    formatted_edges = []
    open_obligations = []
    verified_edges = []
    failed_edges = []

    for eid, edge in sorted(graph.edges.items()):
        edge_summary = {
            "id": eid,
            "inputs": edge.input_nodes,
            "outputs": edge.output_nodes,
            "rule": edge.transformation_rule,
            "justification": edge.justification,
            "checker": edge.checker,
            "status": edge.status.value,
            "side_conditions": edge.side_conditions
        }
        formatted_edges.append(edge_summary)

        if edge.status.is_verified:
            verified_edges.append(eid)
        elif edge.status in (VerificationStatus.FAILED, VerificationStatus.DISPROVED):
            failed_edges.append(eid)

        # Collect open verification obligations
        if not edge.status.is_verified and edge.verification_obligations:
            for obl in edge.verification_obligations:
                open_obligations.append({
                    "edge_id": eid,
                    "claim": obl.get("claim", str(obl)),
                    "description": obl.get("description", "")
                })

    # 3. Format assumptions
    formatted_assumptions = [
        {
            "id": aid,
            "predicate": asm.formal_predicate,
            "description": asm.description,
            "category": asm.category,
            "active": asm.active
        }
        for aid, asm in sorted(graph.assumptions.items())
    ]

    # 4. Format available approved rules
    available_rules = [
        {
            "rule_id": r.rule_id,
            "name": r.name,
            "category": r.category,
            "description": r.description,
            "domain": r.domain,
            "backend": r.implementation_backend,
            "formal_proof_available": r.formal_proof_available,
            "symbolic_checker_available": r.symbolic_checker_available,
        }
        for r in reg.list_rules()
    ]

    return AIContext(
        theory_id=graph.id,
        theory_name=graph.name,
        description=graph.description,
        domain=graph.nodes[list(graph.nodes.keys())[0]].domain if graph.nodes else "general_physics",
        definitions=[n for n in formatted_nodes if n.get("node_kind") == "expression"],
        equations=equations,
        nodes=formatted_nodes,
        edges=formatted_edges,
        assumptions=formatted_assumptions,
        open_obligations=open_obligations,
        verified_edges=verified_edges,
        failed_edges=failed_edges,
        available_rules=available_rules,
        graph_hash=g_hash
    )
