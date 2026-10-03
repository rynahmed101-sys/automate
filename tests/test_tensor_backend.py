"""
Tests for the structural Einstein-index verification backend.
"""

import pytest

from automate.backend.tensor_backend import TensorChecker
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.edge import DerivationEdge
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression
from automate.ir.tensors import TensorIndex


def _tensor_edge(rule, **parameters):
    graph = DerivationGraph(id="tensor_test")
    graph.add_node(DerivationNode(
        id="input",
        expression=MathematicalExpression(raw_str="tensor"),
        node_kind="tensor",
        domain="differential_geometry",
    ))
    graph.add_node(DerivationNode(
        id="output",
        expression=MathematicalExpression(raw_str="tensor"),
        node_kind="tensor",
        domain="differential_geometry",
    ))
    edge = DerivationEdge(
        id=f"edge_{rule}",
        input_nodes=["input"],
        output_nodes=["output"],
        transformation_rule=rule,
        justification="Tensor semantics regression test",
        checker="tensor",
        parameters=parameters,
    )
    graph.add_edge(edge)
    return graph, edge


def test_tensor_valid_contraction():
    graph, edge = _tensor_edge(
        "index_contract",
        indices=[
            {"symbol": "mu", "position": "upper"},
            {"symbol": "mu", "position": "lower"},
        ],
    )

    report = TensorChecker().verify_edge(edge, graph)

    assert report.passed is True
    assert report.status == VerificationStatus.TENSOR_CHECKED
    assert report.details["resultant_rank"] == 0
    assert report.details["dummy_indices"] == ["mu"]


def test_tensor_rejects_same_variance_contraction():
    graph, edge = _tensor_edge(
        "index_contract",
        indices=[
            {"symbol": "mu", "position": "upper"},
            {"symbol": "mu", "position": "upper"},
        ],
    )

    report = TensorChecker().verify_edge(edge, graph)

    assert report.passed is False
    assert report.status == VerificationStatus.FAILED
    assert "Einstein summation" in (report.error_message or "")


def test_tensor_equation_rejects_reordered_free_indices():
    graph, edge = _tensor_edge(
        "tensor_equation",
        lhs_indices=[
            {"symbol": "mu", "position": "lower"},
            {"symbol": "nu", "position": "lower"},
        ],
        rhs_indices=[
            {"symbol": "nu", "position": "lower"},
            {"symbol": "mu", "position": "lower"},
        ],
    )

    report = TensorChecker().verify_edge(edge, graph)

    assert report.passed is False
    assert "Equation index mismatch" in (report.error_message or "")


def test_tensor_raise_index_changes_only_target():
    graph, edge = _tensor_edge(
        "raise_index",
        source_indices=[
            {"symbol": "mu", "position": "lower"},
            {"symbol": "nu", "position": "lower"},
        ],
        result_indices=[
            {"symbol": "mu", "position": "upper"},
            {"symbol": "nu", "position": "lower"},
        ],
        index="mu",
    )

    report = TensorChecker().verify_edge(edge, graph)

    assert report.passed is True
    assert report.status == VerificationStatus.TENSOR_CHECKED


def test_tensor_missing_graph_reference_is_rejected():
    graph = DerivationGraph(id="tensor_missing_ref")
    edge = DerivationEdge(
        id="edge_missing_ref",
        input_nodes=["does_not_exist"],
        output_nodes=["also_missing"],
        transformation_rule="index_contract",
        justification="Missing references",
        checker="tensor",
        parameters={"indices": [
            {"symbol": "mu", "position": "upper"},
            {"symbol": "mu", "position": "lower"},
        ]},
    )

    report = TensorChecker().verify_edge(edge, graph)

    assert report.passed is False
    assert "Referenced nodes missing" in (report.error_message or "")
