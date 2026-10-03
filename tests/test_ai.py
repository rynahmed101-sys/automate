"""
Tests for Universal AI Subsystem: Mock Provider, Security Validation,
Mathematical Context Generation, and the AI Verification Loop.
"""

import pytest

from automate.ai.providers.mock import MockLLMProvider
from automate.ai.schemas import DerivationProposal, CandidateNode, ProposalOrigin
from automate.ai.validation import validate_ai_proposal, ProposalValidationResult
from automate.ai.context import build_ai_context, compute_semantic_graph_hash
from automate.ai.proposals import apply_and_verify_proposal
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.edge import DerivationEdge
from automate.ir.ast import MathematicalExpression
from automate.ir.assumptions import Assumption
from automate.core.status import VerificationStatus
from automate.theory.rules import RuleRegistry


def _create_sample_graph():
    graph = DerivationGraph(id="sho_graph", name="Harmonic Oscillator")
    graph.add_assumption(Assumption(
        id="asm_pos_mass",
        description="Mass is positive",
        formal_predicate="m > 0",
        active=True
    ))
    graph.add_assumption(Assumption(
        id="asm_pos_k",
        description="Spring constant is positive",
        formal_predicate="k > 0",
        active=True
    ))
    n1 = DerivationNode(
        id="node_eom",
        expression=MathematicalExpression(raw_str="m * diff(x(t), t, 2) + k * x(t) = 0", dimension="M*L*T^-2"),
        domain="classical_mechanics",
        status=VerificationStatus.SYMBOLIC_CHECKED
    )
    graph.add_node(n1)
    return graph


def test_mock_llm_provider():
    provider = MockLLMProvider(model_name="test-mock-v1")
    assert provider.name == "mock"
    assert provider.is_available() is True

    context = {"nodes": [{"id": "node_eom"}], "graph_hash": "abc123hash"}
    proposal_dict = provider.propose(context, request="Solve the equation of motion")

    assert proposal_dict["proposal_type"] == "derivation"
    assert proposal_dict["input_nodes"] == ["node_eom"]
    assert len(proposal_dict["output_nodes"]) == 1
    assert proposal_dict["rule"] == "solve_harmonic_oscillator"
    assert proposal_dict["origin"]["provider"] == "mock"
    assert proposal_dict["origin"]["context_hash"] == "abc123hash"


def test_semantic_graph_hashing_and_context():
    graph = _create_sample_graph()
    hash1 = compute_semantic_graph_hash(graph)
    hash2 = compute_semantic_graph_hash(graph)
    assert hash1 == hash2

    # Changing non-structural description does not alter hash
    graph.description = "Updated description text"
    assert compute_semantic_graph_hash(graph) == hash1

    # Changing mathematical expression alters hash
    graph.nodes["node_eom"].expression.raw_str = "m * diff(x(t), t, 2) + 2 * k * x(t) = 0"
    hash3 = compute_semantic_graph_hash(graph)
    assert hash3 != hash1

    # AI context builder
    context = build_ai_context(graph)
    assert context.theory_id == "sho_graph"
    assert context.graph_hash == hash3
    assert len(context.nodes) == 1
    assert len(context.available_rules) > 0


def test_security_validation_rejections():
    graph = _create_sample_graph()

    # 1. Reject eval() / arbitrary execution pattern
    malicious_eval = {
        "proposal_id": "bad1",
        "proposal_type": "derivation",
        "input_nodes": ["node_eom"],
        "output_nodes": [{"id": "bad_node", "expression": "eval('__import__(\"os\").system(\"calc\")')"}],
        "rule": "algebraic_identity",
        "origin": {"type": "ai"}
    }
    res_eval = validate_ai_proposal(malicious_eval, graph)
    assert res_eval.is_valid is False
    assert any("Security violation" in e for e in res_eval.errors)

    # 2. Reject exec()
    malicious_exec = {
        "proposal_id": "bad2",
        "proposal_type": "derivation",
        "input_nodes": ["node_eom"],
        "output_nodes": [{"id": "bad_node", "expression": "exec('import os')"}],
        "rule": "algebraic_identity",
        "origin": {"type": "ai"}
    }
    res_exec = validate_ai_proposal(malicious_exec, graph)
    assert res_exec.is_valid is False
    assert any("Security violation" in e for e in res_exec.errors)

    # 3. Reject powershell / shell injection
    malicious_shell = {
        "proposal_id": "bad3",
        "proposal_type": "derivation",
        "input_nodes": ["node_eom"],
        "output_nodes": [{"id": "bad_node", "expression": "x = 1; powershell -Command rm -rf /"}],
        "rule": "algebraic_identity",
        "origin": {"type": "ai"}
    }
    res_shell = validate_ai_proposal(malicious_shell, graph)
    assert res_shell.is_valid is False
    assert any("powershell" in e or "Security violation" in e for e in res_shell.errors)

    # 4. Reject path traversal
    malicious_path = {
        "proposal_id": "bad4",
        "proposal_type": "derivation",
        "input_nodes": ["node_eom"],
        "output_nodes": [{"id": "bad_node", "expression": "../../etc/passwd"}],
        "rule": "algebraic_identity",
        "origin": {"type": "ai"}
    }
    res_path = validate_ai_proposal(malicious_path, graph)
    assert res_path.is_valid is False
    assert any("Security violation" in e for e in res_path.errors)

    # 5. Reject self-assigned FORMALLY_PROVED
    malicious_status = {
        "proposal_id": "bad5",
        "proposal_type": "derivation",
        "input_nodes": ["node_eom"],
        "output_nodes": [{"id": "bad_node", "expression": "x(t) = A*cos(omega*t)"}],
        "rule": "solve_harmonic_oscillator",
        "status": "FORMALLY_PROVED",
        "origin": {"type": "ai"}
    }
    res_status = validate_ai_proposal(malicious_status, graph)
    assert res_status.is_valid is False
    assert any("cannot self-assign status" in e for e in res_status.errors)

    # 6. Reject missing input node in graph
    missing_input = {
        "proposal_id": "bad6",
        "proposal_type": "derivation",
        "input_nodes": ["non_existent_node"],
        "output_nodes": [{"id": "bad_node", "expression": "x = 1"}],
        "rule": "algebraic_identity",
        "justification": "Test simplification",
        "origin": {"type": "ai"}
    }
    res_missing = validate_ai_proposal(missing_input, graph)
    assert res_missing.is_valid is False
    assert any("does not exist" in e for e in res_missing.errors)


def test_apply_and_verify_proposal_pipeline():
    graph = _create_sample_graph()
    provider = MockLLMProvider()
    context = build_ai_context(graph).to_dict()

    raw_proposal = provider.propose(context, request="Solve harmonic oscillator")
    proposal = DerivationProposal(**raw_proposal)

    # Test dry run first
    dry_result = apply_and_verify_proposal(proposal, graph, dry_run=True)
    assert dry_result.success is True, dry_result.errors
    # Original graph must not be mutated in dry run
    assert "node_ai_solution" not in graph.nodes
    assert len(graph.edges) == 0

    # Real run
    real_result = apply_and_verify_proposal(proposal, graph, dry_run=False)
    assert real_result.success is True, real_result.errors
    assert real_result.graph_updated is True
    assert "node_ai_solution" in graph.nodes
    assert len(graph.edges) == 1

    # Edge status check
    edge = list(graph.edges.values())[0]
    assert edge.checker == "sympy"
    assert edge.status in (VerificationStatus.SYMBOLIC_CHECKED, VerificationStatus.AI_PROPOSED)
    assert edge.metadata["origin"]["provider"] == "mock"


def test_security_validation_rejects_unknown_checker():
    graph = _create_sample_graph()
    raw = {
        "proposal_id": "bad_checker",
        "proposal_type": "derivation",
        "input_nodes": ["node_eom"],
        "output_nodes": [{"id": "bad_node", "expression": "x = 1"}],
        "rule": "algebraic_identity",
        "justification": "Unknown backend test",
        "target_checker": "mystery_backend",
        "origin": {"type": "ai"},
    }
    result = validate_ai_proposal(raw, graph)
    assert result.is_valid is False
    assert any("Unknown verification backend" in e for e in result.errors)


def test_ai_context_exposes_rule_capabilities():
    graph = _create_sample_graph()
    context = build_ai_context(graph)
    divide_rule = next(
        r for r in context.available_rules if r["rule_id"] == "divide_both_sides"
    )
    assert divide_rule["symbolic_checker_available"] is True
    assert divide_rule["formal_proof_available"] is False


def test_tensor_backend_is_exposed_to_ai_context_and_pipeline():
    from automate.ai.schemas import DerivationProposal, CandidateNode, ProposalOrigin

    graph = DerivationGraph(id="tensor_ai_graph", name="Tensor Test")
    graph.add_node(DerivationNode(
        id="tensor_input",
        expression=MathematicalExpression(raw_str="T"),
        node_kind="tensor",
        domain="differential_geometry",
    ))

    proposal = DerivationProposal(
        proposal_id="tensor_proposal",
        proposal_type="derivation",
        input_nodes=["tensor_input"],
        output_nodes=[CandidateNode(
            id="tensor_output",
            expression="T^mu_nu",
            dimension="",
            node_kind="tensor",
            domain="differential_geometry",
        )],
        rule="index_contract",
        justification="Contract an upper and lower index",
        target_checker="tensor",
        parameters={
            "indices": [
                {"symbol": "mu", "position": "upper"},
                {"symbol": "mu", "position": "lower"},
            ]
        },
        origin=ProposalOrigin(
            type="ai",
            provider="test",
            model="tensor-test",
        ),
    )

    result = apply_and_verify_proposal(proposal, graph, dry_run=False)

    assert result.success is True, result.errors
    assert result.graph_updated is True
    assert graph.get_edge(result.edge_id).status == VerificationStatus.TENSOR_CHECKED
    assert "tensor_output" in graph.nodes


def test_failed_ai_proposal_does_not_mutate_canonical_graph():
    from automate.ai.schemas import DerivationProposal, CandidateNode, ProposalOrigin

    graph = DerivationGraph(id="transaction_graph", name="Transactional Test")
    graph.add_assumption(Assumption(
        id="asm_pos_mass",
        description="Mass is positive",
        formal_predicate="m > 0",
        active=True,
    ))
    graph.add_assumption(Assumption(
        id="asm_pos_k",
        description="Spring constant is positive",
        formal_predicate="k > 0",
        active=True,
    ))
    graph.add_node(DerivationNode(
        id="eom",
        expression=MathematicalExpression(
            raw_str="m * diff(x(t), t, 2) + k * x(t) = 0",
            dimension="M*L*T^-2",
        ),
        domain="classical_mechanics",
    ))

    proposal = DerivationProposal(
        proposal_id="bad_transaction",
        proposal_type="derivation",
        input_nodes=["eom"],
        output_nodes=[CandidateNode(
            id="bad_solution",
            expression="x(t) = A * cos(3 * t + phi)",
            dimension="L",
            node_kind="equation",
            domain="classical_mechanics",
        )],
        rule="solve_harmonic_oscillator",
        justification="Intentionally wrong frequency",
        side_conditions=["asm_pos_mass", "asm_pos_k"],
        target_checker="sympy",
        parameters={},
        origin=ProposalOrigin(
            type="ai",
            provider="test",
            model="transaction-test",
        ),
    )

    result = apply_and_verify_proposal(proposal, graph, dry_run=False)

    assert result.success is False
    assert result.graph_updated is False
    assert "bad_solution" not in graph.nodes
    assert result.edge_id not in graph.edges
