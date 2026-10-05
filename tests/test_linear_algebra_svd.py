"""Stage 1A SVD acceptance campaign."""

from automate.backend.linear_algebra_backend import LinearAlgebraChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression


def _check(matrix, u, sigma, vh):
    graph = DerivationGraph(id="linear_algebra_svd")
    for i, expression in enumerate([matrix, u, sigma, vh]):
        graph.add_node(DerivationNode(id=f"node_{i}", expression=MathematicalExpression(raw_str=expression)))
    graph.add_edge(DerivationEdge(
        id="edge", input_nodes=["node_0"], output_nodes=["node_1", "node_2", "node_3"],
        transformation_rule="matrix_svd", justification="Stage 1A SVD acceptance", checker="linear_algebra",
    ))
    return LinearAlgebraChecker().verify_edge(graph.edges["edge"], graph)


def test_square_svd():
    report = _check("Matrix([[3, 0], [0, 2]])", "Matrix([[1, 0], [0, 1]])", "Matrix([[3, 0], [0, 2]])", "Matrix([[1, 0], [0, 1]])")
    assert report.passed and report.status == VerificationStatus.SYMBOLIC_CHECKED
    assert report.details["numpy_cross_check"]["independence_class"] == "DIFFERENT_ENGINE"


def test_tall_rectangular_svd():
    report = _check("Matrix([[3, 0], [0, 2], [0, 0]])", "Matrix([[1, 0], [0, 1], [0, 0]])", "Matrix([[3, 0], [0, 2]])", "Matrix([[1, 0], [0, 1]])")
    assert report.passed
    assert report.details["output_shapes"] == [[3, 2], [2, 2], [2, 2]]


def test_wide_rectangular_svd():
    report = _check("Matrix([[3, 0, 0], [0, 2, 0]])", "Matrix([[1, 0], [0, 1]])", "Matrix([[3, 0], [0, 2]])", "Matrix([[1, 0, 0], [0, 1, 0]])")
    assert report.passed
    assert report.details["output_shapes"] == [[2, 2], [2, 2], [2, 3]]


def test_rank_deficient_and_zero_singular_value():
    report = _check("Matrix([[3, 0, 0], [0, 0, 0]])", "Matrix([[1, 0], [0, 1]])", "Matrix([[3, 0], [0, 0]])", "Matrix([[1, 0, 0], [0, 1, 0]])")
    assert report.passed
    assert report.details["singular_values"] == ["3", "0"]


def test_complex_svd_uses_conjugate_transpose():
    report = _check("Matrix([[3*I, 0], [0, 2]])", "Matrix([[I, 0], [0, 1]])", "Matrix([[3, 0], [0, 2]])", "Matrix([[1, 0], [0, 1]])")
    assert report.passed


def test_symbolic_uncertainty_fails_closed():
    report = _check("Matrix([[a, 0], [0, b]])", "Matrix([[1, 0], [0, 1]])", "Matrix([[a, 0], [0, b]])", "Matrix([[1, 0], [0, 1]])")
    assert not report.passed and report.status == VerificationStatus.UNVERIFIED


def test_adversarial_rejections():
    negative = _check("Matrix([[3, 0], [0, 2]])", "Matrix([[1, 0], [0, 1]])", "Matrix([[-3, 0], [0, 2]])", "Matrix([[-1, 0], [0, 1]])")
    assert not negative.passed and negative.status == VerificationStatus.FAILED
    wrong_order = _check("Matrix([[3, 0], [0, 2]])", "Matrix([[1, 0], [0, 1]])", "Matrix([[2, 0], [0, 3]])", "Matrix([[0, 1], [1, 0]])")
    assert not wrong_order.passed
    wrong_shape = _check("Matrix([[3, 0, 0], [0, 2, 0]])", "Matrix([[1, 0], [0, 1], [0, 0]])", "Matrix([[3, 0], [0, 2]])", "Matrix([[1, 0, 0], [0, 1, 0]])")
    assert not wrong_shape.passed


def test_registry_exposes_svd():
    from automate.theory.rules import RuleRegistry
    rule = RuleRegistry().get("matrix_svd")
    assert rule is not None
    assert rule.implementation_backend == "linear_algebra"
    assert rule.allowed_checkers == ["linear_algebra"]
