"""
Canonical claim identity and verification provenance primitives.

Automate is an open-world verifier: claim identity describes the mathematical
assertion being evaluated, not whether the assertion matches an established
theory. Backend evidence remains responsible for deciding what can currently
be established about that claim.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from typing import Any, Dict, Iterable, Mapping, TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from automate.core.edge import DerivationEdge
    from automate.core.graph import DerivationGraph


CLAIM_IDENTITY_SCHEMA_VERSION = "1.0"

# These values describe observations, fitting/execution configuration, or
# machine-level controls. They belong to evidence, not to the mathematical
# identity of the claim.
_EVIDENCE_PARAMETER_KEYS = {
    "t_data",
    "x_data",
    "y_data",
    "data",
    "data_id",
    "data_source",
    "observations",
    "sample_data",
    "noise_std",
    "fit_initial_guess",
    "seed",
    "random_seed",
    "rtol",
    "atol",
    "fine_rtol",
    "fine_atol",
    "coarse_rtol",
    "coarse_atol",
    "convergence_tolerance",
    "refinement_factor",
    "solver",
    "solver_method",
    "timeout",
    "max_seconds",
    "max_cpu_seconds",
    "max_address_space_bytes",
    "max_result_bytes",
    "max_nodes",
    "max_evaluations",
    "backend_version",
    "engine_version",
    "command_invocation",
}

_EPHEMERAL_EVIDENCE_KEYS = {
    "claim_fingerprint_sha256",
    "dependency_fingerprint_sha256",
    "evidence_fingerprint_sha256",
    "claim_identity",
    "generated_at",
    "timestamp",
    "execution_time_ms",
}


class ClaimIdentity(BaseModel):
    """Stable identity of a mathematical claim independent of its verifier."""

    schema_version: str = CLAIM_IDENTITY_SCHEMA_VERSION
    canonical_payload: Dict[str, Any]
    claim_fingerprint_sha256: str


def _normalize_text(value: str) -> str:
    """Normalize presentation-only differences without asserting equivalence."""
    value = unicodedata.normalize("NFKC", value)
    value = (
        value.replace("−", "-")
        .replace("–", "-")
        .replace("—", "-")
        .replace("×", "*")
        .replace("·", "*")
    )
    value = re.sub(r"\s+", " ", value).strip()

    # Remove redundant balanced outer parentheses, but do not otherwise rewrite
    # the mathematics. Algebraic equivalence belongs to symbolic/formal
    # backends, not to identity generation.
    while value.startswith("(") and value.endswith(")"):
        depth = 0
        balanced_outer = True
        for idx, char in enumerate(value):
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0 and idx != len(value) - 1:
                    balanced_outer = False
                    break
                if depth < 0:
                    balanced_outer = False
                    break
        if balanced_outer and depth == 0:
            value = value[1:-1].strip()
        else:
            break

    return value


def _canonicalize(value: Any) -> Any:
    """Turn supported values into deterministic JSON-compatible structures."""
    if isinstance(value, BaseModel):
        return _canonicalize(value.model_dump())

    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize(value[key])
            for key in sorted(value.keys(), key=lambda item: str(item))
        }

    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]

    if isinstance(value, (set, frozenset)):
        normalized = [_canonicalize(item) for item in value]
        return sorted(
            normalized,
            key=lambda item: json.dumps(
                item, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ),
        )

    if isinstance(value, str):
        return _normalize_text(value)

    if isinstance(value, float):
        if not math.isfinite(value):
            return repr(value)
        return value

    if value is None or isinstance(value, (bool, int)):
        return value

    # Unknown values should never make the fingerprint nondeterministic.
    return _normalize_text(str(value))


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        _canonicalize(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_json(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _semantic_parameters(parameters: Mapping[str, Any]) -> Dict[str, Any]:
    """Remove evidence/runtime controls while preserving claim-relevant data."""
    result: Dict[str, Any] = {}
    for key, value in parameters.items():
        if str(key).lower() in _EVIDENCE_PARAMETER_KEYS:
            continue
        result[str(key)] = value
    return _canonicalize(result)


def _node_signature(node: Any) -> Dict[str, Any]:
    expr = node.expression
    payload: Dict[str, Any] = {
        "node_kind": node.node_kind,
        "domain": node.domain,
        "dimension": expr.dimension,
        "assumptions": sorted(node.assumptions),
    }

    # Prefer the structured IR when it exists. The raw string remains the
    # presentation-level fallback for legacy graphs whose AST is empty.
    if expr.ast:
        payload["expression"] = {"ast": _canonicalize(expr.ast)}
    else:
        payload["expression"] = {"raw": _normalize_text(expr.raw_str)}

    return _canonicalize(payload)


def _assumption_signature(graph: "DerivationGraph", assumption_ids: Iterable[str]) -> Dict[str, Any]:
    signatures: Dict[str, Any] = {}
    for assumption_id in sorted(set(assumption_ids)):
        assumption = graph.assumptions.get(assumption_id)
        if assumption is None:
            signatures[assumption_id] = {"id": assumption_id, "declared": False}
            continue
        signatures[assumption_id] = {
            "id": assumption.id,
            "formal_predicate": _normalize_text(assumption.formal_predicate),
            "category": _normalize_text(assumption.category),
            "active": bool(assumption.active),
        }
    return _canonicalize(signatures)


def build_claim_identity(graph: "DerivationGraph", edge: "DerivationEdge") -> ClaimIdentity:
    """
    Build a backend-independent identity for the mathematical claim represented
    by one derivation edge.

    Backend choice, tolerances, sampled data, execution time, and machine
    settings are deliberately excluded. Thus independent backends can certify
    the same claim, while a novel claim can be represented without matching
    any established theorem.
    """
    relevant_assumptions = set(edge.side_conditions)
    for node_id in [*edge.input_nodes, *edge.output_nodes]:
        relevant_assumptions.update(graph.compute_inherited_assumptions(node_id))

    payload = {
        "schema_version": CLAIM_IDENTITY_SCHEMA_VERSION,
        "claim": {
            "transformation_rule": edge.transformation_rule,
            "inputs": [_node_signature(graph.nodes[node_id]) for node_id in edge.input_nodes],
            "outputs": [_node_signature(graph.nodes[node_id]) for node_id in edge.output_nodes],
            "semantic_parameters": _semantic_parameters(edge.parameters),
            "assumptions": _assumption_signature(graph, relevant_assumptions),
            "side_conditions": sorted(set(edge.side_conditions)),
        },
    }
    payload = _canonicalize(payload)
    return ClaimIdentity(
        canonical_payload=payload,
        claim_fingerprint_sha256=sha256_json(payload),
    )


def _upstream_closure(graph: "DerivationGraph", node_ids: Iterable[str]) -> tuple[set[str], set[str]]:
    """Return transitive upstream node and edge IDs for a claim's inputs."""
    visited_nodes: set[str] = set()
    visited_edges: set[str] = set()
    stack = list(node_ids)

    while stack:
        node_id = stack.pop()
        if node_id in visited_nodes:
            continue
        visited_nodes.add(node_id)

        for incoming in graph.get_incoming_edges(node_id):
            visited_edges.add(incoming.id)
            stack.extend(incoming.input_nodes)

    return visited_nodes, visited_edges


def build_dependency_fingerprint(graph: "DerivationGraph", edge: "DerivationEdge") -> str:
    """
    Hash the graph state that can feed the edge's inputs.

    Unrelated nodes elsewhere in the graph are excluded. This is intentionally
    narrower than a whole-graph hash so a certificate only becomes stale when
    something it depends on has actually changed.
    """
    node_ids, upstream_edge_ids = _upstream_closure(graph, edge.input_nodes)

    nodes = {
        node_id: _node_signature(graph.nodes[node_id])
        for node_id in sorted(node_ids)
    }

    edges: Dict[str, Any] = {}
    for edge_id in sorted(upstream_edge_ids):
        upstream = graph.edges[edge_id]
        edges[edge_id] = {
            "input_nodes": list(upstream.input_nodes),
            "output_nodes": list(upstream.output_nodes),
            "transformation_rule": upstream.transformation_rule,
            "side_conditions": sorted(set(upstream.side_conditions)),
            "semantic_parameters": _semantic_parameters(upstream.parameters),
        }

    assumption_ids = set(edge.side_conditions)
    for node_id in node_ids:
        assumption_ids.update(graph.compute_inherited_assumptions(node_id))

    payload = {
        "schema_version": CLAIM_IDENTITY_SCHEMA_VERSION,
        "target_edge": {
            "input_nodes": list(edge.input_nodes),
            "output_nodes": list(edge.output_nodes),
            "transformation_rule": edge.transformation_rule,
        },
        "upstream_nodes": nodes,
        "upstream_edges": edges,
        "assumptions": _assumption_signature(graph, assumption_ids),
    }
    return sha256_json(payload)


def compute_evidence_fingerprint(payload: Mapping[str, Any]) -> str:
    """
    Hash an execution/evidence record independently from claim and dependency
    identity. Timing and other ephemeral fields are ignored.
    """
    def strip_ephemeral(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                str(key): strip_ephemeral(item)
                for key, item in value.items()
                if str(key).lower() not in _EPHEMERAL_EVIDENCE_KEYS
            }
        if isinstance(value, (list, tuple)):
            return [strip_ephemeral(item) for item in value]
        if isinstance(value, set):
            return sorted(strip_ephemeral(item) for item in value)
        return value

    return sha256_json(strip_ephemeral(payload))
