"""Phase 1A acceptance campaign for positive-definite matrices."""

from automate.backend.linear_algebra_backend import LinearAlgebraChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def _check(matrix, output):
    graph = DerivationGraph(id="positive_definite")
    graph.add_node(DerivationNode(id="in", expression=MathematicalExpression(raw_str=matrix)))
    graph.add_node(DerivationNode(id="out", expression=MathematicalExpression(raw_str=output)))
    graph.add_edge(DerivationEdge(
        id="edge", input_nodes=["in"], output_nodes=["out"],
        transformation_rule="matrix_positive_definite",
        justification="Phase 1A positive-definite acceptance",
        checker="linear_algebra",
    ))
    return LinearAlgebraChecker().verify_edge(graph.edges["edge"], graph)


def test_positive_definite_real_matrix():
    report = _check("Matrix([[2, 1], [1, 2]])", "1")
    assert report.passed
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED
    assert report.details["numpy_cross_check"]["independence_class"] == "DIFFERENT_ENGINE"


def test_positive_definite_complex_hermitian_matrix():
    report = _check("Matrix([[2, 1 + I], [1 - I, 3]])", "1")
    assert report.passed


def test_indefinite_symmetric_matrix():
    report = _check("Matrix([[1, 2], [2, 1]])", "0")
    assert report.passed


def test_negative_definite_matrix_is_not_positive_definite():
    report = _check("Matrix([[-2, 0], [0, -1]])", "0")
    assert report.passed


def test_non_hermitian_matrix_rejected_as_not_positive_definite():
    report = _check("Matrix([[2, 3], [0, 2]])", "0")
    assert report.passed


def test_symbolic_positive_definiteness_fails_closed_without_assumptions():
    report = _check("Matrix([[a, 0], [0, b]])", "1")
    assert not report.passed
    assert report.status == VerificationStatus.UNVERIFIED


def test_wrong_positive_definite_indicator_rejected():
    report = _check("Matrix([[2, 1], [1, 2]])", "0")
    assert not report.passed


def test_non_square_matrix_rejected():
    report = _check("Matrix([[1, 0, 0], [0, 1, 0]])", "1")
    assert not report.passed
