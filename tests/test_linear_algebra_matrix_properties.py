"""Phase 1A acceptance campaign for symmetric and Hermitian matrices."""

from automate.backend.linear_algebra_backend import LinearAlgebraChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def _check(rule, matrix, output):
    graph = DerivationGraph(id=f"matrix_property_{rule}")
    graph.add_node(DerivationNode(
        id="in",
        expression=MathematicalExpression(raw_str=matrix),
    ))
    graph.add_node(DerivationNode(
        id="out",
        expression=MathematicalExpression(raw_str=output),
    ))
    graph.add_edge(DerivationEdge(
        id="edge",
        input_nodes=["in"],
        output_nodes=["out"],
        transformation_rule=rule,
        justification="Phase 1A matrix-property acceptance",
        checker="linear_algebra",
    ))
    return LinearAlgebraChecker().verify_edge(graph.edges["edge"], graph)


def test_symmetric_matrix():
    report = _check("matrix_symmetric", "Matrix([[2, 3], [3, 5]])", "1")
    assert report.passed
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED
    assert report.details["numpy_cross_check"]["independence_class"] == "DIFFERENT_ENGINE"


def test_non_symmetric_matrix():
    report = _check("matrix_symmetric", "Matrix([[2, 3], [4, 5]])", "0")
    assert report.passed


def test_hermitian_complex_matrix():
    report = _check(
        "matrix_hermitian",
        "Matrix([[2, 1 + I], [1 - I, 3]])",
        "1",
    )
    assert report.passed
    assert report.status == VerificationStatus.SYMBOLIC_CHECKED
    assert report.details["numpy_cross_check"]["independence_class"] == "DIFFERENT_ENGINE"


def test_non_hermitian_complex_matrix():
    report = _check(
        "matrix_hermitian",
        "Matrix([[2, 1 + I], [1 + I, 3]])",
        "0",
    )
    assert report.passed


def test_symmetric_and_hermitian_are_distinct():
    symmetric = _check(
        "matrix_symmetric",
        "Matrix([[2, 1 + I], [1 + I, 3]])",
        "1",
    )
    hermitian = _check(
        "matrix_hermitian",
        "Matrix([[2, 1 + I], [1 + I, 3]])",
        "0",
    )
    assert symmetric.passed and hermitian.passed


def test_symbolic_hermitian_claim_fails_closed_without_assumptions():
    report = _check(
        "matrix_hermitian",
        "Matrix([[a, b], [conjugate(b), a]])",
        "1",
    )
    assert not report.passed
    assert report.status == VerificationStatus.UNVERIFIED


def test_wrong_indicator_rejected():
    report = _check("matrix_symmetric", "Matrix([[1, 2], [2, 1]])", "0")
    assert not report.passed


def test_non_square_matrix_rejected():
    report = _check("matrix_hermitian", "Matrix([[1, 0, 0], [0, 1, 0]])", "1")
    assert not report.passed
