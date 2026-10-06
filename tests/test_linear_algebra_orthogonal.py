"""Acceptance tests for Stage 1A orthogonal matrix semantics."""

from automate.backend.linear_algebra_backend import LinearAlgebraChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def _check(matrix, output):
    graph = DerivationGraph(id="orthogonal_matrix_acceptance")
    graph.add_node(DerivationNode(id="matrix", expression=MathematicalExpression(raw_str=matrix)))
    graph.add_node(DerivationNode(id="out", expression=MathematicalExpression(raw_str=output)))
    graph.add_edge(DerivationEdge(
        id="edge", input_nodes=["matrix"], output_nodes=["out"],
        transformation_rule="matrix_orthogonal",
        justification="Stage 1A orthogonal matrix acceptance",
        checker="linear_algebra",
        parameters={},
    ))
    return LinearAlgebraChecker().verify_edge(graph.edges["edge"], graph)


def test_rotation_matrix_is_orthogonal():
    report = _check("Matrix([[0, -1], [1, 0]])", "1")
    assert report.passed
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED
    assert report.details["numpy_cross_check"]["passed"] is True


def test_reflection_matrix_is_orthogonal():
    report = _check("Matrix([[1, 0], [0, -1]])", "1")
    assert report.passed


def test_nonorthogonal_matrix_rejected():
    report = _check("Matrix([[1, 1], [0, 1]])", "1")
    assert not report.passed
    assert report.status == VerificationStatus.FAILED


def test_complex_matrix_is_not_orthogonal():
    report = _check("Matrix([[I, 0], [0, 1]])", "1")
    assert not report.passed
    assert report.status == VerificationStatus.FAILED


def test_symbolic_reality_boundary_fails_closed():
    report = _check("Matrix([[a, 0], [0, 1]])", "1")
    assert report.status == VerificationStatus.UNVERIFIED
    assert not report.passed


def test_rectangular_matrix_rejected():
    report = _check("Matrix([[1, 0, 0], [0, 1, 0]])", "1")
    assert not report.passed
    assert "square" in (report.error_message or "").lower()


def test_wrong_indicator_rejected():
    report = _check("Matrix([[1, 0], [0, 1]])", "0")
    assert not report.passed
    assert report.status == VerificationStatus.FAILED


def test_registry_exposes_orthogonal_rule():
    from automate.theory.rules import RuleRegistry
    assert "matrix_orthogonal" in set(RuleRegistry().list_rule_ids())
