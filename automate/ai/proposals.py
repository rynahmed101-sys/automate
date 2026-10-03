"""
Proposal Processing, Candidate Graph Ingestion, and the AI Derivation Verification Loop.
Implements propose_and_verify:
Proposal -> Validate -> Candidate Edge -> Generate Obligations -> Verify Backends -> Attach Evidence.
"""

from typing import Dict, Any, List, Optional, Tuple
import copy
from pathlib import Path
import json

from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.edge import DerivationEdge
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression
from automate.ir.assumptions import Assumption
from automate.ai.schemas import DerivationProposal, CandidateNode
from automate.ai.validation import validate_ai_proposal, ProposalValidationResult
from automate.theory.rules import RuleRegistry
from automate.backend.sympy_backend import SymPyChecker
from automate.backend.dimension_backend import DimensionChecker
from automate.backend.lean_backend import LeanChecker
from automate.backend.numerical_backend import NumericalChecker
from automate.backend.statistical_backend import StatisticalChecker
from automate.backend.tensor_backend import TensorChecker


class ProposalExecutionResult:
    def __init__(
        self,
        success: bool,
        proposal_id: str,
        edge_id: Optional[str] = None,
        status: VerificationStatus = VerificationStatus.AI_PROPOSED,
        report: Optional[Dict[str, Any]] = None,
        errors: Optional[List[str]] = None,
        graph_updated: bool = False
    ):
        self.success = success
        self.proposal_id = proposal_id
        self.edge_id = edge_id
        self.status = status
        self.report = report or {}
        self.errors = errors or []
        self.graph_updated = graph_updated

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "proposal_id": self.proposal_id,
            "edge_id": self.edge_id,
            "status": self.status.value,
            "errors": self.errors,
            "graph_updated": self.graph_updated,
            "report": self.report
        }


def apply_and_verify_proposal(
    proposal: DerivationProposal,
    graph: DerivationGraph,
    dry_run: bool = False,
    rule_registry: Optional[RuleRegistry] = None
) -> ProposalExecutionResult:
    """
    Core Automate AI verification pipeline:
    1. Validates proposal structure and graph prerequisites.
    2. Constructs candidate nodes and candidate edge with status AI_PROPOSED.
    3. Synthesizes verification obligations from the RuleRegistry.
    4. Executes the targeted verification backend (SymPy, Lean, Numerical, etc.).
    5. Attaches evidence and updates graph (or leaves intact if dry_run=True).
    """
    reg = rule_registry or RuleRegistry()

    # 1. Validate proposal
    val_res = validate_ai_proposal(proposal.model_dump(), graph, reg)
    if not val_res.is_valid:
        return ProposalExecutionResult(
            success=False,
            proposal_id=proposal.proposal_id,
            errors=val_res.errors
        )

    # 2. Always build and verify on an isolated candidate graph.
    # Nothing reaches the canonical graph until verification succeeds.
    working_graph = copy.deepcopy(graph)

    # Register proposed assumptions
    for asm_data in proposal.proposed_assumptions:
        asm_id = asm_data.get("id")
        if asm_id and asm_id not in working_graph.assumptions:
            working_graph.add_assumption(Assumption(
                id=asm_id,
                description=asm_data.get("description", asm_id),
                formal_predicate=asm_data.get("formal_predicate", asm_id),
                category=asm_data.get("category", "approximation")
            ))

    # Add proposed output nodes
    out_node_ids = []
    for c_node in proposal.output_nodes:
        math_expr = MathematicalExpression(
            raw_str=c_node.expression,
            dimension=c_node.dimension,
            latex=c_node.latex
        )
        d_node = DerivationNode(
            id=c_node.id,
            expression=math_expr,
            node_kind=c_node.node_kind,
            domain=c_node.domain,
            source="ai_proposed",
            status=VerificationStatus.AI_PROPOSED
        )
        working_graph.add_node(d_node)
        out_node_ids.append(c_node.id)

    # 3. Create candidate edge
    edge_id = f"edge_ai_{proposal.proposal_id}"
    rule_def = reg.get(proposal.rule)
    obligations = rule_def.generate_obligations(proposal.parameters) if rule_def else []

    edge = DerivationEdge(
        id=edge_id,
        input_nodes=proposal.input_nodes,
        output_nodes=out_node_ids,
        transformation_rule=proposal.rule,
        justification=proposal.justification,
        checker=proposal.target_checker,
        status=VerificationStatus.AI_PROPOSED,
        parameters=proposal.parameters,
        side_conditions=proposal.side_conditions,
        verification_obligations=obligations,
        metadata={"origin": proposal.origin.model_dump()}
    )
    working_graph.add_edge(edge)

    # 4. Enforce dimensional consistency before any substantive verifier.
    # A symbolic identity can still be physically nonsensical if its units are wrong.
    dim_checker = DimensionChecker()
    dim_report = dim_checker.verify_edge(edge, working_graph)
    if not dim_report.passed:
        return ProposalExecutionResult(
            success=False,
            proposal_id=proposal.proposal_id,
            edge_id=edge_id,
            status=dim_report.status,
            report={"dimension_check": dim_report.to_dict()},
            errors=[dim_report.error_message] if dim_report.error_message else [
                "Dimensional consistency check failed."
            ],
            graph_updated=False,
        )

    checker_name = proposal.target_checker
    if checker_name == "sympy":
        checker = SymPyChecker()
    elif checker_name == "lean4":
        checker = LeanChecker()
    elif checker_name == "numerical":
        checker = NumericalChecker()
    elif checker_name == "statistical":
        checker = StatisticalChecker()
    elif checker_name == "tensor":
        checker = TensorChecker()
    else:
        return ProposalExecutionResult(
            success=False,
            proposal_id=proposal.proposal_id,
            edge_id=edge_id,
            errors=[f"Unsupported verification backend '{checker_name}'."]
        )

    verif_report = checker.verify_edge(edge, working_graph)

    # Update output nodes status to match edge verification outcome
    for out_id in out_node_ids:
        node = working_graph.get_node(out_id)
        if node:
            node.status = verif_report.status

    report_data = {
        "checker": checker.name,
        "passed": verif_report.passed,
        "status": verif_report.status.value,
        "execution_time_ms": verif_report.execution_time_ms,
        "details": verif_report.details,
        "error_message": verif_report.error_message,
        "dimension_check": dim_report.to_dict()
    }

    graph_updated = False
    if verif_report.passed and not dry_run:
        # Commit only the newly verified candidate objects.
        for out_id in out_node_ids:
            graph.nodes[out_id] = copy.deepcopy(working_graph.nodes[out_id])
        graph.edges[edge_id] = copy.deepcopy(working_graph.edges[edge_id])
        for asm_data in proposal.proposed_assumptions:
            asm_id = asm_data.get("id")
            if asm_id and asm_id in working_graph.assumptions:
                graph.assumptions[asm_id] = copy.deepcopy(working_graph.assumptions[asm_id])
        graph_updated = True

    return ProposalExecutionResult(
        success=verif_report.passed,
        proposal_id=proposal.proposal_id,
        edge_id=edge_id,
        status=verif_report.status,
        report=report_data,
        errors=[verif_report.error_message] if verif_report.error_message else [],
        graph_updated=graph_updated
    )
