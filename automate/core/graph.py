"""
DerivationGraph: The central data structure representing formal physics derivations
as directed acyclic graphs with assumption tracking, verification backends, and
lossless hierarchical transformation expansion.
"""

from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple, Union
from collections import defaultdict, deque
from datetime import datetime, timezone
import json
import copy
from pydantic import BaseModel, Field

from automate.core.status import VerificationStatus
from automate.core.node import DerivationNode
from automate.core.edge import DerivationEdge, DerivationCertificate
from automate.ir.assumptions import Assumption, AssumptionDependency, AssumptionRegistry
from automate.ir.serialization import dump_json, load_json
from automate.core.claim import (
    build_claim_identity,
    build_dependency_fingerprint,
    compute_evidence_fingerprint,
)


class DerivationGraph(BaseModel):
    """
    A machine-auditable derivation graph for mathematical physics.
    """
    id: str = Field(default="derivation_graph", description="Unique identifier for graph")
    name: str = Field(default="Derivation Graph", description="Title of the derivation")
    description: str = Field(default="", description="High-level description")
    nodes: Dict[str, DerivationNode] = Field(default_factory=dict)
    edges: Dict[str, DerivationEdge] = Field(default_factory=dict)
    assumptions: Dict[str, Assumption] = Field(default_factory=dict)
    assumption_dependencies: List[AssumptionDependency] = Field(
        default_factory=list,
        description="Explicit dependency graph between declared assumptions",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_claim_identity(self, edge_id: str):
        """Return the canonical identity of an edge's mathematical claim."""
        edge = self.get_edge(edge_id)
        if edge is None:
            raise KeyError(f"Edge '{edge_id}' not found in graph.")
        return build_claim_identity(self, edge)

    def get_dependency_fingerprint(self, edge_id: str) -> str:
        """Return the current dependency fingerprint for an edge."""
        edge = self.get_edge(edge_id)
        if edge is None:
            raise KeyError(f"Edge '{edge_id}' not found in graph.")
        return build_dependency_fingerprint(self, edge)

    def get_certificate_staleness(self, edge_id: str) -> Dict[str, Any]:
        """Compare a stored certificate with the graph state it was issued for."""
        edge = self.get_edge(edge_id)
        if edge is None:
            raise KeyError(f"Edge '{edge_id}' not found in graph.")

        cert = edge.certificate
        if cert is None:
            return {
                "current": False,
                "reason": "NO_CERTIFICATE",
                "claim_current": False,
                "dependency_current": False,
            }

        if not cert.claim_fingerprint_sha256 or not cert.dependency_fingerprint_sha256:
            return {
                "current": None,
                "reason": "LEGACY_CERTIFICATE_WITHOUT_IDENTITY",
                "claim_current": None,
                "dependency_current": None,
                "stored_claim_fingerprint_sha256": cert.claim_fingerprint_sha256,
                "stored_dependency_fingerprint_sha256": cert.dependency_fingerprint_sha256,
            }

        current_claim = self.get_claim_identity(edge_id)
        current_dependency = self.get_dependency_fingerprint(edge_id)
        claim_current = cert.claim_fingerprint_sha256 == current_claim.claim_fingerprint_sha256
        dependency_current = cert.dependency_fingerprint_sha256 == current_dependency

        if not claim_current:
            reason = "CLAIM_CHANGED"
        elif not dependency_current:
            reason = "UPSTREAM_DEPENDENCY_CHANGED"
        else:
            reason = "CURRENT"

        return {
            "current": claim_current and dependency_current,
            "reason": reason,
            "claim_current": claim_current,
            "dependency_current": dependency_current,
            "stored_claim_fingerprint_sha256": cert.claim_fingerprint_sha256,
            "current_claim_fingerprint_sha256": current_claim.claim_fingerprint_sha256,
            "stored_dependency_fingerprint_sha256": cert.dependency_fingerprint_sha256,
            "current_dependency_fingerprint_sha256": current_dependency,
        }

    def is_certificate_current(self, edge_id: str) -> bool:
        """True only when a modern certificate matches both claim and dependencies."""
        state = self.get_certificate_staleness(edge_id)
        return state["current"] is True

    def record_verification_report(self, edge_id: str, report: Any) -> DerivationEdge:
        """
        Persist a verification report as an auditable edge certificate.

        This method does not decide whether a claim is physically true. It only
        binds the evidence to the exact claim/dependency state that produced it.
        """
        edge = self.get_edge(edge_id)
        if edge is None:
            raise KeyError(f"Edge '{edge_id}' not found in graph.")

        identity = self.get_claim_identity(edge_id)
        dependency_hash = self.get_dependency_fingerprint(edge_id)
        evidence_payload = report.to_dict()
        evidence_hash = compute_evidence_fingerprint(evidence_payload)
        evidence_payload.update({
            "claim_schema_version": identity.schema_version,
            "claim_fingerprint_sha256": identity.claim_fingerprint_sha256,
            "dependency_fingerprint_sha256": dependency_hash,
            "evidence_fingerprint_sha256": evidence_hash,
            "claim_identity": identity.model_dump(),
        })

        edge.evidence = evidence_payload
        edge.status = report.status
        edge.failed_reason = report.error_message if not report.passed else None

        # Preserve backend-specific certificate material when a checker has
        # already attached one (for example TensorChecker's geometry proof
        # metadata). The kernel adds its provenance fields without discarding
        # richer evidence.
        certificate = edge.certificate
        if certificate is None:
            certificate = DerivationCertificate(
                rule_name=edge.transformation_rule,
                steps=report.certificates,
                proof_code=report.proof_script,
                backend_version=report.backend_version,
                execution_time_ms=report.execution_time_ms,
                metrics=report.details,
                diagnostics=[report.error_message] if report.error_message else [],
            )
            edge.certificate = certificate
        else:
            certificate.rule_name = edge.transformation_rule
            if report.certificates:
                certificate.steps = report.certificates
            if report.proof_script:
                certificate.proof_code = report.proof_script
            if report.backend_version:
                certificate.backend_version = report.backend_version
            certificate.execution_time_ms = report.execution_time_ms
            merged_metrics = dict(certificate.metrics)
            merged_metrics.update(report.details)
            certificate.metrics = merged_metrics
            if report.error_message:
                certificate.diagnostics = [*certificate.diagnostics, report.error_message]

        certificate.claim_schema_version = identity.schema_version
        certificate.claim_fingerprint_sha256 = identity.claim_fingerprint_sha256
        certificate.dependency_fingerprint_sha256 = dependency_hash
        certificate.evidence_fingerprint_sha256 = evidence_hash
        certificate.claim_payload = identity.canonical_payload
        certificate.metrics = dict(certificate.metrics)
        certificate.metrics.update({
            "claim_fingerprint_sha256": identity.claim_fingerprint_sha256,
            "dependency_fingerprint_sha256": dependency_hash,
            "evidence_fingerprint_sha256": evidence_hash,
        })
        return edge

    def add_node(self, node: DerivationNode) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: DerivationEdge) -> None:
        # Check that input and output nodes exist
        for nid in edge.input_nodes:
            if nid not in self.nodes:
                raise ValueError(f"Input node '{nid}' not found in graph.")
        for nid in edge.output_nodes:
            if nid not in self.nodes:
                raise ValueError(f"Output node '{nid}' not found in graph.")
        self.edges[edge.id] = edge

    def add_assumption(self, assumption: Assumption) -> None:
        self.assumptions[assumption.id] = assumption

    def add_assumption_dependency(self, dependency: AssumptionDependency) -> None:
        """Add a declared assumption dependency and reject cycles/unknown IDs."""
        if dependency.assumption_id not in self.assumptions:
            raise ValueError(
                f"Assumption dependency target '{dependency.assumption_id}' is not declared."
            )
        missing = [
            aid for aid in dependency.depends_on if aid not in self.assumptions
        ]
        if missing:
            raise ValueError(
                "Assumption dependency references undeclared prerequisites: "
                + ", ".join(sorted(missing))
            )

        self.assumption_dependencies.append(dependency)
        try:
            self.validate_assumption_dependency_graph()
        except Exception:
            self.assumption_dependencies.pop()
            raise

    def get_assumption_dependencies(self, assumption_id: str) -> List[str]:
        """Return direct active prerequisites of an assumption."""
        dependencies: Set[str] = set()
        for dependency in self.assumption_dependencies:
            if (
                dependency.active
                and dependency.assumption_id == assumption_id
            ):
                dependencies.update(dependency.depends_on)
        return sorted(dependencies)

    def get_assumption_dependency_closure(self, assumption_ids: Set[str] | List[str]) -> Set[str]:
        """Return assumptions plus all transitive active prerequisites."""
        roots = set(assumption_ids)
        # Unknown assumptions remain explicit external premises. They are leaves
        # in the dependency graph because Automate cannot invent their meaning.
        closure: Set[str] = set()
        stack = list(roots)
        while stack:
            current = stack.pop()
            if current in closure:
                continue
            closure.add(current)
            stack.extend(self.get_assumption_dependencies(current))
        return closure

    def validate_assumption_dependency_graph(self) -> bool:
        """Validate that declared assumption prerequisites form a DAG."""
        adjacency: Dict[str, Set[str]] = defaultdict(set)
        for dependency in self.assumption_dependencies:
            if not dependency.active:
                continue
            adjacency[dependency.assumption_id].update(dependency.depends_on)

        visiting: Set[str] = set()
        visited: Set[str] = set()

        def dfs(current: str) -> None:
            if current in visiting:
                raise ValueError(
                    "Assumption dependency graph contains a cycle involving "
                    f"'{current}'."
                )
            if current in visited:
                return
            visiting.add(current)
            for parent in adjacency.get(current, set()):
                dfs(parent)
            visiting.remove(current)
            visited.add(current)

        for assumption_id in self.assumptions:
            dfs(assumption_id)
        return True

    def query_assumption_dependency_tree(self, assumption_id: str) -> Dict[str, Any]:
        """Return direct and transitive prerequisites for one assumption."""
        closure = self.get_assumption_dependency_closure({assumption_id})
        return {
            "assumption_id": assumption_id,
            "direct_dependencies": self.get_assumption_dependencies(assumption_id),
            "transitive_dependencies": sorted(closure - {assumption_id}),
        }

    def get_node(self, node_id: str) -> Optional[DerivationNode]:
        return self.nodes.get(node_id)

    def get_edge(self, edge_id: str) -> Optional[DerivationEdge]:
        return self.edges.get(edge_id)

    def get_incoming_edges(self, node_id: str) -> List[DerivationEdge]:
        return [e for e in self.edges.values() if node_id in e.output_nodes]

    def get_outgoing_edges(self, node_id: str) -> List[DerivationEdge]:
        return [e for e in self.edges.values() if node_id in e.input_nodes]

    def validate_dag(self) -> bool:
        """
        Verifies that the graph is a Directed Acyclic Graph (DAG) with no cycles.
        """
        adj: Dict[str, List[str]] = defaultdict(list)
        in_degree: Dict[str, int] = {nid: 0 for nid in self.nodes}

        for edge in self.edges.values():
            for inp in edge.input_nodes:
                for out in edge.output_nodes:
                    adj[inp].append(out)
                    in_degree[out] += 1

        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        visited_count = 0

        while queue:
            curr = queue.popleft()
            visited_count += 1
            for nxt in adj[curr]:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)

        return visited_count == len(self.nodes)

    def topological_sort(self) -> List[str]:
        """
        Returns node IDs in topological order.
        """
        adj: Dict[str, List[str]] = defaultdict(list)
        in_degree: Dict[str, int] = {nid: 0 for nid in self.nodes}

        for edge in self.edges.values():
            for inp in edge.input_nodes:
                for out in edge.output_nodes:
                    adj[inp].append(out)
                    in_degree[out] += 1

        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        order: List[str] = []

        while queue:
            curr = queue.popleft()
            order.append(curr)
            for nxt in adj[curr]:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)

        if len(order) != len(self.nodes):
            raise ValueError("Graph contains cycles; cannot produce topological order.")
        return order

    def is_fully_verified(self) -> bool:
        """
        True if all derivation edges in the graph have passed verification and there are no failures.
        """
        if not self.edges:
            return False
        failed_edges = self.get_failed_derivations()
        return (len(failed_edges) == 0) and all(
            e.status.is_verified for e in self.edges.values()
        )

    def compute_inherited_assumptions(self, node_id: str) -> Set[str]:
        """
        Computes the complete transitive set of assumptions upon which node_id depends.
        """
        visited_nodes: Set[str] = set()
        accumulated_assumptions: Set[str] = set()

        def dfs(curr_id: str):
            if curr_id in visited_nodes:
                return
            visited_nodes.add(curr_id)
            node = self.nodes.get(curr_id)
            if node:
                accumulated_assumptions.update(
                    self.get_assumption_dependency_closure(set(node.assumptions))
                )
            for edge in self.get_incoming_edges(curr_id):
                for parent_id in edge.input_nodes:
                    dfs(parent_id)

        dfs(node_id)
        return accumulated_assumptions

    def query_assumptions_for_node(self, node_id: str) -> Dict[str, Any]:
        """
        Returns detailed list of all assumptions supporting node_id.
        """
        asm_ids = self.compute_inherited_assumptions(node_id)
        details = []
        for aid in sorted(asm_ids):
            asm = self.assumptions.get(aid)
            if asm:
                details.append(asm.to_dict())
            else:
                details.append({"id": aid, "description": "Undeclared external assumption"})
        return {
            "node_id": node_id,
            "assumption_count": len(asm_ids),
            "assumptions": details
        }

    def query_nodes_dependent_on(self, assumption_id: str) -> List[str]:
        """
        Finds all nodes that depend directly or transitively on assumption_id.
        """
        dependent: List[str] = []
        for nid in self.nodes:
            if assumption_id in self.compute_inherited_assumptions(nid):
                dependent.append(nid)
        return dependent

    def simulate_assumption_removal(self, assumption_id: str) -> Dict[str, Any]:
        """
        Simulates the removal of an assumption.
        Returns which nodes survive, which are invalidated or made CONDITIONAL.
        """
        dependent_nodes = set(self.query_nodes_dependent_on(assumption_id))
        surviving_nodes = [nid for nid in self.nodes if nid not in dependent_nodes]
        invalidated_edges = [
            eid for eid, edge in self.edges.items()
            if any(nid in dependent_nodes for nid in edge.output_nodes)
        ]

        return {
            "dropped_assumption": assumption_id,
            "total_nodes": len(self.nodes),
            "surviving_nodes": surviving_nodes,
            "invalidated_nodes": list(dependent_nodes),
            "invalidated_edges": invalidated_edges,
            "survival_ratio": len(surviving_nodes) / max(1, len(self.nodes))
        }

    def find_nodes_requiring_predicate(self, keyword: str) -> List[str]:
        """
        Finds all nodes whose transitive inherited assumptions match a given keyword or predicate.
        Keyword search matches case-insensitively against assumption ID, formal predicate,
        description, or category.
        """
        kw = keyword.lower()
        matching_assumptions: Set[str] = set()
        for aid, asm in self.assumptions.items():
            if (
                kw in aid.lower()
                or kw in asm.formal_predicate.lower()
                or kw in asm.description.lower()
                or kw in asm.category.lower()
            ):
                matching_assumptions.add(aid)

        matching_nodes: List[str] = []
        for nid in self.nodes:
            inherited = self.compute_inherited_assumptions(nid)
            if any(aid in matching_assumptions for aid in inherited):
                matching_nodes.append(nid)
        return matching_nodes

    def get_failed_derivations(self) -> List[str]:
        """
        Returns IDs of all derivation edges whose verification failed, disproved, or recorded an error.
        """
        failed: List[str] = []
        for eid, edge in self.edges.items():
            if (
                edge.status in (VerificationStatus.FAILED, VerificationStatus.DISPROVED)
                or edge.failed_reason is not None
            ):
                failed.append(eid)
        return failed

    def get_downstream_invalidated_by_failure(self, edge_id: str) -> List[str]:
        """
        Given a failed edge, finds all downstream nodes that depend on this edge's output nodes.
        These downstream nodes are rendered unproven/invalidated due to the upstream failure.
        """
        edge = self.edges.get(edge_id)
        if not edge:
            return []

        invalidated: Set[str] = set(edge.output_nodes)
        queue: deque = deque(edge.output_nodes)

        while queue:
            curr = queue.popleft()
            for out_edge in self.get_outgoing_edges(curr):
                for target_nid in out_edge.output_nodes:
                    if target_nid not in invalidated:
                        invalidated.add(target_nid)
                        queue.append(target_nid)

        return sorted(list(invalidated))

    def get_all_invalidated_nodes(self) -> Dict[str, List[str]]:
        """
        Maps every failed edge ID to its transitively invalidated downstream nodes.
        """
        return {
            eid: self.get_downstream_invalidated_by_failure(eid)
            for eid in self.get_failed_derivations()
        }

    def export_certificate_package(self, output_dir: Union[str, Path]) -> Dict[str, str]:
        """
        Exports a self-contained, machine-auditable verification certificate package:
        1. certificate.json: Overall graph verification summary, verification rate, node/edge statuses.
        2. assumptions.json: Full dictionary of assumptions and per-node assumption dependencies.
        3. obligations.json: All verification obligations and side conditions per edge.
        4. evidence.json: Recorded verification evidence objects, metrics, residuals, proof scripts.
        5. subgraph_expansion.json: Full micro-step expansions of edges with certificates.
        """
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        # 1. certificate.json
        status_counts: Dict[str, int] = defaultdict(int)
        for e in self.edges.values():
            status_counts[e.status.value] += 1
        node_status_counts: Dict[str, int] = defaultdict(int)
        for n in self.nodes.values():
            node_status_counts[n.status.value] += 1

        failed_edges = self.get_failed_derivations()
        is_verified = (len(failed_edges) == 0) and all(
            e.status.is_verified for e in self.edges.values()
        )
        modern_stale_edges = [
            eid for eid, edge in self.edges.items()
            if edge.certificate
            and edge.certificate.claim_fingerprint_sha256
            and edge.certificate.dependency_fingerprint_sha256
            and self.get_certificate_staleness(eid)["current"] is False
        ]
        if modern_stale_edges:
            is_verified = False

        cert_data = {
            "graph_id": self.id,
            "name": self.name,
            "description": self.description,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "is_fully_verified": is_verified,
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "total_assumptions": len(self.assumptions),
            "edge_status_counts": dict(status_counts),
            "node_status_counts": dict(node_status_counts),
            "failed_derivations": failed_edges,
            "invalidated_nodes": self.get_all_invalidated_nodes(),
            "certificate_staleness": {
                eid: self.get_certificate_staleness(eid) for eid in self.edges
            },
            "metadata": self.metadata
        }

        # 2. assumptions.json
        assumptions_data = {
            "declared_assumptions": {aid: asm.to_dict() for aid, asm in self.assumptions.items()},
            "node_assumption_dependencies": {
                nid: sorted(list(self.compute_inherited_assumptions(nid)))
                for nid in self.nodes
            }
        }

        # 3. obligations.json
        obligations_data = {
            eid: {
                "rule": edge.transformation_rule,
                "justification": edge.justification,
                "checker": edge.checker,
                "side_conditions": edge.side_conditions,
                "verification_obligations": edge.verification_obligations,
                "status": edge.status.value
            }
            for eid, edge in self.edges.items()
        }

        # 4. evidence.json
        evidence_data = {
            eid: {
                "checker": edge.checker,
                "status": edge.status.value,
                "evidence": edge.evidence,
                "certificate": edge.certificate.model_dump() if edge.certificate else None,
                "failed_reason": edge.failed_reason
            }
            for eid, edge in self.edges.items()
        }

        # 5. subgraph_expansion.json
        expansions_data: Dict[str, Any] = {}
        for eid in self.edges:
            subgraph = self.expand_edge_certificate(eid)
            if subgraph:
                expansions_data[eid] = subgraph.model_dump()

        # 6. provenance.json
        from automate.ai.context import compute_semantic_graph_hash
        provenance_data = {
            "graph_semantic_hash": compute_semantic_graph_hash(self),
            "generated_at": cert_data["generated_at"],
            "edge_provenance": {
                eid: {
                    "checker": edge.checker,
                    "status": edge.status.value,
                    "origin": edge.metadata.get("origin", {"type": "analytical_definition"}),
                    "lean_provenance": edge.evidence.get("reproducibility") if edge.evidence and edge.checker == "lean4" else None
                }
                for eid, edge in self.edges.items()
            }
        }

        # 7. Write package files
        files = {
            "certificate.json": out_path / "certificate.json",
            "assumptions.json": out_path / "assumptions.json",
            "obligations.json": out_path / "obligations.json",
            "evidence.json": out_path / "evidence.json",
            "subgraph_expansion.json": out_path / "subgraph_expansion.json",
            "provenance.json": out_path / "provenance.json",
        }

        files["certificate.json"].write_text(json.dumps(cert_data, indent=2), encoding="utf-8")
        files["assumptions.json"].write_text(json.dumps(assumptions_data, indent=2), encoding="utf-8")
        files["obligations.json"].write_text(json.dumps(obligations_data, indent=2), encoding="utf-8")
        files["evidence.json"].write_text(json.dumps(evidence_data, indent=2), encoding="utf-8")
        files["subgraph_expansion.json"].write_text(json.dumps(expansions_data, indent=2), encoding="utf-8")
        files["provenance.json"].write_text(json.dumps(provenance_data, indent=2), encoding="utf-8")

        # 8. manifest.json with SHA-256 hashes of all artifacts
        import hashlib
        manifest = {}
        for fname, fpath in files.items():
            manifest[fname] = {
                "sha256": hashlib.sha256(fpath.read_bytes()).hexdigest(),
                "size_bytes": fpath.stat().st_size
            }
        manifest_file = out_path / "manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        files["manifest.json"] = manifest_file

        return {k: str(v) for k, v in files.items()}

    def expand_edge_certificate(self, edge_id: str) -> Optional["DerivationGraph"]:
        """
        Expands a high-level edge into its constituent micro-steps.
        Returns a detailed sub-graph representing the certificate steps.
        Lossless mathematical expansion: A -> B becomes A -> A1 -> A2 -> B.
        """
        edge = self.edges.get(edge_id)
        if not edge or not edge.certificate or not edge.certificate.steps:
            return None

        subgraph = DerivationGraph(
            id=f"{edge_id}_expanded",
            name=f"Expanded Certificate for {edge_id}",
            description=f"Micro-step expansion for rule {edge.transformation_rule}"
        )

        # Include input nodes
        for inp_id in edge.input_nodes:
            if inp_id in self.nodes:
                subgraph.add_node(copy.deepcopy(self.nodes[inp_id]))

        # Create intermediate nodes and edges from certificate steps
        prev_node_id = edge.input_nodes[0] if edge.input_nodes else None
        for i, step in enumerate(edge.certificate.steps):
            sub_node_id = f"{edge_id}_sub_{i+1}"
            sub_edge_id = f"{edge_id}_step_{i+1}"

            # Create node
            expr_data = step.get("expr", "")
            from automate.ir.ast import MathematicalExpression
            sub_node = DerivationNode(
                id=sub_node_id,
                expression=MathematicalExpression(raw_str=str(expr_data)),
                domain=self.nodes[edge.input_nodes[0]].domain if edge.input_nodes else "general_physics",
                source="certificate_intermediate",
                status=VerificationStatus.SYMBOLIC_CHECKED
            )
            subgraph.add_node(sub_node)

            # Create edge
            if prev_node_id:
                sub_edge = DerivationEdge(
                    id=sub_edge_id,
                    input_nodes=[prev_node_id],
                    output_nodes=[sub_node_id],
                    transformation_rule=step.get("operation", "intermediate_step"),
                    justification=step.get("description", "Algebraic micro-step"),
                    checker="sympy",
                    status=VerificationStatus.SYMBOLIC_CHECKED
                )
                subgraph.add_edge(sub_edge)
            prev_node_id = sub_node_id

        # Connect to original output nodes
        if prev_node_id and edge.output_nodes:
            for out_id in edge.output_nodes:
                if out_id in self.nodes:
                    subgraph.add_node(copy.deepcopy(self.nodes[out_id]))
                    final_edge = DerivationEdge(
                        id=f"{edge_id}_finalize",
                        input_nodes=[prev_node_id],
                        output_nodes=[out_id],
                        transformation_rule="conclude_expansion",
                        justification="Term completion of macro rule",
                        checker="sympy",
                        status=VerificationStatus.SYMBOLIC_CHECKED
                    )
                    subgraph.add_edge(final_edge)

        return subgraph

    def to_json(self, indent: int = 2) -> str:
        return dump_json(self.model_dump(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "DerivationGraph":
        data = load_json(json_str)
        return cls(**data)
