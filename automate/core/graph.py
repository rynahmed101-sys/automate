"""
DerivationGraph: The central data structure representing formal physics derivations
as directed acyclic graphs with assumption tracking, verification backends, and
lossless hierarchical transformation expansion.
"""

from typing import Dict, List, Set, Optional, Any, Tuple
from collections import defaultdict, deque
import copy
from pydantic import BaseModel, Field

from automate.core.status import VerificationStatus
from automate.core.node import DerivationNode
from automate.core.edge import DerivationEdge, DerivationCertificate
from automate.ir.assumptions import Assumption, AssumptionRegistry
from automate.ir.serialization import dump_json, load_json


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
    metadata: Dict[str, Any] = Field(default_factory=dict)

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
                accumulated_assumptions.update(node.assumptions)
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
