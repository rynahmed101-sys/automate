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
    Core Automate AI verification pipeline.

    Transactional semantics:
    - ALL mutations happen on a working clone of the canonical graph.
    - The canonical graph is NEVER touched before verification succeeds.
    - On success AND dry_run=False: clone state is merged back.
    - On failure or dry_run=True: canonical graph is byte-identical to input.

    Steps:
    1.  Validate proposal schema and security constraints.
    2.  Validate target_checker against rule capabilities.
    3.  Build candidate state on a DEEP COPY of the canonical graph.
    4.  Run dimensional check (on clone).
    5.  Run semantic verification backend (on clone).
    6.  On success + not dry_run: commit clone to canonical graph.
    7.  On failure: discard clone; canonical graph unchanged.
    """
    reg = rule_registry or RuleRegistry()

    # 1. Validate proposal schema and security
    val_res = validate_ai_proposal(proposal.model_dump(), graph, reg)
    if not val_res.is_valid:
        return ProposalExecutionResult(
            success=False,
            proposal_id=proposal.proposal_id,
            errors=val_res.errors
        )

    # 2. Validate checker name against known checkers and rule capabilities
    _KNOWN_CHECKERS = {"sympy", "lean4", "numerical", "statistical", "dimension", "tensor"}
    checker_name = proposal.target_checker
    if checker_name not in _KNOWN_CHECKERS:
        return ProposalExecutionResult(
            success=False,
            proposal_id=proposal.proposal_id,
            errors=[
                f"Unknown checker '{checker_name}'. "
                f"Must be one of: {', '.join(sorted(_KNOWN_CHECKERS))}. "
                "No fallback to a different checker is permitted."
            ]
        )

    rule_def = reg.get(proposal.rule)
    if rule_def and checker_name not in rule_def.allowed_checkers:
        return ProposalExecutionResult(
            success=False,
            proposal_id=proposal.proposal_id,
            errors=[
                f"Incompatible target_checker '{checker_name}' for rule '{proposal.rule}'. "
                f"Allowed checkers: {', '.join(sorted(rule_def.allowed_checkers))}."
            ]
        )


    # 3. Build candidate state on a DEEP COPY — canonical graph is never touched
    #    until we have a verified result AND dry_run is False.
    working_graph = copy.deepcopy(graph)

    # Register proposed assumptions (on clone only)
    for asm_data in proposal.proposed_assumptions:
        asm_id = asm_data.get("id")
        if asm_id and asm_id not in working_graph.assumptions:
            working_graph.add_assumption(Assumption(
                id=asm_id,
                description=asm_data.get("description", asm_id),
                formal_predicate=asm_data.get("formal_predicate", asm_id),
                category=asm_data.get("category", "approximation")
            ))

    # Add proposed output nodes (on clone only)
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

    # 4. Create candidate edge (on clone)
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

    # 5. Dimensional check (on clone)
    dim_checker = DimensionChecker()
    dim_report = dim_checker.verify_edge(edge, working_graph)

    # 6. Semantic verification backend (on clone)
    if checker_name == "sympy":
        checker = SymPyChecker()
    elif checker_name == "lean4":
        checker = LeanChecker()
    elif checker_name == "numerical":
        checker = NumericalChecker()
    elif checker_name == "statistical":
        checker = StatisticalChecker()
    elif checker_name == "dimension":
        checker = DimensionChecker()
    elif checker_name == "tensor":
        checker = TensorChecker()
    else:
        # Already rejected above — this branch is unreachable
        raise AssertionError(f"Unreachable: unknown checker '{checker_name}'")



    verif_report = checker.verify_edge(edge, working_graph)

    # Update output node statuses on clone
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

    # 7. COMMIT: only merge clone → canonical graph on success AND not dry_run
    graph_updated = False
    if verif_report.passed and not dry_run:
        # Commit assumptions
        for asm_id, asm in working_graph.assumptions.items():
            if asm_id not in graph.assumptions:
                graph.add_assumption(asm)
        # Commit new nodes
        for nid in out_node_ids:
            node = working_graph.get_node(nid)
            if node and nid not in graph.nodes:
                graph.add_node(node)
        # Commit edge
        if edge_id not in graph.edges:
            graph.add_edge(edge)
        graph_updated = True
    # On failure or dry_run: canonical graph is unchanged (clone is discarded)

    return ProposalExecutionResult(
        success=verif_report.passed,
        proposal_id=proposal.proposal_id,
        edge_id=edge_id,
        status=verif_report.status,
        report=report_data,
        errors=[verif_report.error_message] if verif_report.error_message else [],
        graph_updated=graph_updated
    )

